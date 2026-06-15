import sqlite3
from fastapi import APIRouter, BackgroundTasks, Depends
from typing import List
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import JobResponse
from myvoiceclone.config import resolve_artifact_root, resolve_db_path
from myvoiceclone.errors import PipelineError, ResourceNotFoundError
from myvoiceclone.storage.repositories import JobRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.jobs.runner import JobRunner

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=List[JobResponse])
def list_jobs(db: sqlite3.Connection = Depends(get_db)):
    repo = JobRepository(db)
    return repo.list_all()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise ResourceNotFoundError("Job not found", code="job_not_found", detail={"job_id": job_id})
    return job


def _run_job_background(job_id: str) -> None:
    conn = get_connection(resolve_db_path(), load_vec=True)
    try:
        artifact_store = ArtifactStore(conn, resolve_artifact_root())
        JobRunner(conn=conn, artifact_store=artifact_store).run(job_id)
    finally:
        conn.close()


@router.post("/{job_id}/run", response_model=JobResponse)
def run_job(job_id: str, background_tasks: BackgroundTasks, background: bool = False, db: sqlite3.Connection = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise ResourceNotFoundError("Job not found", code="job_not_found", detail={"job_id": job_id})

    if background:
        background_tasks.add_task(_run_job_background, job_id)
        return job
        
    artifact_store = ArtifactStore(db, resolve_artifact_root())
    
    runner = JobRunner(
        conn=db,
        artifact_store=artifact_store
    )
    
    try:
        runner.run(job_id)
        # Fetch updated job
        return repo.get_by_id(job_id)
    except Exception as e:
        raise PipelineError(
            "Job runner execution failed",
            code="job_execution_failed",
            detail={"job_id": job_id, "reason": str(e)},
        )
