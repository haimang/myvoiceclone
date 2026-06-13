import json
import os

import pytest
from fastapi.testclient import TestClient

from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db


@pytest.fixture
def client(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    return TestClient(app)


def create_run(client):
    res = client.post("/api/runs", json={"name": "contract-run", "adapter_mode": "real", "config": {"seed": 1}})
    assert res.status_code == 200
    return res.json()


@pytest.mark.api
def test_create_run_contract_snapshot(client):
    body = create_run(client)
    contract_path = os.path.join(os.path.dirname(__file__), "contracts", "first_test_run_create.json")
    contract = json.load(open(contract_path, encoding="utf-8"))
    normalized = json.loads(json.dumps(body).replace(body["id"], "<run_id>"))

    assert normalized == contract


@pytest.mark.api
def test_upload_audio_immediately_writes_artifact(client, monkeypatch, tmp_path):
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "api-artifacts"))
    run = create_run(client)

    res = client.post(
        f"/api/runs/{run['id']}/audio",
        files={"file": ("sample.wav", b"RIFFtinywav", "audio/wav")},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["artifact_type"] == "uploaded_audio"
    assert body["bytes"] == len(b"RIFFtinywav")
    assert body["metadata_json"]["run_id"] == run["id"]
    assert (tmp_path / "api-artifacts").exists()


@pytest.mark.api
def test_start_jobs_reference_artifact_ids(client, monkeypatch, tmp_path):
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "api-artifacts"))
    run = create_run(client)
    upload = client.post(
        f"/api/runs/{run['id']}/audio",
        files={"file": ("sample.wav", b"RIFFtinywav", "audio/wav")},
    ).json()

    preprocess = client.post(
        f"/api/runs/{run['id']}/preprocess",
        json={"audio_artifact_id": upload["id"], "min_duration": 1.0},
    )
    infer = client.post(
        f"/api/runs/{run['id']}/infer",
        json={"text": "hello", "reference_artifact_id": upload["id"]},
    )
    eval_res = client.post(
        f"/api/runs/{run['id']}/eval",
        json={"inference_artifact_id": upload["id"], "metric_source": "smoke_metric"},
    )

    assert preprocess.status_code == 200
    assert preprocess.json()["name"] == "preprocess_all"
    assert preprocess.json()["payload_json"]["audio_artifact_id"] == upload["id"]
    assert infer.status_code == 200
    assert infer.json()["name"] == "infer_real"
    assert infer.json()["payload_json"]["reference_artifact_id"] == upload["id"]
    assert eval_res.status_code == 200
    assert eval_res.json()["name"] == "eval_first_test"


@pytest.mark.api
def test_run_status_aggregates_events_artifacts_and_failures(client, db_conn, monkeypatch, tmp_path):
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "api-artifacts"))
    run = create_run(client)
    upload = client.post(
        f"/api/runs/{run['id']}/audio",
        files={"file": ("sample.wav", b"RIFFtinywav", "audio/wav")},
    ).json()
    job = client.post(f"/api/runs/{run['id']}/infer", json={"text": "hello", "reference_artifact_id": upload["id"]}).json()
    db_conn.execute(
        """
        INSERT INTO job_events (job_id, event_type, status_to, message, metadata_json)
        VALUES (?, 'step_failed', 'failed', 'boom', '{"step":"infer","error":"missing model"}');
        """,
        (job["id"],),
    )
    db_conn.commit()

    res = client.get(f"/api/runs/{run['id']}/status")

    assert res.status_code == 200
    body = res.json()
    assert body["run_id"] == run["id"]
    assert any(item["id"] == job["id"] for item in body["jobs"])
    assert any(event["event_type"] == "step_failed" for event in body["events"])
    assert body["failure_summary"][job["id"]]["error"] == "missing model"
    assert any(artifact["id"] == upload["id"] for artifact in body["artifacts"])
