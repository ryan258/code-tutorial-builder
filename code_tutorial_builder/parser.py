import ast
import re
from typing import List, Dict, Any
from .config import Config

class CodeParser:
    """Parse Python code into structured components."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def parse(self, code: str) -> Dict[str, Any]:
        """
        Parse Python code into components.
        
        Returns:
            Dict containing:
                - functions: List of function definitions
                - classes: List of class definitions
                - imports: List of import statements
                - main_code: Code outside functions/classes
                - comments: Extracted comments
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        
        functions = []
        classes = []
        imports = []
        main_code = []
        comments = self._extract_comments(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(self._parse_function(node, code))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._parse_class(node, code))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(self._extract_import_statement(node, code))
        
        # Extract main code (code outside functions and classes)
        lines = code.split('\n')
        in_block = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('class '):
                in_block = True
            elif in_block and (stripped == '' or stripped.startswith(' ') or stripped.startswith('\t')):
                continue
            else:
                in_block = False
                if stripped and not stripped.startswith('#'):
                    main_code.append(line)
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'main_code': '\n'.join(main_code),
            'comments': comments
        }
    
    def _parse_function(self, node: ast.FunctionDef, code: str) -> Dict[str, Any]:
        """Parse a function definition node."""
        lines = code.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        body_lines = lines[start_line:end_line]
        
        return {
            'name': node.name,
            'body': '\n'.join(body_lines),
            'args': [arg.arg for arg in node.args.args],
            'docstring': ast.get_docstring(node)
        }
    
    def _parse_class(self, node: ast.ClassDef, code: str) -> Dict[str, Any]:
        """Parse a class definition node."""
        lines = code.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        body_lines = lines[start_line:end_line]
        
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        
        return {
            'name': node.name,
            'body': '\n'.join(body_lines),
            'methods': methods,
            'docstring': ast.get_docstring(node)
        }
    
    def _extract_import_statement(self, node: ast.AST, code: str) -> str:
        """Extract import statement as string."""
        lines = code.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        return '\n'.join(lines[start_line:end_line])
    
    def _extract_comments(self, code: str) -> List[str]:
        """Extract comments from code."""
        comments = []
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                comments.append(line)
        return comments