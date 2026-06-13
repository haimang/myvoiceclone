import os
import shutil
from typing import List
from myvoiceclone.domain.entities import TranscriptSegment

class WhisperAdapter:
    def __init__(self, model_id: str = "medium"):
        self.model_id = model_id

    def metadata(self) -> dict:
        return {
            "tool": "openai-whisper",
            "model": self.model_id,
            "version": None,
            "device": "cuda-or-cpu",
            "cache": os.getenv("XDG_CACHE_HOME") or os.path.expanduser("~/.cache/whisper"),
            "license": "MIT",
        }

    def preflight(self) -> dict:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return {"available": True, "mode": "mock", "skip_reason": None, **self.metadata()}
        if not shutil.which("ffmpeg"):
            return {"available": False, "mode": "real", "skip_reason": "ffmpeg binary required by Whisper is not available", **self.metadata()}
        try:
            import whisper  # noqa: F401
        except Exception as exc:
            return {"available": False, "mode": "real", "skip_reason": f"whisper import failed: {exc}", **self.metadata()}
        return {"available": True, "mode": "real", "skip_reason": None, **self.metadata()}

    def transcribe(self, filepath: str) -> List[TranscriptSegment]:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return [
                TranscriptSegment(start_sec=0.0, end_sec=4.5, text="你好，这是一段测试音频。", confidence=0.98),
                TranscriptSegment(start_sec=5.0, end_sec=9.5, text="今天天气真不错。", confidence=0.95)
            ]
            
        # Real implementation
        preflight = self.preflight()
        if not preflight["available"]:
            raise RuntimeError(preflight["skip_reason"])
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
