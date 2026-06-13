import os
from typing import List, Dict, Any
from myvoiceclone.storage.vector_store import VectorStore

class Vec1Store:
    def __init__(self, conn):
        self.conn = conn
        self.enabled = os.getenv("ENABLE_VEC1_PROBE", "false").lower() == "true"

    def upsert(self, namespace: str, item_id: str, embedding: List[float], model_id: str) -> None:
        if not self.enabled:
            raise RuntimeError("Vec1Store is not enabled. Set ENABLE_VEC1_PROBE=true to use it.")
        # Mock/placeholder implementation for testing
        pass

    def search(self, namespace: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError("Vec1Store is not enabled. Set ENABLE_VEC1_PROBE=true to use it.")
        return []

    def delete(self, namespace: str, item_id: str) -> None:
        if not self.enabled:
            raise RuntimeError("Vec1Store is not enabled. Set ENABLE_VEC1_PROBE=true to use it.")
        pass
