import pytest
import sqlite3
from myvoiceclone.domain.entities import Dataset, ModelRun, Job
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository, JobRepository
from myvoiceclone.adapters.training.sovits_adapter import SovitsAdapter
from myvoiceclone.pipelines.train import run_train_sovits
from myvoiceclone.jobs.runner import JobRunner

@pytest.mark.unit
def test_run_train_sovits_success_flow(db_conn, artifact_store):
    # Setup frozen dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_sovits_ok", name="So-VITS DS", status="frozen", manifest_sha256="manifest_sha_ok"))
    db_conn.commit()
    
    adapter = SovitsAdapter()
    config = {"epochs": 2}
    
    run = run_train_sovits(
        conn=db_conn,
        artifact_store=artifact_store,
        sovits_adapter=adapter,
        dataset_id="ds_sovits_ok",
        model_name="sovits_test_model",
        config=config
    )
    
    assert run.status == "completed"
    assert run.config_json["metrics"]["final_loss"] is not None
    assert "registered_model_artifact_id" in run.config_json
    assert "rendered_artifact_id" in run.config_json
    assert "env_digest" in run.config_json
    
    # Check intermediate checkpoint and registry artifact existence
    reg_art_id = run.config_json["registered_model_artifact_id"]
    reg_art = artifact_store.get_artifact(reg_art_id)
    assert reg_art.artifact_type == "model_registry"

@pytest.mark.unit
def test_run_train_sovits_resume(db_conn, artifact_store):
    # Setup dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_sovits_ok", name="So-VITS DS", status="frozen", manifest_sha256="manifest_sha_ok"))
    db_conn.commit()
    
    adapter = SovitsAdapter()
    run_repo = ModelRunRepository(db_conn)
    
    # 1. Create a model run that was interrupted at epoch 1
    run_id = "run_interrupted_1"
    run_repo.save(ModelRun(id=run_id, name="sovits_model", dataset_id="ds_sovits_ok", status="checkpointed", config_json={"current_epoch": 1, "last_checkpoint_artifact_id": "art_ckpt_1"}))
    
    # Register dummy checkpoint artifact
    artifact_store.conn.execute(
        """
        INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type, metadata_json)
        VALUES ('art_ckpt_1', 'checkpoint_1.pth', 'checkpoint/checkpoint_1.pth', 'dummy_sha', 100, 'checkpoint', '{}');
        """
    )
    db_conn.commit()
    
    # 2. Resume using same model_run_id and checkpoint_id
    res_run = run_train_sovits(
        conn=db_conn,
        artifact_store=artifact_store,
        sovits_adapter=adapter,
        dataset_id="ds_sovits_ok",
        model_name="sovits_model",
        config={"epochs": 2},
        model_run_id=run_id,
        resume_from_checkpoint_id="art_ckpt_1"
    )
    
    # 3. Assertions
    assert res_run.id == run_id # Keep same model run ID / lineage
    assert res_run.status == "completed"
    assert res_run.config_json["current_epoch"] == 2

@pytest.mark.unit
def test_run_train_sovits_cancel_via_job(db_conn, artifact_store):
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_sovits_ok", name="So-VITS DS", status="frozen", manifest_sha256="manifest_sha_ok"))
    
    # Setup job
    job_repo = JobRepository(db_conn)
    job_id = "job_train_1"
    job_repo.save(Job(id=job_id, name="train_sovits", status="running", payload_json={}))
    db_conn.commit()
    
    # 1. Simulate user cancel by updating job status to 'cancelled'
    job = job_repo.get_by_id(job_id)
    job.status = "cancelled"
    job_repo.save(job)
    db_conn.commit()
    
    adapter = SovitsAdapter()
    
    # 2. Run train (should catch cancellation)
    with pytest.raises(KeyboardInterrupt, match="Job cancelled by user"):
        run_train_sovits(
            conn=db_conn,
            artifact_store=artifact_store,
            sovits_adapter=adapter,
            dataset_id="ds_sovits_ok",
            model_name="sovits_model",
            config={"epochs": 5},
            job_id=job_id
        )
        
    # 3. Verify model run state is cancelled in DB
    cursor = db_conn.cursor()
    cursor.execute("SELECT status, config_json FROM model_runs WHERE name = 'sovits_model';")
    row = cursor.fetchone()
    assert row is not None
    assert row["status"] == "cancelled"
    import json
    cfg = json.loads(row["config_json"])
    assert cfg["error_msg"] == "Cancelled by user"

@pytest.mark.unit
def test_job_runner_cancel_capture(db_conn, artifact_store, monkeypatch):
    # Setup dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_sovits_ok", name="So-VITS DS", status="frozen", manifest_sha256="manifest_sha_ok"))
    
    # Setup job
    job_repo = JobRepository(db_conn)
    job_id = "job_train_fail"
    # Create job payload with training parameters
    job_payload = {
        "dataset_id": "ds_sovits_ok",
        "model_name": "sovits_cancel_test",
        "config": {"epochs": 3}
    }
    job_repo.save(Job(id=job_id, name="train_sovits", status="pending", payload_json=job_payload))
    db_conn.commit()
    
    # Mock run_train_sovits to raise KeyboardInterrupt directly to simulate cancel
    def mock_train_interrupt(*args, **kwargs):
        raise KeyboardInterrupt("Simulated cancel")
        
    monkeypatch.setattr("myvoiceclone.jobs.runner.run_train_sovits", mock_train_interrupt)
    
    # Run Job via runner
    # We create a dummy job runner (we pass None/mocks to unused adapters)
    runner = JobRunner(
        conn=db_conn,
        artifact_store=artifact_store,
        ffmpeg_adapter=None,
        pyannote_adapter=None,
        demucs_adapter=None,
        whisper_adapter=None,
        sovits_adapter=SovitsAdapter()
    )
    
    with pytest.raises(KeyboardInterrupt):
        runner.run(job_id)
        
    # Check that job status was updated to 'cancelled' and event was logged
    job = job_repo.get_by_id(job_id)
    assert job.status == "cancelled"
    assert "Cancelled by user" in job.error_msg
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT event_type, status_to FROM job_events WHERE job_id = ? ORDER BY id DESC LIMIT 1;", (job_id,))
    event = cursor.fetchone()
    assert event["event_type"] == "cancel"
    assert event["status_to"] == "cancelled"
