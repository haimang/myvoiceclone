import pytest
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter

@pytest.mark.unit
def test_whisper_mock_transcription():
    adapter = WhisperAdapter()
    segs = adapter.transcribe("/tmp/nonexistent.wav")
    
    assert len(segs) == 2
    assert segs[0].text == "你好，这是一段测试音频。"
    assert segs[0].confidence == 0.98


@pytest.mark.unit
def test_whisper_preflight_metadata(monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    adapter = WhisperAdapter(model_id="tiny")

    preflight = adapter.preflight()

    assert preflight["available"] is True
    assert preflight["mode"] == "mock"
    assert preflight["tool"] == "openai-whisper"
    assert preflight["model"] == "tiny"
