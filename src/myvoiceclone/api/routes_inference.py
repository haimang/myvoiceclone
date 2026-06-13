import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import InferenceRequest, ModelRunResponse
# V5 fix: replaced direct pipeline import with domain service
from myvoiceclone.services import service_synth_xtts

router = APIRouter(prefix="/inference", tags=["inference"])

@router.post("", response_model=ModelRunResponse)
def perform_inference(req: InferenceRequest, db: sqlite3.Connection = Depends(get_db)):
    try:
        # V5 fix: call service layer instead of pipeline directly
        run = service_synth_xtts(
            conn=db,
            speaker_id=req.speaker_id,
            text=req.text,
            config=req.config or {}
        )
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
