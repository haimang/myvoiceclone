import pytest
from myvoiceclone.domain.entities import AudioProbe, DiarizationTurn, TranscriptSegment, SeparationResult

@pytest.mark.unit
def test_dtos_initialization():
    probe = AudioProbe(duration_sec=10.5, sample_rate=16000, channels=1, format="wav")
    assert probe.duration_sec == 10.5
    assert probe.sample_rate == 16000
    
    turn = DiarizationTurn(speaker_id="spk_0", start_sec=0.0, end_sec=3.5)
    assert turn.speaker_id == "spk_0"
    
    transcript = TranscriptSegment(start_sec=0.0, end_sec=3.5, text="Hello", confidence=0.99)
    assert transcript.text == "Hello"
    
    sep = SeparationResult(cleaned_path="/tmp/cleaned.wav")
    assert sep.cleaned_path == "/tmp/cleaned.wav"
