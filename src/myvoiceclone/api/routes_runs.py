import json
import sqlite3
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import (
    ArtifactResponse,
    FirstTestRunCreate,
    FirstTestRunResponse,
    JobResponse,
    RunStatusResponse,
    StartEvalRequest,
    StartInferenceRequest,
    StartPreprocessRequest,
)
from myvoiceclone.config import resolve_artifact_root
from myvoiceclone.domain.entities import Job
from myvoiceclone.domain.states import JobStatus
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.repositories import JobRepository, json_to_dict

router = APIRouter(prefix="/runs", tags=["runs"])


def _links(run_id: str) -> Dict[str, str]:
    return {
        "self": f"/api/runs/{run_id}",
        "status": f"/api/runs/{run_id}/status",
        "upload_audio": f"/api/runs/{run_id}/audio",
        "trace": f"/api/audit/trace?subject_type=job&subject_id={run_id}",
    }


def _model_payload(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _save_job(db: sqlite3.Connection, name: str, payload: Dict[str, Any], *, run_id: str, status: str = JobStatus.PENDING.value) -> Job:
    job = Job(
        id=f"job_{uuid.uuid4().hex[:12]}",
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


@router.post("", response_model=FirstTestRunResponse)
def create_run(req: FirstTestRunCreate, db: sqlite3.Connection = Depends(get_db)):
    run_id = f"run_{uuid.uuid4().hex[:12]}"
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
        raise HTTPException(status_code=404, detail="Run not found")
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
        raise HTTPException(status_code=400, detail="Uploaded audio is empty")
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


@router.post("/{run_id}/preprocess", response_model=JobResponse)
def start_preprocess(run_id: str, req: StartPreprocessRequest, db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    artifact_store = ArtifactStore(db, resolve_artifact_root())
    artifact = artifact_store.get_artifact(req.audio_artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Audio artifact not found")
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
def start_inference(run_id: str, req: StartInferenceRequest, db: sqlite3.Connection = Depends(get_db)):
    get_run(run_id, db)
    job = _save_job(
        db,
        "infer_real",
        {"run_id": run_id, **_model_payload(req)},
        run_id=run_id,
    )
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
