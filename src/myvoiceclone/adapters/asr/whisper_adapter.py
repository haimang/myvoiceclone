import os
from typing import List
from myvoiceclone.domain.entities import TranscriptSegment

class WhisperAdapter:
    def __init__(self, model_id: str = "medium"):
        self.model_id = model_id

    def transcribe(self, filepath: str) -> List[TranscriptSegment]:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return [
                TranscriptSegment(start_sec=0.0, end_sec=4.5, text="你好，这是一段测试音频。", confidence=0.98),
                TranscriptSegment(start_sec=5.0, end_sec=9.5, text="今天天气真不错。", confidence=0.95)
            ]
            
        # Real implementation
        import whisper
        model = whisper.load_model(self.model_id)
        result = model.transcribe(filepath)
        
        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                start_sec=seg.get("start", 0.0),
                end_sec=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
                confidence=seg.get("avg_logprob", 0.0) # simplified mapping
            ))
        return segments
