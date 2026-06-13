import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import JobResponse
from myvoiceclone.storage.repositories import JobRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.jobs.runner import JobRunner
from myvoiceclone.config import resolve_artifact_root

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
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/run", response_model=JobResponse)
def run_job(job_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
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
        raise HTTPException(status_code=500, detail=f"Job runner execution failed: {str(e)}")
