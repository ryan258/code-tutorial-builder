import pytest
from code_tutorial_builder.parser import PythonParser


class TestPythonParser:
    """Tests for PythonParser class."""

    def setup_method(self):
        self.parser = PythonParser()

    def test_parse_simple_function(self):
        code = "def hello():\n    print('Hello, world!')\n"
        result = self.parser.parse(code)
        assert len(result['functions']) == 1
        assert result['functions'][0]['name'] == 'hello'
        assert 'print' in result['functions'][0]['body']

    def test_class_has_kind_field(self):
        code = (
            "class MyClass:\n"
            "    def method(self):\n"
            "        pass\n"
        )
        result = self.parser.parse(code)
        assert result['classes'][0]['kind'] == 'class'

    def test_parse_class(self):
        code = (
            "class MyClass:\n"
            "    def __init__(self):\n"
            "        self.x = 5\n"
            "\n"
            "    def method(self):\n"
            "        return self.x\n"
        )
        result = self.parser.parse(code)
        assert len(result['classes']) == 1
        assert result['classes'][0]['name'] == 'MyClass'
        assert len(result['classes'][0]['methods']) == 2

    def test_class_methods_not_in_functions(self):
        """Methods inside a class must NOT appear as top-level functions."""
        code = (
            "class Foo:\n"
            "    def bar(self):\n"
            "        pass\n"
        )
        result = self.parser.parse(code)
        assert len(result['functions']) == 0
        assert len(result['classes']) == 1

    def test_parse_imports(self):
        code = "import os\nfrom sys import argv\n"
        result = self.parser.parse(code)
        assert len(result['imports']) == 2
        assert 'os' in result['imports'][0]
        assert 'argv' in result['imports'][1]

    def test_imports_excluded_from_main_code(self):
        """Import lines must not leak into main_code."""
        code = "import os\n\nx = 1\n"
        result = self.parser.parse(code)
        assert 'import os' not in result['main_code']
        assert 'x = 1' in result['main_code']

    def test_parse_main_code(self):
        code = (
            "def foo():\n"
            "    pass\n"
            "\n"
            "x = foo()\n"
            "print(x)\n"
        )
        result = self.parser.parse(code)
        assert 'x = foo()' in result['main_code']
        assert 'print(x)' in result['main_code']
        assert 'def foo' not in result['main_code']

    def test_parse_invalid_syntax(self):
        with pytest.raises(ValueError):
            self.parser.parse("def broken(:")

    def test_parse_decorated_function(self):
        code = (
            "@decorator\n"
            "def decorated():\n"
            "    pass\n"
            "\n"
            "x = 1\n"
        )
        result = self.parser.parse(code)
        assert len(result['functions']) == 1
        # Decorator lines must not leak into main_code
        assert '@decorator' not in result['main_code']
        assert 'x = 1' in result['main_code']

    def test_docstring_extracted(self):
        code = 'def greet():\n    """Say hello."""\n    print("hi")\n'
        result = self.parser.parse(code)
        assert result['functions'][0]['docstring'] == 'Say hello.'

    def test_source_line_metadata(self):
        code = (
            "class Greeter:\n"
            "    pass\n"
            "\n"
            "def greet(name):\n"
            "    return name\n"
        )
        result = self.parser.parse(code)
        assert result["classes"][0]["source_line"] == 1
        assert result["functions"][0]["source_line"] == 4

    def test_language_field(self):
        result = self.parser.parse("x = 1\n")
        assert result['language'] == 'python'
