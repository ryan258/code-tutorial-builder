#!/usr/bin/env bash
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: ./start.sh <path/to/file.py>" >&2
    exit 1
fi

INPUT="$1"
OUTPUT="${INPUT%.py}_tutorial.md"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Bootstrap venv + deps on first run
if [ ! -d "$VENV_DIR" ]; then
    echo "First run — setting up environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q "$SCRIPT_DIR"
fi

"$VENV_DIR/bin/python" -m code_tutorial_builder -i "$INPUT" -o "$OUTPUT" -v

echo ""
echo "Tutorial: $OUTPUT"
