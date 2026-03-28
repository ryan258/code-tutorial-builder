import pytest
from code_tutorial_builder.generator import TutorialGenerator
from code_tutorial_builder.config import Config
from code_tutorial_builder.languages import PythonParser


class TestTutorialGenerator:
    """Tests for TutorialGenerator class."""

    def setup_method(self):
        self.config = Config(steps=5)
        self.generator = TutorialGenerator(self.config)
        self.parser = PythonParser()

    def test_generate_simple_tutorial(self):
        code = (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    else:\n"
            "        return n * factorial(n-1)\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed)
        assert "factorial" in tutorial
        assert "step" in tutorial.lower()
        assert len(tutorial) > 100

    def test_generate_with_custom_template(self, tmp_path):
        template_content = (
            "# Custom Template\n\n"
            "{% for step in steps %}\n"
            "- {{ step.title }}\n"
            "{% endfor %}"
        )
        template_file = tmp_path / "custom.md.j2"
        template_file.write_text(template_content)

        config = Config(steps=5, template=str(template_file))
        generator = TutorialGenerator(config)

        code = "def hello():\n    print('Hello')\n"
        parsed = self.parser.parse(code)
        tutorial = generator.generate(parsed)

        assert "Custom Template" in tutorial
        assert "hello" in tutorial

    def test_steps_limited_by_config(self):
        code = (
            "def a():\n    pass\n\n"
            "def b():\n    pass\n\n"
            "def c():\n    pass\n\n"
            "def d():\n    pass\n\n"
        )
        config = Config(steps=2)
        generator = TutorialGenerator(config)
        parsed = self.parser.parse(code)
        tutorial = generator.generate(parsed)
        assert tutorial.count("### Step") == 2

    def test_python_code_fence(self):
        code = "x = 1\n"
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed)
        assert "```python" in tutorial

    def test_language_aware_go_vocabulary(self):
        parsed = {
            "functions": [{"name": "main", "body": "func main() {}", "args": [], "docstring": None, "source_line": 1}],
            "classes": [{"name": "Server", "body": "type Server struct{}", "methods": [], "docstring": None, "kind": "type", "source_line": 3}],
            "imports": ['import "fmt"'],
            "main_code": "",
            "language": "go",
        }
        tutorial = self.generator.generate(parsed)
        assert "```go" in tutorial
        assert "Importing Packages" in tutorial
        assert "type" in tutorial

    def test_language_aware_rust_vocabulary(self):
        parsed = {
            "functions": [],
            "classes": [{"name": "Point", "body": "struct Point {}", "methods": [], "docstring": None, "kind": "struct", "source_line": 1}],
            "imports": ["use std::io;"],
            "main_code": "",
            "language": "rust",
        }
        tutorial = self.generator.generate(parsed)
        assert "```rust" in tutorial
        assert "struct" in tutorial
        assert "Importing Crates" in tutorial

    def test_docstring_used_as_description(self):
        code = 'def greet():\n    """Say hello to everyone."""\n    print("hi")\n'
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed)
        assert "Say hello to everyone." in tutorial

    def test_default_template_reads_like_a_lesson(self):
        code = (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Factorial Tutorial")

        assert "# Factorial Tutorial" in tutorial
        assert "## Big Idea" in tutorial
        assert "## Warm-Up" in tutorial
        assert "## Key Vocabulary" in tutorial
        assert "## What You'll Learn" in tutorial
        assert "## Teaching Tips" in tutorial
        assert "## Checks for Understanding" in tutorial
        assert "## Extension Challenge" in tutorial
        assert "## The Complete Program" in tutorial
        assert "**Look For**" in tutorial
        assert "**Ask Your Students**" in tutorial
        assert "**Predict**" in tutorial
        assert "**Modify**" in tutorial
        assert "**Try It**" in tutorial
        assert "recursion" in tutorial.lower()
        assert "\\n" not in tutorial

    def test_generate_with_ai_client(self):
        class FakeAIClient:
            def rewrite_steps(self, language, steps):
                assert language == "python"
                return [
                    {
                        **steps[0],
                        "title": "AI import step",
                        "description": "AI-generated explanation.",
                    }
                ]

        parsed = {
            "functions": [],
            "classes": [],
            "imports": ["import os"],
            "main_code": "",
            "language": "python",
        }
        config = Config(steps=5, use_ai=True)
        generator = TutorialGenerator(config, ai_client=FakeAIClient())

        tutorial = generator.generate(parsed)

        assert "AI import step" in tutorial
        assert "AI-generated explanation." in tutorial

    def test_custom_title(self):
        code = "x = 1\n"
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="My Custom Title")
        assert "# My Custom Title" in tutorial

    def test_main_code_preserved_when_truncating(self):
        """Main code step should be kept even when truncating functions."""
        code = (
            "def a():\n    pass\n\n"
            "def b():\n    pass\n\n"
            "def c():\n    pass\n\n"
            "x = 1\n"
        )
        config = Config(steps=2)
        generator = TutorialGenerator(config)
        parsed = self.parser.parse(code)
        tutorial = generator.generate(parsed)
        assert "x = 1" in tutorial
        assert tutorial.count("### Step") == 2

    def test_generate_with_ai_requires_credentials(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        parsed = self.parser.parse("x = 1\n")
        generator = TutorialGenerator(Config(steps=5, use_ai=True))

        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            generator.generate(parsed)

    def test_default_template_uses_real_newlines(self):
        parsed = self.parser.parse("x = 1\n")
        tutorial = self.generator.generate(parsed, title="Line Break Check")

        assert "# Line Break Check\n\n## Big Idea" in tutorial

    def test_steps_follow_dependency_order(self):
        """Steps should follow dependency order: leaf functions first."""
        code = (
            "def caller():\n"
            "    return helper()\n"
            "\n"
            "def helper():\n"
            "    return 42\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Dep Order")

        # helper has no deps so should come before caller
        helper_idx = tutorial.index("Define `helper`")
        caller_idx = tutorial.index("Define `caller`")
        assert helper_idx < caller_idx

    def test_transition_narratives_present(self):
        """Steps with dependencies should have transition narratives."""
        code = (
            "def helper():\n"
            "    return 42\n"
            "\n"
            "def caller():\n"
            "    return helper()\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Transitions")

        # caller depends on helper, so should mention it in transition
        assert "With `helper` available" in tutorial

    def test_cross_references_in_key_points(self):
        """Dependency relationships show up in key points."""
        code = (
            "def leaf():\n"
            "    return 1\n"
            "\n"
            "def caller():\n"
            "    return leaf() + 1\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Cross Refs")

        assert "Depends on: `leaf`" in tutorial
        assert "Used later by: `caller`" in tutorial

    def test_predict_exercises_present(self):
        code = (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Exercises")

        assert "**Predict**" in tutorial
        assert "factorial(n=3)" in tutorial

    def test_modify_exercises_present(self):
        code = (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Exercises")

        assert "**Modify**" in tutorial
        assert "base case" in tutorial

    def test_complete_program_section(self):
        code = (
            "def greet(name):\n"
            "    return name\n\n"
            "print(greet('Ada'))\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Complete")

        assert "## The Complete Program" in tutorial
        assert "def greet(name):" in tutorial
        assert "print(greet('Ada'))" in tutorial

    def test_complete_program_preserves_original_source_order(self):
        code = (
            "class Greeter:\n"
            "    pass\n"
            "\n"
            "def helper():\n"
            "    return 1\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Complete Order")

        assert code.strip() in tutorial

    def test_dependency_map_in_output(self):
        code = (
            "def helper():\n"
            "    return 1\n\n"
            "def caller():\n"
            "    return helper()\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Dep Map")

        assert "How the Pieces Connect" in tutorial
        assert "| `helper` |" in tutorial
        assert "| `caller` |" in tutorial

    def test_dependency_sections_omitted_when_components_are_independent(self):
        code = (
            "class Greeter:\n"
            "    pass\n"
            "\n"
            "def helper():\n"
            "    return 1\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Independent")

        assert "How the Pieces Connect" not in tutorial
        assert "follow the call chain" not in tutorial
        assert "Trace the dependency chain" not in tutorial

    def test_at_a_glance_reads_like_teacher_planning_notes(self):
        code = (
            "def factorial(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Planning Notes")

        assert "Suggested level:" in tutorial
        assert "Estimated pacing:" in tutorial
        assert "Core concepts:" in tutorial

    def test_main_execution_prompts_prefer_program_calls_over_builtins(self):
        parsed = self.parser.parse(
            "def greet(name):\n"
            "    return name\n\n"
            "print(greet('Ada'))\n"
        )
        tutorial = self.generator.generate(parsed, title="Builtin Filter")

        assert "calling `greet`" in tutorial
        assert "explains the behavior of `greet`" in tutorial

    def test_handout_format(self):
        code = (
            "def greet(name):\n"
            "    return name\n\n"
            "print(greet('Ada'))\n"
        )
        config = Config(steps=5, output_format="handout")
        generator = TutorialGenerator(config)
        parsed = self.parser.parse(code)
        tutorial = generator.generate(parsed, title="Handout Test")

        # Handout should have student-facing sections
        assert "## Building the Program" in tutorial
        assert "**Predict:**" in tutorial
        assert "**Modify:**" in tutorial
        assert "## Exercises" in tutorial
        assert "## Challenge" in tutorial

        # Handout should NOT have teacher-only sections
        assert "## Teaching Tips" not in tutorial
        assert "## Warm-Up" not in tutorial
        assert "**Try It**" not in tutorial

    def test_language_aware_builtin_filtering(self):
        """Python builtins are filtered; Go builtins would not be."""
        code = "def compute():\n    return 42\n\nresult = compute()\nprint(result)\n"
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Builtins")

        # print should be filtered as a Python builtin in main code description
        assert "calling `compute`" in tutorial
        # print should NOT appear as a top-level call to trace
        assert "calling `print`" not in tutorial

    def test_module_docstring_does_not_become_main_execution(self):
        code = (
            '"""Module docs."""\n'
            "\n"
            "def greet():\n"
            "    pass\n"
        )
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed, title="Docstrings")

        assert "### Step 2: Main Execution" not in tutorial
        assert code.strip() in tutorial
