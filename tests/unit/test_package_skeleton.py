import os
import pytest

@pytest.mark.unit
def test_directory_structure():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Check key directories exist
    dirs = [
        "src/myvoiceclone/domain",
        "src/myvoiceclone/storage",
        "src/myvoiceclone/pipelines",
        "src/myvoiceclone/adapters",
        "src/myvoiceclone/jobs",
        "src/myvoiceclone/api",
        "configs",
        "db/migrations",
        "tests/unit"
    ]
    for d in dirs:
        abs_path = os.path.join(base_dir, d)
        assert os.path.isdir(abs_path), f"Directory {d} does not exist at {abs_path}"

@pytest.mark.unit
def test_package_imports():
    # Attempt imports of our skeleton modules
    import myvoiceclone.domain.entities
    import myvoiceclone.domain.states
    import myvoiceclone.storage.sqlite
    import myvoiceclone.storage.migrations
    import myvoiceclone.storage.repositories
    import myvoiceclone.storage.artifact_store
    import myvoiceclone.storage.vector_store
    import myvoiceclone.storage.vec0_store
    import myvoiceclone.storage.vec1_store
    
    assert True
