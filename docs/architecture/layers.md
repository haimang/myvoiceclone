# Architecture Layers Specification

This document defines the layers and dependency rules for the `myvoiceclone` project, as frozen in phase P0.

## Layer Dependencies Matrix

| Layer | Allowed Dependencies | Forbidden Dependencies | Core Interfaces / Responsibilities |
| :--- | :--- | :--- | :--- |
| `domain` | stdlib, typing | `storage`, `api`, `adapters`, `FastAPI` | Core entities: `Recording`, `Segment`, `Dataset`, `Job`, `Policy`, state enums. Business rules. |
| `storage` | `domain` DTOs, stdlib `sqlite3`, `sqlalchemy` | `adapters`, `FastAPI` | Persistence mechanisms: repositories, migrations, `VectorStore` protocol, `ArtifactStore`. |
| `pipelines` | `domain`, `storage`, `adapters` protocols | FastAPI route internals | Orchestration of workflow steps: `run_ingest(ctx)`, `run_clean(ctx)`. |
| `adapters` | External tools/libs | `storage` repositories | Wrappers for external tools (FFmpeg, pyannote, Demucs, Whisper, RVC, So-VITS). Outputs normalized DTOs: `DiarizationResult`, `TranscriptResult`, `TrainResult`. |
| `jobs` | `domain`, `storage`, `pipelines` | API response schemas | Asynchronous job execution: queue, runner, event writer. |
| `api` | `domain` services, `jobs` | External tools directly | HTTP entrypoints: route handlers + Pydantic schemas. |
| `cli` | `domain` services, `jobs` | External tools directly | Command line entrypoints: Typer commands. |
| `eval` | `domain`, `storage`, `artifacts` | Training internals | Evaluation metrics and report contracts. |

## Dependency Rules

1. **Downwards Only**: High-level layers (like `api` or `cli`) may depend on domain services and jobs, but lower-level layers (like `domain`) MUST NOT depend on database or presentation details.
2. **Adapter Isolation**: Adapters must encapsulate third-party libraries and command executions completely. They must return clean, standard Python DTOs (Data Transfer Objects) and must not reference storage repositories or project database schemas directly.
3. **No Direct Model/External Calls from API**: The API and CLI must always orchestrate via service or job layer. They are forbidden from calling adapter functions directly.
