#!/usr/bin/env bash
set -e

DRY_RUN=0
for arg in "$@"; do
  if [ "$arg" == "--dry-run" ]; then
    DRY_RUN=1
  fi
done

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would download RVC, XTTS, So-VITS base models and checkpoint weights."
  exit 0
fi

echo "Downloading base models..."
mkdir -p models/pretrained
# In a live environment, download via wget or curl
echo "Downloaded models placeholders successfully."
