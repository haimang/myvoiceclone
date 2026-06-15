import os
import pytest
from myvoiceclone.domain.entities import Dataset, ModelRun
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository
from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter
from myvoiceclone.pipelines.train import run_train_sovits
from myvoiceclone.config import resolve_models_dir

@pytest.mark.unit
def test_model_registry_file_and_db_alignment(db_conn, artifact_store):
    # Setup dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_reg_test", name="Registry DS", status="frozen", manifest_sha256="manifest_sha_123"))
    db_conn.commit()
    
    adapter = SovitsAdapter()
    run = run_train_sovits(
        conn=db_conn,
        artifact_store=artifact_store,
        sovits_adapter=adapter,
        dataset_id="ds_reg_test",
        model_name="sovits_reg_model",
        config={"epochs": 1}
    )
    
    # Verify DB ModelRun registry fields
    assert run.status == "completed"
    reg_art_id = run.config_json.get("registered_model_artifact_id")
    assert reg_art_id is not None
    
    # Verify ArtifactStore has the record
    art = artifact_store.get_artifact(reg_art_id)
    assert art is not None
    assert art.artifact_type == "model_registry"
    assert art.name == "sovits_reg_model_final.pth"
    
    # Verify local file registry directory alignment
    registry_file_path = os.path.join(resolve_models_dir(), "registry", "sovits_reg_model_final.pth")
    assert os.path.exists(registry_file_path)
    
    # Clean up local file generated during test
    if os.path.exists(registry_file_path):
        os.remove(registry_file_path)
