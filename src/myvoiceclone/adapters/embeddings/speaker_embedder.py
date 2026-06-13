import os
import hashlib
from typing import List

class SpeakerEmbedder:
    def __init__(self, model_id: str = "speaker_resnet"):
        self.model_id = model_id

    def embed(self, filepath: str) -> List[float]:
        # Return deterministic mock vector for testing
        hasher = hashlib.md5(filepath.encode('utf-8'))
        digest = hasher.digest()
        
        # Expand 16 bytes to 128 floats
        vec = []
        for i in range(128):
            byte_val = digest[i % 16]
            # Normalize to [-1.0, 1.0]
            val = (byte_val / 127.5) - 1.0
            vec.append(val)
            
        return vec
