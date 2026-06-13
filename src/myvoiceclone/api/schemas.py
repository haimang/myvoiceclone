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

class PreprocessJobCreate(BaseModel):
    filepath: str
    min_duration: float = 2.0
    max_duration: float = 10.0
    min_quality_score: float = 0.6

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

class RealInferenceRequestBody(BaseModel):
    text: str
    reference_artifact_id: str
    model_id: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    source_artifact_id: Optional[str] = None
    language: str = "en"
    adapter_mode: str = "real"
    config: Dict[str, Any] = {}

class ArtifactResponse(BaseModel):
    id: str
    name: str
    uri: str
    sha256: str
    bytes: int
    artifact_type: str
    parent_artifact_id: Optional[str] = None
    job_id: Optional[str] = None
    metadata_json: Dict[str, Any] = {}

class FirstTestRunCreate(BaseModel):
    name: str = "first-test-run"
    adapter_mode: str = "real"
    config: Dict[str, Any] = {}

class FirstTestRunResponse(BaseModel):
    id: str
    status: str
    name: str
    adapter_mode: str
    config: Dict[str, Any] = {}
    links: Dict[str, str] = {}

class StartPreprocessRequest(BaseModel):
    audio_artifact_id: str
    min_duration: float = 2.0
    max_duration: float = 10.0
    min_quality_score: float = 0.6

class StartInferenceRequest(BaseModel):
    text: str
    reference_artifact_id: str
    model_id: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    source_artifact_id: Optional[str] = None
    language: str = "en"
    adapter_mode: str = "real"

class StartEvalRequest(BaseModel):
    inference_artifact_id: str
    reference_artifact_id: Optional[str] = None
    metric_source: str = "smoke_metric"

class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    jobs: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    failure_summary: Dict[str, Any] = {}
    links: Dict[str, str] = {}

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
