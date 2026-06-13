import sqlite3
from typing import Any, Dict, Optional

from myvoiceclone.storage.artifact_store import ArtifactStore


def select_reference_artifact(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    *,
    dataset_id: Optional[str] = None,
    min_duration_sec: float = 1.0,
) -> Dict[str, Any]:
    params: list[Any] = [min_duration_sec]
    dataset_join = ""
    dataset_filter = ""
    if dataset_id:
        dataset_join = "JOIN dataset_segments ds ON ds.segment_id = s.id"
        dataset_filter = "AND ds.dataset_id = ?"
        params.append(dataset_id)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT s.id, s.recording_id, s.cleaned_artifact_id, s.transcript,
               (s.end_sec - s.start_sec) AS duration_sec
        FROM segments s
        {dataset_join}
        WHERE s.cleaned_artifact_id IS NOT NULL
          AND COALESCE(TRIM(s.transcript), '') != ''
          AND (s.end_sec - s.start_sec) >= ?
          {dataset_filter}
        ORDER BY duration_sec DESC, s.id ASC
        LIMIT 1;
        """,
        params,
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError("No eligible reference audio artifact found")

    artifact = artifact_store.get_artifact(row["cleaned_artifact_id"])
    if not artifact:
        raise ValueError(f"Reference cleaned artifact {row['cleaned_artifact_id']} is missing")

    return {
        "segment_id": row["id"],
        "recording_id": row["recording_id"],
        "artifact_id": artifact.id,
        "uri": artifact.uri,
        "path": artifact_store.get_absolute_path(artifact),
        "sha256": artifact.sha256,
        "bytes": artifact.bytes,
        "duration_sec": row["duration_sec"],
        "transcript": row["transcript"],
        "metadata_json": artifact.metadata_json,
    }
