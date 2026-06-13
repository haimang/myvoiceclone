import pytest
from myvoiceclone.storage.vec0_store import Vec0Store
from myvoiceclone.adapters.embeddings.speaker_embedder import SpeakerEmbedder

@pytest.mark.unit
def test_embedding_model_upsert_search(db_conn):
    import sqlite_vec
    try:
        sqlite_vec.load(db_conn)
    except Exception:
        pytest.skip("sqlite-vec not loadable in this environment")
        
    store = Vec0Store(db_conn)
    embedder = SpeakerEmbedder()
    
    # Register model
    db_conn.execute(
        """
        INSERT INTO embedding_models (id, name, dimension, provider)
        VALUES ('emb_model', 'resnet_speaker', 128, 'resnet');
        """
    )
    db_conn.commit()
    
    # Embed items
    vec_1 = embedder.embed("segment_a")
    vec_2 = embedder.embed("segment_b")
    
    store.upsert("speaker", "item_a", vec_1, "emb_model")
    store.upsert("speaker", "item_b", vec_2, "emb_model")
    db_conn.commit()
    
    # Search
    results = store.search("speaker", vec_1, limit=2)
    assert len(results) >= 1
    assert results[0]["item_id"] == "item_a"
    assert results[0]["distance"] < 1e-5
