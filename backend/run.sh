#!/usr/bin/env bash
set -euo pipefail

# Activate virtual environment based on OS type
activate_venv() {
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    . .venv/Scripts/activate
  else
    # Assumes a Unix-like OS (Linux, macOS) if not Windows
    . .venv/bin/activate
  fi
}


if [ ! -d ".venv" ]; then
  python -m venv .venv
  activate_venv
  python -m pip install --upgrade pip
  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
else
  activate_venv
fi

python app.py
