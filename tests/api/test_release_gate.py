import pytest
from fastapi.testclient import TestClient
from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db

@pytest.fixture
def api_client(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    return TestClient(app)

def setup_gate_test_data(conn):
    # Insert speaker
    conn.execute("INSERT INTO speakers (id, display_name, role) VALUES ('gate_spk_1', 'Gate Speaker', 'owner');")
    # Insert recording
    conn.execute("INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status) VALUES ('gate_rec_1', 'uri_1', 'sha_1', 10.0, 16000, 1, 'completed');")
    # Insert segment
    conn.execute(
        """
        INSERT INTO segments (id, recording_id, speaker_id, start_sec, end_sec, status)
        VALUES ('gate_seg_1', 'gate_rec_1', 'gate_spk_1', 0.0, 5.0, 'completed');
        """
    )
    # Insert dataset
    conn.execute("INSERT INTO datasets (id, name, status) VALUES ('gate_ds_1', 'Gate Dataset', 'active');")
    # Link dataset/segment
    conn.execute("INSERT INTO dataset_segments (dataset_id, segment_id, split) VALUES ('gate_ds_1', 'gate_seg_1', 'train');")
    # Insert model run
    conn.execute("INSERT INTO model_runs (id, name, dataset_id, status) VALUES ('gate_run_1', 'Gate Run', 'gate_ds_1', 'completed');")
    conn.commit()

@pytest.mark.api
def test_create_release_gate_unauthorized(monkeypatch, api_client, db_conn):
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": True}}
    )
    setup_gate_test_data(db_conn)
    
    # Try to create release gate. Since no consent exists, it should fail (passed=0)
    res = api_client.post(
        "/api/reports/release-gates",
        json={"gate_id": "gate_unauth", "model_run_id": "gate_run_1"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "gate_unauth"
    assert data["passed"] == 0
    assert "details_json" in data
    assert "Missing consent" in data["details_json"]["reason"]

@pytest.mark.api
def test_create_release_gate_authorized(monkeypatch, api_client, db_conn):
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": True}}
    )
    setup_gate_test_data(db_conn)
    
    # Insert consent to authorize the speaker
    db_conn.execute("INSERT INTO consent_ledger (id, speaker_id, recording_id, granted) VALUES ('c_gate_1', 'gate_spk_1', 'gate_rec_1', 1);")
    db_conn.commit()
    
    res = api_client.post(
        "/api/reports/release-gates",
        json={"gate_id": "gate_auth", "model_run_id": "gate_run_1"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "gate_auth"
    assert data["passed"] == 1
    assert "All speakers have granted consent" in data["details_json"]["reason"]

@pytest.mark.api
def test_waive_release_gate_validation_errors(monkeypatch, api_client, db_conn):
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": True}}
    )
    setup_gate_test_data(db_conn)
    
    # Create failed gate first
    api_client.post(
        "/api/reports/release-gates",
        json={"gate_id": "gate_to_waive_err", "model_run_id": "gate_run_1"}
    )
    
    # Attempt to waive with missing reason or empty reason
    res = api_client.post(
        "/api/reports/release-gates/gate_to_waive_err/waive",
        json={"approved_by": "admin", "reason": ""}
    )
    assert res.status_code == 400
    assert "reason is required" in res.json()["detail"]

@pytest.mark.api
def test_waive_release_gate_success(monkeypatch, api_client, db_conn):
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": True}}
    )
    setup_gate_test_data(db_conn)
    
    # Create failed gate first
    api_client.post(
        "/api/reports/release-gates",
        json={"gate_id": "gate_to_waive_ok", "model_run_id": "gate_run_1"}
    )
    
    # Waive it
    res = api_client.post(
        "/api/reports/release-gates/gate_to_waive_ok/waive",
        json={"approved_by": "supervisor_bob", "reason": "Low risk local debug override"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] == 1
    assert data["approved_by"] == "supervisor_bob"
    assert data["details_json"]["waived"] is True
    assert data["details_json"]["waived_reason"] == "Low risk local debug override"

@pytest.mark.api
def test_release_gate_not_found(api_client):
    res = api_client.post(
        "/api/reports/release-gates",
        json={"gate_id": "gate_missing", "model_run_id": "non_existent_run"}
    )
    assert res.status_code == 404
    
    res2 = api_client.get("/api/reports/release-gates/gate_missing")
    assert res2.status_code == 404


@pytest.mark.api
def test_release_gate_blocks_mock_metrics(monkeypatch, api_client, db_conn):
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": False}}
    )
    db_conn.execute("INSERT INTO model_runs (id, name, status, config_json) VALUES ('gate_mock_run', 'Mock Run', 'completed', '{}');")
    db_conn.execute(
        """
        INSERT INTO eval_metrics (run_id, metric_name, metric_value, metric_json)
        VALUES ('gate_mock_run', 'speaker_similarity', 0.99, '{"metric_source":"mock","quality_gate_eligible":false}');
        """
    )
    db_conn.commit()

    res = api_client.post(
        "/api/reports/release-gates",
        json={"gate_id": "gate_mock_metric", "model_run_id": "gate_mock_run"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is False
    assert data["details_json"]["smoke_pass"] is True
    assert data["details_json"]["quality_pass"] is False
    assert "mock metrics" in data["details_json"]["blocked_reasons"][0]
