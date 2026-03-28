import importlib
import json
import shlex
import subprocess
import sys

import pytest
from click.testing import CliRunner
from code_tutorial_builder.__main__ import cli


_has_tree_sitter = importlib.util.find_spec("tree_sitter_language_pack") is not None


class TestCLI:
    """Tests for CLI interface."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_cli_help(self):
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Convert working code into step-by-step lessons" in result.output

    def test_generate_missing_input(self):
        result = self.runner.invoke(cli, ['generate', '--output', 'out.md'])
        assert result.exit_code != 0

    def test_generate_missing_output(self):
        result = self.runner.invoke(cli, ['generate', '--input', 'example.py'])
        assert result.exit_code != 0

    def test_generate_end_to_end(self, tmp_path):
        """Full round-trip: write input, run CLI, verify output."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            'generate',
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

    def test_generate_custom_title(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            'generate',
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
                "generate",
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

    def test_generate_input_not_found(self):
        result = self.runner.invoke(cli, [
            'generate',
            '--input', 'nonexistent.py',
            '--output', 'out.md',
        ])
        assert result.exit_code == 1
        assert "nonexistent.py" in result.output

    def test_generate_output_dir_not_found(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")
        bad_output = tmp_path / "no-such-dir" / "tutorial.md"

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(bad_output),
        ])
        assert result.exit_code == 1
        assert "no-such-dir" in result.output

    def test_generate_output_is_directory(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_generate_bad_template(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")
        bad_template = tmp_path / "bad.j2"
        bad_template.write_text("{% if %}")

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--template', str(bad_template),
        ])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_generate_template_not_found(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--template', 'ghost.j2',
        ])
        assert result.exit_code == 1
        assert "ghost.j2" in result.output

    def test_generate_unknown_extension(self, tmp_path):
        input_file = tmp_path / "file.xyz"
        input_file.write_text("hello")

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
        ])
        assert result.exit_code == 1
        assert "could not detect language" in result.output

    def test_generate_language_override(self, tmp_path):
        input_file = tmp_path / "code.txt"
        input_file.write_text("def greet():\n    pass\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(output_file),
            '--language', 'python',
        ])
        assert result.exit_code == 0
        assert "greet" in output_file.read_text()

    @pytest.mark.skipif(not _has_tree_sitter, reason="tree-sitter not installed")
    def test_generate_javascript_end_to_end(self, tmp_path):
        input_file = tmp_path / "app.js"
        input_file.write_text("function greet(name) {\n  console.log(name);\n}\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(output_file),
        ])
        assert result.exit_code == 0
        content = output_file.read_text()
        assert "greet" in content
        assert "```javascript" in content

    def test_generate_ai_requires_credentials(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--ai',
        ])

        assert result.exit_code == 1
        assert "OPENROUTER_API_KEY" in result.output

    def test_generate_format_option(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "handout.md"

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(output_file),
            '--format', 'handout',
        ])
        assert result.exit_code == 0
        content = output_file.read_text()
        assert "## Building the Program" in content
        assert "## Teaching Tips" not in content

    def test_generate_format_invalid_rejected(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("x = 1\n")

        result = self.runner.invoke(cli, [
            'generate',
            '--input', str(input_file),
            '--output', str(tmp_path / "out.md"),
            '--format', 'invalid',
        ])
        assert result.exit_code != 0


class TestBackwardCompat:
    """Ensure the old CLI form (without subcommand) still works."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_old_form_without_subcommand(self, tmp_path):
        """``-i file -o out`` without ``generate`` must still work."""
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            '--input', str(input_file),
            '--output', str(output_file),
        ])
        assert result.exit_code == 0
        assert output_file.exists()
        assert "greet" in output_file.read_text()

    def test_old_form_short_flags(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            '-i', str(input_file),
            '-o', str(output_file),
        ])
        assert result.exit_code == 0
        assert output_file.exists()

    def test_old_form_with_all_options(self, tmp_path):
        input_file = tmp_path / "sample.py"
        input_file.write_text("def greet():\n    print('hi')\n")
        output_file = tmp_path / "tutorial.md"

        result = self.runner.invoke(cli, [
            '-i', str(input_file),
            '-o', str(output_file),
            '--title', 'Old Style',
            '-v',
        ])
        assert result.exit_code == 0
        assert "# Old Style" in output_file.read_text()

    def test_unknown_subcommand_still_errors_normally(self):
        result = self.runner.invoke(cli, ['scna'])
        assert result.exit_code != 0
        assert "No such command 'scna'" in result.output


class TestScanCLI:
    """Tests for the scan subcommand."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_scan_help(self):
        result = self.runner.invoke(cli, ['scan', '--help'])
        assert result.exit_code == 0
        assert "Scan a project directory" in result.output

    def test_scan_project_directory(self, tmp_path):
        # Create a small project
        (tmp_path / "calc.py").write_text(
            "def add(a, b):\n    return a + b\n\n"
            "def multiply(a, b):\n    result = 0\n    for _ in range(b):\n"
            "        result = add(result, a)\n    return result\n"
        )
        (tmp_path / "greet.py").write_text(
            "def greet(name):\n    print(name)\n"
        )

        result = self.runner.invoke(cli, ['scan', str(tmp_path)])
        assert result.exit_code == 0
        assert "Scanned" in result.output
        assert "learning opportunities" in result.output

    def test_scan_json_output(self, tmp_path):
        (tmp_path / "example.py").write_text(
            "def hello():\n    print('hi')\n"
        )

        result = self.runner.invoke(cli, ['scan', str(tmp_path), '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "opportunities" in data
        assert data["files_scanned"] >= 1

    def test_scan_empty_directory(self, tmp_path):
        result = self.runner.invoke(cli, ['scan', str(tmp_path)])
        assert result.exit_code == 0
        assert "No learning opportunities found" in result.output

    def test_scan_nonexistent_directory(self):
        result = self.runner.invoke(cli, ['scan', '/nonexistent/path'])
        assert result.exit_code == 1
        assert "Not a directory" in result.output

    def test_scan_max_opportunities(self, tmp_path):
        for i in range(5):
            (tmp_path / f"mod{i}.py").write_text(
                f"def func{i}():\n    return {i}\n"
            )

        result = self.runner.invoke(cli, [
            'scan', str(tmp_path), '--max', '2', '--json',
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["opportunities"]) <= 2

    def test_scan_skips_venv(self, tmp_path):
        # File in venv should be skipped
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "hidden.py").write_text("def secret():\n    pass\n")

        # File at root should be found
        (tmp_path / "visible.py").write_text("def hello():\n    pass\n")

        result = self.runner.invoke(cli, ['scan', str(tmp_path), '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["files_scanned"] == 1
        assert all("venv" not in o["file_path"] for o in data["opportunities"])

    def test_scan_verbose(self, tmp_path):
        (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
        result = self.runner.invoke(cli, ['scan', str(tmp_path), '-v'])
        assert result.exit_code == 0
        assert "Scanning" in result.output

    def test_scan_json_output_with_verbose_stays_valid_json(self, tmp_path):
        (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "code_tutorial_builder",
                "scan",
                str(tmp_path),
                "--json",
                "-v",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["files_scanned"] == 1

    def test_scan_generate_suggestion_quotes_absolute_path(self, tmp_path):
        scan_root = tmp_path / "my project"
        scan_root.mkdir()
        source_file = scan_root / "file name.py"
        source_file.write_text("def f():\n    return 1\n")

        result = self.runner.invoke(cli, ['scan', str(scan_root)])
        assert result.exit_code == 0
        expected = shlex.quote(str(source_file.resolve()))
        assert expected in result.output

    def test_scan_skips_symlinked_directories(self, tmp_path):
        # Real directory with a file
        real = tmp_path / "real"
        real.mkdir()
        (real / "mod.py").write_text("def f():\n    return 1\n")

        # Symlink pointing to real
        link = tmp_path / "linked"
        link.symlink_to(real)

        result = self.runner.invoke(cli, ['scan', str(tmp_path), '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # Only the real file should be scanned, not the symlinked copy
        assert data["files_scanned"] == 1

    def test_scan_handles_symlink_loop(self, tmp_path):
        """A directory symlink loop must not cause infinite recursion."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "mod.py").write_text("def f():\n    return 1\n")
        # Create a loop: sub/loop -> tmp_path
        (sub / "loop").symlink_to(tmp_path)

        result = self.runner.invoke(cli, ['scan', str(tmp_path), '--json'])
        assert result.exit_code == 0
