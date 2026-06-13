import json
import uuid
import sqlite3
from typing import List
from myvoiceclone.domain.entities import Segment, Speaker
from myvoiceclone.domain.states import SegmentStatus
from myvoiceclone.storage.repositories import RecordingRepository, SegmentRepository, SpeakerRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter

def run_diarize(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    diarize_adapter: PyannoteAdapter,
    recording_id: str,
    job_id: str = None
) -> List[Segment]:
    rec_repo = RecordingRepository(conn)
    seg_repo = SegmentRepository(conn)
    spk_repo = SpeakerRepository(conn)
    
    rec = rec_repo.get_by_id(recording_id)
    if not rec:
        raise ValueError(f"Recording {recording_id} not found")
        
    normalized_art_id = rec.metadata_json.get("normalized_artifact_id")
    if not normalized_art_id:
        raise ValueError(f"Normalized artifact not found for recording {recording_id}")
        
    normalized_art = artifact_store.get_artifact(normalized_art_id)
    if not normalized_art:
        raise ValueError(f"Artifact {normalized_art_id} not found in store")
        
    abs_path = artifact_store.get_absolute_path(normalized_art)
    
    # Run PyAnnote diarization
    turns = diarize_adapter.diarize(abs_path)
    
    # Standardize turns output to a JSON artifact
    turns_data = [
        {"speaker_id": turn.speaker_id, "start_sec": turn.start_sec, "end_sec": turn.end_sec}
        for turn in turns
    ]
    turns_bytes = json.dumps(turns_data).encode('utf-8')
    turns_artifact = artifact_store.create_artifact(
        name=f"{recording_id}_turns.json",
        content=turns_bytes,
        artifact_type="diarized",
        parent_artifact_id=normalized_art.id,
        job_id=job_id,
        metadata_json={
            "recording_id": recording_id,
            "turn_count": len(turns),
            **diarize_adapter.metadata(),
        },
    )
    
    segments = []
    for turn in turns:
        # Check and save speaker
        speaker = spk_repo.get_by_id(turn.speaker_id)
        if not speaker:
            speaker = Speaker(
                id=turn.speaker_id,
                display_name=f"Speaker {turn.speaker_id[-6:] if len(turn.speaker_id) > 6 else turn.speaker_id}",
                role="other"
            )
            spk_repo.save(speaker)
            
        seg_id = f"seg_{uuid.uuid4().hex[:12]}"
        seg = Segment(
            id=seg_id,
            recording_id=recording_id,
            speaker_id=turn.speaker_id,
            start_sec=turn.start_sec,
            end_sec=turn.end_sec,
            audio_artifact_id=None,
            cleaned_artifact_id=None,
            transcript=None,
            status=SegmentStatus.DRAFT.value,
            metadata_json={
                "turns_artifact_id": turns_artifact.id,
                "diarization_model": diarize_adapter.model_id,
            }
        )
        seg_repo.save(seg)
        segments.append(seg)
        
    # Commit changes
    conn.commit()
    return segments
