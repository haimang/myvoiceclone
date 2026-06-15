import io
import os
import sqlite3
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from myvoiceclone.api.app import create_app
from myvoiceclone.config import resolve_artifact_root
from myvoiceclone.ids import is_mvc_id, new_id
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.storage.migrations import run_migrations


def wav_bytes(*, silent: bool = False, seconds: float = 0.25, rate: int = 16000) -> bytes:
    sample_count = int(seconds * rate)
    samples = [0] * sample_count if silent else [int(8000 * ((i % 32) / 31.0 - 0.5)) for i in range(sample_count)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(struct.pack(f"<{sample_count}h", *samples))
    return buf.getvalue()


@pytest.fixture
def live_api(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    artifact_root = tmp_path / "artifacts"
    run_migrations(str(db_path), os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "db", "migrations"))
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    app = create_app()
    return TestClient(app), db_path, artifact_root


def create_run(client: TestClient) -> str:
    res = client.post("/api/runs", json={"name": "api-flow", "adapter_mode": "real"})
    assert res.status_code == 200
    run_id = res.json()["id"]
    assert is_mvc_id(run_id)
    return run_id


@pytest.mark.api
def test_reference_audio_upload_and_silent_rejection(live_api):
    client, _, _ = live_api
    run_id = create_run(client)

    ok = client.post(
        f"/api/runs/{run_id}/reference-audio",
        files={"file": ("voice.wav", wav_bytes(), "audio/wav")},
    )
    assert ok.status_code == 200
    assert is_mvc_id(ok.json()["id"])
    assert ok.json()["artifact_type"] == "reference_audio"
    assert ok.json()["metadata_json"]["metric_source"] == "reference_upload"

    bad = client.post(
        f"/api/runs/{run_id}/reference-audio",
        files={"file": ("silent.wav", wav_bytes(silent=True), "audio/wav")},
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "reference_audio_silent"


@pytest.mark.api
def test_promote_reference_audio_and_download(live_api):
    client, _, _ = live_api
    run_id = create_run(client)
    uploaded = client.post(
        f"/api/runs/{run_id}/audio",
        files={"file": ("upload.wav", wav_bytes(), "audio/wav")},
    ).json()

    promoted = client.post(
        f"/api/runs/{run_id}/reference-audio/from-artifact",
        json={"artifact_id": uploaded["id"], "name": "reference.wav"},
    )
    assert promoted.status_code == 200
    body = promoted.json()
    assert is_mvc_id(uploaded["id"])
    assert is_mvc_id(body["id"])
    assert body["artifact_type"] == "reference_audio"
    assert body["parent_artifact_id"] == uploaded["id"]

    downloaded = client.get(f"/api/artifacts/{body['id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"RIFF")


@pytest.mark.api
def test_api_request_logs_success_and_error(live_api):
    client, db_path, _ = live_api
    run_id = create_run(client)
    trace_id = new_id()
    res = client.get(f"/api/runs/{run_id}", headers={"x-trace-id": trace_id})
    assert res.status_code == 200
    err = client.get("/api/runs/mvc_e92042338a2bf627a85643ee6d42ae71", headers={"x-trace-id": "trace_missing"})
    assert err.status_code == 404
    assert err.json()["error"]["code"] == "run_not_found"
    assert is_mvc_id(err.headers["x-trace-id"])

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ok_row = conn.execute("SELECT * FROM api_request_logs WHERE trace_id = ?", (trace_id,)).fetchone()
        err_row = conn.execute("SELECT * FROM api_request_logs WHERE trace_id = ?", (err.headers["x-trace-id"],)).fetchone()
    finally:
        conn.close()
    assert ok_row["status_code"] == 200
    assert ok_row["run_id"] == run_id
    assert err_row["status_code"] == 404
    assert err_row["error_code"] == "run_not_found"


@pytest.mark.api
def test_async_infer_flow_writes_rendered_artifact(live_api, monkeypatch):
    client, db_path, artifact_root = live_api
    run_id = create_run(client)
    reference = client.post(
        f"/api/runs/{run_id}/reference-audio",
        files={"file": ("voice.wav", wav_bytes(), "audio/wav")},
    ).json()

    def fake_run_real_inference(conn, artifact_store, request, *, adapter=None, job_id=None):
        return artifact_store.create_artifact(
            name="out.wav",
            content=wav_bytes(),
            artifact_type="rendered_audio",
            parent_artifact_id=request.reference_artifact_id,
            job_id=job_id,
            metadata_json={
                "run_id": run_id,
                "adapter_mode": "real",
                "metric_source": "inference_output",
                "text": request.text,
                "tool": "coqui-tts",
                "device": "cuda",
            },
        )

    monkeypatch.setattr("myvoiceclone.pipelines.infer_real.run_real_inference", fake_run_real_inference)

    job = client.post(
        f"/api/runs/{run_id}/infer",
        json={"text": "hello clone", "reference_artifact_id": reference["id"], "start_immediately": True},
    )
    assert job.status_code == 200
    assert is_mvc_id(job.json()["id"])

    status = client.get(f"/api/runs/{run_id}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    rendered = [item for item in body["artifacts"] if item["artifact_type"] == "rendered_audio"]
    assert rendered
    assert rendered[-1]["links"]["download"].endswith("/download")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    store = ArtifactStore(conn, str(artifact_root))
    try:
        art = store.get_artifact(rendered[-1]["id"])
        assert os.path.exists(store.get_absolute_path(art))
    finally:
        conn.close()
