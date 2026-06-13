import sqlite3
import struct
from typing import List, Dict, Any
from myvoiceclone.storage.vector_store import VectorStore

class Vec0Store:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _get_or_create_item_id(self, namespace: str, item_id: str, model_id: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id FROM embedding_jobs
            WHERE namespace = ? AND item_id = ? AND model_id = ?;
            """,
            (namespace, item_id, model_id)
        )
        row = cursor.fetchone()
        if row:
            return row["id"]
            
        cursor.execute(
            """
            INSERT INTO embedding_jobs (namespace, item_id, model_id, status)
            VALUES (?, ?, ?, 'completed');
            """,
            (namespace, item_id, model_id)
        )
        return cursor.lastrowid

    def upsert(self, namespace: str, item_id: str, embedding: List[float], model_id: str) -> None:
        if namespace not in ('speaker', 'audio', 'text'):
            raise ValueError(f"Invalid namespace: {namespace}")
            
        db_id = self._get_or_create_item_id(namespace, item_id, model_id)
        embedding_bytes = struct.pack(f"{len(embedding)}f", *embedding)
        
        # In sqlite-vec, update rowid by deleting first and inserting
        self.conn.execute(f"DELETE FROM vec_{namespace} WHERE rowid = ?;", (db_id,))
        self.conn.execute(
            f"INSERT INTO vec_{namespace}(rowid, embedding) VALUES (?, ?);",
            (db_id, embedding_bytes)
        )

    def search(self, namespace: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        if namespace not in ('speaker', 'audio', 'text'):
            raise ValueError(f"Invalid namespace: {namespace}")
            
        query_bytes = struct.pack(f"{len(query_embedding)}f", *query_embedding)
        cursor = self.conn.cursor()
        
        # sqlite-vec syntax: SELECT rowid, distance FROM vec_x WHERE embedding MATCH ? AND k = ?
        cursor.execute(
            f"""
            SELECT rowid, distance 
            FROM vec_{namespace} 
            WHERE embedding MATCH ? AND k = ?;
            """,
            (query_bytes, limit)
        )
        
        results = []
        for row in cursor.fetchall():
            rowid = row["rowid"]
            distance = row["distance"]
            
            # Map rowid back to item_id
            cursor2 = self.conn.cursor()
            cursor2.execute("SELECT item_id FROM embedding_jobs WHERE id = ?;", (rowid,))
            item_row = cursor2.fetchone()
            if item_row:
                results.append({
                    "item_id": item_row["item_id"],
                    "distance": distance
                })
        return results

    def delete(self, namespace: str, item_id: str) -> None:
        if namespace not in ('speaker', 'audio', 'text'):
            raise ValueError(f"Invalid namespace: {namespace}")
            
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM embedding_jobs WHERE namespace = ? AND item_id = ?;",
            (namespace, item_id)
        )
        rows = cursor.fetchall()
        for row in rows:
            db_id = row["id"]
            self.conn.execute(f"DELETE FROM vec_{namespace} WHERE rowid = ?;", (db_id,))
            
        self.conn.execute(
            "DELETE FROM embedding_jobs WHERE namespace = ? AND item_id = ?;",
            (namespace, item_id)
        )
