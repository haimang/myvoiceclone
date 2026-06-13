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
def test_inference_endpoints_success(client):
    payload = {
        "speaker_id": "spk_target",
        "text": "Hello, synthesis test",
        "config": {"speed": 1.0}
    }
    
    res = client.post("/api/inference", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "xtts_synth_spk_target" in data["name"]
    assert "rendered_artifact_id" in data["config_json"]
