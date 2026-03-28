# HAPPYPATH

This file is the shortest safe path from "I have code" to "I have a lesson."

If you do not want the full details yet, start here.

## Goal

Turn one real source code file into a Markdown lesson.

## The Fastest Path

### 1. Go to the repo

```bash
cd /path/to/code-tutorial-builder
```

### 2. Run the helper script

```bash
./run.sh path/to/file.py
```

That is the easiest path.

On the first run, it will:

- make a `.venv`
- install the project
- install multi-language support
- generate a tutorial file

The output file will be saved next to your source file.

If your file is `lesson_example.py`, the output will usually be:

```text
lesson_example_tutorial.md
```

A copy is also archived in the `outputs/` folder inside this repo, grouped by project and lesson title:

```text
outputs/
  my-project--lesson-example-tutorial/
    my-project--lesson-example-tutorial-lesson.md
```

## If You Want More Control

Use the CLI directly.

### Teacher lesson

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md
```

### Student handout

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o handout.md --format handout
```

### More lesson steps

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md --steps 7
```

### Custom title

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md --title "My Class Lesson"
```

### Show progress

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md --verbose
```

## If You Do Not Know Which File To Use

Ask the scanner to help.

### 1. Scan the project

```bash
python -m code_tutorial_builder scan path/to/project
```

You will get a ranked list of lesson ideas.

### 2. Pick one file from the list

Then run:

```bash
python -m code_tutorial_builder generate -i /full/path/from/scan.py -o lesson.md
```

The scan output prints a ready-to-run example command for you.

## If You Want JSON From The Scanner

```bash
python -m code_tutorial_builder scan path/to/project --json
```

This is useful for scripts and tools.

## If You Want AI Help

AI is optional.

### 1. Add a `.env` file

```bash
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
```

### 2. Run generate with `--ai`

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md --ai
```

AI improves some lesson text.

It does not change the source code.

## Both Formats At Once

Generate a lesson and a handout for the same file:

```bash
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md
python -m code_tutorial_builder generate -i path/to/file.py -o handout.md --format handout
```

Both files will be archived together in the same `outputs/` directory:

```text
outputs/
  my-project--file-tutorial/
    my-project--file-tutorial-lesson.md
    my-project--file-tutorial-handout.md
```

## Good First Examples

Pick files that:

- are under a few hundred lines
- have 1 to 6 main parts
- have clear helper functions
- show loops, conditionals, or recursion
- are not full of setup code

## Good First Commands

If you only want three commands, use these:

```bash
./run.sh path/to/file.py
python -m code_tutorial_builder scan .
python -m code_tutorial_builder generate -i path/to/file.py -o lesson.md --format handout
```

## What Success Looks Like

You are done when:

- the command exits without errors
- your Markdown output file exists
- the file has sections like "Big Idea" or "Building the Program"
- the steps teach helper code before code that depends on it
- large classes are broken into per-method steps instead of one giant block
- a copy appears in the `outputs/` folder

## Common Problems

### Problem: "could not detect language"

Fix:

```bash
python -m code_tutorial_builder generate -i path/to/file.txt -o lesson.md --language python
```

### Problem: non-Python file will not parse

You probably need multi-language support:

```bash
pip install ".[multilang]"
```

### Problem: AI mode fails

Check that `OPENROUTER_API_KEY` is set in the environment or a `.env` file.

## Next Step

When this flow works, read [README.md](README.md) for the full system guide.
