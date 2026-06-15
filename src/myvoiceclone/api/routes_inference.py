import sqlite3
from fastapi import APIRouter, Depends
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import InferenceRequest, ModelRunResponse, RealInferenceRequestBody, ArtifactResponse
# V5 fix: replaced direct pipeline import with domain service
from myvoiceclone.services import service_synth_xtts, service_run_real_inference
from myvoiceclone.errors import PipelineError, ValidationError

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
        raise PipelineError("Inference failed", code="inference_failed", detail={"reason": str(e)})


@router.post("/real", response_model=ArtifactResponse)
def perform_real_inference(req: RealInferenceRequestBody, db: sqlite3.Connection = Depends(get_db)):
    try:
        artifact = service_run_real_inference(
            conn=db,
            text=req.text,
            reference_artifact_id=req.reference_artifact_id,
            model_id=req.model_id,
            source_artifact_id=req.source_artifact_id,
            language=req.language,
            adapter_mode=req.adapter_mode,
            config=req.config,
        )
        return artifact
    except Exception as e:
        message = str(e)
        code = "inference_failed"
        if "not found" in message.lower():
            code = "artifact_not_found"
        elif "unsupported kind" in message.lower():
            code = "artifact_type_unsupported"
        elif "model" in message.lower() and "download" in message.lower():
            code = "inference_model_unavailable"
        raise ValidationError(message or "Real inference failed", code=code)
