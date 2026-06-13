import os
import hashlib
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from myvoiceclone.domain.entities import Artifact
from myvoiceclone.storage.repositories import dict_to_json, json_to_dict, parse_datetime

class ArtifactStore:
    def __init__(self, conn: sqlite3.Connection, root_dir: str):
        self.conn = conn
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def create_artifact(
        self,
        name: str,
        content: bytes,
        artifact_type: str,
        parent_artifact_id: Optional[str] = None,
        job_id: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Artifact:
        sha256 = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)
        
        # Generate unique artifact ID
        import uuid
        artifact_id = f"art_{uuid.uuid4().hex[:12]}"
        
        # Determine target file path
        rel_dir = os.path.join(artifact_type)
        abs_dir = os.path.join(self.root_dir, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        
        # Use unique filename to prevent collisions
        file_ext = os.path.splitext(name)[1]
        unique_name = f"{artifact_id}{file_ext}" if file_ext else artifact_id
        rel_uri = os.path.join(rel_dir, unique_name)
        abs_path = os.path.join(self.root_dir, rel_uri)
        
        # Write content
        with open(abs_path, 'wb') as f:
            f.write(content)
            
        metadata = metadata_json or {}
        
        # Save to DB
        self.conn.execute(
            """
            INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type, parent_artifact_id, job_id, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (artifact_id, name, rel_uri, sha256, size_bytes, artifact_type, parent_artifact_id, job_id, dict_to_json(metadata))
        )
        
        return Artifact(
            id=artifact_id,
            name=name,
            uri=rel_uri,
            sha256=sha256,
            bytes=size_bytes,
            artifact_type=artifact_type,
            parent_artifact_id=parent_artifact_id,
            job_id=job_id,
            metadata_json=metadata
        )

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM artifacts WHERE id = ?;", (artifact_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Artifact(
            id=row["id"],
            name=row["name"],
            uri=row["uri"],
            sha256=row["sha256"],
            bytes=row["bytes"],
            artifact_type=row["artifact_type"],
            parent_artifact_id=row["parent_artifact_id"],
            job_id=row["job_id"],
            metadata_json=json_to_dict(row["metadata_json"]),
            created_at=parse_datetime(row["created_at"])
        )

    def get_absolute_path(self, artifact: Artifact) -> str:
        return os.path.abspath(os.path.join(self.root_dir, artifact.uri))

    def get_lineage(self, artifact_id: str) -> List[Artifact]:
        lineage = []
        current_id = artifact_id
        
        while current_id:
            art = self.get_artifact(current_id)
            if not art:
                break
            lineage.append(art)
            current_id = art.parent_artifact_id
            
        return lineage
