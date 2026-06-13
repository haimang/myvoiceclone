import pytest
from myvoiceclone.config import load_local_config, load_models_config, load_pipeline_config

@pytest.mark.unit
def test_local_config():
    cfg = load_local_config()
    assert "db_path" in cfg
    assert "artifact_root" in cfg
    assert "models_dir" in cfg
    assert cfg["db_path"] == "db/myvoiceclone.sqlite"

@pytest.mark.unit
def test_models_config():
    cfg = load_models_config()
    assert "pretrained_dir" in cfg
    assert "checkpoints_dir" in cfg
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
