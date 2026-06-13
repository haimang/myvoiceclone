import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.pipelines.clean import run_clean
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter

@pytest.mark.unit
def test_clean_pipeline_step(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    clean_adapter = DemucsAdapter()
    
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    run_slice(db_conn, artifact_store, ffmpeg_adapter, rec.id)
    
    # Run clean
    cleaned_segs = run_clean(db_conn, artifact_store, clean_adapter, rec.id)
    
    assert len(cleaned_segs) == 2
    assert all(s.status == "cleaned" for s in cleaned_segs)
    assert all(s.cleaned_artifact_id is not None for s in cleaned_segs)
    
    # Verify artifact lineage in store
    child_art = artifact_store.get_artifact(cleaned_segs[0].cleaned_artifact_id)
    assert child_art.parent_artifact_id == cleaned_segs[0].audio_artifact_id
