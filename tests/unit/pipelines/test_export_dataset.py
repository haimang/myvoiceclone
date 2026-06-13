import pytest
import sqlite3
import os
from myvoiceclone.domain.entities import Segment, Dataset
from myvoiceclone.storage.repositories import DatasetRepository, SegmentRepository
from myvoiceclone.pipelines.export_dataset import run_export_dataset, detect_split_leak

@pytest.mark.unit
def test_split_leak_detector(db_conn):
    # Setup dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_leak", name="Leak Dataset", status="draft"))
    
    # Setup recording (required by FK constraint on segments)
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_shared', 'uri_shared', 'sha_shared', 10.0, 16000, 1, 'processed');
        """
    )
    
    # Setup two segments from the SAME recording_id
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status)
        VALUES ('seg_a', 'rec_shared', 0.0, 5.0, 'processed'),
               ('seg_b', 'rec_shared', 5.0, 10.0, 'processed');
        """
    )
    db_conn.commit()
    
    # Place seg_a in train split and seg_b in test split
    ds_repo.add_segment("ds_leak", "seg_a", "train")
    ds_repo.add_segment("ds_leak", "seg_b", "test")
    db_conn.commit()
    
    # Assert split leak is detected
    assert detect_split_leak(db_conn, "ds_leak") is True

@pytest.mark.unit
def test_manifest_checksum_immutable(db_conn, artifact_store):
    # Setup segments in DB
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_1', 'uri', 'hash1', 10.0, 16000, 1, 'processed'),
               ('rec_2', 'uri', 'hash2', 10.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, cleaned_artifact_id, transcript)
        VALUES ('seg_1', 'rec_1', 0.0, 5.0, 'processed', 'art_clean1', 'Hello'),
               ('seg_2', 'rec_2', 0.0, 5.0, 'processed', 'art_clean2', 'World');
        """
    )
    # Register mock cleaned artifacts
    db_conn.execute(
        """
        INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type)
        VALUES ('art_clean1', 'c1.wav', 'c1.wav', 'h1', 10, 'cleaned'),
               ('art_clean2', 'c2.wav', 'c2.wav', 'h2', 10, 'cleaned');
        """
    )
    db_conn.commit()
    
    # Generate mock cleaned files
    os_dir1 = os.path.join(artifact_store.root_dir, "c1.wav")
    os_dir2 = os.path.join(artifact_store.root_dir, "c2.wav")
    os.makedirs(os.path.dirname(os_dir1), exist_ok=True)
    with open(os_dir1, 'w') as f: f.write("mock")
    with open(os_dir2, 'w') as f: f.write("mock")
    
    # Run export
    ds = run_export_dataset(
        db_conn, artifact_store, dataset_id="ds_freeze", name="Freeze DS",
        train_ratio=0.5, val_ratio=0.0, test_ratio=0.5
    )
    
    assert ds.status == "frozen"
    assert ds.manifest_sha256 is not None
    assert ds.frozen_at is not None
    
    # Try running export again on the frozen dataset, should raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        run_export_dataset(db_conn, artifact_store, dataset_id="ds_freeze", name="Freeze DS")
        
    assert "frozen and cannot be modified" in str(exc_info.value)
