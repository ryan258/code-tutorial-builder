from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader, Template

from .config import Config

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


class TutorialGenerator:
    """Generate tutorials from parsed code."""

    def __init__(self, config: Config):
        self.config = config
        self.env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))

    def generate(self, parsed_code: Dict[str, Any]) -> str:
        """
        Generate a tutorial from parsed code.

        Returns:
            Markdown formatted tutorial string
        """
        steps = self._create_steps(parsed_code)

        if self.config.template:
            template = Template(Path(self.config.template).read_text())
        else:
            template = self.env.get_template("default.md.j2")

        return template.render(title="Code Tutorial", steps=steps)

    def _create_steps(self, parsed_code: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create tutorial steps from parsed code."""
        steps: List[Dict[str, str]] = []

        if parsed_code.get('imports'):
            steps.append({
                'title': 'Importing Required Modules',
                'description': 'First, we import the necessary modules for our code.',
                'code': '\n'.join(parsed_code['imports']),
            })

        for func in parsed_code.get('functions', []):
            steps.append({
                'title': f"Understanding the {func['name']} function",
                'description': f"This function {func['name']} does the following:",
                'code': func['body'],
            })

        for cls in parsed_code.get('classes', []):
            steps.append({
                'title': f"Understanding the {cls['name']} class",
                'description': f"This class {cls['name']} contains the following methods:",
                'code': cls['body'],
            })

        if parsed_code.get('main_code'):
            steps.append({
                'title': 'Main Execution',
                'description': 'This is the main execution part of the code.',
                'code': parsed_code['main_code'],
            })

        if len(steps) > self.config.steps:
            steps = steps[:self.config.steps]

        return steps
