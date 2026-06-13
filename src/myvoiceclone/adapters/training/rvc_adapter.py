import os
from typing import Optional
from myvoiceclone.domain.entities import TrainRequest, TrainResult, ConvertRequest, ConvertResult

class RvcAdapter:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir

    def train(self, request: TrainRequest) -> TrainResult:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            # Return a successful train result with fake checkpoint bytes
            return TrainResult(
                model_run_id=request.model_name,
                status="completed",
                checkpoint_bytes=b"fake_rvc_checkpoint_data",
                metrics={"loss": 0.045, "val_loss": 0.052, "epochs": 10}
            )

        # Real RVC training logic placeholder or subprocess call
        # Since first-build is focused on local workbench lifecycle integration
        # we raise NotImplementedError or return simple status if external tool is missing
        raise NotImplementedError("Real RVC training is not implemented in first-build. Use MOCK_ADAPTERS=true.")

    def convert(self, request: ConvertRequest) -> ConvertResult:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return ConvertResult(
                status="completed",
                audio_bytes=b"fake_rvc_converted_audio_data_wav_format",
                duration_sec=3.5
            )

        raise NotImplementedError("Real RVC conversion is not implemented in first-build. Use MOCK_ADAPTERS=true.")
