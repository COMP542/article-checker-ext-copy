#!/usr/bin/env bash
set -euo pipefail

# Activate virtual environment based on OS type
activate_venv() {
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    . .venv/Scripts/activate
  else
    . .venv/bin/activate
  fi
}

# Create the venv if it doesn't exist yet
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python -m venv .venv
  activate_venv
  python -m pip install --upgrade pip --quiet
else
  activate_venv
fi

# Always sync packages in case requirements.txt changed since last run.
# This prevents "ModuleNotFoundError" when new dependencies are added.
if [ -f requirements.txt ]; then
  echo "Syncing packages..."
  pip install -r requirements.txt --quiet
fi

echo "Starting server..."
python app.py