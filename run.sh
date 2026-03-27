#!/usr/bin/env bash
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: ./run.sh <path/to/file> [extra code-tutorial-builder args...]" >&2
    exit 1
fi

INPUT="$1"
BASH_ARGS=("${@:2}")
BASENAME="${INPUT%.*}"
OUTPUT="${BASENAME}_tutorial.md"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Bootstrap venv + deps on first run
if [ ! -d "$VENV_DIR" ]; then
    echo "First run — setting up environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q "$SCRIPT_DIR[multilang]"
fi

"$VENV_DIR/bin/python" -m code_tutorial_builder -i "$INPUT" -o "$OUTPUT" -v "${BASH_ARGS[@]}"

echo ""
echo "Tutorial: $OUTPUT"
