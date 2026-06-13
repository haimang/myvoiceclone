import os
import json
import hashlib
import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from myvoiceclone.domain.entities import Dataset, DatasetSegment, Artifact
from myvoiceclone.domain.states import DatasetStatus, SegmentStatus
from myvoiceclone.storage.repositories import DatasetRepository, SegmentRepository
from myvoiceclone.storage.artifact_store import ArtifactStore

def detect_split_leak(conn: sqlite3.Connection, dataset_id: str) -> bool:
    """Returns True if there is a split leak (same recording_id in different splits)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.recording_id, COUNT(DISTINCT ds.split) as split_count
        FROM dataset_segments ds
        JOIN segments s ON ds.segment_id = s.id
        WHERE ds.dataset_id = ?
        GROUP BY s.recording_id
        HAVING split_count > 1;
        """,
        (dataset_id,)
    )
    return cursor.fetchone() is not None

def run_export_dataset(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    dataset_id: str,
    name: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    job_id: str = None
) -> Dataset:
    ds_repo = DatasetRepository(conn)
    seg_repo = SegmentRepository(conn)
    
    # Check if dataset already exists and is frozen
    existing = ds_repo.get_by_id(dataset_id)
    if existing and existing.status == DatasetStatus.FROZEN.value:
        raise RuntimeError(f"Dataset {dataset_id} is frozen and cannot be modified")
        
    # Get all keep / processed / fixed segments
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, recording_id, speaker_id, start_sec, end_sec, cleaned_artifact_id, transcript, quality_score
        FROM segments
        WHERE status IN (?, ?, ?, ?, ?)
          AND cleaned_artifact_id IS NOT NULL;
        """
        ,
        (
            SegmentStatus.PROCESSED.value,
            SegmentStatus.KEEP.value,
            SegmentStatus.FIXED.value,
            SegmentStatus.CLEANED.value,
            SegmentStatus.TRANSCRIBED.value,
        ),
    )
    rows = cursor.fetchall()
    if not rows:
        raise RuntimeError(
            "Dataset freeze refused: no eligible segments with cleaned artifacts. "
            "Run preprocess/curation first; empty manifests are not valid first-test evidence."
        )
    
    # Group segment IDs by recording_id to prevent leak
    recording_groups = {}
    for r in rows:
        rec_id = r["recording_id"]
        if rec_id not in recording_groups:
            recording_groups[rec_id] = []
        recording_groups[rec_id].append(r)
        
    # Deterministic split allocation based on recording IDs
    sorted_rec_ids = sorted(list(recording_groups.keys()))
    
    # Calculate partition boundaries
    num_recs = len(sorted_rec_ids)
    train_limit = int(num_recs * train_ratio)
    val_limit = train_limit + int(num_recs * val_ratio)
    
    # Assign recording groups to splits
    split_mapping = {}
    for idx, rec_id in enumerate(sorted_rec_ids):
        if idx < train_limit:
            split_mapping[rec_id] = "train"
        elif idx < val_limit:
            split_mapping[rec_id] = "val"
        else:
            split_mapping[rec_id] = "test"
            
    # Save dataset row as draft first
    ds = Dataset(
        id=dataset_id,
        name=name,
        status=DatasetStatus.DRAFT.value,
        filter_json={
            "train_ratio": train_ratio,
            "val_ratio": val_ratio,
            "test_ratio": test_ratio
        }
    )
    ds_repo.save(ds)
    
    # Link segments to dataset
    manifest_rows = []
    for rec_id, segs in recording_groups.items():
        split = split_mapping[rec_id]
        for s in segs:
            ds_repo.add_segment(dataset_id, s["id"], split)
            
            clean_art = artifact_store.get_artifact(s["cleaned_artifact_id"])
            if not clean_art:
                raise RuntimeError(f"Cleaned artifact {s['cleaned_artifact_id']} for segment {s['id']} not found")
            manifest_rows.append({
                "id": s["id"],
                "segment_id": s["id"],
                "audio_path": clean_art.uri,
                "uri": clean_art.uri,
                "cleaned_artifact_id": clean_art.id,
                "sha256": clean_art.sha256,
                "bytes": clean_art.bytes,
                "transcript": s["transcript"] or "",
                "split": split,
                "speaker_id": s["speaker_id"],
                "duration": s["end_sec"] - s["start_sec"],
                "duration_sec": s["end_sec"] - s["start_sec"],
                "lineage": {
                    "cleaned_artifact_id": clean_art.id,
                    "source_artifact_id": clean_art.source_artifact_id or clean_art.parent_artifact_id,
                },
            })

    if not manifest_rows:
        raise RuntimeError("Dataset freeze refused: manifest would be empty")
            
    # Perform split leak detection before freezing
    if detect_split_leak(conn, dataset_id):
        raise RuntimeError("Split leak detected! Same recording found in multiple splits.")
        
    # Write manifest JSONL content
    manifest_lines = [json.dumps(row, ensure_ascii=False) for row in manifest_rows]
    manifest_content = "\n".join(manifest_lines).encode('utf-8')
    
    # Register manifest artifact
    manifest_filename = f"{dataset_id}_manifest.jsonl"
    manifest_art = artifact_store.create_artifact(
        name=manifest_filename,
        content=manifest_content,
        artifact_type="dataset",
        job_id=job_id
    )
    
    # Update dataset to frozen status
    ds.status = DatasetStatus.FROZEN.value
    ds.manifest_artifact_id = manifest_art.id
    ds.manifest_sha256 = manifest_art.sha256
    ds.frozen_at = datetime.utcnow()
    ds_repo.save(ds)
    
    conn.commit()
    return ds
