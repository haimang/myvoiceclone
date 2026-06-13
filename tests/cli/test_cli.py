import os
import pytest
from typer.testing import CliRunner
from myvoiceclone.cli import app
from myvoiceclone.config import get_project_root

runner = CliRunner()

@pytest.mark.cli
def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "MyVoiceClone CLI" in result.output

@pytest.mark.cli
def test_cli_init_db(tmp_path):
    db_file = tmp_path / "cli_test.db"
    result = runner.invoke(app, ["init-db", "--db", str(db_file)])
    assert result.exit_code == 0
    assert "Initializing database" in result.output
    assert os.path.exists(str(db_file))

@pytest.mark.cli
def test_cli_vec_health_error(monkeypatch):
    import sqlite3
    def mock_get_connection(*args, **kwargs):
        raise sqlite3.OperationalError("Mocked load extension failure")
    monkeypatch.setattr("myvoiceclone.cli.get_connection", mock_get_connection)
    
    result = runner.invoke(app, ["vec-health"])
    assert result.exit_code == 1
    assert "Error" in result.output

@pytest.mark.cli
def test_cli_ingest_dry_run():
    result = runner.invoke(app, ["ingest", "fake_path.wav", "--dry-run"])
    assert result.exit_code == 0
    assert "[Dry-run] Would ingest" in result.output


@pytest.mark.cli
def test_cli_preprocess_all_payload(monkeypatch):
    captured = {}

    def fake_run_step_job(name, payload):
        captured["name"] = name
        captured["payload"] = payload

    monkeypatch.setattr("myvoiceclone.cli._run_step_job", fake_run_step_job)

    result = runner.invoke(
        app,
        [
            "run",
            "preprocess-all",
            "audio.wav",
            "--min-duration",
            "1.5",
            "--max-duration",
            "8.0",
            "--min-quality-score",
            "0.7",
        ],
    )

    assert result.exit_code == 0
    assert captured["name"] == "preprocess_all"
    assert captured["payload"] == {
        "filepath": "audio.wav",
        "min_duration": 1.5,
        "max_duration": 8.0,
        "min_quality_score": 0.7,
    }


@pytest.mark.cli
def test_cli_diarize_uses_single_step_job(monkeypatch):
    captured = {}

    def fake_run_step_job(name, payload):
        captured["name"] = name
        captured["payload"] = payload

    monkeypatch.setattr("myvoiceclone.cli._run_step_job", fake_run_step_job)

    result = runner.invoke(app, ["run", "diarize", "rec_123"])

    assert result.exit_code == 0
    assert captured == {"name": "diarize", "payload": {"recording_id": "rec_123"}}


@pytest.mark.cli
def test_cli_real_inference_smoke(monkeypatch):
    class FakeConn:
        def close(self):
            pass

    class FakeArtifact:
        id = "art_cli_real"
        uri = "rendered_audio/art_cli_real.wav"

    def fake_service(**kwargs):
        assert kwargs["reference_artifact_id"] == "art_ref"
        assert kwargs["adapter_mode"] == "real"
        return FakeArtifact()

    monkeypatch.setattr("myvoiceclone.cli.get_db_conn", lambda: FakeConn())
    monkeypatch.setattr("myvoiceclone.services.service_run_real_inference", fake_service)

    result = runner.invoke(
        app,
        [
            "infer",
            "real",
            "--text",
            "hello",
            "--reference-artifact-id",
            "art_ref",
            "--model-id",
            "tts_models/multilingual/multi-dataset/xtts_v2",
        ],
    )

    assert result.exit_code == 0
    assert "Inference artifact: art_cli_real" in result.output


@pytest.mark.cli
def test_cli_eval_uses_evaluation_pipeline(monkeypatch):
    class FakeConn:
        def close(self):
            pass

    class FakeRunRepo:
        def __init__(self, conn):
            pass

        def get_by_id(self, run_id):
            return object()

    captured = {}

    def fake_run_evaluation(conn, artifact_store, run_id):
        captured["run_id"] = run_id
        return {"status": "degraded", "reason": "fixture"}

    monkeypatch.setattr("myvoiceclone.cli.get_db_conn", lambda: FakeConn())
    monkeypatch.setattr("myvoiceclone.cli.ModelRunRepository", FakeRunRepo)
    monkeypatch.setattr("myvoiceclone.pipelines.evaluate.run_evaluation", fake_run_evaluation)

    result = runner.invoke(app, ["eval", "run_123"])

    assert result.exit_code == 0
    assert captured == {"run_id": "run_123"}
    assert "Evaluation completed" in result.output
