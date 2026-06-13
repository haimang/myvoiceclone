import pytest

from myvoiceclone.api.app import create_app
from myvoiceclone.api.dependencies import get_db
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(db_conn):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_conn
    return TestClient(app)


@pytest.mark.api
def test_run_job_uses_env_artifact_root(api_client, db_conn, monkeypatch, tmp_path, synthetic_wav):
    artifact_root = tmp_path / "env-artifacts"
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifact_root))
    db_conn.execute(
        """
        INSERT INTO jobs (id, name, status, payload_json)
        VALUES ('job_env_root', 'ingest', 'pending', ?);
        """,
        (f'{{"filepath": "{synthetic_wav}"}}',),
    )
    db_conn.commit()

    res = api_client.post("/api/jobs/job_env_root/run")

    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    assert artifact_root.exists()
    assert any(artifact_root.rglob("*"))
