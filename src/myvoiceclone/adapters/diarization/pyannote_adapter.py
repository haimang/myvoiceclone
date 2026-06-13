import os
from typing import List, Optional
from myvoiceclone.domain.entities import DiarizationTurn

class PyannoteAdapter:
    def __init__(self, hf_token: Optional[str] = None, model_id: str = "pyannote/speaker-diarization-3.1"):
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")
        self.model_id = model_id

    def diarize(self, filepath: str) -> List[DiarizationTurn]:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return [
                DiarizationTurn(speaker_id="speaker_0", start_sec=0.0, end_sec=4.5),
                DiarizationTurn(speaker_id="speaker_1", start_sec=5.0, end_sec=9.5)
            ]
            
        # Real implementation
        if not self.hf_token:
            raise ValueError("Hugging Face token is required for PyAnnote diarization")
            
        from pyannote.audio import Pipeline
        pipeline = Pipeline.from_pretrained(self.model_id, use_auth_token=self.hf_token)
        # Move pipeline to GPU if available
        import torch
        if torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
            
        diarization = pipeline(filepath)
        turns = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            turns.append(DiarizationTurn(
                speaker_id=speaker,
                start_sec=turn.start,
                end_sec=turn.end
            ))
        return turns
