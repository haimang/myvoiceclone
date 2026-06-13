import pytest
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter
from myvoiceclone.adapters.training.rvc_adapter import RvcAdapter
from myvoiceclone.pipelines.train import run_synth_xtts, run_train_rvc
from myvoiceclone.domain.entities import Dataset
from myvoiceclone.storage.repositories import DatasetRepository

@pytest.mark.unit
def test_synthetic_metadata_xtts(db_conn, artifact_store):
    xtts_adapter = XttsAdapter()
    run = run_synth_xtts(
        conn=db_conn,
        artifact_store=artifact_store,
        xtts_adapter=xtts_adapter,
        speaker_id="spk_target",
        text="Hello target",
        config={}
    )
    
    assert run.status == "completed"
    rendered_art_id = run.config_json.get("rendered_artifact_id")
    assert rendered_art_id is not None
    rendered_art = artifact_store.get_artifact(rendered_art_id)
    
    assert rendered_art.artifact_type == "rendered_audio"
    assert rendered_art.metadata_json.get("synthetic") is True
    assert rendered_art.metadata_json.get("source_model_run") == run.id
    assert rendered_art.metadata_json.get("watermark") == "placeholder"

@pytest.mark.unit
def test_synthetic_metadata_rvc(db_conn, artifact_store):
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_frozen", name="Frozen DS", status="frozen"))
    db_conn.commit()

    rvc_adapter = RvcAdapter()
    run = run_train_rvc(
        conn=db_conn,
        artifact_store=artifact_store,
        rvc_adapter=rvc_adapter,
        dataset_id="ds_frozen",
        model_name="rvc_test_model",
        config={}
    )
    
    assert run.status == "completed"
    rendered_art_id = run.config_json.get("rendered_artifact_id")
    assert rendered_art_id is not None
    rendered_art = artifact_store.get_artifact(rendered_art_id)
    
    assert rendered_art.artifact_type == "rendered_audio"
    assert rendered_art.metadata_json.get("synthetic") is True
    assert rendered_art.metadata_json.get("source_model_run") == run.id
    assert rendered_art.metadata_json.get("watermark") == "placeholder"
