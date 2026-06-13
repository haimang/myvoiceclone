import wave
from typing import Any, Dict, Optional

from myvoiceclone.storage.artifact_store import ArtifactStore


def evaluate_wav_smoke(
    artifact_store: ArtifactStore,
    *,
    artifact_id: Optional[str] = None,
    filepath: Optional[str] = None,
    transcript: Optional[str] = None,
) -> Dict[str, Any]:
    if artifact_id:
        artifact = artifact_store.get_artifact(artifact_id)
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")
        filepath = artifact_store.get_absolute_path(artifact)
    if not filepath:
        raise ValueError("Either artifact_id or filepath is required")

    with wave.open(filepath, "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        frames = wav.readframes(frame_count)

    if frame_count <= 0:
        raise ValueError("WAV file has no frames")

    max_amplitude = float((2 ** (8 * sample_width - 1)) - 1) if sample_width else 1.0
    values = []
    if sample_width == 2:
        import struct

        values = list(struct.unpack(f"<{len(frames) // 2}h", frames))
    elif sample_width == 1:
        values = [b - 128 for b in frames]

    peak = max((abs(v) for v in values), default=0)
    clipping_ratio = sum(1 for v in values if abs(v) >= max_amplitude) / len(values) if values else 0.0
    silence_ratio = sum(1 for v in values if abs(v) <= max_amplitude * 0.01) / len(values) if values else 1.0
    duration_sec = frame_count / float(sample_rate)
    transcript_ok = transcript is None or bool(transcript.strip())

    smoke_pass = duration_sec > 0 and clipping_ratio < 0.01 and transcript_ok
    return {
        "metric_source": "smoke_metric",
        "duration_sec": duration_sec,
        "sample_rate": sample_rate,
        "channels": channels,
        "peak_amplitude": peak / max_amplitude if max_amplitude else 0.0,
        "clipping_ratio": clipping_ratio,
        "silence_ratio": silence_ratio,
        "transcript_sanity": transcript_ok,
        "smoke_pass": smoke_pass,
        "quality_gate_eligible": True,
    }
