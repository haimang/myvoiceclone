import os
import pytest
from myvoiceclone.config import (
    load_local_config,
    load_models_config,
    load_pipeline_config,
    resolve_artifact_root,
    resolve_db_path,
    resolve_mock_adapters,
    resolve_models_dir,
)

@pytest.mark.unit
def test_local_config():
    cfg = load_local_config()
    assert "db_path" in cfg
    assert "artifact_root" in cfg
    assert "models_dir" in cfg
    assert cfg["db_path"] == ".data/db/myvoiceclone.sqlite"

@pytest.mark.unit
def test_models_config():
    cfg = load_models_config()
    assert "pretrained_dir" in cfg
    assert "checkpoints_dir" in cfg
    assert cfg["pretrained_dir"] == ".data/models/pretrained"
    assert cfg["checkpoints_dir"] == ".data/models/checkpoints"
    assert cfg["registry_dir"] == ".data/models/registry"
    assert "pyannote" in cfg
    assert "whisper" in cfg
    assert cfg["pyannote"]["model_id"] == "pyannote/speaker-diarization-3.1"

@pytest.mark.unit
def test_pipeline_config():
    cfg = load_pipeline_config()
    assert "ingest" in cfg
    assert "diarize" in cfg
    assert "clean" in cfg
    assert "score" in cfg
    assert cfg["clean"]["denoise_method"] == "demucs"


@pytest.mark.unit
def test_runtime_env_resolvers(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    artifact_root = tmp_path / "artifacts"
    models_dir = tmp_path / "models"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("MODELS_DIR", str(models_dir))
    monkeypatch.setenv("MOCK_ADAPTERS", "false")

    assert resolve_db_path() == str(db_path)
    assert resolve_artifact_root() == str(artifact_root)
    assert resolve_models_dir() == str(models_dir)
    assert resolve_mock_adapters() is False


@pytest.mark.unit
def test_env_example_uses_runtime_keys():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env_example = os.path.join(project_root, ".env.example")
    content = open(env_example, encoding="utf-8").read()

    for key in ("DB_PATH=", "ARTIFACT_ROOT=", "MODELS_DIR=", "MOCK_ADAPTERS="):
        assert key in content
    assert "DATABASE_URL=" not in content
