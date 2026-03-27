# Code Tutorial Builder

A tool that converts working code into step-by-step lessons with explanations, warm-ups, vocabulary, checks for understanding, extension prompts, and runnable examples. Supports multiple programming languages.

## Supported Languages

| Language   | Extensions        | Parser            |
|------------|-------------------|-------------------|
| Python     | `.py`             | Built-in (ast)    |
| JavaScript | `.js`, `.mjs`, `.cjs` | tree-sitter   |
| TypeScript | `.ts`             | tree-sitter       |
| Go         | `.go`             | tree-sitter       |
| Rust       | `.rs`             | tree-sitter       |
| Java       | `.java`           | tree-sitter       |

JSX and TSX files are not yet supported.

## Quick Start

```bash
./run.sh path/to/file.py
./run.sh path/to/file.js
./run.sh path/to/file.go
./run.sh path/to/file.py --steps 8 --title "Recursion Lesson"
```

This handles everything — creates a virtualenv on first run, installs dependencies, and generates the tutorial. The output is saved alongside the input file (e.g. `file_tutorial.md`).

## Installation

For Python-only usage (no extra dependencies):

```bash
pip install .
```

For multi-language support:

```bash
pip install ".[multilang]"
```

For development (includes pytest + tree-sitter):

```bash
pip install -e ".[dev]"
```

## Usage

```bash
python -m code_tutorial_builder --input example.py --output tutorial.md --steps 5
```

Language is auto-detected from the file extension. Override with `--language`:

```bash
python -m code_tutorial_builder -i app.ts -o tutorial.md --language typescript
```

Set a classroom-friendly title explicitly with `--title`:

```bash
python -m code_tutorial_builder -i example.py -o tutorial.md --title "Intro to Recursion"
```

To use OpenRouter for richer tutorial copy, create a `.env` file in the repo or source-file directory:

```bash
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
```

Then run with `--ai`:

```bash
python -m code_tutorial_builder -i example.py -o tutorial.md --ai
```

The parser and code extraction stay deterministic; OpenRouter is only used to improve step titles and descriptions.

## Example

Given a Python file `example.py`:

```python
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

result = factorial(5)
print(result)
```

The tool generates a teacher-friendly tutorial with language-appropriate terminology, source-order-aware steps, real Markdown formatting, warm-up prompts, teaching goals, guided questions, recap notes, extension ideas, and syntax-highlighted code blocks.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/
```

## License

MIT
