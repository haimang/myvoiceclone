import subprocess
import json
import os
import shutil
from typing import Optional
from myvoiceclone.domain.entities import AudioProbe

class FFmpegAdapterError(Exception):
    pass

class FFmpegAdapter:
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def _check_binaries(self):
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return
        if not shutil.which(self.ffmpeg_path):
            raise FFmpegAdapterError(f"ffmpeg binary not found: {self.ffmpeg_path}")
        if not shutil.which(self.ffprobe_path):
            raise FFmpegAdapterError(f"ffprobe binary not found: {self.ffprobe_path}")

    def probe(self, filepath: str) -> AudioProbe:
        self._check_binaries()
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            return AudioProbe(
                duration_sec=10.0,
                sample_rate=16000,
                channels=1,
                format="wav"
            )
            
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            filepath
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            
            # Find audio stream
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break
                    
            if not audio_stream:
                raise FFmpegAdapterError("No audio stream found in file")
                
            duration = float(audio_stream.get("duration", data.get("format", {}).get("duration", 0.0)))
            sample_rate = int(audio_stream.get("sample_rate", 16000))
            channels = int(audio_stream.get("channels", 1))
            fmt = data.get("format", {}).get("format_name", "unknown")
            
            return AudioProbe(
                duration_sec=duration,
                sample_rate=sample_rate,
                channels=channels,
                format=fmt
            )
        except subprocess.CalledProcessError as e:
            raise FFmpegAdapterError(f"ffprobe failed: {e.stderr}")
        except Exception as e:
            raise FFmpegAdapterError(f"Failed to probe file: {e}")

    def normalize(self, in_path: str, out_path: str) -> None:
        self._check_binaries()
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            shutil.copy(in_path, out_path)
            return
            
        if not os.path.exists(in_path):
            raise FileNotFoundError(f"Input file not found: {in_path}")
            
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        # Normalize to 16kHz, mono (1 channel), 16-bit PCM wav
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", in_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            out_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise FFmpegAdapterError(f"ffmpeg normalize failed: {e.stderr}")
        except Exception as e:
            raise FFmpegAdapterError(f"Failed to normalize audio: {e}")

    def extract_segment(self, in_path: str, out_path: str, start_sec: float, end_sec: float) -> None:
        self._check_binaries()
        if os.getenv("MOCK_ADAPTERS", "true").lower() == "true":
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            shutil.copy(in_path, out_path)
            return
            
        if not os.path.exists(in_path):
            raise FileNotFoundError(f"Input file not found: {in_path}")
            
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        duration = end_sec - start_sec
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_sec),
            "-i", in_path,
            "-t", str(duration),
            "-acodec", "copy",
            out_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise FFmpegAdapterError(f"ffmpeg segment extraction failed: {e.stderr}")
        except Exception as e:
            raise FFmpegAdapterError(f"Failed to extract segment: {e}")
