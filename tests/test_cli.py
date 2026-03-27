import subprocess
import sys

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
        assert "# Sample Tutorial" in content
        assert "\n## Big Idea\n" in content
        assert "\n## Warm-Up\n" in content
        assert "greet" in content
        assert "## What You'll Learn" in content
        assert "## Checks for Understanding" in content

    def test_cli_custom_title(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(output_file),
            '--title', 'Loops and Functions',
        ])

        assert result.exit_code == 0
        assert output_file.read_text().startswith("# Loops and Functions\n")

    def test_module_entrypoint_end_to_end(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_tutorial_builder",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert output_file.exists()
        assert output_file.read_text().startswith("# Sample Tutorial\n")

    def test_cli_input_not_found(self):
        result = self.runner.invoke(main, [
            '--input', 'nonexistent.py',
            '--output', 'out.md',
        ])
        assert result.exit_code == 1
        assert "nonexistent.py" in result.output

    def test_cli_output_dir_not_found(self, tmp_path):
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
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_cli_bad_template(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")
        bad_template = tmp_path / "bad.j2"
        bad_template.write_text("{% if %}")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--template', str(bad_template),
        ])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_cli_template_not_found(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--template', 'ghost.j2',
        ])
        assert result.exit_code == 1
        assert "ghost.j2" in result.output

    def test_cli_unknown_extension(self, tmp_path):
        input_file = tmp_path / "file.xyz"
        input_file.write_text("hello")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
        ])
        assert result.exit_code == 1
        assert "could not detect language" in result.output

    def test_cli_language_override(self, tmp_path):
        input_file = tmp_path / "code.txt"
        input_file.write_text("def greet():\n    pass\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(output_file),
            '--language', 'python',
        ])
        assert result.exit_code == 0
        assert "greet" in output_file.read_text()

    def test_cli_javascript_end_to_end(self, tmp_path):
        input_file = tmp_path / "app.js"
        input_file.write_text("function greet(name) {\n  console.log(name);\n}\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(output_file),
        ])
        assert result.exit_code == 0
        content = output_file.read_text()
        assert "greet" in content
        assert "```javascript" in content

    def test_cli_ai_requires_credentials(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(main, [
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--ai',
        ])

        assert result.exit_code == 1
        assert "OPENROUTER_API_KEY" in result.output
