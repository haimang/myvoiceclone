import pytest
from myvoiceclone.domain.entities import ModelRun
from myvoiceclone.storage.repositories import ModelRunRepository
from myvoiceclone.eval.objective import evaluate_objective_metrics, evaluate_objective_proxy

@pytest.mark.unit
def test_evaluate_objective_metrics_success(db_conn, artifact_store):
    run_repo = ModelRunRepository(db_conn)
    # 1. Setup completed model run with rendered sample
    run_id = "run_obj_ok"
    run_repo.save(ModelRun(
        id=run_id,
        name="rvc_test",
        dataset_id=None,
        status="completed",
        config_json={"rendered_artifact_id": "art_rendered_sample"}
    ))
    
    # Save a mock artifact
    db_conn.execute(
        """
        INSERT INTO artifacts (id, name, uri, sha256, bytes, artifact_type)
        VALUES ('art_rendered_sample', 'sample.wav', 'rendered_audio/sample.wav', 'sha_rendered', 10, 'rendered_audio');
        """
    )
    db_conn.commit()
    
    # 2. Run evaluation
    res = evaluate_objective_metrics(db_conn, artifact_store, run_id)
    
    # 3. Assertions
    assert res["status"] == "success"
    assert res["metrics"]["speaker_similarity"] == 0.84
    assert res["metrics"]["wer"] == 0.06
    
    # Check metrics table entries
    cursor = db_conn.cursor()
    cursor.execute("SELECT metric_name, metric_value, metric_json FROM eval_metrics WHERE run_id = ?;", (run_id,))
    rows = cursor.fetchall()
    metrics = {row["metric_name"]: row["metric_value"] for row in rows}
    assert metrics["speaker_similarity"] == 0.84
    assert metrics["wer"] == 0.06
    assert all('"metric_source": "mock"' in row["metric_json"] for row in rows)
    assert all('"quality_gate_eligible": false' in row["metric_json"] for row in rows)

@pytest.mark.unit
def test_evaluate_objective_metrics_degraded(db_conn, artifact_store):
    run_repo = ModelRunRepository(db_conn)
    # Setup model run without rendered sample
    run_id = "run_obj_degraded"
    run_repo.save(ModelRun(
        id=run_id,
        name="rvc_test",
        dataset_id=None,
        status="completed",
        config_json={}
    ))
    db_conn.commit()
    
    res = evaluate_objective_metrics(db_conn, artifact_store, run_id)
    assert res["status"] == "degraded"
    assert "No rendered sample artifact" in res["reason"]


@pytest.mark.unit
def test_objective_proxy_unavailable_is_explicit(db_conn, artifact_store):
    res = evaluate_objective_proxy(db_conn, artifact_store, "run_missing_proxy")

    assert res["status"] == "unavailable"
    assert res["metric_source"] == "objective_proxy"
    assert res["metrics"] == {}
