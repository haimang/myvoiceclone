# Local Setup and Developer Onboarding Guide

This guide describes how to set up `myvoiceclone` locally, configure the system, and execute it using Docker containers.

---

## 1. Installation

### 1.1 Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `ffmpeg` installed on your system path
- SQLite (supported natively in Python)

### 1.2 Virtual Environment Setup
Run the bootstrap script to create a virtualenv and install the package in editable mode:
```bash
./scripts/bootstrap_env.sh
source venv/bin/activate
```

---

## 2. Configuration (`configs/local.yaml`)

The file `configs/local.yaml` controls local workspace directories, database location, and security flags.

### Configuration Fields:
- `db_path`: Path to SQLite database file. Defaults to `db/myvoiceclone.sqlite`.
- `artifact_root`: Storage location for audio files and training checkpoints. Defaults to `data/artifacts`.
- `models_dir`: Target directory for downloaded base model weights. Defaults to `models`.
- `security.enabled`: Set `true` to enable local release gate policy checking. Defaults to `false`.

Example:
```yaml
db_path: "db/myvoiceclone.sqlite"
artifact_root: "data/artifacts"
models_dir: "models"
security:
  enabled: true
```

---

## 3. Mock Mode vs. Live GPU Mode

`myvoiceclone` adopts a decoupling architecture:
- **Mock Mode (Default & Testing)**:
  - All neural network processing modules (pyannote, Demucs, Whisper, RVC, So-VITS, XTTS) run via fake mock adapters.
  - This mode requires zero GPU, zero neural weights, and executes instantly.
  - Recommended for unit tests, pipeline debugging, API/CLI development, and system integrations.
- **Live GPU Mode**:
  - Requires GPU hardware acceleration, CUDA drivers, and base models downloaded under `models/base`.
  - To run in live mode, execute CLI commands or start the API with actual model configs.

To download model weights:
```bash
./scripts/download_models.sh
```

---

## 4. Docker Container Execution

You can build and execute the preprocessing and training pipelines inside isolated Docker containers using the provided Compose configuration.

### 4.1 Set Environment Variables (`.env`)
Create a `.env` file in the project root:
```env
DB_PATH=db/myvoiceclone.sqlite
ARTIFACT_ROOT=data/artifacts
MODELS_DIR=models
```

### 4.2 Run Preprocessing Container
```bash
docker compose -f infra/docker/compose.yaml build preprocess
docker compose -f infra/docker/compose.yaml run preprocess ingest /app/data/raw/my_sample.wav
```

### 4.3 Run Training Container (with NVIDIA GPU Access)
```bash
docker compose -f infra/docker/compose.yaml build train
docker compose -f infra/docker/compose.yaml run train train sovits --dataset my_dataset
```
