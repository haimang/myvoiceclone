import os
import shutil
from typing import Optional
from myvoiceclone.domain.entities import SynthRequest, SynthResult

class XttsAdapter:
    def __init__(self, model_dir: Optional[str] = None, model_id: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_dir = model_dir
        self.model_id = model_id

    def metadata(self) -> dict:
        return {
            "tool": "coqui-tts",
            "model": self.model_id,
            "version": None,
            "device": "cuda-or-cpu",
            "cache": self.model_dir,
            "license": "Coqui Public Model License",
            "source": "https://huggingface.co/coqui/XTTS-v2",
        }

    def preflight(self) -> dict:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return {"available": True, "mode": "mock", "skip_reason": None, **self.metadata()}
        try:
            import TTS  # noqa: F401
        except Exception as exc:
            return {"available": False, "mode": "real", "skip_reason": f"Coqui TTS import failed: {exc}", **self.metadata()}
        return {"available": True, "mode": "real", "skip_reason": None, **self.metadata()}

    def synth(self, request: SynthRequest) -> SynthResult:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return SynthResult(
                status="completed",
                audio_bytes=b"fake_xtts_synthetic_audio_data_wav_format",
                duration_sec=4.2
            )

        raise RuntimeError("Real XTTS synthesis requires synth_to_file with explicit reference_wav; no mock fallback is allowed.")

    def synth_to_file(self, text: str, reference_wav: str, output_path: str, *, language: str = "en") -> dict:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"fake_xtts_synthetic_audio_data_wav_format")
            return {"duration_sec": 4.2, **self.metadata(), "adapter_mode": "mock"}

        if not os.path.exists(reference_wav):
            raise FileNotFoundError(f"Reference wav not found: {reference_wav}")
        preflight = self.preflight()
        if not preflight["available"]:
            raise RuntimeError(preflight["skip_reason"])

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        from TTS.api import TTS
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
        tts = TTS(self.model_id).to(device)
        tts.tts_to_file(text=text, speaker_wav=reference_wav, language=language, file_path=output_path)
        return {"duration_sec": None, **self.metadata(), "device": device, "adapter_mode": "real"}


def xtts_model_manifest(model_dir: Optional[str] = None) -> dict:
    adapter = XttsAdapter(model_dir=model_dir)
    manifest = adapter.metadata()
    manifest.update(
        {
            "model_id": adapter.model_id,
            "cache_path": model_dir,
            "provenance": "Coqui XTTS-v2 model card",
            "first_test_use": "local research validation only",
        }
    )
    return manifest
