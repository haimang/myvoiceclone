#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${RUN_ID:-first-test-$(date -u +%Y%m%dT%H%M%SZ)}"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-.data/test-runs}"
ADAPTER_MODE="${ADAPTER_MODE:-real}"
STATUS="${STATUS:-collected}"
PYTHON_BIN="${PYTHON_BIN:-./venv/bin/python}"

args=(
  -m myvoiceclone.evidence collect
  --run-id "$RUN_ID"
  --output-root "$EVIDENCE_ROOT"
  --adapter-mode "$ADAPTER_MODE"
  --status "$STATUS"
)

if [[ -n "${DB_PATH:-}" ]]; then
  args+=(--db-path "$DB_PATH")
fi

if [[ -n "${ARTIFACT_ROOT:-}" ]]; then
  args+=(--artifact-root "$ARTIFACT_ROOT")
fi

if [[ -n "${SKIP_REASON:-}" ]]; then
  args+=(--skip-reason "$SKIP_REASON")
fi

PACK_DIR="$("$PYTHON_BIN" "${args[@]}")"
"$PYTHON_BIN" -m myvoiceclone.evidence validate "$PACK_DIR" --repo-root "$(pwd)"
echo "$PACK_DIR"
