#!/usr/bin/env bash
set -e

DRY_RUN=0
FILEPATH=""
for arg in "$@"; do
  if [ "$arg" == "--dry-run" ]; then
    DRY_RUN=1
  else
    FILEPATH="$arg"
  fi
done

if [ -z "$FILEPATH" ]; then
  echo "Error: Filepath argument required."
  echo "Usage: ./scripts/run_preprocess.sh [FILEPATH] [--dry-run]"
  exit 1
fi

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would run preprocess pipeline for: $FILEPATH"
  exit 0
fi

echo "Running preprocessing for $FILEPATH..."
./venv/bin/python -m myvoiceclone.cli ingest "$FILEPATH"
