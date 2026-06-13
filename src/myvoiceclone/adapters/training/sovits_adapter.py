import os
from typing import Optional
from myvoiceclone.domain.entities import TrainRequest, TrainResult

class SovitsAdapter:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir

    def prepare(self, dataset_id: str) -> None:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            # Mock preparation
            return
            
        # Real preparation script call placeholder
        # e.g., subprocess.run(["python", "so-vits-svc/preprocess.py", ...])
        pass

    def train(self, request: TrainRequest) -> TrainResult:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return TrainResult(
                model_run_id=request.model_name,
                status="completed",
                checkpoint_bytes=b"fake_sovits_checkpoint_data",
                metrics={"loss": 0.035, "val_loss": 0.042, "epochs": 50}
            )

        raise NotImplementedError("Real So-VITS-SVC training is not implemented in first-build. Use MOCK_ADAPTERS=true.")

    def resume(self, checkpoint_path: str, request: TrainRequest) -> TrainResult:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return TrainResult(
                model_run_id=request.model_name,
                status="completed",
                checkpoint_bytes=b"fake_sovits_resumed_checkpoint_data",
                metrics={"loss": 0.025, "val_loss": 0.031, "epochs": 100}
            )

        raise NotImplementedError("Real So-VITS-SVC training resume is not implemented. Use MOCK_ADAPTERS=true.")

    def export(self, checkpoint_path: str, output_path: str) -> None:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            # Mock export writes a small dummy file to output_path
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(b"fake_exported_sovits_model_data")
            return

        raise NotImplementedError("Real So-VITS-SVC export is not implemented. Use MOCK_ADAPTERS=true.")
