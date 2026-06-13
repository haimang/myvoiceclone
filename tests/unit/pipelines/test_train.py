import pytest
from myvoiceclone.domain.entities import Dataset, ModelRun
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository
from myvoiceclone.adapters.training.rvc_adapter import RvcAdapter
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter
from myvoiceclone.pipelines.train import run_train_rvc, run_synth_xtts

@pytest.mark.unit
def test_run_train_rvc_success(db_conn, artifact_store):
    # 1. Setup frozen dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_frozen", name="Frozen DS", status="frozen"))
    db_conn.commit()

    rvc_adapter = RvcAdapter()
    config = {"epochs": 10}

    # 2. Run training
    run = run_train_rvc(
        conn=db_conn,
        artifact_store=artifact_store,
        rvc_adapter=rvc_adapter,
        dataset_id="ds_frozen",
        model_name="rvc_test_model",
        config=config
    )

    # 3. Assertions
    assert run.id is not None
    assert run.status == "completed"
    assert run.name == "rvc_test_model"
    assert run.dataset_id == "ds_frozen"
    assert run.config_json["metrics"]["loss"] == 0.045
    
    # Check that artifact checkpoint and rendered sample were registered
    checkpoint_art_id = run.config_json.get("checkpoint_artifact_id")
    rendered_art_id = run.config_json.get("rendered_artifact_id")
    assert checkpoint_art_id is not None
    assert rendered_art_id is not None

    checkpoint_art = artifact_store.get_artifact(checkpoint_art_id)
    rendered_art = artifact_store.get_artifact(rendered_art_id)
    assert checkpoint_art.artifact_type == "checkpoint"
    assert rendered_art.artifact_type == "rendered_audio"
    assert rendered_art.parent_artifact_id == checkpoint_art.id

@pytest.mark.unit
def test_run_train_rvc_dataset_not_frozen(db_conn, artifact_store):
    # Setup active dataset (not frozen)
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_active", name="Active DS", status="active"))
    db_conn.commit()

    rvc_adapter = RvcAdapter()
    
    with pytest.raises(ValueError, match="must be frozen before training"):
        run_train_rvc(
            conn=db_conn,
            artifact_store=artifact_store,
            rvc_adapter=rvc_adapter,
            dataset_id="ds_active",
            model_name="rvc_test_model",
            config={}
        )

@pytest.mark.unit
def test_run_train_rvc_failure(db_conn, artifact_store, monkeypatch):
    # Setup frozen dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_frozen", name="Frozen DS", status="frozen"))
    db_conn.commit()

    # Mock adapter to fail
    rvc_adapter = RvcAdapter()
    def mock_train_fail(request):
        from myvoiceclone.domain.entities import TrainResult
        return TrainResult(model_run_id=request.model_name, status="failed", checkpoint_bytes=b"", error_msg="Insufficient memory")
    monkeypatch.setattr(rvc_adapter, "train", mock_train_fail)

    with pytest.raises(RuntimeError, match="RVC training failed: Insufficient memory"):
        run_train_rvc(
            conn=db_conn,
            artifact_store=artifact_store,
            rvc_adapter=rvc_adapter,
            dataset_id="ds_frozen",
            model_name="rvc_failed_model",
            config={}
        )

    # Verify that the ModelRun status in DB is "failed"
    run_repo = ModelRunRepository(db_conn)
    # Since run_id is random, we search in model_runs table
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, status, config_json FROM model_runs WHERE name = 'rvc_failed_model';")
    row = cursor.fetchone()
    assert row is not None
    assert row["status"] == "failed"
    import json
    cfg = json.loads(row["config_json"])
    assert "Insufficient memory" in cfg.get("error_msg", "")

@pytest.mark.unit
def test_run_synth_xtts_success(db_conn, artifact_store):
    xtts_adapter = XttsAdapter()
    run = run_synth_xtts(
        conn=db_conn,
        artifact_store=artifact_store,
        xtts_adapter=xtts_adapter,
        speaker_id="spk_target",
        text="Hello target",
        config={}
    )
    
    assert run.id is not None
    assert run.status == "completed"
    assert run.dataset_id is None
    
    rendered_art_id = run.config_json.get("rendered_artifact_id")
    assert rendered_art_id is not None
    rendered_art = artifact_store.get_artifact(rendered_art_id)
    assert rendered_art.artifact_type == "rendered_audio"
