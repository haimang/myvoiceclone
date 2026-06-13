import logging

logger = logging.getLogger("myvoiceclone.adapters.audio.torchaudio_io")

class TorchaudioIO:
    def __init__(self):
        self.available = False
        try:
            import torchaudio
            self.available = True
        except ImportError:
            logger.warning("torchaudio package is not installed.")

    def load_metadata(self, filepath: str) -> dict:
        if self.available:
            import torchaudio
            try:
                info = torchaudio.info(filepath)
                return {
                    "duration_sec": info.num_frames / info.sample_rate,
                    "sample_rate": info.sample_rate,
                    "channels": info.num_channels
                }
            except Exception as e:
                logger.error(f"torchaudio failed to read metadata: {e}")
                
        # Fallback to soundfile if available
        try:
            import soundfile as sf
            info = sf.info(filepath)
            return {
                "duration_sec": info.duration,
                "sample_rate": info.samplerate,
                "channels": info.channels
            }
        except ImportError:
            raise RuntimeError("Neither torchaudio nor soundfile is available to read metadata.")
        except Exception as e:
            raise RuntimeError(f"soundfile failed to read metadata: {e}")
