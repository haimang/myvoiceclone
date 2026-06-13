import os
import pytest
from myvoiceclone.storage.vec1_store import Vec1Store

@pytest.mark.unit
def test_vec1_disabled_by_default(monkeypatch):
    monkeypatch.setenv("ENABLE_VEC1_PROBE", "false")
    store = Vec1Store(conn=None)
    
    with pytest.raises(RuntimeError) as exc_info:
        store.upsert("speaker", "item_1", [0.1]*128, "model_a")
    assert "Vec1Store is not enabled" in str(exc_info.value)
    
    with pytest.raises(RuntimeError) as exc_info:
        store.search("speaker", [0.1]*128, limit=5)
    assert "Vec1Store is not enabled" in str(exc_info.value)
    
    with pytest.raises(RuntimeError) as exc_info:
        store.delete("speaker", "item_1")
    assert "Vec1Store is not enabled" in str(exc_info.value)

@pytest.mark.unit
def test_vec1_enabled_behavior(monkeypatch):
    monkeypatch.setenv("ENABLE_VEC1_PROBE", "true")
    store = Vec1Store(conn=None)
    
    # Should not raise exception
    store.upsert("speaker", "item_1", [0.1]*128, "model_a")
    results = store.search("speaker", [0.1]*128, limit=5)
    assert len(results) == 0
    store.delete("speaker", "item_1")
