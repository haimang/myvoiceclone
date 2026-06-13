"""
domain/services.py — Domain service orchestration layer.

This module is the ONLY permitted bridge between the API/CLI layer and the
pipelines/eval modules. API routes and CLI commands MUST orchestrate all
pipeline and evaluation calls through this layer.

Architecture rule (final-execution-plan.md §12.3):
    api | domain services, jobs
    cli | domain services, jobs
    pipelines MUST NOT be imported directly by api or cli

V4 fix (domain/services.py was missing): Creates this module to serve as the
canonical orchestration interface, eliminating the 5 layer boundary violations
found in api/routes_datasets.py, api/routes_inference.py, api/routes_reports.py,
cli.py:221, and cli.py:250.
"""
from __future__ import annotations

import sqlite3
import logging
from typing import Optional, Dict, Any

from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.config import resolve_artifact_root
from myvoiceclone.storage.sqlite import get_connection

logger = logging.getLogger("myvoiceclone.domain.services")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: shared artifact store factory
# ─────────────────────────────────────────────────────────────────────────────

def _make_artifact_store(conn: sqlite3.Connection) -> ArtifactStore:
    """Create an ArtifactStore with config-resolved artifact root."""
    return ArtifactStore(conn, resolve_artifact_root())


# ─────────────────────────────────────────────────────────────────────────────
# Dataset Services
# ─────────────────────────────────────────────────────────────────────────────

def service_export_dataset(
    conn: sqlite3.Connection,
    dataset_id: str,
    name: str,
) -> Any:
    """Freeze/export a dataset — the only permitted entry point for dataset freeze.

    Replaces direct pipeline imports in:
    - api/routes_datasets.py (formerly imported run_export_dataset directly)
    - cli.py (formerly imported run_export_dataset directly)
    """
    from myvoiceclone.pipelines.export_dataset import run_export_dataset
    artifact_store = _make_artifact_store(conn)
    return run_export_dataset(conn, artifact_store, dataset_id, name=name)


# ─────────────────────────────────────────────────────────────────────────────
# Training Services
# ─────────────────────────────────────────────────────────────────────────────

