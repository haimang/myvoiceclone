import os
import pytest
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter

@pytest.mark.unit
def test_demucs_mock_separation(tmp_path):
    adapter = DemucsAdapter()
    res = adapter.separate("/tmp/nonexistent.wav", str(tmp_path))
    
    assert res.cleaned_path.endswith(".wav")
    assert os.path.exists(res.cleaned_path)
