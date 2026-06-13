from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


# ─────────────────────────────────────────────
# Audio probe DTO — returned by torchaudio_io and ffmpeg adapters
# V9 fix: torchaudio_io was returning a bare dict instead of this DTO
# ─────────────────────────────────────────────
@dataclass
class AudioProbe:
    """Typed result of an audio file probe operation."""
    duration_sec: float
    sample_rate: int
    channels: int


@dataclass
class Speaker:
    id: str
    display_name: str
    role: str  # 'owner', 'other', 'unknown'
    created_at: Optional[datetime] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Recording:
    id: str
    source_uri: str
    sha256: str
    duration_sec: float
    sample_rate: int
    channels: int
    status: str
    metadata_json: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

@dataclass
class Segment:
    id: str
    recording_id: str
    speaker_id: Optional[str]
    start_sec: float
    end_sec: float
    audio_artifact_id: Optional[str]
    cleaned_artifact_id: Optional[str]
    transcript: Optional[str]
    status: str
    quality_score: Optional[float] = None
    speaker_score: Optional[float] = None
    noise_score: Optional[float] = None
    overlap_score: Optional[float] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

@dataclass
class Dataset:
    id: str
    name: str
    status: str
    manifest_artifact_id: Optional[str] = None
    manifest_sha256: Optional[str] = None
    filter_json: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    frozen_at: Optional[datetime] = None

@dataclass
class DatasetSegment:
    dataset_id: str
    segment_id: str
    split: str  # 'train', 'val', 'test'

@dataclass
class Job:
    id: str
    name: str
    status: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    payload_json: Dict[str, Any] = field(default_factory=dict)
    error_msg: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class JobEvent:
    id: Optional[int]
    job_id: str
    event_type: str
    status_from: Optional[str]
    status_to: Optional[str]
    message: Optional[str]
    created_at: Optional[datetime] = None

@dataclass
class Artifact:
    id: str
    name: str
    uri: str
    sha256: str
    bytes: int
    artifact_type: str
    parent_artifact_id: Optional[str] = None
    job_id: Optional[str] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

@dataclass
class ModelRun:
    id: str
    name: str
    dataset_id: Optional[str]
    status: str
    config_json: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

@dataclass
class Report:
    id: str
    name: str
    report_type: str
    summary_json: Dict[str, Any] = field(default_factory=dict)
    artifact_id: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class AudioProbe:
    duration_sec: float
    sample_rate: int
    channels: int
    format: str

@dataclass
class DiarizationTurn:
    speaker_id: str
    start_sec: float
    end_sec: float

@dataclass
class TranscriptSegment:
    start_sec: float
    end_sec: float
    text: str
    confidence: float

@dataclass
class SeparationResult:
    cleaned_path: str


@dataclass
class TrainRequest:
    dataset_id: str
    model_name: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainResult:
    model_run_id: str
    status: str  # 'completed', 'failed'
    checkpoint_bytes: bytes
    metrics: Dict[str, float] = field(default_factory=dict)
    error_msg: Optional[str] = None


@dataclass
class SynthRequest:
    text: str
    speaker_id: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthResult:
    status: str  # 'completed', 'failed'
    audio_bytes: bytes
    duration_sec: float
    error_msg: Optional[str] = None


@dataclass
class ConvertRequest:
    model_run_id: str
    source_audio_path: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConvertResult:
    status: str  # 'completed', 'failed'
    audio_bytes: bytes
    duration_sec: float
    error_msg: Optional[str] = None

