import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.pipelines.clean import run_clean
from myvoiceclone.pipelines.transcribe import run_transcribe
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter

@pytest.mark.unit
def test_transcribe_pipeline_step(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    clean_adapter = DemucsAdapter()
    asr_adapter = WhisperAdapter()
    
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    run_slice(db_conn, artifact_store, ffmpeg_adapter, rec.id)
    run_clean(db_conn, artifact_store, clean_adapter, rec.id)
    
    # Run transcribe
    transcribed_segs = run_transcribe(db_conn, artifact_store, asr_adapter, rec.id)
    
    assert len(transcribed_segs) == 2
    assert all(s.status == "transcribed" for s in transcribed_segs)
    assert all(s.transcript is not None for s in transcribed_segs)
    assert transcribed_segs[0].transcript == "你好，这是一段测试音频。 今天天气真不错。"
    
    # Check artifact registered in DB
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type = 'transcript';")
    assert cursor.fetchone()[0] == 2
