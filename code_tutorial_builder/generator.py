from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, Template
from .config import Config

class TutorialGenerator:
    """Generate tutorials from parsed code."""
    
    def __init__(self, config: Config):
        self.config = config
        self.env = Environment(loader=FileSystemLoader('.'))
    
    def generate(self, parsed_code: Dict[str, Any]) -> str:
        """
        Generate a tutorial from parsed code.
        
        Returns:
            Markdown formatted tutorial string
        """
        steps = self._create_steps(parsed_code)
        
        if self.config.template:
            with open(self.config.template, 'r') as file:
                template_content = file.read()
            template = Template(template_content)
        else:
            template = self.env.get_template('templates/default.md.j2')
        
        return template.render(title="Code Tutorial", steps=steps)
    
    def _create_steps(self, parsed_code: Dict[str, Any]) -> list:
        """Create tutorial steps from parsed code."""
        steps = []
        
        # Add import step
        if parsed_code.get('imports'):
            steps.append({
                'title': 'Importing Required Modules',
                'description': 'First, we import the necessary modules for our code.',
                'code': '\n'.join(parsed_code['imports'])
            })
        
        # Add function steps
        for func in parsed_code.get('functions', []):
            steps.append({
                'title': f"Understanding the {func['name']} function",
                'description': f"This function {func['name']} does the following:",
                'code': func['body']
            })
        
        # Add class steps
        for cls in parsed_code.get('classes', []):
            steps.append({
                'title': f"Understanding the {cls['name']} class",
                'description': f"This class {cls['name']} contains the following methods:",
                'code': cls['body']
            })
        
        # Add main code step
        if parsed_code.get('main_code'):
            steps.append({
                'title': 'Main Execution',
                'description': 'This is the main execution part of the code.',
                'code': parsed_code['main_code']
            })
        
        # Limit steps to configured number
        return steps[:self.config.steps]