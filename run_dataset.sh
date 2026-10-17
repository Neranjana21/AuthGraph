#!/usr/bin/env bash
# Generate extensions -> run them in real Chromium against the local lab -> validate -> build graphs.
set -e
cd "$(dirname "$0")"
PY=.venv/Scripts/python; [ -x "$PY" ] || PY=.venv/bin/python
$PY lab/collect.py --per-family 12 --sessions 4 --batch 12 --out data/raw
$PY build_graphs.py
