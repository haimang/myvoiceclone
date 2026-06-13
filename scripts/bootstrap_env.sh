#!/usr/bin/env bash
set -e

DRY_RUN=0
for arg in "$@"; do
  if [ "$arg" == "--dry-run" ]; then
    DRY_RUN=1
  fi
done

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would bootstrap virtual environment and install myvoiceclone[first-test]."
  echo "[Dry-run] Dependency probes: ffmpeg ffprobe python-import demucs whisper pyannote.audio"
  exit 0
fi

echo "Bootstrapping virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -e ".[first-test]"
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
./venv/bin/python - <<'PY'
import importlib.util
for name in ("demucs", "whisper", "pyannote.audio"):
    print(f"{name}: {'ok' if importlib.util.find_spec(name) else 'missing'}")
PY
echo "Environment bootstrapped successfully."
