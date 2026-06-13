import os
import shutil
import pytest
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter, FFmpegAdapterError

@pytest.mark.unit
def test_ffmpeg_probe_mock(synthetic_wav, monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    adapter = FFmpegAdapter()
    probe = adapter.probe(synthetic_wav)
    
    assert probe.duration_sec == 10.0
    assert probe.sample_rate == 16000
    assert probe.channels == 1
    assert probe.format == "wav"

@pytest.mark.unit
def test_ffmpeg_normalize_mock(synthetic_wav, tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "true")
    adapter = FFmpegAdapter()
    out_path = str(tmp_path / "normalized.wav")
    
    adapter.normalize(synthetic_wav, out_path)
    assert os.path.exists(out_path)

@pytest.mark.unit
def test_ffmpeg_live_probe(synthetic_wav, monkeypatch):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg or ffprobe binaries not found. Skipping live FFmpeg tests.")
        
    monkeypatch.setenv("MOCK_ADAPTERS", "false")
    adapter = FFmpegAdapter()
    probe = adapter.probe(synthetic_wav)
    
    assert probe.duration_sec == 1.0
    assert probe.sample_rate == 16000
    assert probe.channels == 1
    assert "wav" in probe.format
