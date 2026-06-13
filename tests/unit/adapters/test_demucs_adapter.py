import os
import pytest
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter

@pytest.mark.unit
def test_demucs_mock_separation(tmp_path):
    adapter = DemucsAdapter()
    res = adapter.separate("/tmp/nonexistent.wav", str(tmp_path))
    
    assert res.cleaned_path.endswith(".wav")
    assert os.path.exists(res.cleaned_path)


@pytest.mark.unit
def test_demucs_preflight_and_metadata(monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "false")
    adapter = DemucsAdapter(model_id="htdemucs")

    preflight = adapter.preflight()

    assert preflight["tool"] == "demucs"
    assert preflight["claim"] == "source_separation_smoke_not_speech_enhancement"
    if not preflight["available"]:
        assert "demucs CLI not found" in preflight["skip_reason"]
