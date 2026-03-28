# Code Tutorial Builder

Code Tutorial Builder turns working code into a step-by-step lesson.

It is made for teachers, tutors, mentors, and developers who want to explain real code in a clear order. Instead of walking from the top of the file to the bottom, it tries to teach the code in the order a student should learn it.

## What This Tool Does

You give the tool a source code file.

It:

1. Reads the file.
2. Finds the main pieces, like functions, classes, imports, and main code.
3. Checks which pieces depend on other pieces.
4. Splits large classes into per-method steps so students learn one method at a time.
5. Finds simple programming ideas, like loops, control flow, recursion, and error handling.
6. Builds a Markdown lesson from that information.
7. Archives every generated lesson in the `outputs/` folder, grouped by project and title.

The final lesson can include:

- a big idea
- a warm-up
- key vocabulary
- learning goals
- teaching tips
- step-by-step code sections
- predict and modify activities
- checks for understanding
- an extension challenge
- the complete program

## What Makes It Different

Many code explainers go line by line from top to bottom. That is easy for a computer, but it is not always the best way to teach.

This tool tries to teach like a person would:

- It teaches helper code before code that uses it.
- It breaks large classes into one step per method, in dependency order.
- It shows how parts connect.
- It adds simple teaching prompts.
- It recognizes setup code (like logging config) and labels it differently from real orchestration.
- It can make a teacher lesson or a student handout.
- It can scan a whole project and help you choose a good lesson file.

## The Two Main Jobs

This project has two main commands:

### 1. `generate`

Use `generate` when you already know which file you want to teach.

Example:

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md
```

### 2. `scan`

Use `scan` when you want the tool to look through a folder and suggest good lesson files.

Example:

```bash
python -m code_tutorial_builder scan .
```

## How The System Works

Here is the happy path inside the codebase:

1. The CLI lives in `code_tutorial_builder/__main__.py`.
2. The parser reads the file and turns it into a shared structure.
3. The analyzer studies dependencies and concepts.
4. The generator builds lesson steps and lesson sections.
5. A Jinja template turns that data into Markdown.

### The main parts of the system

- `code_tutorial_builder/__main__.py`
  This is the command line entry point. It handles `generate` and `scan`.

- `code_tutorial_builder/languages/`
  This folder knows how to parse each language.

- `code_tutorial_builder/languages/_python_parser.py`
  Python uses the built-in `ast` module, so Python works without tree-sitter.

- `code_tutorial_builder/languages/_treesitter.py`
  JavaScript, TypeScript, Go, Rust, and Java use tree-sitter.

- `code_tutorial_builder/analysis.py`
  This file finds function and class dependencies and spots big ideas like loops and recursion.

- `code_tutorial_builder/generator.py`
  This file turns the parsed code and analysis into lesson content.

- `code_tutorial_builder/scanner.py`
  This file walks a project, scores files, and picks strong teaching candidates.

- `code_tutorial_builder/templates/default.md.j2`
  This is the teacher lesson template.

- `code_tutorial_builder/templates/handout.md.j2`
  This is the student handout template.

- `code_tutorial_builder/ai.py`
  This file handles optional OpenRouter AI rewriting for step titles and descriptions.

## Supported Languages

| Language | File endings | Parser |
| --- | --- | --- |
| Python | `.py` | built-in `ast` |
| JavaScript | `.js`, `.mjs`, `.cjs` | tree-sitter |
| TypeScript | `.ts` | tree-sitter |
| Go | `.go` | tree-sitter |
| Rust | `.rs` | tree-sitter |
| Java | `.java` | tree-sitter |

Notes:

- Python works with the base install.
- The other languages need the optional multi-language install.
- JSX and TSX are not supported yet.

## Installation

### Option 1: Python only

Use this if you only need Python files.

```bash
pip install .
```

### Option 2: Multi-language support

Use this if you want JavaScript, TypeScript, Go, Rust, or Java too.

```bash
pip install ".[multilang]"
```

### Option 3: Development setup

Use this if you want to work on the project itself.

```bash
pip install -e ".[dev]"
```

## Quick Start

### Fastest way

Use the helper script:

```bash
./run.sh path/to/file.py
```

This script:

- creates a local virtual environment the first time
- installs the project with multi-language support
- runs the `generate` command
- saves the lesson next to the source file

Example:

```bash
./run.sh path/to/file.py --steps 8 --title "My Lesson"
```

### Direct CLI way

If you already installed the package, run:

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md
```

The older short form still works too:

```bash
python -m code_tutorial_builder -i path/to/file.py -o lesson.md
```

The recommended form is the one with the `generate` subcommand.

## Generate A Lesson From One File

### Basic example

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md
```

### Choose the number of steps

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md --steps 7
```

### Pick a title

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md --title "Intro to Loops"
```

### Force the language

Use this if the file ending is not enough.

```bash
python -m code_tutorial_builder generate -i code.txt -o lesson.md --language python
```

### Make a student handout

```bash
python -m code_tutorial_builder generate -i example.py -o handout.md --format handout
```

### Use a custom template

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md --template my_template.j2
```

