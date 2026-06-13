import os
import pytest
from myvoiceclone.domain.entities import Dataset, Report
from myvoiceclone.storage.repositories import DatasetRepository, ReportRepository
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.eval.report import generate_corpus_report

@pytest.mark.unit
def test_corpus_report_generation(db_conn, artifact_store):
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_rpt", name="Report Dataset", status="frozen"))
    
    # Add recordings first (required by FK constraint on segments)
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_1', 'uri_1', 'sha_1', 10.0, 16000, 1, 'processed'),
               ('rec_2', 'uri_2', 'sha_2', 10.0, 16000, 1, 'processed');
        """
    )
    
    # Add segments
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score)
        VALUES ('seg_1', 'rec_1', 0.0, 5.0, 'processed', 0.9),
               ('seg_2', 'rec_2', 0.0, 5.0, 'processed', 0.8),
               ('seg_3', 'rec_2', 5.0, 10.0, 'drop', 0.2);
        """
    )
    # Add review log for dropped segment
    db_conn.execute(
        """
        INSERT INTO segment_reviews (id, segment_id, status_from, status_to, reason, reviewer)
        VALUES ('rev_1', 'seg_3', 'processed', 'drop', 'noise too high', 'reviewer_bob');
        """
    )
    
    ds_repo.add_segment("ds_rpt", "seg_1", "train")
    ds_repo.add_segment("ds_rpt", "seg_2", "val")
    db_conn.commit()
    
    # Generate report
    rpt = generate_corpus_report(db_conn, artifact_store, "ds_rpt", "rpt_corpus")
    
    assert rpt.id == "rpt_corpus"
    assert rpt.report_type == "corpus_audit"
    assert rpt.summary_json["dataset_id"] == "ds_rpt"
    assert rpt.summary_json["total_segments_scanned"] == 3
    assert rpt.summary_json["kept_segments_count"] == 2
    assert abs(rpt.summary_json["average_quality_score"] - 0.85) < 1e-6
    assert rpt.summary_json["splits"]["train"]["count"] == 1
    assert rpt.summary_json["splits"]["val"]["count"] == 1
    assert rpt.summary_json["drop_reasons"] == {"noise too high": 1}
    
    # Verify report artifact exists
    report_repo = ReportRepository(db_conn)
    rpt_db = report_repo.get_by_id("rpt_corpus")
    assert rpt_db is not None
    assert rpt_db.artifact_id is not None
    
    art = artifact_store.get_artifact(rpt_db.artifact_id)
    assert art is not None
    assert os.path.exists(artifact_store.get_absolute_path(art))
