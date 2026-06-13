import os
import sqlite3
from typing import List
from myvoiceclone.domain.entities import Segment, Artifact
from myvoiceclone.domain.states import SegmentStatus
from myvoiceclone.storage.repositories import SegmentRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter

def run_clean(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    clean_adapter: DemucsAdapter,
    recording_id: str,
    job_id: str = None
) -> List[Segment]:
    seg_repo = SegmentRepository(conn)
    segments = seg_repo.list_by_recording(recording_id)
    
    cleaned_segments = []
    
    for seg in segments:
        if seg.status != SegmentStatus.SLICED.value or not seg.audio_artifact_id:
            continue
            
        audio_art = artifact_store.get_artifact(seg.audio_artifact_id)
        if not audio_art:
            continue
            
        abs_audio_path = artifact_store.get_absolute_path(audio_art)
        
        # Prepare target directories
        clean_dir = os.path.join(artifact_store.root_dir, "cleaned")
        os.makedirs(clean_dir, exist_ok=True)
        
        try:
            # Perform source separation
            sep_result = clean_adapter.separate(abs_audio_path, clean_dir)
            cleaned_path = sep_result.cleaned_path
            
            # Read cleaned file
            with open(cleaned_path, 'rb') as f:
                cleaned_bytes = f.read()
                
            # Register cleaned artifact
            cleaned_filename = f"{seg.id}_cleaned.wav"
            cleaned_art = artifact_store.create_artifact(
                name=cleaned_filename,
                content=cleaned_bytes,
                artifact_type="cleaned",
                parent_artifact_id=audio_art.id,
                job_id=job_id,
                metadata_json={
                    "segment_id": seg.id,
                    "denoised": True,
                    "separation_smoke": True,
                    "quality_claim": "not_speech_enhancement",
                    **clean_adapter.metadata(),
                }
            )
            
            seg.cleaned_artifact_id = cleaned_art.id
            seg.status = SegmentStatus.CLEANED.value
            seg_repo.save(seg)
            cleaned_segments.append(seg)
            
        except Exception as e:
            # Failure does not delete original segment audio. We mark status but preserve seg info.
            seg.status = SegmentStatus.CLEAN_FAILED.value
            seg.metadata_json["clean_error"] = str(e)
            seg_repo.save(seg)
            
    conn.commit()
    return cleaned_segments
