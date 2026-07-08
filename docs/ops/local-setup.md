# Local Setup and Developer Onboarding Guide

This guide describes the NF1 container-only runtime for `myvoiceclone`.

## 1. Runtime Contract

`myvoiceclone` is not run from a host Python virtual environment. The host provides only:

- the Git checkout,
- Docker and the NVIDIA container runtime,
- bind-mounted runtime data under `.data/`,
- the external API port `658`.

All application commands run inside the dedicated `ai-voiceclone` container.

## 2. Build and Start

```bash
./scripts/bootstrap_env.sh
```

Equivalent explicit commands:

```bash
docker compose -f infra/docker/compose.voiceclone.yaml build ai-voiceclone
docker compose -f infra/docker/compose.voiceclone.yaml up -d ai-voiceclone
```

The API listens on the host at:

```bash
curl http://127.0.0.1:658/health
```

Expected response:

```json
{"status":"healthy","version":"1.0.0"}
```

## 3. Container CLI

Run CLI commands via `docker exec`:

```bash
docker exec ai-voiceclone python -m myvoiceclone.cli init-db
docker exec ai-voiceclone python -m myvoiceclone.cli vec-health
docker exec ai-voiceclone python -m myvoiceclone.cli run preprocess-all /app/data/raw/sample.wav
docker exec ai-voiceclone python -m myvoiceclone.cli train sovits my_dataset
```

The helper scripts are wrappers around the same container boundary:

```bash
./scripts/run_preprocess.sh /app/data/raw/sample.wav
./scripts/run_train_sovits.sh my_dataset
```

## 4. Data and Configuration

The compose file mounts project-local runtime data:

| Host path | Container path |
|---|---|
| `.data/db` | `/app/.data/db` |
| `.data/artifacts` | `/app/data/artifacts` |
| `.data/raw` | `/app/data/raw` |
| `.data/models` | `/app/models` |
| `.data/test-runs` | `/app/test-runs` |
| `configs` | `/app/configs:ro` |

The service publishes only:

```text
0.0.0.0:658 -> 658/tcp
```

No SSH, debug, vLLM, or auxiliary ports are part of the `myvoiceclone` runtime contract.

## 5. Mock Mode vs. Real Mode

`MOCK_ADAPTERS=false` is the default in the compose runtime. For offline mock workflows:

```bash
MOCK_ADAPTERS=true docker compose -f infra/docker/compose.voiceclone.yaml up -d ai-voiceclone
```

Known real-mode limits remain unchanged by NF1:

- Real XTTS inference can run only when Coqui/Torch/model cache requirements are satisfied.
- Real So-VITS/RVC training is still not implemented in the current adapters.
- Objective quality metrics are still placeholder/mock unless a later live-eval plan replaces them.

## 6. Tests

Run tests inside the container:

```bash
docker exec ai-voiceclone python -m pytest -q
```

Host Python test execution is not a valid NF1 closure signal.
