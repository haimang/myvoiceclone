import pytest
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter

@pytest.mark.unit
def test_whisper_mock_transcription():
    adapter = WhisperAdapter()
    segs = adapter.transcribe("/tmp/nonexistent.wav")
    
    assert len(segs) == 2
    assert segs[0].text == "你好，这是一段测试音频。"
    assert segs[0].confidence == 0.98
