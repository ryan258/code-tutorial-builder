import re
import shlex
import shutil
from pathlib import Path

import click

from .config import Config, VALID_FORMATS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_OUTPUTS_DIR = _PROJECT_ROOT / "outputs"


class _FallbackGroup(click.Group):
    """Click group that falls back to ``generate`` for backward compatibility.

    If the first CLI argument is an option (e.g. ``-i``,
    ``--input``), the argument list is silently prefixed with ``generate``
    so the old ``python -m code_tutorial_builder -i file -o out`` form
    continues to work.
    """

    def parse_args(self, ctx, args):
        if args and args[0].startswith("-") and args[0] != "--help":
            args = ["generate"] + args
        return super().parse_args(ctx, args)


@click.group(cls=_FallbackGroup, invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Convert working code into step-by-step lessons."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ──────────────────────────────────────────────────────────────────────
# generate — the original single-file tutorial workflow
# ──────────────────────────────────────────────────────────────────────


@cli.command()
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
def generate(input_file, output_file, steps, template, title, language, output_format, ai, verbose):
    """Generate a tutorial from a single source file."""
    from .generator import TutorialGenerator
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

        # Save a copy to the outputs archive
        archive_path = _save_to_outputs(
            input_file, lesson_title, output_format, tutorial,
        )
        if archive_path and verbose:
            click.echo(f"Archived to {archive_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# ──────────────────────────────────────────────────────────────────────
# scan — discover learning opportunities in a project
# ──────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument('directory', default='.')
@click.option('--max', '-n', 'max_opportunities', default=10,
              help='Maximum number of opportunities to return (1-10)')
@click.option('--max-lines', default=500,
              help='Skip files longer than this many lines')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def scan(directory, max_opportunities, max_lines, as_json, verbose):
    """Scan a project directory for learning opportunities.

    Walks DIRECTORY (default: current directory), parses all supported source
    files, and ranks them by teaching potential.  Use the results to choose
    which file to turn into a tutorial.
    """
    from .scanner import scan_project

    if verbose:
        click.echo(f"Scanning {Path(directory).resolve()} ...", err=as_json)

    try:
        result = scan_project(
            directory,
            max_opportunities=max_opportunities,
            max_file_lines=max_lines,
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(result.to_json())
        return

    # Human-readable output
    click.echo(
        f"\nScanned {result.files_scanned} files "
        f"({result.files_skipped} skipped)"
    )

    if result.gitnexus_available:
        click.echo("GitNexus index detected — deeper analysis available via MCP tools")

    if not result.opportunities:
        click.echo("\nNo learning opportunities found.")
        return

    click.echo(f"\nFound {len(result.opportunities)} learning opportunities:\n")

    resolved_root = Path(result.root)
    for i, opp in enumerate(result.opportunities, 1):
        stars = _score_to_stars(opp.score)
        click.echo(f"  {i}. [{stars}] {opp.title}")
        click.echo(f"     File: {opp.file_path}")
        click.echo(f"     Difficulty: {opp.difficulty} | "
                    f"Components: {opp.component_count} | "
                    f"Depth: {opp.dependency_depth}")
        if opp.concepts:
            click.echo(f"     Concepts: {', '.join(opp.concepts)}")
        click.echo(f"     {opp.rationale}")
        click.echo()

    sample_path = resolved_root / result.opportunities[0].file_path
    click.echo(
        "To generate a tutorial, run:\n"
        f"  code-tutorial-builder generate -i {shlex.quote(str(sample_path))} -o tutorial.md"
    )


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _lesson_title_from_path(input_file: str) -> str:
    stem = Path(input_file).stem.replace("_", " ").replace("-", " ").strip()
    if not stem:
        return "Code Tutorial"
    return f"{stem.title()} Tutorial"


def _slugify(text: str) -> str:
    """Turn a title into a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def _guess_project_name(input_file: str) -> str | None:
    """Derive a project name from the input file's path.

    Returns None when no recognisable project root is found (e.g. temp dirs
    during testing).
    """
    path = Path(input_file).resolve()
    # Walk up looking for a pyproject.toml, setup.py, or .git directory
    for parent in path.parents:
        if any((parent / marker).exists() for marker in (
            "pyproject.toml", "setup.py", "setup.cfg",
            "package.json", "Cargo.toml", "go.mod",
        )):
            return _slugify(parent.name)
        if (parent / ".git").is_dir():
            return _slugify(parent.name)
    return None


def _save_to_outputs(
    input_file: str,
    lesson_title: str,
    output_format: str,
    content: str,
) -> str | None:
    """Save a copy of the generated tutorial to the outputs archive.

    Returns the archive path on success, or None if it couldn't be saved.
    """
    try:
        project = _guess_project_name(input_file)
        if project is None:
            return None
        title_slug = _slugify(lesson_title)
        group_dir = _OUTPUTS_DIR / f"{project}--{title_slug}"
        group_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{project}--{title_slug}-{output_format}.md"
        dest = group_dir / filename
        dest.write_text(content, encoding="utf-8")
        return str(dest)
    except OSError:
        return None


def _score_to_stars(score: float) -> str:
    """Convert a 0-1 score to a 1-5 star display."""
    filled = max(1, min(5, round(score * 5)))
    return "*" * filled + "-" * (5 - filled)


# Keep backward compat: `python -m code_tutorial_builder` still works
main = cli

if __name__ == '__main__':
    cli()
