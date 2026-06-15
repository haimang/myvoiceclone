import json
import sqlite3
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from myvoiceclone.api.audio_validation import validate_reference_audio_bytes
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import (
    ArtifactResponse,
    FirstTestRunCreate,
    FirstTestRunResponse,
    JobResponse,
    PromoteReferenceAudioRequest,
    RunStatusResponse,
    StartEvalRequest,
    StartInferenceRequest,
    StartPreprocessRequest,
)
from myvoiceclone.config import resolve_artifact_root, resolve_db_path
from myvoiceclone.domain.entities import Job
from myvoiceclone.domain.states import JobStatus
from myvoiceclone.errors import ResourceNotFoundError, ValidationError
from myvoiceclone.ids import new_id
from myvoiceclone.jobs.runner import JobRunner
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.repositories import JobRepository, json_to_dict
from myvoiceclone.storage.sqlite import get_connection

router = APIRouter(prefix="/runs", tags=["runs"])


def _links(run_id: str) -> Dict[str, str]:
    return {
        "self": f"/api/runs/{run_id}",
        "status": f"/api/runs/{run_id}/status",
        "upload_audio": f"/api/runs/{run_id}/audio",
        "upload_reference_audio": f"/api/runs/{run_id}/reference-audio",
        "trace": f"/api/audit/trace?subject_type=job&subject_id={run_id}",
    }


