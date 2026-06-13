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
    metadata = adapter.metadata()
    assert metadata["tool"] == "ffmpeg"
    assert "license" in metadata


@pytest.mark.unit
def test_ffmpeg_preflight_reports_missing_binary(monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "false")
    adapter = FFmpegAdapter(ffmpeg_path="missing-ffmpeg-bin", ffprobe_path="missing-ffprobe-bin")

    preflight = adapter.preflight()

    assert preflight["available"] is False
    assert "missing-ffmpeg-bin" in preflight["missing"]
    assert "Missing FFmpeg binaries" in preflight["skip_reason"]

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
