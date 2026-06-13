import os
import pytest
from myvoiceclone.domain.entities import TrainRequest
from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter

@pytest.mark.unit
def test_sovits_adapter_mock_methods(tmp_path):
    os.environ["MOCK_ADAPTERS"] = "true"
    adapter = SovitsAdapter()
    
    # 1. Test prepare (no throw/error)
    adapter.prepare("ds_test")
    
    # 2. Test train
    req = TrainRequest(dataset_id="ds_test", model_name="sovits_test", config={})
    res = adapter.train(req)
    assert res.status == "completed"
    assert res.model_run_id == "sovits_test"
    assert res.checkpoint_bytes == b"fake_sovits_checkpoint_data"
    assert res.metrics["loss"] == 0.035
    
    # 3. Test resume
    res_resume = adapter.resume("ckpt_path.pth", req)
    assert res_resume.status == "completed"
    assert res_resume.checkpoint_bytes == b"fake_sovits_resumed_checkpoint_data"
    assert res_resume.metrics["loss"] == 0.025
    
    # 4. Test export
    out_path = str(tmp_path / "exported.pth")
    adapter.export("ckpt_path.pth", out_path)
    assert os.path.exists(out_path)
    with open(out_path, 'rb') as f:
        data = f.read()
    assert data == b"fake_exported_sovits_model_data"
