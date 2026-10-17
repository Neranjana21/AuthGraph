#!/usr/bin/env bash
# One-time environment setup (Git Bash / Linux / macOS). Creates .venv, installs deps + Playwright Chromium.
set -e
cd "$(dirname "$0")"
python -m venv .venv
PY=.venv/Scripts/python; [ -x "$PY" ] || PY=.venv/bin/python
$PY -m pip install -q --upgrade pip
$PY -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu
$PY -m pip install -q -r requirements.txt
$PY -m playwright install chromium
echo "setup done"
