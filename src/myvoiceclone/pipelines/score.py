import sqlite3
from typing import List
from myvoiceclone.domain.entities import Segment
from myvoiceclone.domain.states import SegmentStatus
from myvoiceclone.storage.repositories import SegmentRepository

def calculate_duration_score(duration: float) -> float:
    # Target optimal duration is around 5.0 seconds. 
    # Scores decay as duration gets closer to 2.0 or 10.0 seconds.
    if duration < 2.0 or duration > 10.0:
        return 0.0
    if 4.0 <= duration <= 7.0:
        return 1.0
    elif duration < 4.0:
        # Interpolate between 2.0 (0.0 score) and 4.0 (1.0 score)
        return (duration - 2.0) / 2.0
    else:
        # Interpolate between 7.0 (1.0 score) and 10.0 (0.0 score)
        return (10.0 - duration) / 3.0

def run_score(
    conn: sqlite3.Connection,
    recording_id: str,
    min_quality_score: float = 0.6
) -> List[Segment]:
    seg_repo = SegmentRepository(conn)
    segments = seg_repo.list_by_recording(recording_id)
    
    scored_segments = []
    
    for seg in segments:
        # We only score transcribed segments (or allow re-scoring of processed/needs_review segments)
        if seg.status not in (SegmentStatus.TRANSCRIBED.value, SegmentStatus.PROCESSED.value, SegmentStatus.NEEDS_REVIEW.value):
            continue
            
        duration = seg.end_sec - seg.start_sec
        
        # Calculate quality metrics
        dur_score = calculate_duration_score(duration)
        noise_score = 0.9  # Mock noise score
        overlap_score = 1.0  # Mock overlap score
        speaker_score = 0.85  # Mock speaker similarity
        
        overall_score = (dur_score + noise_score + overlap_score + speaker_score) / 4.0
        
        seg.quality_score = overall_score
        seg.speaker_score = speaker_score
        seg.noise_score = noise_score
        seg.overlap_score = overlap_score
        
        # Update status based on score threshold
        if overall_score < min_quality_score:
            seg.status = SegmentStatus.NEEDS_REVIEW.value
        else:
            seg.status = SegmentStatus.PROCESSED.value
            
        seg_repo.save(seg)
        scored_segments.append(seg)
        
    conn.commit()
    return scored_segments
