import pytest
from fastapi.testclient import TestClient
from myvoiceclone.domain.entities import Artifact
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


@pytest.mark.api
def test_real_inference_endpoint_returns_artifact(client, monkeypatch):
    def fake_service(**kwargs):
        return Artifact(
            id="art_real_api",
            name="out.wav",
            uri="rendered_audio/out.wav",
            sha256="sha",
            bytes=12,
            artifact_type="rendered_audio",
            parent_artifact_id=kwargs["reference_artifact_id"],
            metadata_json={"adapter_mode": "real", "model": kwargs["model_id"]},
        )

    monkeypatch.setattr("myvoiceclone.api.routes_inference.service_run_real_inference", fake_service)

    res = client.post(
        "/api/inference/real",
        json={
            "text": "hello",
            "reference_artifact_id": "art_ref",
            "model_id": "tts_models/multilingual/multi-dataset/xtts_v2",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "art_real_api"
    assert body["metadata_json"]["adapter_mode"] == "real"
