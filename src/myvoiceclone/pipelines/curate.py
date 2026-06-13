import uuid
import sqlite3
from typing import List, Optional
from myvoiceclone.domain.entities import Segment, Speaker
from myvoiceclone.storage.repositories import SegmentRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.vector_store import VectorStore
from myvoiceclone.adapters.embeddings.audio_embedder import AudioEmbedder

def update_segment_status(
    conn: sqlite3.Connection,
    segment_id: str,
    status: str,
    reason: str,
    reviewer: str
) -> Segment:
    if status not in ("keep", "drop", "needs_review", "fixed"):
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
    repo.save(seg)
    
    # Write append-only segment review audit entry
    rev_id = f"rev_{uuid.uuid4().hex[:12]}"
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
        if seg.status in ("processed", "keep", "cleaned", "transcribed") and seg.cleaned_artifact_id:
            candidates.append(seg)
            
    duplicate_ids = []
    
    for seg in candidates:
        # Check if already marked as drop in this run
        current_seg = repo.get_by_id(seg.id)
        if current_seg.status == "drop":
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
                if not other_seg or other_seg.status == "drop":
                    continue
                    
                # Deduplication decision: keep the one with higher quality score
                my_score = seg.quality_score or 0.0
                other_score = other_seg.quality_score or 0.0
                
                if my_score >= other_score:
                    # Drop other
                    update_segment_status(
                        conn=conn,
                        segment_id=other_id,
                        status="drop",
                        reason=f"duplicate of {seg.id} (distance {distance:.4f})",
                        reviewer="deduper"
                    )
                    duplicate_ids.append(other_id)
                else:
                    # Drop me
                    update_segment_status(
                        conn=conn,
                        segment_id=seg.id,
                        status="drop",
                        reason=f"duplicate of {other_id} (distance {distance:.4f})",
                        reviewer="deduper"
                    )
                    duplicate_ids.append(seg.id)
                    break # Break out of loop since this segment is now dropped
                    
    return duplicate_ids
