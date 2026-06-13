import os
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter
from myvoiceclone.domain.entities import Artifact
from myvoiceclone.storage.artifact_store import ArtifactStore

SUPPORTED_XTTS_MODEL_IDS = {"tts_models/multilingual/multi-dataset/xtts_v2"}


@dataclass
class RealInferenceRequest:
    text: str
    reference_artifact_id: str
    model_id: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    source_artifact_id: Optional[str] = None
    language: str = "en"
    adapter_mode: str = "real"
    config: Dict[str, Any] = None


def validate_inference_request(request: RealInferenceRequest) -> None:
    if not request.text or not request.text.strip():
        raise ValueError("Inference request missing required text")
    if not request.reference_artifact_id:
        raise ValueError("Inference request missing required reference_artifact_id")
    if not request.model_id:
        raise ValueError("Inference request missing required model_id")
    if request.model_id not in SUPPORTED_XTTS_MODEL_IDS:
        raise ValueError(
            f"Unsupported first-test real inference model_id '{request.model_id}'. "
            f"Supported model ids: {sorted(SUPPORTED_XTTS_MODEL_IDS)}"
        )


def run_real_inference(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    request: RealInferenceRequest,
    *,
    adapter: Optional[Any] = None,
    job_id: Optional[str] = None,
) -> Artifact:
    validate_inference_request(request)
    reference_artifact = artifact_store.get_artifact(request.reference_artifact_id)
    if not reference_artifact:
        raise ValueError(f"Reference artifact {request.reference_artifact_id} not found")

    adapter = adapter or XttsAdapter(model_id=request.model_id)
    tmp_dir = os.path.join(artifact_store.root_dir, "_tmp_inference")
    os.makedirs(tmp_dir, exist_ok=True)
    out_path = os.path.join(tmp_dir, f"infer_{uuid.uuid4().hex[:12]}.wav")
    reference_path = artifact_store.get_absolute_path(reference_artifact)

    metadata = adapter.synth_to_file(
        request.text,
        reference_path,
        out_path,
        language=request.language,
    )

    with open(out_path, "rb") as f:
        audio_bytes = f.read()
    if not audio_bytes:
        raise RuntimeError("Inference adapter produced an empty wav artifact")

    artifact = artifact_store.create_artifact(
        name=os.path.basename(out_path),
        content=audio_bytes,
        artifact_type="rendered_audio",
        parent_artifact_id=reference_artifact.id,
        job_id=job_id,
        metadata_json={
            "adapter_mode": metadata.get("adapter_mode", request.adapter_mode),
            "metric_source": "inference_output",
            "text": request.text,
            "language": request.language,
            "model": request.model_id,
            "input_refs": {
                "reference_artifact_id": reference_artifact.id,
                "source_artifact_id": request.source_artifact_id,
            },
            "duration_sec": metadata.get("duration_sec"),
            "license": metadata.get("license"),
            "provenance": metadata.get("source") or metadata.get("provenance"),
            "device": metadata.get("device"),
            "cache": metadata.get("cache"),
            "tool": metadata.get("tool"),
            "version": metadata.get("version"),
            "config": request.config or {},
        },
    )
    conn.commit()
    return artifact
