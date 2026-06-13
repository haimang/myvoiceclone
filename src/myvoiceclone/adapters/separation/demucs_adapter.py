import os
import shutil
import subprocess
import struct
import wave
from myvoiceclone.domain.entities import SeparationResult

class DemucsAdapter:
    def __init__(self, model_id: str = "htdemucs"):
        self.model_id = model_id

    def metadata(self) -> dict:
        return {
            "tool": "demucs",
            "model": self.model_id,
            "version": None,
            "device": "cuda-or-cpu",
            "cache": None,
            "license": "MIT",
            "claim": "source_separation_smoke_not_speech_enhancement",
        }

    def preflight(self) -> dict:
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return {"available": True, "mode": "mock", "skip_reason": None, **self.metadata()}
        if not shutil.which("demucs"):
            return {"available": False, "mode": "real", "skip_reason": "demucs CLI not found", **self.metadata()}
        return {"available": True, "mode": "real", "skip_reason": None, **self.metadata()}

    def _write_silence_wav(self, path: str, duration_sec: float = 1.0, sample_rate: int = 16000) -> None:
        frame_count = int(duration_sec * sample_rate)
        with wave.open(path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(struct.pack(f"<{frame_count}h", *([0] * frame_count)))

    def separate(self, filepath: str, out_dir: str) -> SeparationResult:
        os.makedirs(out_dir, exist_ok=True)
        filename = os.path.basename(filepath)
        cleaned_path = os.path.join(out_dir, f"cleaned_{filename}")
        
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            if os.path.exists(filepath):
                shutil.copy(filepath, cleaned_path)
            else:
                self._write_silence_wav(cleaned_path)
            return SeparationResult(cleaned_path=cleaned_path)
            
        # Real subprocess demucs call
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Input file not found: {filepath}")
        preflight = self.preflight()
        if not preflight["available"]:
            raise RuntimeError(preflight["skip_reason"])
        tmp_out_dir = os.path.join(out_dir, "_demucs_tmp")
        os.makedirs(tmp_out_dir, exist_ok=True)
        try:
            cmd = [
                "demucs",
                "--two-stems", "vocals",
                "-n", self.model_id,
                "-o", tmp_out_dir,
                filepath
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            # Locate the generated vocals file. Demucs outputs to: out_dir/{model_id}/{filename_no_ext}/vocals.wav
            name_no_ext = os.path.splitext(filename)[0]
            vocals_src = os.path.join(tmp_out_dir, self.model_id, name_no_ext, "vocals.wav")
            if os.path.exists(vocals_src):
                shutil.move(vocals_src, cleaned_path)
                return SeparationResult(cleaned_path=cleaned_path)
            else:
                raise FileNotFoundError(f"Demucs ran but output vocals.wav not found at {vocals_src}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Demucs command failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to run Demucs: {e}")
        finally:
            shutil.rmtree(tmp_out_dir, ignore_errors=True)
