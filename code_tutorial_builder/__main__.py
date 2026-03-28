from pathlib import Path

import click

from .config import Config, VALID_FORMATS
from .generator import TutorialGenerator


@click.command()
@click.option('--input', '-i', 'input_file', required=True, help='Input source file to convert')
@click.option('--output', '-o', 'output_file', required=True, help='Output Markdown file')
@click.option('--steps', '-s', default=5, help='Number of steps to generate')
@click.option('--template', '-t', default=None, help='Custom Jinja2 template file')
@click.option('--title', default=None, help='Custom tutorial title')
@click.option('--language', '-l', default=None, help='Override language detection (python, javascript, go, ...)')
@click.option('--format', '-f', 'output_format', default='lesson',
              type=click.Choice(VALID_FORMATS, case_sensitive=False),
              help='Output format (lesson = teacher plan, handout = student facing)')
@click.option('--ai/--no-ai', default=False, help='Use OpenRouter settings from .env to improve step titles and descriptions')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def main(input_file, output_file, steps, template, title, language, output_format, ai, verbose):
    """Convert working code into step-by-step lessons."""
    from .languages import detect_language, get_parser

    if language is None:
        language = detect_language(input_file)
        if language is None:
            click.echo(
                f"Error: could not detect language for {input_file}. "
                f"Use --language to specify.",
                err=True,
            )
            raise SystemExit(1)

    if verbose:
        click.echo(f"Parsing {input_file} as {language}...")

    config = Config(
        steps=steps,
        template=template,
        output_format=output_format,
        use_ai=ai,
        env_search_path=input_file,
    )

    try:
        parser = get_parser(language)
    except (ImportError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    generator = TutorialGenerator(config)

    try:
        code = Path(input_file).read_text(encoding="utf-8")
        parsed = parser.parse(code)

        lesson_title = title or _lesson_title_from_path(input_file)

        if verbose and ai:
            click.echo("Enhancing tutorial with OpenRouter AI...")
        tutorial = generator.generate(parsed, title=lesson_title)

        with open(output_file, 'w', encoding="utf-8") as f:
            f.write(tutorial)

        if verbose:
            click.echo(f"Tutorial generated at {output_file}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _lesson_title_from_path(input_file: str) -> str:
    stem = Path(input_file).stem.replace("_", " ").replace("-", " ").strip()
    if not stem:
        return "Code Tutorial"
    return f"{stem.title()} Tutorial"


if __name__ == '__main__':
    main()
