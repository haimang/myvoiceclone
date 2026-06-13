import pytest
from myvoiceclone.domain.entities import TrainRequest, ConvertRequest
from myvoiceclone.adapters.training.rvc_adapter import RvcAdapter

# V13 fix: Use monkeypatch.setenv instead of os.environ["MOCK_ADAPTERS"] = "true"
# to ensure automatic cleanup after each test (no env var residue between tests).

@pytest.mark.unit
def test_rvc_adapter_mock_train(monkeypatch):
    # V13 fix: monkeypatch.setenv auto-restores MOCK_ADAPTERS after the test
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    adapter = RvcAdapter()
    
    req = TrainRequest(
        dataset_id="ds_test",
        model_name="rvc_baseline",
        config={"lr": 0.001}
    )
    
    result = adapter.train(req)
    assert result.status == "completed"
    assert result.model_run_id == "rvc_baseline"
    assert len(result.checkpoint_bytes) > 0
    assert result.metrics["loss"] == 0.045

@pytest.mark.unit
def test_rvc_adapter_mock_convert(monkeypatch):
    # V13 fix: monkeypatch.setenv auto-restores MOCK_ADAPTERS after the test
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    adapter = RvcAdapter()
    
    req = ConvertRequest(
        model_run_id="run_1",
        source_audio_path="fake_source.wav",
        config={}
    )
    
    result = adapter.convert(req)
    assert result.status == "completed"
    assert len(result.audio_bytes) > 0
    assert result.duration_sec == 3.5
