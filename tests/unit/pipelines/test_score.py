import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.pipelines.clean import run_clean
from myvoiceclone.pipelines.transcribe import run_transcribe
from myvoiceclone.pipelines.score import run_score
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter

@pytest.mark.unit
def test_score_pipeline_step(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    clean_adapter = DemucsAdapter()
    asr_adapter = WhisperAdapter()
    
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    run_slice(db_conn, artifact_store, ffmpeg_adapter, rec.id)
    run_clean(db_conn, artifact_store, clean_adapter, rec.id)
    run_transcribe(db_conn, artifact_store, asr_adapter, rec.id)
    
    # 1. Run scoring with high min score threshold (e.g. 0.95), segments should status=needs_review
    scored_high = run_score(db_conn, rec.id, min_quality_score=0.95)
    assert len(scored_high) == 2
    assert all(s.status == "needs_review" for s in scored_high)
    
    # 2. Run scoring with low min score threshold (e.g. 0.5), segments should status=processed
    scored_low = run_score(db_conn, rec.id, min_quality_score=0.5)
    assert len(scored_low) == 2
    assert all(s.status == "processed" for s in scored_low)


@pytest.mark.unit
def test_score_refuses_hidden_mock_metrics_in_real_mode(db_conn, monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "false")

    with pytest.raises(RuntimeError, match="Real segment quality scoring is not configured"):
        run_score(db_conn, "rec_missing")
