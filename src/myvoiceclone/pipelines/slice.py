import os
import sqlite3
from typing import List
from myvoiceclone.domain.entities import Segment, Artifact
from myvoiceclone.storage.repositories import RecordingRepository, SegmentRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter

def run_slice(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    ffmpeg_adapter: FFmpegAdapter,
    recording_id: str,
    min_duration: float = 2.0,
    max_duration: float = 10.0,
    job_id: str = None
) -> List[Segment]:
    rec_repo = RecordingRepository(conn)
    seg_repo = SegmentRepository(conn)
    
    rec = rec_repo.get_by_id(recording_id)
    if not rec:
        raise ValueError(f"Recording {recording_id} not found")
        
    normalized_art_id = rec.metadata_json.get("normalized_artifact_id")
    normalized_art = artifact_store.get_artifact(normalized_art_id)
    abs_rec_path = artifact_store.get_absolute_path(normalized_art)
    
    segments = seg_repo.list_by_recording(recording_id)
    processed_segments = []
    
    for seg in segments:
        duration = seg.end_sec - seg.start_sec
        
        # Duration bound check
        if duration < min_duration or duration > max_duration:
            seg.status = "ignored_duration_bounds"
            seg_repo.save(seg)
            continue
            
        # Define slice path
        slice_dir = os.path.join(artifact_store.root_dir, "sliced")
        os.makedirs(slice_dir, exist_ok=True)
        slice_filename = f"{seg.id}.wav"
        slice_path = os.path.join(slice_dir, slice_filename)
        
        # Extract audio segment using FFmpeg
        ffmpeg_adapter.extract_segment(abs_rec_path, slice_path, seg.start_sec, seg.end_sec)
        
        # Register segment audio artifact
        with open(slice_path, 'rb') as f:
            slice_bytes = f.read()
            
        slice_artifact = artifact_store.create_artifact(
            name=slice_filename,
            content=slice_bytes,
            artifact_type="sliced",
            parent_artifact_id=normalized_art.id,
            job_id=job_id,
            metadata_json={
                "segment_id": seg.id,
                "start_sec": seg.start_sec,
                "end_sec": seg.end_sec,
                "duration_sec": duration
            }
        )
        
        seg.audio_artifact_id = slice_artifact.id
        seg.status = "sliced"
        seg_repo.save(seg)
        processed_segments.append(seg)
        
    conn.commit()
    return processed_segments
