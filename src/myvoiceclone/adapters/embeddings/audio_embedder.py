import os
import hashlib
from typing import List

class AudioEmbedder:
    def __init__(self, model_id: str = "audio_clap"):
        self.model_id = model_id

    def embed(self, filepath: str) -> List[float]:
        # Return deterministic mock vector for testing
        hasher = hashlib.md5(filepath.encode('utf-8'))
        digest = hasher.digest()
        
        vec = []
        for i in range(128):
            byte_val = digest[i % 16]
            val = (byte_val / 127.5) - 1.0
            vec.append(val)
            
        return vec