### Show extra details while it runs

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md --verbose
```

## Scan A Project For Lesson Ideas

The scanner helps when you do not know which file to teach.

Example:

```bash
python -m code_tutorial_builder scan .
```

The scanner:

- walks through the folder
- skips common junk folders like `.git`, `node_modules`, `dist`, and `.venv`
- ignores symlinked directories
- skips very large files if they are over the line limit
- parses each supported file
- scores files for teaching value
- prints the best learning opportunities

### Basic scan

```bash
python -m code_tutorial_builder scan path/to/project
```

### Limit the number of results

```bash
python -m code_tutorial_builder scan path/to/project --max 5
```

### Skip very long files

```bash
python -m code_tutorial_builder scan path/to/project --max-lines 300
```

### Get JSON output

```bash
python -m code_tutorial_builder scan path/to/project --json
```

### Show progress while scanning

```bash
python -m code_tutorial_builder scan path/to/project --verbose
```

### What the scanner looks for

The scanner gives higher scores to files that:

- show more than one useful concept
- have clear dependencies between parts
- are not too small and not too large
- are fairly self-contained
- have a nice build-up from simple parts to bigger parts

It also gives each result:

- a title
- a file path
- a difficulty level
- a list of concepts
- a score
- a short reason

If the project has a `.gitnexus/meta.json` file, the scan result also adds project-level GitNexus details.

## Output Formats

There are two output formats.

### `lesson`

This is the teacher-facing format.

It includes:

- Big Idea
- At a Glance
- Warm-Up
- Key Vocabulary
- What You'll Learn
- Teaching Tips
- Steps
- Checks for Understanding
- Extension Challenge
- Recap

### `handout`

This is the student-facing format.

It includes:

- overview
- key terms
- building steps
- predict prompts
- modify prompts
- exercises
- challenge

## How The Teaching Order Works

The system does not just keep the source order.

It tries to find an order that makes sense for teaching:

1. Imports can come first.
2. Helper functions and classes come before code that uses them.
3. Large classes (more than 4 methods) are split into per-method steps. The class constructor is introduced first, then each method follows in dependency order.
4. Module-level setup code (like logging configuration) is labeled as "Module Setup" instead of "Main Execution."
5. Real main execution code comes near the end.

This is handled by dependency analysis in `code_tutorial_builder/analysis.py`.

### Method splitting

When a class has more than 4 methods, the tool breaks it into separate steps:

- An intro step that shows the class declaration and `__init__`
- One step per remaining method, ordered by intra-class dependencies

Methods that call other methods (via `self.method()`) are taught after the methods they depend on. This prevents students from seeing a call to something they have not learned yet.

Small classes (4 methods or fewer) stay as a single step.

The analyzer also finds concepts like:

- iteration
- control flow
- recursion
- error handling
- state management

## AI Mode

AI mode is optional.

Without AI, the tool still works. It still parses the file, builds steps, orders dependencies, and creates the lesson.

With AI, the tool asks OpenRouter to improve step titles and descriptions.

### What AI changes

AI mode only rewrites some lesson text.

It does not:

- change the code
- change the parser
- change the dependency order
- change the lesson structure

### Set up AI mode

Create a `.env` file in the repo, the source file folder, or a parent folder:

```bash
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
```

Then run:

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md --ai
```

### AI notes

- If there is no API key, AI mode will fail with an error.
- The default model can be changed with `OPENROUTER_MODEL`.
- The system looks for `.env` files near the source path and current folder.

## Common Commands

### Show help

```bash
python -m code_tutorial_builder --help
python -m code_tutorial_builder generate --help
python -m code_tutorial_builder scan --help
```

### Make a teacher lesson

```bash
python -m code_tutorial_builder generate -i example.py -o lesson.md --format lesson
```

### Make a student handout

```bash
python -m code_tutorial_builder generate -i example.py -o handout.md --format handout
```

### Scan and then generate

```bash
python -m code_tutorial_builder scan .
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md
```

## Output Archive

Every successful `generate` run saves a copy to the `outputs/` folder in this repo.

Files are grouped into a directory named `{project}--{lesson-title}`, and each file inside is named `{project}--{lesson-title}-{format}.md`.

Example:

```text
outputs/
  wcag-auditor--auditor-tutorial/
    wcag-auditor--auditor-tutorial-lesson.md
    wcag-auditor--auditor-tutorial-handout.md
```

The project name is detected by walking up from the input file and looking for `pyproject.toml`, `package.json`, `.git`, or similar markers.

The `outputs/` folder is in `.gitignore` so generated lessons do not clutter the repo.

## Project Layout

Here is the main layout of the repo:

```text
code_tutorial_builder/
  __main__.py
  ai.py
  analysis.py
  config.py
  generator.py
  scanner.py
  languages/
  templates/
tests/
outputs/          (generated lessons, gitignored)
run.sh
README.md
HAPPYPATH.md
```

## Development

### Install dev tools

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
python -m pytest
```

### Run a smaller test set

```bash
python -m pytest tests/test_cli.py tests/test_scanner.py
```

## Limits And Notes

- JSX and TSX are not supported.
- The scanner returns up to 10 opportunities.
- Large files can be skipped by line count.
- Python uses the standard library parser.
- Other languages need tree-sitter packages installed.
- The lesson quality depends on how clear the source file is.
- A file with too many unrelated ideas may make a weaker lesson.
- Classes with more than 4 methods are split into per-method steps. Increase `--steps` for large files.
- The output archive detects the project name automatically. If no project root is found, archiving is skipped.

## When To Use Which Command

Use `generate` when:

- you already know the file you want
- you want a lesson right away

Use `scan` when:

- you are looking at a whole project
- you want help finding a strong teaching example
- you want to compare lesson ideas before generating one

## Recommended Reading Order

If you are new to the project:

1. Read [HAPPYPATH.md](HAPPYPATH.md)
2. Try `./run.sh path/to/file.py`
3. Try `python -m code_tutorial_builder scan .`
4. Read `code_tutorial_builder/__main__.py`
5. Read `code_tutorial_builder/analysis.py`
6. Read `code_tutorial_builder/generator.py`

## License

MIT
