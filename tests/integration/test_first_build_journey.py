import pytest
import sqlite3
import uuid
import os
from fastapi.testclient import TestClient
from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db

@pytest.fixture
def api_client(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    return TestClient(app)

@pytest.mark.integration
def test_capstone_journey(api_client, db_conn, synthetic_wav):
    # A. Setup config/feature flag for security
    db_conn.execute("INSERT INTO speakers (id, display_name, role) VALUES ('target_spk', 'Target Speaker', 'owner');")
    db_conn.commit()

    # B. Ingest + Preprocessing
    # We create a preprocess_all job directly in DB, then trigger it via API
    job_id = "job_capstone_preprocess"
    db_conn.execute(
        """
        INSERT INTO jobs (id, name, status, payload_json)
        VALUES (?, 'preprocess_all', 'pending', ?);
        """,
        (job_id, f'{{"filepath": "{synthetic_wav}", "min_quality_score": 0.6}}')
    )
    db_conn.commit()

    # Run the preprocess job via API
    res_run_preprocess = api_client.post(f"/api/jobs/{job_id}/run")
    assert res_run_preprocess.status_code == 200
    assert res_run_preprocess.json()["status"] == "completed"

    # Query recording
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM recordings LIMIT 1;")
    rec_row = cursor.fetchone()
    assert rec_row is not None
    recording_id = rec_row["id"]

    # C, D, E, F, G. Verify segments created and score/curate them
    cursor.execute("SELECT id, status FROM segments WHERE recording_id = ?;", (recording_id,))
    segments = cursor.fetchall()
    assert len(segments) > 0
    segment_id = segments[0]["id"]

    # Associate segment with speaker
    db_conn.execute("UPDATE segments SET speaker_id = 'target_spk' WHERE id = ?;", (segment_id,))
    db_conn.commit()

    # Review segment via API
    res_review = api_client.patch(
        f"/api/segments/{segment_id}/review",
        json={"status_to": "keep", "reason": "clean high quality target speaker audio", "reviewer": "admin"}
    )
    assert res_review.status_code == 200
    assert res_review.json()["status"] == "keep"

    # H. Create and freeze dataset
    res_ds = api_client.post(
        "/api/datasets",
        json={"name": "capstone_dataset", "filter_json": {"min_quality_score": 0.6}}
    )
    assert res_ds.status_code == 200
    dataset_id = res_ds.json()["id"]

    # Freeze dataset
    res_freeze = api_client.post(f"/api/datasets/{dataset_id}/freeze")
    assert res_freeze.status_code == 200
    assert res_freeze.json()["status"] == "frozen"

    # I. Create and run training job (fake RVC/So-VITS)
    res_train_job = api_client.post(
        "/api/training/jobs",
        json={"dataset_id": dataset_id, "model_name": "capstone_model", "config": {"epochs": 1}}
    )
    assert res_train_job.status_code == 200
    train_job_id = res_train_job.json()["id"]

    # Run training
    res_run_train = api_client.post(f"/api/jobs/{train_job_id}/run")
    assert res_run_train.status_code == 200
    assert res_run_train.json()["status"] == "completed"

    # Retrieve model run ID
    cursor.execute("SELECT id FROM model_runs WHERE dataset_id = ? LIMIT 1;", (dataset_id,))
    run_row = cursor.fetchone()
    assert run_row is not None
    model_run_id = run_row["id"]

    # J. Release gate & policy checks (P7 policy-on variant)
    # Enable policy flag temporarily by mocking policies config
    import myvoiceclone.domain.policies
    original_config = myvoiceclone.domain.policies.load_local_config
    myvoiceclone.domain.policies.load_local_config = lambda: {"security": {"enabled": True}}

    try:
        # Create release gate (unauthorized since no consent exists for target_spk)
        gate_id = "capstone_gate"
        res_gate = api_client.post(
            "/api/reports/release-gates",
            json={"gate_id": gate_id, "model_run_id": model_run_id}
        )
        assert res_gate.status_code == 200
        assert res_gate.json()["passed"] == 0

        # Attempt to waive with empty reason (should fail)
        res_waive_fail = api_client.post(
            f"/api/reports/release-gates/{gate_id}/waive",
            json={"approved_by": "admin", "reason": "   "}
        )
        assert res_waive_fail.status_code == 400

        # Waive with valid reason
        res_waive_ok = api_client.post(
            f"/api/reports/release-gates/{gate_id}/waive",
            json={"approved_by": "admin", "reason": "Physical consent signature verified manually"}
        )
        assert res_waive_ok.status_code == 200
        assert res_waive_ok.json()["passed"] == 1

    finally:
        # Restore original config loader
        myvoiceclone.domain.policies.load_local_config = original_config

    # K. Verify Audit Trace
    res_trace = api_client.get(f"/api/audit/trace?subject_id={recording_id}&subject_type=recording")
    assert res_trace.status_code == 200
    trace_data = res_trace.json()
    assert trace_data["subject_id"] == recording_id
    assert len(trace_data["trace_events"]) > 0
