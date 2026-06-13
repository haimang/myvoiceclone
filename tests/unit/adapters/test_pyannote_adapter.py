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