def service_train_rvc(
    conn: sqlite3.Connection,
    dataset_id: str,
    model_name: str,
    config: Dict[str, Any] = None,
    model_run_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Any:
    """Train an RVC voice clone model."""
    from myvoiceclone.pipelines.train import run_train_rvc
    artifact_store = _make_artifact_store(conn)
    return run_train_rvc(
        conn=conn,
        artifact_store=artifact_store,
        dataset_id=dataset_id,
        model_name=model_name,
        config=config or {},
        model_run_id=model_run_id,
        job_id=job_id,
    )


def service_train_sovits(
    conn: sqlite3.Connection,
    dataset_id: str,
    model_name: str,
    config: Dict[str, Any] = None,
    model_run_id: Optional[str] = None,
    resume_from_checkpoint_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Any:
    """Train a So-VITS-SVC voice clone model."""
    from myvoiceclone.pipelines.train import run_train_sovits
    artifact_store = _make_artifact_store(conn)
    return run_train_sovits(
        conn=conn,
        artifact_store=artifact_store,
        dataset_id=dataset_id,
        model_name=model_name,
        config=config or {},
        model_run_id=model_run_id,
        resume_from_checkpoint_id=resume_from_checkpoint_id,
        job_id=job_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inference Services
# ─────────────────────────────────────────────────────────────────────────────

def service_synth_xtts(
    conn: sqlite3.Connection,
    speaker_id: str,
    text: str,
    config: Dict[str, Any] = None,
    job_id: Optional[str] = None,
) -> Any:
    """Synthesize speech via XTTS (TTS inference).

    Replaces direct pipeline import in api/routes_inference.py.
    """
    from myvoiceclone.pipelines.train import run_synth_xtts
    artifact_store = _make_artifact_store(conn)
    return run_synth_xtts(
        conn=conn,
        artifact_store=artifact_store,
        speaker_id=speaker_id,
        text=text,
        config=config or {},
        job_id=job_id,
    )


def service_run_real_inference(
    conn: sqlite3.Connection,
    text: str,
    reference_artifact_id: str,
    model_id: str,
    config: Dict[str, Any] = None,
    source_artifact_id: Optional[str] = None,
    language: str = "en",
    adapter_mode: str = "real",
) -> Any:
    from myvoiceclone.pipelines.infer_real import RealInferenceRequest, run_real_inference
    artifact_store = _make_artifact_store(conn)
    return run_real_inference(
        conn,
        artifact_store,
        RealInferenceRequest(
            text=text,
            reference_artifact_id=reference_artifact_id,
            model_id=model_id,
            source_artifact_id=source_artifact_id,
            language=language,
            adapter_mode=adapter_mode,
            config=config or {},
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation / Report Services
# ─────────────────────────────────────────────────────────────────────────────

def service_generate_baseline_report(
    conn: sqlite3.Connection,
    report_id: str,
    model_run_ids: list,
) -> Any:
    """Generate a baseline evaluation report.

    Replaces direct eval import in api/routes_reports.py.
    """
    from myvoiceclone.eval.report import generate_baseline_report
    artifact_store = _make_artifact_store(conn)
    return generate_baseline_report(conn, artifact_store, report_id, model_run_ids)


def service_generate_train_report(
    conn: sqlite3.Connection,
    report_id: str,
    model_run_id: str,
) -> Any:
    """Generate a training evaluation report."""
    from myvoiceclone.eval.report import generate_train_report
    artifact_store = _make_artifact_store(conn)
    return generate_train_report(conn, artifact_store, report_id, model_run_id)


def service_generate_subjective_report(
    conn: sqlite3.Connection,
    report_id: str,
    run_id: str,
    abx_score: float,
    mos_score: float,
    reviewer: str,
    comment: str = "",
    sample_artifact_id: Optional[str] = None,
) -> Any:
    from myvoiceclone.eval.subjective import generate_subjective_report
    artifact_store = _make_artifact_store(conn)
    return generate_subjective_report(
        conn,
        artifact_store,
        report_id=report_id,
        run_id=run_id,
        abx_score=abx_score,
        mos_score=mos_score,
        reviewer=reviewer,
        comment=comment,
        sample_artifact_id=sample_artifact_id,
    )


def service_evaluate_long_train_gate(
    conn: sqlite3.Connection,
    dataset_id: str,
    baseline_report_id: str,
) -> Any:
    """Evaluate the long-train gate (passes/fails a model run for release)."""
    from myvoiceclone.eval.report import evaluate_long_train_gate
    return evaluate_long_train_gate(conn, dataset_id, baseline_report_id)


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing Pipeline Services (for individual step dispatch)
# ─────────────────────────────────────────────────────────────────────────────

def service_ingest(
    conn: sqlite3.Connection,
    filepath: str,
    job_id: Optional[str] = None,
) -> Any:
    """Ingest an audio file into the system."""
    from myvoiceclone.pipelines.ingest import run_ingest
    from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
    artifact_store = _make_artifact_store(conn)
    return run_ingest(conn, artifact_store, FFmpegAdapter(), filepath, job_id=job_id)


def service_preprocess_all(
    conn: sqlite3.Connection,
    filepath: str,
    job_id: Optional[str] = None,
    min_duration: float = 2.0,
    max_duration: float = 10.0,
    min_quality_score: float = 0.6,
) -> Any:
    """Run the full preprocess chain: ingest→diarize→slice→clean→transcribe→score."""
    from myvoiceclone.pipelines.ingest import run_ingest
    from myvoiceclone.pipelines.diarize import run_diarize
    from myvoiceclone.pipelines.slice import run_slice
    from myvoiceclone.pipelines.clean import run_clean
    from myvoiceclone.pipelines.transcribe import run_transcribe
    from myvoiceclone.pipelines.score import run_score
    from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
    from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
    from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
    from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter
    artifact_store = _make_artifact_store(conn)
    rec = run_ingest(conn, artifact_store, FFmpegAdapter(), filepath, job_id=job_id)
    run_diarize(conn, artifact_store, PyannoteAdapter(), rec.id, job_id=job_id)
    run_slice(conn, artifact_store, FFmpegAdapter(), rec.id, min_duration=min_duration, max_duration=max_duration, job_id=job_id)
    run_clean(conn, artifact_store, DemucsAdapter(), rec.id, job_id=job_id)
    run_transcribe(conn, artifact_store, WhisperAdapter(), rec.id, job_id=job_id)
    run_score(conn, rec.id, min_quality_score=min_quality_score)
    return rec
