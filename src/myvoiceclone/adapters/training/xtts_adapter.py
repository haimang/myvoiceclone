import os
from typing import Optional
from myvoiceclone.domain.entities import SynthRequest, SynthResult

class XttsAdapter:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir

    def synth(self, request: SynthRequest) -> SynthResult:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return SynthResult(
                status="completed",
                audio_bytes=b"fake_xtts_synthetic_audio_data_wav_format",
                duration_sec=4.2
            )

        # Real XTTS synthesis placeholder
        raise NotImplementedError("Real XTTS synthesis is not implemented in first-build. Use MOCK_ADAPTERS=true.")
