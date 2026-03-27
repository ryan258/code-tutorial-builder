import ast
from typing import List, Dict, Any

from .languages._base import ParseResult


class PythonParser:
    """Parse Python code into structured components."""

    def parse(self, code: str) -> ParseResult:
        """
        Parse Python code into components.

        Returns:
            Dict containing:
                - functions: List of function definitions
                - classes: List of class definitions
                - imports: List of import statements
                - main_code: Code outside functions/classes/imports
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")

        lines = code.split('\n')
        functions = []
        classes = []
        imports = []

        # Track line ranges occupied by functions, classes, and imports
        # so we can extract main_code as everything else.
        occupied = set()

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(self._parse_function(node, lines))
                self._mark_occupied(node, occupied)
            elif isinstance(node, ast.ClassDef):
                classes.append(self._parse_class(node, lines))
                self._mark_occupied(node, occupied)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(self._extract_source(node, lines))
                self._mark_occupied(node, occupied)

        # Main code is every non-empty, non-comment line not inside a
        # function, class, or import statement.
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
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mark_occupied(node: ast.AST, occupied: set) -> None:
        """Mark the line range of *node* (including decorators) as occupied."""
        start = node.lineno - 1
        # Decorators sit above the def/class line
        if hasattr(node, 'decorator_list') and node.decorator_list:
            start = node.decorator_list[0].lineno - 1
        end = node.end_lineno  # end_lineno is 1-based inclusive
        for line_no in range(start, end):
            occupied.add(line_no)

    @staticmethod
    def _extract_source(node: ast.AST, lines: List[str]) -> str:
        """Extract the source text for an AST node."""
        return '\n'.join(lines[node.lineno - 1 : node.end_lineno])

    def _parse_function(self, node: ast.FunctionDef, lines: List[str]) -> Dict[str, Any]:
        """Parse a function definition node."""
        return {
            'name': node.name,
            'body': self._extract_source(node, lines),
            'args': [arg.arg for arg in node.args.args],
            'docstring': ast.get_docstring(node),
            'source_line': node.lineno,
        }

    def _parse_class(self, node: ast.ClassDef, lines: List[str]) -> Dict[str, Any]:
        """Parse a class definition node."""
        methods = [
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return {
            'name': node.name,
            'body': self._extract_source(node, lines),
            'methods': methods,
            'docstring': ast.get_docstring(node),
            'kind': 'class',
            'source_line': node.lineno,
        }
