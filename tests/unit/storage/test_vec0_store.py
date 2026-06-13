import os
import pytest
from myvoiceclone.storage.sqlite import get_connection, load_vector_extension
from myvoiceclone.storage.migrations import run_migrations
from myvoiceclone.storage.vec0_store import Vec0Store

@pytest.fixture
def db_conn(tmp_path):
    db_file = str(tmp_path / "test.db")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    migrations_dir = os.path.join(project_root, "db", "migrations")
    
    conn = get_connection(db_file, load_vec=True)
    run_migrations(db_file, migrations_dir)
    yield conn
    conn.close()

@pytest.mark.unit
def test_vec0_store_lifecycle(db_conn):
    # Verify extension loaded
    has_vec = load_vector_extension(db_conn)
    if not has_vec:
        pytest.skip("sqlite-vec extension is not loaded/available. Skipping vec0 tests.")
        
    store = Vec0Store(db_conn)
    
    # 1. Register embedding model in database
    db_conn.execute(
        """
        INSERT INTO embedding_models (id, name, dimension, provider)
        VALUES ('model_1', 'speaker_embed_v1', 128, 'local_mock');
        """
    )
    db_conn.commit()
    
    # 2. Upsert embeddings
    vec_a = [0.1] * 128
    vec_b = [0.9] * 128
    vec_c = [0.15] * 128  # Close to vec_a
    
    store.upsert(namespace="speaker", item_id="spk_a", embedding=vec_a, model_id="model_1")
    store.upsert(namespace="speaker", item_id="spk_b", embedding=vec_b, model_id="model_1")
    store.upsert(namespace="speaker", item_id="spk_c", embedding=vec_c, model_id="model_1")
    db_conn.commit()
    
    # 3. Search nearest to vec_a (which is [0.1]*128)
    results = store.search(namespace="speaker", query_embedding=vec_a, limit=3)
    
    assert len(results) == 3
    # First result should be spk_a itself (distance close to 0)
    assert results[0]["item_id"] == "spk_a"
    assert results[0]["distance"] < 1e-5
    # Second result should be spk_c (which is close to vec_a)
    assert results[1]["item_id"] == "spk_c"
    # Third result should be spk_b (which is far away)
    assert results[2]["item_id"] == "spk_b"
    
    # 4. Delete spk_c
    store.delete(namespace="speaker", item_id="spk_c")
    db_conn.commit()
    
    # Search again
    results_after = store.search(namespace="speaker", query_embedding=vec_a, limit=3)
    assert len(results_after) == 2
    assert results_after[0]["item_id"] == "spk_a"
    assert results_after[1]["item_id"] == "spk_b"
