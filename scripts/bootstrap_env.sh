#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/compose.voiceclone.yaml}"
SERVICE="${SERVICE:-ai-voiceclone}"
CONTAINER="${CONTAINER:-ai-voiceclone}"

DRY_RUN=0
for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=1
  fi
done

if [ $DRY_RUN -eq 1 ]; then
  echo "[Dry-run] Would build ai-voiceclone container image and start the dedicated runtime."
  echo "[Dry-run] Compose file: $COMPOSE_FILE"
  echo "[Dry-run] Dependency probes run inside container: myvoiceclone fastapi sqlite_vec torch torchaudio TTS"
  exit 0
fi

mkdir -p .data/db .data/artifacts .data/raw .data/test-runs .data/models

echo "Building ai-voiceclone image..."
docker compose -f "$COMPOSE_FILE" build "$SERVICE"

echo "Starting ai-voiceclone container..."
docker compose -f "$COMPOSE_FILE" up -d "$SERVICE"

echo "Running container dependency probes..."
docker exec "$CONTAINER" python - <<'PY'
import importlib.util
for name in ("myvoiceclone", "fastapi", "sqlite_vec", "torch", "torchaudio", "TTS"):
    print(f"{name}: {'ok' if importlib.util.find_spec(name) else 'missing'}")
PY
echo "ai-voiceclone container environment bootstrapped successfully."
