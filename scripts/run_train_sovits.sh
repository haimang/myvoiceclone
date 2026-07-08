#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-ai-voiceclone}"

DRY_RUN=0
DATASET_ID=""
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=1
  else
    DATASET_ID="$arg"
  fi
done

if [ -z "$DATASET_ID" ]; then
  echo "Error: Dataset ID argument required."
  echo "Usage: ./scripts/run_train_sovits.sh [DATASET_ID] [--dry-run]"
  exit 1
fi

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would train So-VITS model inside $CONTAINER on dataset: $DATASET_ID"
  exit 0
fi

echo "Running training inside $CONTAINER on dataset $DATASET_ID..."
docker exec "$CONTAINER" python -m myvoiceclone.cli train sovits "$DATASET_ID"
