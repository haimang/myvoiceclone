import pytest
import os
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter

@pytest.mark.unit
def test_ingest_lifecycle(db_conn, artifact_store, synthetic_wav):
    ffmpeg_adapter = FFmpegAdapter()
    
    # Ingest for the first time
    rec1 = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    
    assert rec1.id.startswith("rec_")
    assert rec1.status == "processed"
    assert rec1.sample_rate == 16000
    assert rec1.channels == 1
    
    # Check artifacts exist
    raw_art_id = rec1.metadata_json.get("raw_artifact_id")
    norm_art_id = rec1.metadata_json.get("normalized_artifact_id")
    assert raw_art_id is not None
    assert norm_art_id is not None
    
    raw_art = artifact_store.get_artifact(raw_art_id)
    norm_art = artifact_store.get_artifact(norm_art_id)
    assert raw_art is not None
    assert norm_art is not None
    assert os.path.exists(artifact_store.get_absolute_path(raw_art))
    assert os.path.exists(artifact_store.get_absolute_path(norm_art))
    
    # Duplicate ingest check
    rec2 = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    assert rec1.id == rec2.id
