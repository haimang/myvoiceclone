from typing import Protocol, List, Dict, Any

class VectorStore(Protocol):
    def upsert(self, namespace: str, item_id: str, embedding: List[float], model_id: str) -> None:
        """Insert or update an embedding for an item within a namespace."""
        ...

    def search(self, namespace: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search nearest neighbor embeddings, returning list of dicts with keys 'item_id', 'distance'."""
        ...

    def delete(self, namespace: str, item_id: str) -> None:
        """Delete an embedding from a namespace."""
        ...

class NullVectorStore:
    def upsert(self, namespace: str, item_id: str, embedding: List[float], model_id: str) -> None:
        pass

    def search(self, namespace: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        return []

    def delete(self, namespace: str, item_id: str) -> None:
        pass
