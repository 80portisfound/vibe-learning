#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$DESKTOP_DIR/../.." && pwd)"
RUNTIME_DIR="$DESKTOP_DIR/build/python-runtime"
PYTHON_BIN="${PYTHON_BIN:-python3}"

rm -rf "$RUNTIME_DIR"
"$PYTHON_BIN" -m venv --copies "$RUNTIME_DIR"
"$RUNTIME_DIR/bin/python" -m pip install --upgrade pip
"$RUNTIME_DIR/bin/python" -m pip install -r "$REPO_DIR/apps/api/requirements-runtime.txt"
