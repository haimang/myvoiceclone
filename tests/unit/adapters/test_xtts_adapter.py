import os
import pytest
from myvoiceclone.domain.entities import SynthRequest
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter

@pytest.mark.unit
def test_xtts_adapter_mock_synth(monkeypatch):
    # V13 fix: monkeypatch.setenv auto-restores MOCK_ADAPTERS after the test
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    adapter = XttsAdapter()
    
    req = SynthRequest(
        text="Hello world",
        speaker_id="spk_test",
        config={}
    )
    
    result = adapter.synth(req)
    assert result.status == "completed"
    assert len(result.audio_bytes) > 0
    assert result.duration_sec == 4.2


@pytest.mark.unit
def test_xtts_real_mode_no_mock_fallback(monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "false")
    adapter = XttsAdapter()

    req = SynthRequest(text="Hello", speaker_id="spk_test", config={})

    with pytest.raises(RuntimeError, match="no mock fallback"):
        adapter.synth(req)


@pytest.mark.unit
def test_xtts_model_manifest_records_license():
    from myvoiceclone.adapters.training.xtts_adapter import xtts_model_manifest

    manifest = xtts_model_manifest(model_dir="/models")

    assert manifest["model_id"] == "tts_models/multilingual/multi-dataset/xtts_v2"
    assert manifest["license"] == "Coqui Public Model License"
    assert manifest["source"] == "https://huggingface.co/coqui/XTTS-v2"
