#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
else
  . .venv/bin/activate
fi

python app.py
