#!/usr/bin/env bash
set -e

DRY_RUN=0
for arg in "$@"; do
  if [ "$arg" == "--dry-run" ]; then
    DRY_RUN=1
  fi
done

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would prepare model manifest for XTTS-v2, RVC, and So-VITS weights."
  echo "[Dry-run] XTTS-v2 source=https://huggingface.co/coqui/XTTS-v2 license=Coqui Public Model License cache=${MODELS_DIR:-models}"
  exit 0
fi

echo "Downloading base models..."
mkdir -p models/pretrained
# In a live environment, download via wget or curl
cat > models/pretrained/first-test-model-manifest.json <<'JSON'
{
  "xtts_v2": {
    "model_id": "tts_models/multilingual/multi-dataset/xtts_v2",
    "source": "https://huggingface.co/coqui/XTTS-v2",
    "license": "Coqui Public Model License",
    "first_test_use": "local research validation only"
  }
}
JSON
echo "Model manifest written to models/pretrained/first-test-model-manifest.json."
