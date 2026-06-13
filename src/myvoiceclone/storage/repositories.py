import json
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
from myvoiceclone.domain.entities import (
    Speaker, Recording, Segment, Dataset, DatasetSegment, Job, JobEvent, Artifact, ModelRun, Report
)

def dict_to_json(d: Optional[Dict[str, Any]]) -> str:
    return json.dumps(d if d is not None else {})

def json_to_dict(s: Optional[str]) -> Dict[str, Any]:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}

def parse_datetime(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # SQLite returns timestamps as strings or datetime
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        return None

class SpeakerRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, speaker: Speaker):
        self.conn.execute(
            """
            INSERT INTO speakers (id, display_name, role, metadata_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name=excluded.display_name,
                role=excluded.role,
                metadata_json=excluded.metadata_json;
            """,
            (speaker.id, speaker.display_name, speaker.role, dict_to_json(speaker.metadata_json))
        )

    def get_by_id(self, id: str) -> Optional[Speaker]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, display_name, role, created_at, metadata_json FROM speakers WHERE id = ?;", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Speaker(
            id=row["id"],
            display_name=row["display_name"],
            role=row["role"],
            created_at=parse_datetime(row["created_at"]),
            metadata_json=json_to_dict(row["metadata_json"])
        )

    def list_all(self) -> List[Speaker]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, display_name, role, created_at, metadata_json FROM speakers;")
        return [
            Speaker(
                id=row["id"],
                display_name=row["display_name"],
                role=row["role"],
                created_at=parse_datetime(row["created_at"]),
                metadata_json=json_to_dict(row["metadata_json"])
            )
            for row in cursor.fetchall()
        ]

class RecordingRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, rec: Recording):
        self.conn.execute(
            """
            INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_uri=excluded.source_uri,
                sha256=excluded.sha256,
                duration_sec=excluded.duration_sec,
                sample_rate=excluded.sample_rate,
                channels=excluded.channels,
                status=excluded.status,
                metadata_json=excluded.metadata_json;
            """,
            (rec.id, rec.source_uri, rec.sha256, rec.duration_sec, rec.sample_rate, rec.channels, rec.status, dict_to_json(rec.metadata_json))
        )

    def get_by_id(self, id: str) -> Optional[Recording]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, source_uri, sha256, duration_sec, sample_rate, channels, status, metadata_json, created_at FROM recordings WHERE id = ?;", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Recording(
            id=row["id"],
            source_uri=row["source_uri"],
            sha256=row["sha256"],
            duration_sec=row["duration_sec"],
            sample_rate=row["sample_rate"],
            channels=row["channels"],
            status=row["status"],
            metadata_json=json_to_dict(row["metadata_json"]),
            created_at=parse_datetime(row["created_at"])
        )

    def list_all(self) -> List[Recording]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, source_uri, sha256, duration_sec, sample_rate, channels, status, metadata_json, created_at FROM recordings;")
        return [
            Recording(
                id=row["id"],
                source_uri=row["source_uri"],
                sha256=row["sha256"],
                duration_sec=row["duration_sec"],
                sample_rate=row["sample_rate"],
                channels=row["channels"],
                status=row["status"],
                metadata_json=json_to_dict(row["metadata_json"]),
                created_at=parse_datetime(row["created_at"])
            )
            for row in cursor.fetchall()
        ]

class SegmentRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, seg: Segment):
        self.conn.execute(
            """
            INSERT INTO segments (
                id, recording_id, speaker_id, start_sec, end_sec, 
                audio_artifact_id, cleaned_artifact_id, transcript, status, 
                quality_score, speaker_score, noise_score, overlap_score, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                recording_id=excluded.recording_id,
                speaker_id=excluded.speaker_id,
                start_sec=excluded.start_sec,
                end_sec=excluded.end_sec,
                audio_artifact_id=excluded.audio_artifact_id,
                cleaned_artifact_id=excluded.cleaned_artifact_id,
                transcript=excluded.transcript,
                status=excluded.status,
                quality_score=excluded.quality_score,
                speaker_score=excluded.speaker_score,
                noise_score=excluded.noise_score,
                overlap_score=excluded.overlap_score,
                metadata_json=excluded.metadata_json;
            """,
            (
                seg.id, seg.recording_id, seg.speaker_id, seg.start_sec, seg.end_sec,
                seg.audio_artifact_id, seg.cleaned_artifact_id, seg.transcript, seg.status,
                seg.quality_score, seg.speaker_score, seg.noise_score, seg.overlap_score,
                dict_to_json(seg.metadata_json)
            )
        )

    def get_by_id(self, id: str) -> Optional[Segment]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, recording_id, speaker_id, start_sec, end_sec, 
                   audio_artifact_id, cleaned_artifact_id, transcript, status, 
                   quality_score, speaker_score, noise_score, overlap_score, metadata_json, created_at 
            FROM segments WHERE id = ?;
            """,
            (id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Segment(
            id=row["id"],
            recording_id=row["recording_id"],
            speaker_id=row["speaker_id"],
            start_sec=row["start_sec"],
            end_sec=row["end_sec"],
            audio_artifact_id=row["audio_artifact_id"],
            cleaned_artifact_id=row["cleaned_artifact_id"],
            transcript=row["transcript"],
            status=row["status"],
            quality_score=row["quality_score"],
            speaker_score=row["speaker_score"],
            noise_score=row["noise_score"],
            overlap_score=row["overlap_score"],
            metadata_json=json_to_dict(row["metadata_json"]),
            created_at=parse_datetime(row["created_at"])
        )

    def list_by_recording(self, recording_id: str) -> List[Segment]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM segments WHERE recording_id = ? ORDER BY start_sec;", (recording_id,))
        return [
            Segment(
                id=row["id"],
                recording_id=row["recording_id"],
                speaker_id=row["speaker_id"],
                start_sec=row["start_sec"],
                end_sec=row["end_sec"],
                audio_artifact_id=row["audio_artifact_id"],
                cleaned_artifact_id=row["cleaned_artifact_id"],
                transcript=row["transcript"],
                status=row["status"],
                quality_score=row["quality_score"],
                speaker_score=row["speaker_score"],
                noise_score=row["noise_score"],
                overlap_score=row["overlap_score"],
                metadata_json=json_to_dict(row["metadata_json"]),
                created_at=parse_datetime(row["created_at"])
            )
            for row in cursor.fetchall()
        ]

class DatasetRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, ds: Dataset):
        frozen_str = ds.frozen_at.isoformat() if ds.frozen_at else None
        self.conn.execute(
            """
            INSERT INTO datasets (id, name, status, manifest_artifact_id, manifest_sha256, filter_json, frozen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                status=excluded.status,
                manifest_artifact_id=excluded.manifest_artifact_id,
                manifest_sha256=excluded.manifest_sha256,
                filter_json=excluded.filter_json,
                frozen_at=excluded.frozen_at;
            """,
            (ds.id, ds.name, ds.status, ds.manifest_artifact_id, ds.manifest_sha256, dict_to_json(ds.filter_json), frozen_str)
        )

    def get_by_id(self, id: str) -> Optional[Dataset]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM datasets WHERE id = ?;", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Dataset(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            manifest_artifact_id=row["manifest_artifact_id"],
            manifest_sha256=row["manifest_sha256"],
            filter_json=json_to_dict(row["filter_json"]),
            created_at=parse_datetime(row["created_at"]),
            frozen_at=parse_datetime(row["frozen_at"])
        )

    def add_segment(self, dataset_id: str, segment_id: str, split: str):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO dataset_segments (dataset_id, segment_id, split)
            VALUES (?, ?, ?);
            """,
            (dataset_id, segment_id, split)
        )

    def get_segments(self, dataset_id: str) -> List[DatasetSegment]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT dataset_id, segment_id, split FROM dataset_segments WHERE dataset_id = ?;", (dataset_id,))
        return [
            DatasetSegment(
                dataset_id=row["dataset_id"],
                segment_id=row["segment_id"],
                split=row["split"]
            )
            for row in cursor.fetchall()
        ]

class JobRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, job: Job):
        self.conn.execute(
            """
            INSERT INTO jobs (id, name, status, payload_json, error_msg, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                payload_json=excluded.payload_json,
                error_msg=excluded.error_msg,
                updated_at=CURRENT_TIMESTAMP;
            """,
            (job.id, job.name, job.status, dict_to_json(job.payload_json), job.error_msg)
        )

    def add_event(self, job_id: str, event_type: str, status_from: Optional[str], status_to: Optional[str], message: Optional[str]):
        self.conn.execute(
            """
            INSERT INTO job_events (job_id, event_type, status_from, status_to, message)
            VALUES (?, ?, ?, ?, ?);
            """,
            (job_id, event_type, status_from, status_to, message)
        )

    def get_by_id(self, id: str) -> Optional[Job]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, status, payload_json, error_msg, created_at, updated_at FROM jobs WHERE id = ?;", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Job(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            payload_json=json_to_dict(row["payload_json"]),
            error_msg=row["error_msg"],
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"])
        )

    def get_events(self, job_id: str) -> List[JobEvent]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, job_id, event_type, status_from, status_to, message, created_at FROM job_events WHERE job_id = ? ORDER BY id;", (job_id,))
        return [
            JobEvent(
                id=row["id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                status_from=row["status_from"],
                status_to=row["status_to"],
                message=row["message"],
                created_at=parse_datetime(row["created_at"])
            )
            for row in cursor.fetchall()
        ]

class ModelRunRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, run: ModelRun):
        self.conn.execute(
            """
            INSERT INTO model_runs (id, name, dataset_id, status, config_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                config_json=excluded.config_json;
            """,
            (run.id, run.name, run.dataset_id, run.status, dict_to_json(run.config_json))
        )

    def get_by_id(self, id: str) -> Optional[ModelRun]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, dataset_id, status, config_json, created_at FROM model_runs WHERE id = ?;", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return ModelRun(
            id=row["id"],
            name=row["name"],
            dataset_id=row["dataset_id"],
            status=row["status"],
            config_json=json_to_dict(row["config_json"]),
            created_at=parse_datetime(row["created_at"])
        )

class ReportRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, rpt: Report):
        self.conn.execute(
            """
            INSERT INTO reports (id, name, report_type, summary_json, artifact_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                report_type=excluded.report_type,
                summary_json=excluded.summary_json,
                artifact_id=excluded.artifact_id;
            """,
            (rpt.id, rpt.name, rpt.report_type, dict_to_json(rpt.summary_json), rpt.artifact_id)
        )

    def get_by_id(self, id: str) -> Optional[Report]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, report_type, summary_json, artifact_id, created_at FROM reports WHERE id = ?;", (id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Report(
            id=row["id"],
            name=row["name"],
            report_type=row["report_type"],
            summary_json=json_to_dict(row["summary_json"]),
            artifact_id=row["artifact_id"],
            created_at=parse_datetime(row["created_at"])
        )
