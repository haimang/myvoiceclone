import os
import hashlib
from typing import List

class TextEmbedder:
    def __init__(self, model_id: str = "text_bge"):
        self.model_id = model_id

    def embed(self, text: str) -> List[float]:
        # Return deterministic mock vector for testing
        hasher = hashlib.md5(text.encode('utf-8'))
        digest = hasher.digest()
        
        vec = []
        for i in range(128):
            byte_val = digest[i % 16]
            val = (byte_val / 127.5) - 1.0
            vec.append(val)
            
        return vec
