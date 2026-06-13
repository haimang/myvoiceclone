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
    assert events[1]["data"]["metadata_json"] == {}


@pytest.mark.api
def test_audit_trace_run_includes_eval_release_and_policy(client, db_conn):
    db_conn.execute(
        """
        INSERT INTO model_runs (id, name, status, config_json, created_at)
        VALUES ('run_trace_1', 'trace run', 'completed', '{}', '2026-06-13 11:00:00');
        """
    )
    db_conn.execute(
        """
        INSERT INTO reports (id, name, report_type, kind, subject_type, subject_id, status, summary_json, created_at)
        VALUES ('rpt_trace_1', 'Trace Report', 'eval', 'eval', 'run', 'run_trace_1', 'completed', '{}', '2026-06-13 11:01:00');
        """
    )
    db_conn.execute(
        """
        INSERT INTO eval_metrics (run_id, report_id, metric_name, metric_value, metric_json, created_at)
        VALUES ('run_trace_1', 'rpt_trace_1', 'smoke_duration', 1.0, '{"metric_source":"smoke_metric","adapter_mode":"real"}', '2026-06-13 11:02:00');
        """
    )
    db_conn.execute(
        """
        INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type, created_at)
        VALUES ('art_trace_1', 'trace.wav', 'rendered/trace.wav', 'sha_trace_sample', 10, 'rendered_audio', '2026-06-13 11:02:30');
        """
    )
    db_conn.execute(
        """
        INSERT INTO eval_samples (id, run_id, report_id, prompt, audio_artifact_id, scores_json, created_at)
        VALUES ('sample_trace_1', 'run_trace_1', 'rpt_trace_1', 'hello', 'art_trace_1', '{"metric_source":"manual_mos"}', '2026-06-13 11:03:00');
        """
    )
    db_conn.execute(
        """
        INSERT INTO release_gates (id, model_run_id, passed, status, details_json, decision_json)
        VALUES ('gate_trace_1', 'run_trace_1', 1, 'passed', '{"smoke_pass":true}', '{"quality_pass":true}');
        """
    )
    db_conn.execute(
        """
        INSERT INTO policy_events (event_type, status, details_json, subject_type, subject_id, policy_name, decision, payload_json, created_at)
        VALUES ('release_policy', 'passed', '{}', 'run', 'run_trace_1', 'release_gate', 'passed', '{"run_id":"run_trace_1"}', '2026-06-13 11:05:00');
        """
    )
    db_conn.commit()

    res = client.get("/api/audit/trace?subject_id=run_trace_1&subject_type=run")

    assert res.status_code == 200
    event_types = [event["type"] for event in res.json()["trace_events"]]
    assert "model_run" in event_types
    assert "eval_metric" in event_types
    assert "eval_sample" in event_types
    assert "release_gate" in event_types
    assert "policy_event" in event_types
    metric_event = next(event for event in res.json()["trace_events"] if event["type"] == "eval_metric")
    assert metric_event["data"]["metric_json"]["metric_source"] == "smoke_metric"


@pytest.mark.api
def test_audit_trace_report_includes_eval_links(client, db_conn):
    db_conn.execute(
        """
        INSERT INTO model_runs (id, name, status, config_json)
        VALUES ('run_report_trace', 'report trace run', 'completed', '{}');
        """
    )
    db_conn.execute(
        """
        INSERT INTO reports (id, name, report_type, kind, subject_type, subject_id, status, summary_json)
        VALUES ('rpt_report_trace', 'Trace Report', 'eval', 'eval', 'run', 'run_report_trace', 'completed', '{"adapter_mode":"real"}');
        """
    )
    db_conn.execute(
        """
        INSERT INTO eval_metrics (run_id, report_id, metric_name, metric_value, metric_json)
        VALUES ('run_report_trace', 'rpt_report_trace', 'smoke_duration', 1.0, '{"metric_source":"smoke_metric"}');
        """
    )
    db_conn.commit()

    res = client.get("/api/audit/trace?subject_id=rpt_report_trace&subject_type=report")

    assert res.status_code == 200
    events = res.json()["trace_events"]
    assert [event["type"] for event in events] == ["report", "eval_metric"]
    assert events[0]["data"]["summary_json"]["adapter_mode"] == "real"

@pytest.mark.api
def test_audit_trace_missing_404(client):
    res = client.get("/api/audit/trace?subject_id=non_existent_job&subject_type=job")
    assert res.status_code == 404
