import sqlite3
from typing import Optional
from myvoiceclone.storage.repositories import JobRepository

def write_job_event(
    conn: sqlite3.Connection,
    job_id: str,
    event_type: str,
    status_from: Optional[str] = None,
    status_to: Optional[str] = None,
    message: Optional[str] = None
) -> None:
    repo = JobRepository(conn)
    repo.add_event(
        job_id=job_id,
        event_type=event_type,
        status_from=status_from,
        status_to=status_to,
        message=message
    )
