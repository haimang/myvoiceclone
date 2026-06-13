import uuid
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import ModelRunResponse, JobResponse
from myvoiceclone.domain.entities import Job
from myvoiceclone.domain.states import JobStatus
from myvoiceclone.storage.repositories import ModelRunRepository, JobRepository
from pydantic import BaseModel

router = APIRouter(prefix="/training", tags=["training"])

class TrainJobCreate(BaseModel):
    dataset_id: str
    model_name: str
    config: Dict[str, Any]

@router.get("/runs", response_model=List[ModelRunResponse])
def list_runs(db: sqlite3.Connection = Depends(get_db)):
    repo = ModelRunRepository(db)
    # ModelRunRepository doesn't have list_all by default, let's implement a quick raw query or fetch
    cursor = db.cursor()
    cursor.execute("SELECT id FROM model_runs;")
    rows = cursor.fetchall()
    runs = []
    for r in rows:
        run = repo.get_by_id(r["id"])
        if run:
            runs.append(run)
    return runs

@router.get("/runs/{run_id}", response_model=ModelRunResponse)
def get_run(run_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = ModelRunRepository(db)
    run = repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Model run not found")
    return run

@router.post("/jobs", response_model=JobResponse)
def create_training_job(req: TrainJobCreate, db: sqlite3.Connection = Depends(get_db)):
    job_repo = JobRepository(db)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = Job(
        id=job_id,
        name="train_sovits",
        status=JobStatus.PENDING.value,
        payload_json={
            "dataset_id": req.dataset_id,
            "model_name": req.model_name,
            "config": req.config
        }
    )
    job_repo.save(job)
    db.commit()
    return job
