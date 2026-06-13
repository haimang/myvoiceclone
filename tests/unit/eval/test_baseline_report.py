import os
import pytest
import json
from myvoiceclone.domain.entities import Dataset, ModelRun, Report
from myvoiceclone.storage.repositories import DatasetRepository, ModelRunRepository, ReportRepository
from myvoiceclone.eval.report import generate_eval_pack, generate_baseline_report, evaluate_long_train_gate

@pytest.mark.unit
def test_generate_eval_pack_success(db_conn, artifact_store):
    art = generate_eval_pack(db_conn, artifact_store, "test_pack_1")
    assert art is not None
    assert art.artifact_type == "eval_pack"
    assert "eval_pack_test_pack_1.json" in art.name
    
    # Read content and check structure
    abs_path = artifact_store.get_absolute_path(art)
    with open(abs_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data["eval_pack_id"] == "test_pack_1"
    assert len(data["prompts"]) > 0
    assert len(data["reference_clips"]) > 0
    
    # Check idempotency / reusability
    art2 = generate_eval_pack(db_conn, artifact_store, "test_pack_1")
    assert art.id == art2.id

@pytest.mark.unit
def test_generate_baseline_report_flow(db_conn, artifact_store):
    # Setup some completed model runs
    run_repo = ModelRunRepository(db_conn)
    run_repo.save(ModelRun(id="run_rvc_1", name="RVC model", dataset_id=None, status="completed", config_json={"rendered_artifact_id": "art_sample"}))
    run_repo.save(ModelRun(id="run_xtts_1", name="XTTS model", dataset_id=None, status="completed", config_json={}))
    db_conn.commit()

    # Generate baseline report
    report = generate_baseline_report(
        conn=db_conn,
        artifact_store=artifact_store,
        report_id="rpt_base_1",
        model_run_ids=["run_rvc_1", "run_xtts_1"]
    )

    assert report.id == "rpt_base_1"
    assert report.report_type == "baseline_report"
    assert report.summary_json["status"] == "generated"
    assert len(report.summary_json["model_runs"]) == 2
    
    # Check that metrics were written to DB
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM eval_metrics WHERE run_id = 'run_rvc_1';")
    assert cursor.fetchone()[0] == 3
    
    cursor.execute("SELECT metric_value FROM eval_metrics WHERE run_id = 'run_rvc_1' AND metric_name = 'speaker_similarity';")
    assert cursor.fetchone()[0] == 0.82

    # Check report artifact file exists
    assert report.artifact_id is not None
    art = artifact_store.get_artifact(report.artifact_id)
    assert os.path.exists(artifact_store.get_absolute_path(art))

@pytest.mark.unit
def test_long_train_gate_logic(db_conn, artifact_store):
    # 1. Setup dataset and recordings
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_gate_test", name="Gate Test DS", status="frozen"))
    
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_g1', 'uri_g1', 'sha_g1', 20.0, 16000, 1, 'processed');
        """
    )
    # Average quality score >= 0.6, duration >= 10s
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score)
        VALUES ('seg_g1', 'rec_g1', 0.0, 12.0, 'processed', 0.85);
        """
    )
    ds_repo.add_segment("ds_gate_test", "seg_g1", "train")
    
    # 2. Setup baseline runs & report
    run_repo = ModelRunRepository(db_conn)
    run_repo.save(ModelRun(id="run_gate_rvc", name="RVC test", dataset_id="ds_gate_test", status="completed", config_json={}))
    db_conn.commit()
    
    # We generate a baseline report. Metrics speaker_similarity will default to 0.82 (>= 0.7), and wer to 0.08 (<= 0.2)
    report = generate_baseline_report(
        conn=db_conn,
        artifact_store=artifact_store,
        report_id="rpt_gate_baseline",
        model_run_ids=["run_gate_rvc"]
    )
    
    # 3. Evaluate gate (should PASS)
    gate_result = evaluate_long_train_gate(
        conn=db_conn,
        dataset_id="ds_gate_test",
        baseline_report_id="rpt_gate_baseline"
    )
    
    assert gate_result["long_train_ready"] is True
    assert gate_result["data_quality_ok"] is True
    assert gate_result["learnability_ok"] is True
    assert gate_result["environment_ok"] is True

    # 4. Check report entry in DB
    report_repo = ReportRepository(db_conn)
    gate_rpt = report_repo.get_by_id("gate_rpt_gate_baseline")
    assert gate_rpt is not None
    assert gate_rpt.report_type == "gate_report"
    assert gate_rpt.summary_json["long_train_ready"] is True

@pytest.mark.unit
def test_long_train_gate_fail_quality(db_conn, artifact_store):
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_gate_fail", name="Fail DS", status="frozen"))
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_f1', 'uri_f1', 'sha_f1', 20.0, 16000, 1, 'processed');
        """
    )
    # Average quality score too low (0.4 < 0.6)
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score)
        VALUES ('seg_f1', 'rec_f1', 0.0, 5.0, 'processed', 0.4);
        """
    )
    ds_repo.add_segment("ds_gate_fail", "seg_f1", "train")
    
    run_repo = ModelRunRepository(db_conn)
    run_repo.save(ModelRun(id="run_f1", name="RVC test", dataset_id="ds_gate_fail", status="completed", config_json={}))
    db_conn.commit()
    
    generate_baseline_report(db_conn, artifact_store, "rpt_fail_base", ["run_f1"])
    
    # Evaluate (should FAIL due to quality)
    gate_result = evaluate_long_train_gate(db_conn, "ds_gate_fail", "rpt_fail_base")
    assert gate_result["long_train_ready"] is False
    assert gate_result["data_quality_ok"] is False
    assert "quality" in gate_result["reason"].lower()

@pytest.mark.unit
def test_long_train_gate_fail_learnability(db_conn, artifact_store):
    ds_repo = DatasetRepository(db_conn)
    ds_repo.save(Dataset(id="ds_gate_ok", name="Ok DS", status="frozen"))
    db_conn.execute(
        """
        INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status)
        VALUES ('rec_ok', 'uri_ok', 'sha_ok', 20.0, 16000, 1, 'processed');
        """
    )
    db_conn.execute(
        """
        INSERT INTO segments (id, recording_id, start_sec, end_sec, status, quality_score)
        VALUES ('seg_ok', 'rec_ok', 0.0, 15.0, 'processed', 0.8);
        """
    )
    ds_repo.add_segment("ds_gate_ok", "seg_ok", "train")
    
    run_repo = ModelRunRepository(db_conn)
    run_repo.save(ModelRun(id="run_poor", name="RVC poor", dataset_id="ds_gate_ok", status="completed", config_json={}))
    db_conn.commit()
    
    # Pre-insert poor metrics so it fails learnability
    db_conn.execute("INSERT INTO eval_metrics (run_id, metric_name, metric_value) VALUES ('run_poor', 'speaker_similarity', 0.5);")
    db_conn.execute("INSERT INTO eval_metrics (run_id, metric_name, metric_value) VALUES ('run_poor', 'wer', 0.4);")
    
    generate_baseline_report(db_conn, artifact_store, "rpt_poor_base", ["run_poor"])
    
    # Evaluate (should FAIL due to learnability)
    gate_result = evaluate_long_train_gate(db_conn, "ds_gate_ok", "rpt_poor_base")
    assert gate_result["long_train_ready"] is False
    assert gate_result["learnability_ok"] is False
    assert "similarity" in gate_result["reason"].lower()
