import os
import pytest
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations
from myvoiceclone.storage.artifact_store import ArtifactStore

@pytest.fixture
def db_conn(tmp_path):
    db_file = str(tmp_path / "test.db")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    migrations_dir = os.path.join(project_root, "db", "migrations")
    run_migrations(db_file, migrations_dir)
    conn = get_connection(db_file, load_vec=True)
    yield conn
    conn.close()

@pytest.mark.unit
def test_artifact_store_lifecycle(db_conn, tmp_path):
    artifact_root = str(tmp_path / "artifacts")
    store = ArtifactStore(db_conn, artifact_root)
    
    content = b"fake audio data"
    # Create parent artifact
    parent = store.create_artifact(
        name="original.wav",
        content=content,
        artifact_type="recordings",
        metadata_json={"channels": 1}
    )
    
    assert parent.id.startswith("art_")
    assert parent.name == "original.wav"
    assert parent.sha256 is not None
    assert parent.bytes == len(content)
    assert parent.artifact_type == "recordings"
    assert parent.metadata_json["channels"] == 1
    assert parent.metadata_json["metadata_contract_version"] == "first-test-v1"
    
    # Check physical file exists
    abs_path = store.get_absolute_path(parent)
    assert os.path.exists(abs_path)
    with open(abs_path, 'rb') as f:
        assert f.read() == content
        
    # Create derived artifact
    child_content = b"cleaned audio data"
    child = store.create_artifact(
        name="cleaned.wav",
        content=child_content,
        artifact_type="cleaned",
        parent_artifact_id=parent.id,
        metadata_json={"noise_reduced": True}
    )
    
    # Verify retrieval
    retrieved_child = store.get_artifact(child.id)
    assert retrieved_child is not None
    assert retrieved_child.parent_artifact_id == parent.id
    assert retrieved_child.metadata_json["noise_reduced"] is True
    
    # Verify lineage
    lineage = store.get_lineage(child.id)
    assert len(lineage) == 2
    assert lineage[0].id == child.id
    assert lineage[1].id == parent.id
