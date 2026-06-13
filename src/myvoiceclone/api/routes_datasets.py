import uuid
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import DatasetResponse, DatasetCreate
from myvoiceclone.domain.entities import Dataset
from myvoiceclone.storage.repositories import DatasetRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.config import load_local_config
# V5 fix: replaced direct pipeline import with domain service
from myvoiceclone.services import service_export_dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("", response_model=List[DatasetResponse])
def list_datasets(db: sqlite3.Connection = Depends(get_db)):
    repo = DatasetRepository(db)
    return repo.list_all()

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = DatasetRepository(db)
    ds = repo.get_by_id(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

@router.post("", response_model=DatasetResponse)
def create_dataset(req: DatasetCreate, db: sqlite3.Connection = Depends(get_db)):
    repo = DatasetRepository(db)
    ds_id = f"ds_{uuid.uuid4().hex[:12]}"
    ds = Dataset(
        id=ds_id,
        name=req.name,
        status="active",
        filter_json=req.filter_json
    )
    
    # Pre-select matching segments and add them to dataset
    min_quality = req.filter_json.get("min_quality_score", 0.6)
    cursor = db.cursor()
    cursor.execute("SELECT id FROM segments WHERE quality_score >= ? AND cleaned_artifact_id IS NOT NULL;", (min_quality,))
    segments = cursor.fetchall()
    
    repo.save(ds)
    for seg in segments:
        repo.add_segment(ds_id, seg["id"], "train") # Default split, run_export_dataset will re-balance
        
    db.commit()
    return ds

@router.post("/{dataset_id}/freeze", response_model=DatasetResponse)
def freeze_dataset(dataset_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = DatasetRepository(db)
    ds = repo.get_by_id(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        # V5 fix: use domain service instead of direct pipeline call
        frozen_ds = service_export_dataset(conn=db, dataset_id=dataset_id, name=ds.name)
        return frozen_ds
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
