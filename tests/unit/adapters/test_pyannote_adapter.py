import pytest
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter

@pytest.mark.unit
def test_pyannote_mock_diarization():
    # PyAnnote mock mode defaults to True in tests via MOCK_ADAPTERS=true
    adapter = PyannoteAdapter()
    turns = adapter.diarize("/tmp/nonexistent.wav")
    
    assert len(turns) == 2
    assert turns[0].speaker_id == "speaker_0"
    assert turns[0].start_sec == 0.0
    assert turns[0].end_sec == 4.5
    assert turns[1].speaker_id == "speaker_1"


@pytest.mark.unit
def test_pyannote_real_preflight_requires_token(monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "false")
    monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)

    preflight = PyannoteAdapter().preflight()

    assert preflight["available"] is False
    assert preflight["mode"] == "real"
    assert "HUGGINGFACE_TOKEN" in preflight["skip_reason"]
    assert preflight["model"] == "pyannote/speaker-diarization-3.1"
