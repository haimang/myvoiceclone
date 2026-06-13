import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter

@pytest.mark.unit
def test_diarize_pipeline_step(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    segments = run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    
    assert len(segments) == 2
    assert segments[0].recording_id == rec.id
    assert segments[0].status == "draft"
    assert segments[0].speaker_id in ("speaker_0", "speaker_1")
    
    # Check segment created in DB
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM segments WHERE recording_id = ?;", (rec.id,))
    assert cursor.fetchone()[0] == 2
    
    # Check turns JSON artifact registered
    cursor.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type = 'diarized';")
    assert cursor.fetchone()[0] == 1
