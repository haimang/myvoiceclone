import pytest
from myvoiceclone.storage.vector_store import VectorStore, NullVectorStore

def verify_protocol_compatibility(store: VectorStore):
    # This function checks static typing compatibility at runtime
    store.upsert(namespace="speaker", item_id="spk_1", embedding=[0.1]*128, model_id="model_a")
    results = store.search(namespace="speaker", query_embedding=[0.1]*128, limit=5)
    assert isinstance(results, list)
    store.delete(namespace="speaker", item_id="spk_1")

@pytest.mark.unit
def test_null_vector_store():
    store = NullVectorStore()
    verify_protocol_compatibility(store)
    
    # NullVectorStore always returns empty search results
    results = store.search(namespace="speaker", query_embedding=[0.1]*128, limit=5)
    assert len(results) == 0
