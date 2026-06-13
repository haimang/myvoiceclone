import os
import pytest
from myvoiceclone.domain.entities import Dataset, ModelRun
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository, ReportRepository
from myvoiceclone.eval.report import generate_train_report

@pytest.mark.unit
def test_generate_train_report_success_flow(db_conn, artifact_store):
    # Setup dataset
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_train_ok", name="Train Ok DS", status="frozen"))
    
    # Setup model run
    run_repo = ModelRunRepository(db_conn)
    run_repo.save(ModelRun(
        id="run_sovits_success",
        name="sovits_test",
        dataset_id="ds_train_ok",
        status="completed",
        config_json={
            "rendered_artifact_id": "art_sample_1",
            "last_checkpoint_artifact_id": "art_ckpt_1",
            "env_digest": {
                "python_version": "3.12.3",
                "torch_version": "2.2.0",
                "cuda_version": "12.1",
                "cuda_available": True,
                "git_commit": "abc1234"
            },
            "config": {"epochs": 10}
        }
    ))
    
    # Insert mock artifacts
    db_conn.execute("INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type) VALUES ('art_sample_1', 'sample.wav', 'rendered_audio/sample.wav', 'sha_s', 10, 'rendered_audio');")
    db_conn.execute("INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type) VALUES ('art_ckpt_1', 'ckpt.pth', 'checkpoint/ckpt.pth', 'sha_c', 100, 'checkpoint');")
    
    # Insert mock loss metrics
    db_conn.execute("INSERT INTO eval_metrics (run_id, metric_name, metric_value, step) VALUES ('run_sovits_success', 'loss', 0.05, 1);")
    db_conn.execute("INSERT INTO eval_metrics (run_id, metric_name, metric_value, step) VALUES ('run_sovits_success', 'loss', 0.03, 2);")
    db_conn.commit()
    
    # Generate report
    report = generate_train_report(db_conn, artifact_store, "rpt_train_ok", "run_sovits_success")
    
    # Assertions
    assert report.id == "rpt_train_ok"
    assert report.report_type == "train_report"
    assert report.summary_json["status"] == "generated"
    assert report.summary_json["run_status"] == "completed"
    assert len(report.summary_json["loss_history"]) == 2
    assert report.summary_json["env_digest"]["python_version"] == "3.12.3"
    
    # Verify file is written
    report_repo = ReportRepository(db_conn)
    rpt = report_repo.get_by_id("rpt_train_ok")
    assert rpt.artifact_id is not None
    art = artifact_store.get_artifact(rpt.artifact_id)
    assert os.path.exists(artifact_store.get_absolute_path(art))

@pytest.mark.unit
def test_generate_train_report_cancelled_flow(db_conn, artifact_store):
    # Setup model run
    run_repo = ModelRunRepository(db_conn)
    run_repo.save(ModelRun(
        id="run_sovits_cancelled",
        name="sovits_test_c",
        dataset_id=None,
        status="cancelled",
        config_json={
            "error_msg": "Cancelled by user"
        }
    ))
    db_conn.commit()
    
    report = generate_train_report(db_conn, artifact_store, "rpt_train_c", "run_sovits_cancelled")
    assert report.summary_json["run_status"] == "cancelled"
    assert report.summary_json["error_msg"] == "Cancelled by user"
