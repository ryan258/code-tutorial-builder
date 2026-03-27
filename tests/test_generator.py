import pytest
from code_tutorial_builder.generator import TutorialGenerator
from code_tutorial_builder.config import Config
from code_tutorial_builder.parser import CodeParser

class TestTutorialGenerator:
    """Tests for TutorialGenerator class."""
    
    def setup_method(self):
        self.config = Config(steps=5)
        self.generator = TutorialGenerator(self.config)
        self.parser = CodeParser(self.config)
    
    def test_generate_simple_tutorial(self):
        """Test generating a simple tutorial."""
        code = """def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)
"""
        parsed = self.parser.parse(code)
        tutorial = self.generator.generate(parsed)
        assert "factorial" in tutorial
        assert "step" in tutorial.lower()
        assert len(tutorial) > 100  # Reasonable length check
    
    def test_generate_with_custom_template(self, tmp_path):
        """Test generating with a custom template."""
        # Create a temporary template file
        template_content = "# Custom Template\n\n{% for step in steps %}\n- {{ step.title }}\n{% endfor %}"
        template_file = tmp_path / "custom.md.j2"
        template_file.write_text(template_content)
        
        config = Config(steps=5, template=str(template_file))
        generator = TutorialGenerator(config)
        parser = CodeParser(config)
        
        code = """def hello():
    print('Hello')
"""
        parsed = parser.parse(code)
        tutorial = generator.generate(parsed)
        
        assert "Custom Template" in tutorial
        assert "hello" in tutorial