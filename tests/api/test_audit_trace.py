import pytest
from fastapi.testclient import TestClient
from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db

@pytest.fixture
def client(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    return TestClient(app)

@pytest.mark.api
def test_audit_trace_job_flow(client, db_conn):
    # Setup job
    db_conn.execute(
        """
        INSERT INTO jobs (id, name, status, payload_json, created_at)
        VALUES ('job_trace_1', 'ingest', 'completed', '{}', '2026-06-13 11:00:00');
        """
    )
    # Setup job event
    db_conn.execute(
        """
        INSERT INTO job_events (id, job_id, event_type, status_from, status_to, message, created_at)
        VALUES (10, 'job_trace_1', 'start', 'pending', 'running', 'Started', '2026-06-13 11:01:00'),
               (11, 'job_trace_1', 'complete', 'running', 'completed', 'Completed', '2026-06-13 11:02:00');
        """
    )
    # Setup artifact produced by this job
    db_conn.execute(
        """
        INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type, job_id, created_at)
        VALUES ('art_trace_1', 'raw.wav', 'raw/raw.wav', 'sha_t', 10, 'raw', 'job_trace_1', '2026-06-13 11:03:00');
        """
    )
    db_conn.commit()

    # Query audit trace
    res = client.get("/api/audit/trace?subject_id=job_trace_1&subject_type=job")
    assert res.status_code == 200
    data = res.json()
    assert data["subject_id"] == "job_trace_1"
    assert data["subject_type"] == "job"
    
    events = data["trace_events"]
    # Total events: 1 job + 2 job_events + 1 artifact = 4
    assert len(events) == 4
    
    # Chronological sort check
    timestamps = [e["timestamp"] for e in events]
    assert timestamps == sorted(timestamps)
    assert events[0]["type"] == "job"
    assert events[1]["type"] == "job_event"
    assert events[2]["type"] == "job_event"
    assert events[3]["type"] == "artifact"

@pytest.mark.api
def test_audit_trace_missing_404(client):
    res = client.get("/api/audit/trace?subject_id=non_existent_job&subject_type=job")
    assert res.status_code == 404
