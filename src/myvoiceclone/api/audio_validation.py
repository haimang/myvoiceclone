import audioop
import io
import wave
from dataclasses import dataclass

from myvoiceclone.errors import ValidationError


@dataclass
class AudioValidationResult:
    channels: int
    sample_rate: int
    duration_sec: float
    max_amplitude: int
    rms: int


def validate_reference_audio_bytes(content: bytes) -> AudioValidationResult:
    if not content:
        raise ValidationError("Uploaded audio is empty", code="reference_audio_invalid")

    try:
        with wave.open(io.BytesIO(content), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            sample_width = wav.getsampwidth()
            frames = wav.readframes(frame_count)
    except Exception as exc:
        raise ValidationError(
            "Reference audio must be a readable WAV file",
            code="reference_audio_invalid",
            detail={"reason": str(exc)},
        ) from exc

    if channels <= 0 or sample_rate <= 0 or frame_count <= 0 or sample_width <= 0:
        raise ValidationError("Reference audio has invalid WAV parameters", code="reference_audio_invalid")

    max_amplitude = audioop.max(frames, sample_width) if frames else 0
    rms = audioop.rms(frames, sample_width) if frames else 0
    if max_amplitude <= 0 or rms <= 0:
        raise ValidationError(
            "Reference audio is silent",
            code="reference_audio_silent",
            detail={"max_amplitude": max_amplitude, "rms": rms},
        )

    return AudioValidationResult(
        channels=channels,
        sample_rate=sample_rate,
        duration_sec=frame_count / sample_rate,
        max_amplitude=max_amplitude,
        rms=rms,
    )
