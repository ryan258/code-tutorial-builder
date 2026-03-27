import click
from .parser import CodeParser
from .generator import TutorialGenerator
from .config import Config

@click.command()
@click.option('--input', '-i', required=True, help='Input Python file to convert')
@click.option('--output', '-o', required=True, help='Output Markdown file')
@click.option('--steps', '-s', default=5, help='Number of steps to generate')
@click.option('--template', '-t', default=None, help='Custom Jinja2 template file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def main(input, output, steps, template, verbose):
    """Convert working code into step-by-step lessons."""
    if verbose:
        click.echo(f"Parsing {input}...")
    
    config = Config(steps=steps, template=template)
    parser = CodeParser(config)
    generator = TutorialGenerator(config)
    
    try:
        with open(input, 'r') as f:
            code = f.read()
        
        parsed = parser.parse(code)
        tutorial = generator.generate(parsed)
        
        with open(output, 'w') as f:
            f.write(tutorial)
        
        if verbose:
            click.echo(f"Tutorial generated at {output}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

if __name__ == '__main__':
    main()