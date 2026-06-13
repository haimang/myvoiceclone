import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import InferenceRequest, ModelRunResponse
from myvoiceclone.pipelines.train import run_synth_xtts
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.config import load_local_config

router = APIRouter(prefix="/inference", tags=["inference"])

@router.post("", response_model=ModelRunResponse)
def perform_inference(req: InferenceRequest, db: sqlite3.Connection = Depends(get_db)):
    config = load_local_config()
    artifact_store = ArtifactStore(db, config.get("artifact_root", "data/artifacts"))
    
    try:
        run = run_synth_xtts(
            conn=db,
            artifact_store=artifact_store,
            speaker_id=req.speaker_id,
            text=req.text,
            config=req.config or {}
        )
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
