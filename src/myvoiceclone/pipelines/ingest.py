import os
import hashlib
import uuid
import shutil
import sqlite3
from myvoiceclone.domain.entities import Recording, Artifact
from myvoiceclone.domain.states import RecordingStatus
from myvoiceclone.storage.repositories import RecordingRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter

def compute_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def run_ingest(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    ffmpeg_adapter: FFmpegAdapter,
    filepath: str,
    job_id: str = None
) -> Recording:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Source file not found: {filepath}")
        
    sha256 = compute_sha256(filepath)
    repo = RecordingRepository(conn)
    
    # Check if duplicate sha256 exists
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM recordings WHERE sha256 = ?;", (sha256,))
    row = cursor.fetchone()
    if row:
        # Return existing recording
        return repo.get_by_id(row["id"])
        
    # Create new recording record
    rec_id = f"rec_{uuid.uuid4().hex[:12]}"
    
    # Probe audio
    probe_info = ffmpeg_adapter.probe(filepath)
    
    # Save original audio to raw storage
    raw_dir = os.path.join(artifact_store.root_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    ext = os.path.splitext(filepath)[1]
    raw_filename = f"{rec_id}{ext}"
    raw_dest = os.path.join(raw_dir, raw_filename)
    shutil.copy(filepath, raw_dest)
    
    # Register raw artifact
    with open(raw_dest, 'rb') as f:
        raw_bytes = f.read()
    raw_artifact = artifact_store.create_artifact(
        name=os.path.basename(filepath),
        content=raw_bytes,
        artifact_type="raw",
        job_id=job_id,
        metadata_json={
            "original_duration_sec": probe_info.duration_sec,
            "original_sample_rate": probe_info.sample_rate,
            "original_channels": probe_info.channels,
            "input_format": probe_info.format,
            "smoke_metrics": ffmpeg_adapter.smoke_metrics(filepath),
            **ffmpeg_adapter.metadata(),
        }
    )
    
    # Create normalized copy in staging
    staging_filename = f"{rec_id}_normalized.wav"
    staging_dir = os.path.join(artifact_store.root_dir, "staging")
    os.makedirs(staging_dir, exist_ok=True)
    staging_path = os.path.join(staging_dir, staging_filename)
    
    ffmpeg_adapter.normalize(raw_dest, staging_path)
    
    # Register normalized artifact
    with open(staging_path, 'rb') as f:
        normalized_bytes = f.read()
    normalized_artifact = artifact_store.create_artifact(
        name=staging_filename,
        content=normalized_bytes,
        artifact_type="staging",
        parent_artifact_id=raw_artifact.id,
        job_id=job_id,
        metadata_json={
            "duration_sec": probe_info.duration_sec,
            "sample_rate": 16000,
            "channels": 1,
            "normalization": {
                "target_sample_rate": 16000,
                "target_channels": 1,
                "target_codec": "pcm_s16le",
            },
            **ffmpeg_adapter.metadata(),
        }
    )
    
    rec = Recording(
        id=rec_id,
        source_uri=f"staging/{staging_filename}",
        sha256=sha256,
        duration_sec=probe_info.duration_sec,
        sample_rate=16000,
        channels=1,
        status=RecordingStatus.PROCESSED.value,
        metadata_json={
            "raw_artifact_id": raw_artifact.id,
            "normalized_artifact_id": normalized_artifact.id
        }
    )
    
    repo.save(rec)
    return rec
