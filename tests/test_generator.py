import pytest
from code_tutorial_builder.generator import TutorialGenerator
from code_tutorial_builder.config import Config
from code_tutorial_builder.parser import CodeParser


class TestTutorialGenerator:
    """Tests for TutorialGenerator class."""

    def setup_method(self):
        self.config = Config(steps=5)
        self.generator = TutorialGenerator(self.config)
        self.parser = CodeParser()

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

        # Only 2 of the 4 functions should appear as steps
        assert tutorial.count("### Step") == 2
