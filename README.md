# MyVoiceClone: High-Fidelity Voice Cloning Workbench

`myvoiceclone` is a local engineering workbench designed for high-fidelity voice cloning, featuring step-by-step processing pipelines, rigorous evaluation metrics, and local governance policies.

---

## 1. Quickstart (Mock Flow)

For fast development, testing, and verifying the entire pipeline without requiring GPU, network, or actual voice data:

### 1.1 Bootstrap Environment
```bash
./scripts/bootstrap_env.sh
source venv/bin/activate
```

### 1.2 Initialize Database
```bash
mvc init-db
```

### 1.3 Verify Extension Loading & Vector Store Health
```bash
mvc vec-health
```

### 1.4 Preprocess Audio (Ingest & Diarize & Transcribe & Score)
```bash
mvc ingest [WAV_FILEPATH]
# Or run end-to-end preprocess:
# mvc run diarize RECORDING_ID
```

### 1.5 Dataset Creation & Freezing
```bash
# Curate keeping keep-status segments
mvc dataset create first-build --filter keep
mvc dataset freeze first-build
```

### 1.6 Training Models
```bash
mvc train sovits --dataset first-build --profile long
```

### 1.7 Objective & Subjective Evaluation
```bash
mvc eval [MODEL_RUN_ID] --suite default
mvc report show [REPORT_ID]
```

### 1.8 Release Gate and Audit Trace
```bash
# Query audit trace for full path lineage of a recording
mvc audit recording RECORDING_ID
```

---

## 2. Local Setup and Advanced Usage

For complete developer onboarding instructions, base model downloading details, and Docker container support, please refer to the detailed documentation:
- [Local Setup and Onboarding Guide](file:///root/workspace/myvoiceclone/docs/ops/local-setup.md)
- [Security and Governance Policies](file:///root/workspace/myvoiceclone/docs/ops/security-governance.md)
- [API OpenAPI Specifications](file:///root/workspace/myvoiceclone/docs/api/openapi.md)
- [P0-P8 Action Plan Index](file:///root/workspace/myvoiceclone/docs/plan/first-build/index.md)

---

## 3. Running Tests

To execute the complete unit and integration tests (including the capstone mock journey):
```bash
./venv/bin/pytest
```
