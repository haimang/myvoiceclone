import sqlite3
from typing import Any, Dict, Optional
from myvoiceclone.storage.repositories import JobRepository

def write_job_event(
    conn: sqlite3.Connection,
    job_id: str,
    event_type: str,
    status_from: Optional[str] = None,
    status_to: Optional[str] = None,
    message: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> None:
    repo = JobRepository(conn)
    repo.add_event(
        job_id=job_id,
        event_type=event_type,
        status_from=status_from,
        status_to=status_to,
        message=message,
        metadata_json=metadata_json,
    )


def write_step_event(
    conn: sqlite3.Connection,
    job_id: str,
    step: str,
    status: str,
    *,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None,
    artifact_ids: Optional[list[str]] = None,
    adapter_mode: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> None:
    metadata = {
        "step": step,
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
        "artifact_ids": artifact_ids or [],
        "adapter_mode": adapter_mode,
    }
    if metadata_json:
        metadata.update(metadata_json)
    compact = {k: v for k, v in metadata.items() if v is not None}
    write_job_event(
        conn,
        job_id,
        f"step_{status}",
        None,
        status,
        f"{step} {status}",
        metadata_json=compact,
    )
