import json
import sqlite3
from typing import List
from myvoiceclone.domain.entities import Segment, Artifact
from myvoiceclone.domain.states import RecordingStatus, SegmentStatus
from myvoiceclone.pipelines.status import mark_recording_status
from myvoiceclone.storage.repositories import SegmentRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter

def run_transcribe(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    asr_adapter: WhisperAdapter,
    recording_id: str,
    job_id: str = None
) -> List[Segment]:
    seg_repo = SegmentRepository(conn)
    segments = seg_repo.list_by_recording(recording_id)
    
    transcribed_segments = []
    
    for seg in segments:
        if seg.status != SegmentStatus.CLEANED.value or not seg.cleaned_artifact_id:
            continue
            
        clean_art = artifact_store.get_artifact(seg.cleaned_artifact_id)
        if not clean_art:
            continue
            
        abs_clean_path = artifact_store.get_absolute_path(clean_art)
        
        try:
            # Transcribe audio using Whisper
            transcript_segs = asr_adapter.transcribe(abs_clean_path)
            
            # Combine transcript text
            full_text = " ".join([s.text for s in transcript_segs]).strip()
            
            # Create transcript JSON artifact
            transcript_data = [
                {"start_sec": s.start_sec, "end_sec": s.end_sec, "text": s.text, "confidence": s.confidence}
                for s in transcript_segs
            ]
            transcript_bytes = json.dumps(transcript_data, ensure_ascii=False).encode('utf-8')
            
            transcript_filename = f"{seg.id}_transcript.json"
            transcript_art = artifact_store.create_artifact(
                name=transcript_filename,
                content=transcript_bytes,
                artifact_type="transcript",
                parent_artifact_id=clean_art.id,
                job_id=job_id,
                metadata_json={
                    "segment_id": seg.id,
                    "duration_sec": seg.end_sec - seg.start_sec,
                    "segment_count": len(transcript_segs),
                    **asr_adapter.metadata(),
                }
            )
            
            seg.transcript = full_text
            seg.status = SegmentStatus.TRANSCRIBED.value
            # Save ASR confidence metadata
            avg_conf = sum([s.confidence for s in transcript_segs]) / len(transcript_segs) if transcript_segs else 0.0
            seg.metadata_json["asr_confidence"] = avg_conf
            seg.metadata_json["transcript_artifact_id"] = transcript_art.id
            
            seg_repo.save(seg)
            transcribed_segments.append(seg)
            
        except Exception as e:
            seg.status = SegmentStatus.TRANSCRIBE_FAILED.value
            seg.metadata_json["transcribe_error"] = str(e)
            seg_repo.save(seg)
            
    mark_recording_status(conn, recording_id, RecordingStatus.TRANSCRIBED.value)
    conn.commit()
    return transcribed_segments
