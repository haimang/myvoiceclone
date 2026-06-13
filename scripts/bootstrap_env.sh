#!/usr/bin/env bash
set -e

DRY_RUN=0
for arg in "$@"; do
  if [ "$arg" == "--dry-run" ]; then
    DRY_RUN=1
  fi
done

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would bootstrap virtual environment and install requirements."
  exit 0
fi

echo "Bootstrapping virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -e .
echo "Environment bootstrapped successfully."
