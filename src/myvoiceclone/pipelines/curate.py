import sqlite3
from typing import List, Optional, Dict, Any
from myvoiceclone.domain.entities import Segment, Speaker
from myvoiceclone.domain.states import RecordingStatus, SegmentStatus
from myvoiceclone.pipelines.status import mark_recording_status
from myvoiceclone.storage.repositories import SegmentRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.vector_store import VectorStore
from myvoiceclone.adapters.embeddings.audio_embedder import AudioEmbedder
from myvoiceclone.ids import new_id

def update_segment_status(
    conn: sqlite3.Connection,
    segment_id: str,
    status: str,
    reason: str,
    reviewer: str
) -> Segment:
    if status not in (SegmentStatus.KEEP.value, SegmentStatus.DROP.value, SegmentStatus.NEEDS_REVIEW.value, "fixed"):
        raise ValueError(f"Invalid status: {status}")
    if not reason:
        raise ValueError("Reason is required for status updates")
    if not reviewer:
        raise ValueError("Reviewer is required")
        
    repo = SegmentRepository(conn)
    seg = repo.get_by_id(segment_id)
    if not seg:
        raise ValueError(f"Segment {segment_id} not found")
        
    old_status = seg.status
    seg.status = status
    # V8 fix: persist drop_reason and reviewer into metadata_json so callers can inspect it
    seg.metadata_json = dict(seg.metadata_json or {})
    if reason:
        seg.metadata_json["drop_reason"] = reason
    if reviewer:
        seg.metadata_json["reviewed_by"] = reviewer
    seg.metadata_json["prev_status"] = old_status
    repo.save(seg)

    # Write append-only segment review audit entry
    rev_id = new_id()
    conn.execute(
        """
        INSERT INTO segment_reviews (id, segment_id, status_from, status_to, reason, reviewer)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (rev_id, segment_id, old_status, status, reason, reviewer)
    )
    conn.commit()
    return seg

def run_deduplication(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    audio_embedder: AudioEmbedder,
    vector_store: VectorStore,
    recording_id: str,
    threshold: float = 0.05
) -> List[str]:
    repo = SegmentRepository(conn)
    segments = repo.list_by_recording(recording_id)
    
    candidates = []
    for seg in segments:
        if seg.status in (
            SegmentStatus.PROCESSED.value,
            SegmentStatus.KEEP.value,
            SegmentStatus.CLEANED.value,
            SegmentStatus.TRANSCRIBED.value,
        ) and seg.cleaned_artifact_id:
            candidates.append(seg)
            
    duplicate_ids = []
    
    for seg in candidates:
        # Check if already marked as drop in this run
        current_seg = repo.get_by_id(seg.id)
        if current_seg.status == SegmentStatus.DROP.value:
            continue
            
        clean_art = artifact_store.get_artifact(seg.cleaned_artifact_id)
        abs_path = artifact_store.get_absolute_path(clean_art)
        
        # 1. Compute embedding
        emb = audio_embedder.embed(abs_path)
        
        # 2. Upsert into VectorStore
        vector_store.upsert("audio", seg.id, emb, audio_embedder.model_id)
        
        # 3. Search nearest
        results = vector_store.search("audio", emb, limit=5)
        
        # Compare distances
        for res in results:
            other_id = res["item_id"]
            distance = res["distance"]
            
            if other_id == seg.id:
                continue
                
            if distance < threshold:
                other_seg = repo.get_by_id(other_id)
                if not other_seg or other_seg.status == SegmentStatus.DROP.value:
                    continue
                    
                # Deduplication decision: keep the one with higher quality score
                my_score = seg.quality_score or 0.0
                other_score = other_seg.quality_score or 0.0
                
                if my_score >= other_score:
                    # Drop other
                    update_segment_status(
                        conn=conn,
                        segment_id=other_id,
                        status=SegmentStatus.DROP.value,
                        reason=f"duplicate of {seg.id} (distance {distance:.4f})",
                        reviewer="deduper"
                    )
                    duplicate_ids.append(other_id)
                else:
                    # Drop me
                    update_segment_status(
                        conn=conn,
                        segment_id=seg.id,
                        status=SegmentStatus.DROP.value,
                        reason=f"duplicate of {other_id} (distance {distance:.4f})",
                        reviewer="deduper"
                    )
                    duplicate_ids.append(seg.id)
                    break # Break out of loop since this segment is now dropped
                    
    return duplicate_ids


def run_curation(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    recording_id: str,
    *,
    min_quality_score: float = 0.6,
    dedupe: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    repo = SegmentRepository(conn)
    segments = repo.list_by_recording(recording_id)
    if not segments:
        raise ValueError(f"No segments found for recording {recording_id}")

    kept = []
    needs_review = []
    dropped = []
    for seg in segments:
        if seg.status == SegmentStatus.DROP.value:
            dropped.append(seg.id)
            continue
        if seg.status not in (
            SegmentStatus.PROCESSED.value,
            SegmentStatus.CLEANED.value,
            SegmentStatus.TRANSCRIBED.value,
            SegmentStatus.NEEDS_REVIEW.value,
            SegmentStatus.KEEP.value,
        ):
            continue

        quality = seg.quality_score if seg.quality_score is not None else 0.0
        if quality >= min_quality_score and seg.status != SegmentStatus.KEEP.value:
            update_segment_status(
                conn=conn,
                segment_id=seg.id,
                status=SegmentStatus.KEEP.value,
                reason=f"first-test curation quality pass >= {min_quality_score}",
                reviewer="curation",
            )
            kept.append(seg.id)
        elif quality < min_quality_score and seg.status != SegmentStatus.NEEDS_REVIEW.value:
            update_segment_status(
                conn=conn,
                segment_id=seg.id,
                status=SegmentStatus.NEEDS_REVIEW.value,
                reason=f"first-test curation quality below {min_quality_score}",
                reviewer="curation",
            )
            needs_review.append(seg.id)
        elif seg.status == SegmentStatus.KEEP.value:
            kept.append(seg.id)
        elif seg.status == SegmentStatus.NEEDS_REVIEW.value:
            needs_review.append(seg.id)

    duplicate_ids: List[str] = []
    if dedupe:
        from myvoiceclone.storage.vec0_store import Vec0Store

        duplicate_ids = run_deduplication(
            conn,
            artifact_store,
            AudioEmbedder(),
            Vec0Store(conn),
            recording_id,
        )

    mark_recording_status(conn, recording_id, RecordingStatus.CURATED.value)
    conn.commit()
    return {
        "recording_id": recording_id,
        "job_id": job_id,
        "kept_segment_ids": kept,
        "needs_review_segment_ids": needs_review,
        "dropped_segment_ids": dropped,
        "duplicate_segment_ids": duplicate_ids,
    }
