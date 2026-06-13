import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter

@pytest.mark.unit
def test_slice_pipeline_step(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    
    # 1. Run slice with narrow bounds so that they get ignored
    processed_ignored = run_slice(
        db_conn, artifact_store, ffmpeg_adapter, rec.id, 
        min_duration=10.0, max_duration=20.0
    )
    assert len(processed_ignored) == 0
    
    # Check segment status in DB is ignored
    cursor = db_conn.cursor()
    cursor.execute("SELECT status FROM segments;")
    statuses = [r[0] for r in cursor.fetchall()]
    assert all(s == "ignored_duration_bounds" for s in statuses)
    
    # Reset status for second test
    db_conn.execute("UPDATE segments SET status = 'draft';")
    db_conn.commit()
    
    # 2. Run slice with normal bounds [2.0, 10.0]
    processed_ok = run_slice(
        db_conn, artifact_store, ffmpeg_adapter, rec.id,
        min_duration=2.0, max_duration=10.0
    )
    assert len(processed_ok) == 2
    assert all(s.status == "sliced" for s in processed_ok)
    assert all(s.audio_artifact_id is not None for s in processed_ok)
