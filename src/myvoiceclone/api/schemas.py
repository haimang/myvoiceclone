from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class RecordingResponse(BaseModel):
    id: str
    source_uri: str
    sha256: str
    duration_sec: float
    sample_rate: int
    channels: int
    status: str
    metadata_json: Dict[str, Any]
    created_at: Optional[datetime]

class SegmentResponse(BaseModel):
    id: str
    recording_id: str
    speaker_id: Optional[str]
    start_sec: float
    end_sec: float
    audio_artifact_id: Optional[str]
    cleaned_artifact_id: Optional[str]
    transcript: Optional[str]
    status: str
    quality_score: Optional[float]
    speaker_score: Optional[float]
    noise_score: Optional[float]
    overlap_score: Optional[float]
    metadata_json: Dict[str, Any]
    created_at: Optional[datetime]

class SegmentReviewUpdate(BaseModel):
    status_to: str
    reason: Optional[str]
    reviewer: str

class DatasetCreate(BaseModel):
    name: str
    filter_json: Dict[str, Any]

class DatasetResponse(BaseModel):
    id: str
    name: str
    status: str
    manifest_artifact_id: Optional[str]
    manifest_sha256: Optional[str]
    filter_json: Dict[str, Any]
    created_at: Optional[datetime]
    frozen_at: Optional[datetime]

class JobResponse(BaseModel):
    id: str
    name: str
    status: str
    payload_json: Dict[str, Any]
    type: Optional[str] = None
    params_json: Dict[str, Any] = {}
    subject_type: Optional[str] = None
    subject_id: Optional[str] = None
    pipeline: Optional[str] = None
    requested_by: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_msg: Optional[str]
    created_at: Optional[datetime]

class ModelRunResponse(BaseModel):
    id: str
    name: str
    model_family: Optional[str] = None
    dataset_id: Optional[str]
    status: str
    config_json: Dict[str, Any]
    checkpoint_artifact_id: Optional[str] = None
    env_digest: Dict[str, Any] = {}
    git_commit: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class InferenceRequest(BaseModel):
    speaker_id: str
    text: str
    config: Optional[Dict[str, Any]] = None

class ReportResponse(BaseModel):
    id: str
    name: str
    report_type: str
    kind: Optional[str] = None
    subject_type: Optional[str] = None
    subject_id: Optional[str] = None
    status: Optional[str] = None
    summary_json: Dict[str, Any]
    artifact_id: Optional[str]
    created_at: Optional[datetime]

class ReleaseGateResponse(BaseModel):
    id: str
    model_run_id: str
    passed: bool
    status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    details_json: Dict[str, Any] = {}
    decision_json: Dict[str, Any] = {}
