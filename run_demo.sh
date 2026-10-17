#!/usr/bin/env bash
# Professor entry point.  ./run_demo.sh          -> uses the frozen dataset/models if present, else builds them
#                         ./run_demo.sh --rebuild -> regenerate everything from scratch (~25 min)
set -e
cd "$(dirname "$0")"
PY=.venv/Scripts/python; [ -x "$PY" ] || { ./setup.sh; PY=.venv/Scripts/python; [ -x "$PY" ] || PY=.venv/bin/python; }
if [ "$1" = "--rebuild" ] || [ ! -f data/graphs.pkl ]; then ./run_dataset.sh; fi
if [ "$1" = "--rebuild" ] || [ ! -f results/main.json ]; then $PY train.py --exp all && $PY evaluate.py; fi
$PY -m streamlit run dashboard.py
