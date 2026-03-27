# Code Tutorial Builder

A tool that converts working code into step-by-step lessons with explanations and runnable examples.

## Features

- Parse Python source files and extract code blocks
- Generate step-by-step tutorials with explanations
- Support for custom lesson templates
- Output in Markdown format for easy sharing
- Configurable step granularity

## Installation

```bash
pip install .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
./run.sh path/to/file.py
```

This handles everything — creates a virtualenv on first run, installs dependencies, and generates the tutorial. The output is saved alongside the input file (e.g. `file_tutorial.md`).

## Usage

For more control, use the module directly:

```bash
python -m code_tutorial_builder --input example.py --output tutorial.md --steps 5
```

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

The tool will generate a tutorial with steps:
1. Understanding the factorial function
2. Base case: n == 0
3. Recursive case: n * factorial(n-1)
4. Calling the function
5. Printing the result

## Development

```bash
python -m pytest tests/
```

## License

MIT
