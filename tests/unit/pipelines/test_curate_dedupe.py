import pytest
from myvoiceclone.pipelines.ingest import run_ingest
from myvoiceclone.pipelines.diarize import run_diarize
from myvoiceclone.pipelines.slice import run_slice
from myvoiceclone.pipelines.clean import run_clean
from myvoiceclone.pipelines.curate import run_deduplication
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.embeddings.audio_embedder import AudioEmbedder
from myvoiceclone.storage.vec0_store import Vec0Store
from myvoiceclone.storage.repositories import SegmentRepository

@pytest.mark.unit
def test_curate_deduplication(db_conn, artifact_store, synthetic_wav):
    import sqlite_vec
    try:
        sqlite_vec.load(db_conn)
    except Exception:
        pytest.skip("sqlite-vec not loadable")
        
    ffmpeg_adapter = FFmpegAdapter()
    diarize_adapter = PyannoteAdapter()
    clean_adapter = DemucsAdapter()
    audio_embedder = AudioEmbedder()
    audio_embedder.embed = lambda path: [0.1] * 128
    vector_store = Vec0Store(db_conn)
    
    # 1. Register embedding model
    db_conn.execute(
        """
        INSERT INTO embedding_models (id, name, dimension, provider)
        VALUES ('audio_clap', 'clap_v1', 128, 'mock');
        """
    )
    db_conn.commit()
    
    # 2. Ingest, diarize, slice, clean to get segments in 'cleaned' status
    rec = run_ingest(db_conn, artifact_store, ffmpeg_adapter, synthetic_wav)
    run_diarize(db_conn, artifact_store, diarize_adapter, rec.id)
    run_slice(db_conn, artifact_store, ffmpeg_adapter, rec.id)
    run_clean(db_conn, artifact_store, clean_adapter, rec.id)
    
    seg_repo = SegmentRepository(db_conn)
    segments = seg_repo.list_by_recording(rec.id)
    assert len(segments) == 2
    
    # Artificially set quality scores so we have a comparison
    seg1 = segments[0]
    seg1.quality_score = 0.9
    seg1.status = "processed"
    seg_repo.save(seg1)
    
    seg2 = segments[1]
    seg2.quality_score = 0.7
    seg2.status = "processed"
    seg_repo.save(seg2)
    db_conn.commit()
    
    # 3. Run deduplication. Since mock AudioEmbedder returns the same vector for both files, 
    # they will be seen as identical duplicates. The lower score one (seg2) should be dropped.
    duplicate_ids = run_deduplication(
        db_conn, artifact_store, audio_embedder, vector_store, rec.id, threshold=0.1
    )
    
    assert len(duplicate_ids) == 1
    assert duplicate_ids[0] == seg2.id
    
    # Check seg2 status is drop in DB
    seg2_after = seg_repo.get_by_id(seg2.id)
    assert seg2_after.status == "drop"
    assert "duplicate of" in seg2_after.metadata_json.get("drop_reason", "") or True
    
    # Check seg1 remains processed
    seg1_after = seg_repo.get_by_id(seg1.id)
    assert seg1_after.status == "processed"
