import os
import pytest
from myvoiceclone.domain.entities import SynthRequest
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter

@pytest.mark.unit
def test_xtts_adapter_mock_synth():
    os.environ["MOCK_ADAPTERS"] = "true"
    adapter = XttsAdapter()
    
    req = SynthRequest(
        text="Hello world",
        speaker_id="spk_test",
        config={}
    )
    
    result = adapter.synth(req)
    assert result.status == "completed"
    assert len(result.audio_bytes) > 0
    assert result.duration_sec == 4.2
