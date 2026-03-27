import pytest
from code_tutorial_builder.parser import CodeParser
from code_tutorial_builder.config import Config

class TestCodeParser:
    """Tests for CodeParser class."""
    
    def setup_method(self):
        self.config = Config(steps=5)
        self.parser = CodeParser(self.config)
    
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        code = """def hello():
    print('Hello, world!')
"""
        result = self.parser.parse(code)
        assert len(result['functions']) == 1
        assert result['functions'][0]['name'] == 'hello'
        assert 'print' in result['functions'][0]['body']
    
    def test_parse_class(self):
        """Test parsing a class."""
        code = """class MyClass:
    def __init__(self):
        self.x = 5
    
    def method(self):
        return self.x
"""
        result = self.parser.parse(code)
        assert len(result['classes']) == 1
        assert result['classes'][0]['name'] == 'MyClass'
        assert len(result['classes'][0]['methods']) == 2
    
    def test_parse_imports(self):
        """Test parsing imports."""
        code = """import os
from sys import argv
"""
        result = self.parser.parse(code)
        assert len(result['imports']) == 2
        assert 'os' in result['imports'][0]
        assert 'argv' in result['imports'][1]
    
    def test_parse_invalid_syntax(self):
        """Test that invalid syntax raises ValueError."""
        code = "def broken(:"
        with pytest.raises(ValueError):
            self.parser.parse(code)