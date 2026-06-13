import uuid
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import SegmentResponse, SegmentReviewUpdate
from myvoiceclone.domain.entities import Segment
from myvoiceclone.storage.repositories import SegmentRepository

router = APIRouter(prefix="/segments", tags=["segments"])

@router.get("", response_model=List[SegmentResponse])
def list_segments(recording_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = SegmentRepository(db)
    return repo.list_by_recording(recording_id)

@router.get("/{segment_id}", response_model=SegmentResponse)
def get_segment(segment_id: str, db: sqlite3.Connection = Depends(get_db)):
    repo = SegmentRepository(db)
    seg = repo.get_by_id(segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    return seg

@router.patch("/{segment_id}/review", response_model=SegmentResponse)
def review_segment(segment_id: str, review: SegmentReviewUpdate, db: sqlite3.Connection = Depends(get_db)):
    repo = SegmentRepository(db)
    seg = repo.get_by_id(segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
        
    old_status = seg.status
    seg.status = review.status_to
    repo.save(seg)
    
    # Save review record
    review_id = f"rev_{uuid.uuid4().hex[:12]}"
    db.execute(
        """
        INSERT INTO segment_reviews (id, segment_id, status_from, status_to, reason, reviewer)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (review_id, segment_id, old_status, review.status_to, review.reason, review.reviewer)
    )
    db.commit()
    return seg
