from __future__ import annotations

import ast
from typing import Any

from ._base import ParseResult


class PythonParser:
    """Parse Python code into structured components using the ast module."""

    def parse(self, code: str) -> ParseResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")

        lines = code.split('\n')
        functions: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []
        imports: list[str] = []
        occupied: set[int] = set()

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._parse_function(node, lines))
                self._mark_occupied(node, occupied)
            elif isinstance(node, ast.ClassDef):
                classes.append(self._parse_class(node, lines))
                self._mark_occupied(node, occupied)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(self._extract_source(node, lines))
                self._mark_occupied(node, occupied)
            elif self._is_docstring_expr(node):
                self._mark_occupied(node, occupied)

        main_lines = []
        for i, line in enumerate(lines):
            if i in occupied:
                continue
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
                main_lines.append(line)

        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'main_code': '\n'.join(main_lines),
            'language': 'python',
            'source': code,
        }

    @staticmethod
    def _mark_occupied(node: ast.stmt, occupied: set[int]) -> None:
        start = node.lineno - 1
        decorators = getattr(node, 'decorator_list', None)
        if decorators:
            start = decorators[0].lineno - 1
        end = node.end_lineno if node.end_lineno is not None else node.lineno
        for line_no in range(start, end):
            occupied.add(line_no)

    @staticmethod
    def _extract_source(node: ast.stmt, lines: list[str]) -> str:
        start = node.lineno
        decorators = getattr(node, 'decorator_list', None)
        if decorators:
            start = decorators[0].lineno
        return '\n'.join(lines[start - 1 : node.end_lineno])

    @staticmethod
    def _extract_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        a = node.args
        names: list[str] = [arg.arg for arg in getattr(a, 'posonlyargs', [])]
        names += [arg.arg for arg in a.args]
        if a.vararg is not None:
            names.append('*' + a.vararg.arg)
        names += [arg.arg for arg in a.kwonlyargs]
        if a.kwarg is not None:
            names.append('**' + a.kwarg.arg)
        return names

    @staticmethod
    def _is_docstring_expr(node: ast.stmt) -> bool:
        if not isinstance(node, ast.Expr):
            return False
        value = node.value
        return isinstance(value, ast.Constant) and isinstance(value.value, str)

    def _parse_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str]
    ) -> dict[str, Any]:
        return {
            'name': node.name,
            'body': self._extract_source(node, lines),
            'args': self._extract_args(node),
            'docstring': ast.get_docstring(node),
            'source_line': node.lineno,
        }

    def _parse_class(self, node: ast.ClassDef, lines: list[str]) -> dict[str, Any]:
        methods = [
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        method_details = [
            self._parse_function(item, lines)
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return {
            'name': node.name,
            'body': self._extract_source(node, lines),
            'methods': methods,
            'method_details': method_details,
            'docstring': ast.get_docstring(node),
            'kind': 'class',
            'source_line': node.lineno,
        }
