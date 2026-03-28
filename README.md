# Code Tutorial Builder

A tool that converts working code into step-by-step lessons with dependency-aware ordering, transition narratives, predict/modify exercises, cross-reference maps, and runnable examples. Supports multiple programming languages.

## What Makes It Different

Most code explainers walk through code top-to-bottom. This tool **teaches like an instructor would**:

- **Dependency-ordered steps** --- Leaf functions come first, then the code that uses them. Students never see a call to something they haven't learned yet.
- **Transition narratives** --- Each step explains *why* it comes next: "With `helper` available, we can now build `process` which uses it."
- **Cross-reference map** --- A table showing what each component uses and what uses it.
- **Predict & Modify exercises** --- Concrete, code-specific exercises for each step, not generic prompts.
- **Complete program listing** --- The full code at the end so students can see how everything fits together.
- **Two output formats** --- `lesson` (teacher plan with tips, warm-ups, vocabulary) and `handout` (student-facing with code and exercises).

## Supported Languages

| Language   | Extensions            | Parser            |
|------------|-----------------------|-------------------|
| Python     | `.py`                 | Built-in (ast)    |
| JavaScript | `.js`, `.mjs`, `.cjs` | tree-sitter       |
| TypeScript | `.ts`                 | tree-sitter       |
| Go         | `.go`                 | tree-sitter       |
| Rust       | `.rs`                 | tree-sitter       |
| Java       | `.java`               | tree-sitter       |

JSX and TSX files are not yet supported.

## Quick Start

```bash
./run.sh path/to/file.py
./run.sh path/to/file.js
./run.sh path/to/file.go
./run.sh path/to/file.py --steps 8 --title "Recursion Lesson"
```

This handles everything --- creates a virtualenv on first run, installs dependencies, and generates the tutorial. The output is saved alongside the input file (e.g. `file_tutorial.md`).

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

### Output formats

Generate a full teacher lesson plan (default):

```bash
python -m code_tutorial_builder -i example.py -o lesson.md
```

Generate a student-facing handout with code and exercises only:

```bash
python -m code_tutorial_builder -i example.py -o handout.md --format handout
```

### Language detection

Language is auto-detected from the file extension. Override with `--language`:

```bash
python -m code_tutorial_builder -i app.ts -o tutorial.md --language typescript
```

### Custom titles

Set a classroom-friendly title with `--title`:

```bash
python -m code_tutorial_builder -i example.py -o tutorial.md --title "Intro to Recursion"
```

### AI enhancement

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

Given `example.py` with two recursive functions and a class, the tool produces a lesson that:

1. Teaches `factorial` first (no dependencies, natural starting point)
2. Teaches `fibonacci` next (also independent)
3. Introduces `Calculator` (self-contained class)
4. Shows the main execution tying them together

Each step includes transition narratives ("This function has no dependencies... a natural starting point"), predict exercises ("Trace `factorial(n=3)` by hand"), modify challenges ("Change the base case --- what happens?"), and a dependency map showing how the pieces connect.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/
```

## License

MIT
