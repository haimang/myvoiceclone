import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.pipelines.curate import update_segment_status
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter

@pytest.mark.unit
def test_curate_status_transitions(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    segments = run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    
    seg = segments[0]
    assert seg.status == "draft"
    
    # Update status to keep
    updated = update_segment_status(db_conn, seg.id, "keep", "Good voice print quality", "reviewer_alice")
    assert updated.status == "keep"
    
    # Check segment reviews table
    cursor = db_conn.cursor()
    cursor.execute("SELECT status_from, status_to, reason, reviewer FROM segment_reviews WHERE segment_id = ?;", (seg.id,))
    row = cursor.fetchone()
    assert row is not None
    assert row["status_from"] == "draft"
    assert row["status_to"] == "keep"
    assert row["reason"] == "Good voice print quality"
    assert row["reviewer"] == "reviewer_alice"
    
    # Check validations
    with pytest.raises(ValueError):
        update_segment_status(db_conn, seg.id, "invalid_status", "x", "x")
    with pytest.raises(ValueError):
        update_segment_status(db_conn, seg.id, "keep", "", "reviewer_alice")
    with pytest.raises(ValueError):
        update_segment_status(db_conn, seg.id, "keep", "Good", "")
