import logging
from myvoiceclone.domain.entities import AudioProbe

logger = logging.getLogger("myvoiceclone.adapters.audio.torchaudio_io")


class TorchaudioIO:
    """Audio metadata reader using torchaudio (with soundfile fallback).

    V9 fix: Changed return type from bare dict to AudioProbe DTO to comply
    with the adapter DTO contract (final-execution-plan.md §15.3 / adapter_contracts).
    """

    def __init__(self):
        self.available = False
        try:
            import torchaudio
            self.available = True
        except ImportError:
            logger.warning("torchaudio package is not installed.")

    def load_metadata(self, filepath: str) -> AudioProbe:
        """Read audio file metadata and return a typed AudioProbe DTO.

        V9 fix: Previously returned a bare dict; now returns AudioProbe(duration_sec, sample_rate, channels).
        """
        if self.available:
            import torchaudio
            try:
                info = torchaudio.info(filepath)
                return AudioProbe(
                    duration_sec=info.num_frames / info.sample_rate,
                    sample_rate=info.sample_rate,
                    channels=info.num_channels,
                )
            except Exception as e:
                logger.error(f"torchaudio failed to read metadata: {e}")

        # Fallback to soundfile if available
        try:
            import soundfile as sf
            info = sf.info(filepath)
            return AudioProbe(
                duration_sec=info.duration,
                sample_rate=info.samplerate,
                channels=info.channels,
            )
        except ImportError:
            raise RuntimeError("Neither torchaudio nor soundfile is available to read metadata.")
        except Exception as e:
            raise RuntimeError(f"soundfile failed to read metadata: {e}")
