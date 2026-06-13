"""
tests/fakes/__init__.py — Test double (fake) implementations.

V10 fix: Created tests/fakes/ directory with 6 stub fake classes as
specified in final-execution-plan.md §8.3. These provide injectable
test doubles for integration and unit tests without relying on the
MOCK_ADAPTERS environment variable pattern inside production adapters.

Usage in tests:
    from tests.fakes import FakeDiarizer, FakeSeparator, FakeASR, FakeTrainer, FakeEmbedder, FakeInference

Note: Full implementations will be fleshed out as adapter interfaces stabilize (V10.r deferred item).
"""

from __future__ import annotations
from typing import List, Any
from myvoiceclone.domain.entities import (
    AudioProbe, DiarizationTurn, SeparationResult, TranscriptResult,
    TrainResult, EmbeddingResult, SynthResult, AudioConvertResult,
)
import logging

logger = logging.getLogger("myvoiceclone.tests.fakes")


class FakeDiarizer:
    """Fake diarizer: always returns 2 synthetic speaker turns."""

    def diarize(self, filepath: str) -> List[Any]:
        from myvoiceclone.domain.entities import DiarizationTurn
        return [
            DiarizationTurn(speaker_id="speaker_0", start_sec=0.0, end_sec=4.5),
            DiarizationTurn(speaker_id="speaker_1", start_sec=5.0, end_sec=9.0),
        ]


class FakeSeparator:
    """Fake source separator: returns the input path as-is without processing."""

    def separate(self, filepath: str, output_dir: str) -> str:
        """Return a fake vocals-only path (same as input for test purposes)."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "vocals.wav")
        # Copy or link input to output (fake)
        import shutil
        if os.path.exists(filepath):
            shutil.copy2(filepath, output_path)
        else:
            # Write a minimal placeholder for test setups without real audio
            with open(output_path, "wb") as f:
                f.write(b"FAKE_AUDIO_CONTENT")
        return output_path


class FakeASR:
    """Fake ASR transcriber: returns a canned transcript for any input."""

    def transcribe(self, filepath: str, language: str = "en") -> Any:
        from myvoiceclone.domain.entities import TranscriptResult
        return TranscriptResult(
            text="Hello world, this is a test transcript.",
            language=language,
            segments=[
                {"id": 0, "start": 0.0, "end": 2.0, "text": "Hello world,"},
                {"id": 1, "start": 2.0, "end": 4.0, "text": "this is a test transcript."},
            ],
        )


class FakeTrainer:
    """Fake model trainer: immediately returns a completed training result."""

    def train(self, request: Any) -> Any:
        from myvoiceclone.domain.entities import TrainResult
        return TrainResult(
            status="completed",
            model_run_id=getattr(request, "model_name", "fake_run"),
            checkpoint_bytes=b"fake_checkpoint_data",
            metrics={"loss": 0.042, "mos": 3.8},
        )

    def prepare(self, dataset_id: str) -> None:
        pass

    def export(self, checkpoint_path: str, output_path: str) -> None:
        with open(output_path, "wb") as f:
            f.write(b"fake_exported_model")


class FakeEmbedder:
    """Fake embedder: returns a deterministic fixed-dimension vector."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, filepath: str) -> List[float]:
        """Return a deterministic vector based on filepath hash."""
        import hashlib
        h = hashlib.md5(filepath.encode()).digest()
        # Repeat hash bytes to fill dim
        raw = (h * ((self.dim // len(h)) + 1))[:self.dim]
        return [b / 255.0 for b in raw]


class FakeInference:
    """Fake inference engine: synthesizes a silent audio stub for any input."""

    def synth(self, request: Any) -> Any:
        from myvoiceclone.domain.entities import SynthResult
        return SynthResult(
            status="completed",
            audio_bytes=b"\x00" * 1000,  # silent audio stub
            duration_sec=0.0625,  # 1000 bytes at 16kHz 16-bit = 0.0625s
        )

    def convert(self, request: Any) -> Any:
        from myvoiceclone.domain.entities import AudioConvertResult
        return AudioConvertResult(
            status="completed",
            audio_bytes=b"\x00" * 1000,
            duration_sec=0.0625,
        )
