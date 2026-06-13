import pytest
from myvoiceclone.pipelines.train import capture_env_digest

@pytest.mark.unit
def test_capture_env_digest_fields():
    digest = capture_env_digest()
    assert digest is not None
    assert "python_version" in digest
    assert "torch_version" in digest
    assert "cuda_available" in digest
    assert "cuda_version" in digest
    assert "git_commit" in digest
    
    # Assert type characteristics
    assert isinstance(digest["python_version"], str)
    assert isinstance(digest["cuda_available"], bool)
