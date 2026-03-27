import pytest
from click.testing import CliRunner
from code_tutorial_builder.__main__ import main

class TestCLI:
    """Tests for CLI interface."""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help message."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "Convert working code into step-by-step lessons" in result.output
    
    def test_cli_missing_input(self):
        """Test CLI with missing input."""
        result = self.runner.invoke(main, ['--output', 'out.md'])
        assert result.exit_code != 0
    
    def test_cli_missing_output(self):
        """Test CLI with missing output."""
        result = self.runner.invoke(main, ['--input', 'example.py'])
        assert result.exit_code != 0