def _model_payload(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _save_job(db: sqlite3.Connection, name: str, payload: Dict[str, Any], *, run_id: str, status: str = JobStatus.PENDING.value) -> Job:
    job = Job(
        id=new_id(),
        name=name,
        status=status,
        payload_json=payload,
        subject_type="first_test_run",
        subject_id=run_id,
        pipeline="first-test",
    )
    JobRepository(db).save(job)
    db.commit()
    return job


def _run_job_in_background(job_id: str) -> None:
    conn = get_connection(resolve_db_path(), load_vec=True)
    try:
        artifact_store = ArtifactStore(conn, resolve_artifact_root())
        JobRunner(conn=conn, artifact_store=artifact_store).run(job_id)
    finally:
        conn.close()


@router.post("", response_model=FirstTestRunResponse)
def create_run(req: FirstTestRunCreate, db: sqlite3.Connection = Depends(get_db)):
    run_id = new_id()
    job = Job(
        id=run_id,
        name="first_test_run",
        status=JobStatus.PENDING.value,
        payload_json={"name": req.name, "adapter_mode": req.adapter_mode, "config": req.config},
        subject_type="first_test_run",
        subject_id=run_id,
        pipeline="first-test",
    )
    JobRepository(db).save(job)
    db.commit()
    return FirstTestRunResponse(
        id=run_id,
        status=job.status,
        name=req.name,
        adapter_mode=req.adapter_mode,
        config=req.config,
        links=_links(run_id),
    )


@router.get("/{run_id}", response_model=FirstTestRunResponse)
def get_run(run_id: str, db: sqlite3.Connection = Depends(get_db)):
    job = JobRepository(db).get_by_id(run_id)
    if not job or job.name != "first_test_run":
        raise ResourceNotFoundError("Run not found", code="run_not_found", detail={"run_id": run_id})
    return FirstTestRunResponse(
        id=run_id,
        status=job.status,
        name=job.payload_json.get("name", "first-test-run"),
        adapter_mode=job.payload_json.get("adapter_mode", "real"),
        config=job.payload_json.get("config", {}),
        links=_links(run_id),
    )


@router.post("/{run_id}/audio", response_model=ArtifactResponse)
async def upload_audio(run_id: str, file: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    content = await file.read()
    if not content:
        raise ValidationError("Uploaded audio is empty", code="reference_audio_invalid")
    artifact_store = ArtifactStore(db, resolve_artifact_root())
    artifact = artifact_store.create_artifact(
        name=file.filename or f"{run_id}.wav",
        content=content,
        artifact_type="uploaded_audio",
        metadata_json={
            "run_id": run_id,
            "upload_filename": file.filename,
            "content_type": file.content_type,
            "adapter_mode": "real",
            "metric_source": "upload",
        },
    )
    db.commit()
    return artifact


@router.post("/{run_id}/reference-audio", response_model=ArtifactResponse)
async def upload_reference_audio(run_id: str, file: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    content = await file.read()
    validation = validate_reference_audio_bytes(content)
    artifact_store = ArtifactStore(db, resolve_artifact_root())
    artifact = artifact_store.create_artifact(
        name=file.filename or f"{run_id}_reference.wav",
        content=content,
        artifact_type="reference_audio",
        metadata_json={
            "run_id": run_id,
            "upload_filename": file.filename,
            "content_type": file.content_type,
            "adapter_mode": "real",
            "metric_source": "reference_upload",
            "duration_sec": validation.duration_sec,
            "sample_rate": validation.sample_rate,
            "channels": validation.channels,
            "max_amplitude": validation.max_amplitude,
            "rms": validation.rms,
        },
    )
    db.commit()
    return artifact


@router.post("/{run_id}/reference-audio/from-artifact", response_model=ArtifactResponse)
def promote_reference_audio(run_id: str, req: PromoteReferenceAudioRequest, db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    artifact_store = ArtifactStore(db, resolve_artifact_root())
    source = artifact_store.get_artifact(req.artifact_id)
    if not source:
        raise ResourceNotFoundError("Artifact not found", code="artifact_not_found", detail={"artifact_id": req.artifact_id})
    with open(artifact_store.get_absolute_path(source), "rb") as handle:
        content = handle.read()
    validation = validate_reference_audio_bytes(content)
    artifact = artifact_store.create_artifact(
        name=req.name or source.name or f"{run_id}_reference.wav",
        content=content,
        artifact_type="reference_audio",
        parent_artifact_id=source.id,
        metadata_json={
            "run_id": run_id,
            "source_artifact_id": source.id,
            "source_artifact_type": source.artifact_type,
            "adapter_mode": "real",
            "metric_source": "reference_promotion",
            "duration_sec": validation.duration_sec,
            "sample_rate": validation.sample_rate,
            "channels": validation.channels,
            "max_amplitude": validation.max_amplitude,
            "rms": validation.rms,
        },
    )
    db.commit()
    return artifact


@router.post("/{run_id}/preprocess", response_model=JobResponse)
def start_preprocess(run_id: str, req: StartPreprocessRequest, db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    artifact_store = ArtifactStore(db, resolve_artifact_root())
    artifact = artifact_store.get_artifact(req.audio_artifact_id)
    if not artifact:
        raise ResourceNotFoundError("Audio artifact not found", code="artifact_not_found", detail={"artifact_id": req.audio_artifact_id})
    job = _save_job(
        db,
        "preprocess_all",
        {
            "run_id": run_id,
            "audio_artifact_id": artifact.id,
            "filepath": artifact_store.get_absolute_path(artifact),
            "min_duration": req.min_duration,
            "max_duration": req.max_duration,
            "min_quality_score": req.min_quality_score,
        },
        run_id=run_id,
    )
    return job


@router.post("/{run_id}/infer", response_model=JobResponse)
def start_inference(
    run_id: str,
    req: StartInferenceRequest,
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_db),
):
    get_run(run_id, db)
    job = _save_job(
        db,
        "infer_real",
        {"run_id": run_id, **_model_payload(req)},
        run_id=run_id,
    )
    if req.start_immediately:
        background_tasks.add_task(_run_job_in_background, job.id)
    return job


@router.post("/{run_id}/eval", response_model=JobResponse)
def start_eval(run_id: str, req: StartEvalRequest, db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    job = _save_job(
        db,
        "eval_first_test",
        {"run_id": run_id, **_model_payload(req)},
        run_id=run_id,
    )
    return job


@router.get("/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(run_id: str, db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT * FROM jobs
        WHERE id = ? OR subject_id = ? OR payload_json LIKE ?
        ORDER BY created_at, id;
        """,
        (run_id, run_id, f"%{run_id}%"),
    )
    jobs = [dict(row) for row in cursor.fetchall()]
    job_ids = [job["id"] for job in jobs]

    events: List[Dict[str, Any]] = []
    failure_summary: Dict[str, Any] = {}
    if job_ids:
        placeholders = ",".join("?" for _ in job_ids)
        cursor.execute(f"SELECT * FROM job_events WHERE job_id IN ({placeholders}) ORDER BY created_at, id;", job_ids)
        for row in cursor.fetchall():
            event = dict(row)
            event["metadata_json"] = json_to_dict(event.get("metadata_json"))
            events.append(event)
            if event["event_type"] in {"fail", "step_failed", "failure_summary"}:
                failure_summary[event["job_id"]] = event["metadata_json"] or {"message": event.get("message")}

    cursor.execute(
        """
        SELECT * FROM artifacts
        WHERE metadata_json LIKE ? OR job_id IN (SELECT id FROM jobs WHERE subject_id = ?)
           OR created_by_job_id IN (SELECT id FROM jobs WHERE subject_id = ?)
        ORDER BY created_at, id;
        """,
        (f"%{run_id}%", run_id, run_id),
    )
    artifacts = []
    for row in cursor.fetchall():
        art = dict(row)
        art["metadata_json"] = json_to_dict(art.get("metadata_json"))
        art["links"] = {
            "self": f"/api/artifacts/{art['id']}",
            "download": f"/api/artifacts/{art['id']}/download",
        }
        artifacts.append(art)

    terminal = [job["status"] for job in jobs if job["id"] != run_id]
    if any(status in {"failed", "cancelled", "canceled"} for status in terminal):
        status = "failed"
    elif terminal and all(status in {"completed", "succeeded"} for status in terminal):
        status = "completed"
    else:
        status = "running" if any(status == "running" for status in terminal) else "pending"

    return RunStatusResponse(
        run_id=run_id,
        status=status,
        jobs=jobs,
        events=events,
        artifacts=artifacts,
        failure_summary=failure_summary,
        links=_links(run_id),
    )
