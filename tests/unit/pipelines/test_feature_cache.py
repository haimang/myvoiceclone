import pytest
from myvoiceclone.domain.entities import Dataset
from myvoiceclone.storage.repositories import DatasetRepository
from myvoiceclone.pipelines.train import generate_feature_cache_key, run_prepare_features

@pytest.mark.unit
def test_feature_cache_key_generation():
    key1 = generate_feature_cache_key("sha123", {"epochs": 10})
    key2 = generate_feature_cache_key("sha123", {"epochs": 10})
    key3 = generate_feature_cache_key("sha123", {"epochs": 20})
    
    assert key1 == key2
    assert key1 != key3

@pytest.mark.unit
def test_run_prepare_features_hit_and_miss(db_conn, artifact_store):
    # Setup dataset
    ds_repo = DatasetRepository(db_conn)
    ds = Dataset(id="ds_cache_test", name="Cache Test DS", status="frozen", manifest_sha256="dataset_manifest_checksum_123")
    ds_repo.save(ds)
    db_conn.commit()
    
    config = {"feature_size": 256}
    
    # 1. First run - Cache Miss
    art_id_1 = run_prepare_features(db_conn, artifact_store, "ds_cache_test", config)
    assert art_id_1 is not None
    
    # Verify artifact exists and has correct type
    art_1 = artifact_store.get_artifact(art_id_1)
    assert art_1.artifact_type == "feature_cache"
    
    # 2. Second run with same config - Cache Hit
    art_id_2 = run_prepare_features(db_conn, artifact_store, "ds_cache_test", config)
    assert art_id_1 == art_id_2
    
    # 3. Third run with different config - Cache Miss (invalidation)
    different_config = {"feature_size": 512}
    art_id_3 = run_prepare_features(db_conn, artifact_store, "ds_cache_test", different_config)
    assert art_id_1 != art_id_3
