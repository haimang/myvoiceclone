import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import RecordingResponse, JobResponse, PreprocessJobCreate
from myvoiceclone.domain.entities import Job
from myvoiceclone.domain.states import JobStatus
from myvoiceclone.ids import new_id
from myvoiceclone.storage.repositories import RecordingRepository, JobRepository

router = APIRouter(prefix="/recordings", tags=["recordings"])

@router.get("", response_model=List[RecordingResponse])
def list_recordings(db: sqlite3.Connection = Depends(get_db)):
    repo = RecordingRepository(db)
    return [RecordingResponse(**rec.__dict__) for rec in repo.list_all()]

@router.get("/{recording_id}", response_model=RecordingResponse)
def get_recording(recording_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = RecordingRepository(db)
    rec = repo.get_by_id(recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    return RecordingResponse(**rec.__dict__)

@router.post("", response_model=JobResponse)
def create_ingest_job(filepath: str, db: sqlite3.Connection = Depends(get_db)):
    job_repo = JobRepository(db)
    job_id = new_id()
    job = Job(
        id=job_id,
        name="ingest",
        status=JobStatus.PENDING.value,
        payload_json={"filepath": filepath}
    )
    job_repo.save(job)
    db.commit()
    return job


@router.post("/preprocess", response_model=JobResponse)
def create_preprocess_job(request: PreprocessJobCreate, db: sqlite3.Connection = Depends(get_db)):
    if not request.filepath:
        raise HTTPException(status_code=422, detail="filepath is required")

    job_repo = JobRepository(db)
    job_id = new_id()
    job = Job(
        id=job_id,
        name="preprocess_all",
        status=JobStatus.PENDING.value,
        payload_json={
            "filepath": request.filepath,
            "min_duration": request.min_duration,
            "max_duration": request.max_duration,
            "min_quality_score": request.min_quality_score,
        },
    )
    job_repo.save(job)
    db.commit()
    return job
