import sqlite3
import json
from typing import Dict, Any
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.eval.objective import evaluate_objective_metrics
from myvoiceclone.eval.smoke import evaluate_wav_smoke
from myvoiceclone.ids import new_id

def run_evaluation(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    run_id: str
) -> Dict[str, Any]:
    result = evaluate_objective_metrics(conn, artifact_store, run_id)
    rendered_artifact_id = None
    row = conn.execute("SELECT config_json FROM model_runs WHERE id = ?;", (run_id,)).fetchone()
    if row and row["config_json"]:
        try:
            rendered_artifact_id = json.loads(row["config_json"]).get("rendered_artifact_id")
        except Exception:
            rendered_artifact_id = None
    if rendered_artifact_id:
        try:
            result["smoke_metrics"] = evaluate_wav_smoke(artifact_store, artifact_id=rendered_artifact_id)
        except Exception as exc:
            result["smoke_metrics"] = {"status": "unavailable", "reason": str(exc), "metric_source": "smoke_metric"}
    return result


def run_first_test_evaluation(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    *,
    run_id: str,
    inference_artifact_id: str,
    reference_artifact_id: str = None,
    metric_source: str = "smoke_metric",
    job_id: str = None,
) -> Dict[str, Any]:
    if not run_id:
        raise ValueError("First-test evaluation missing run_id")
    if not inference_artifact_id:
        raise ValueError("First-test evaluation missing inference_artifact_id")

    metrics = evaluate_wav_smoke(artifact_store, artifact_id=inference_artifact_id)
    metrics["metric_source"] = metric_source or metrics.get("metric_source", "smoke_metric")
    metrics["inference_artifact_id"] = inference_artifact_id
    metrics["reference_artifact_id"] = reference_artifact_id
    metrics["job_id"] = job_id

    report_id = new_id()
    conn.execute(
        """
        INSERT INTO reports (id, name, report_type, kind, subject_type, subject_id, status, summary_json, artifact_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            report_id,
            f"first-test evaluation {run_id}",
            "first_test_eval",
            "first_test_eval",
            "first_test_run",
            run_id,
            "completed" if metrics.get("smoke_pass") else "failed",
            json.dumps(metrics),
            inference_artifact_id,
        ),
    )
    conn.commit()
    return {"status": "completed", "report_id": report_id, "metrics": metrics}
