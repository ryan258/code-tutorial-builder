import pytest
from click.testing import CliRunner
from code_tutorial_builder.__main__ import main


class TestCLI:
    """Tests for CLI interface."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_cli_help(self):
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "Convert working code into step-by-step lessons" in result.output

    def test_cli_missing_input(self):
        result = self.runner.invoke(main, ['--output', 'out.md'])
        assert result.exit_code != 0

    def test_cli_missing_output(self):
        result = self.runner.invoke(main, ['--input', 'example.py'])
        assert result.exit_code != 0

    def test_cli_end_to_end(self, tmp_path):
        """Full round-trip: write input, run CLI, verify output."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(output_file),
            '--verbose',
        ])
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "greet" in content

    def test_cli_input_not_found(self):
        result = self.runner.invoke(main, [
            '--input', 'nonexistent.py',
            '--output', 'out.md',
        ])
        assert result.exit_code == 1
        assert "nonexistent.py" in result.output

    def test_cli_output_dir_not_found(self, tmp_path):
        """Output path in a missing directory must report the real path."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")
        bad_output = tmp_path / "no-such-dir" / "tutorial.md"

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(bad_output),
        ])
        assert result.exit_code == 1
        assert "no-such-dir" in result.output

    def test_cli_output_is_directory(self, tmp_path):
        """Writing to a directory path must produce a clean error."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_cli_bad_template(self, tmp_path):
        """A malformed custom template must produce a clean error."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")
        bad_template = tmp_path / "bad.j2"
        bad_template.write_text("{% if %}")  # invalid Jinja2

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--template', str(bad_template),
        ])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_cli_template_not_found(self, tmp_path):
        """A missing custom template must report the template path."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--template', 'ghost.j2',
        ])
        assert result.exit_code == 1
        assert "ghost.j2" in result.output
