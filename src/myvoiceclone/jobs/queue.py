import uuid
import sqlite3
from typing import Dict, Any
from myvoiceclone.domain.entities import Job
from myvoiceclone.domain.states import JobStatus
from myvoiceclone.storage.repositories import JobRepository
from myvoiceclone.jobs.events import write_job_event

class JobQueue:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo = JobRepository(conn)

    def enqueue(self, name: str, payload_json: Dict[str, Any]) -> Job:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(
            id=job_id,
            name=name,
            status=JobStatus.PENDING.value,
            payload_json=payload_json
        )
        self.repo.save(job)
        write_job_event(
            conn=self.conn,
            job_id=job_id,
            event_type="enqueue",
            status_from=None,
            status_to=JobStatus.PENDING.value,
            message=f"Job '{name}' submitted to queue"
        )
        self.conn.commit()
        return job
