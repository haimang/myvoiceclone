import sqlite3
import json
from typing import Dict, Any
from myvoiceclone.storage.repositories import ModelRunRepository
from myvoiceclone.storage.artifact_store import ArtifactStore


def evaluate_objective_proxy(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    run_id: str,
) -> Dict[str, Any]:
    try:
        import torchaudio  # noqa: F401
    except Exception as exc:
        return {
            "status": "unavailable",
            "metric_source": "objective_proxy",
            "reason": f"optional objective proxy dependency unavailable: {exc}",
            "metrics": {},
        }
    return {
        "status": "unavailable",
        "metric_source": "objective_proxy",
        "reason": "SQUIM/DNSMOS proxy model is not configured for first-test local run",
        "metrics": {},
    }

def evaluate_objective_metrics(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    run_id: str
) -> Dict[str, Any]:
    run_repo = ModelRunRepository(conn)
    run = run_repo.get_by_id(run_id)
    if not run:
        raise ValueError(f"Model run {run_id} not found")
        
    rendered_art_id = run.config_json.get("rendered_artifact_id")
    if not rendered_art_id:
        # Return degraded metrics
        degraded_result = {
            "status": "degraded",
            "reason": "No rendered sample artifact found for model run",
            "metrics": {}
        }
        # Update run configuration with degraded reason
        run.config_json["degraded_reason"] = degraded_result["reason"]
        run_repo.save(run)
        conn.commit()
        return degraded_result

    # Ensure artifact exists
    art = artifact_store.get_artifact(rendered_art_id)
    if not art:
        degraded_result = {
            "status": "degraded",
            "reason": f"Rendered sample artifact {rendered_art_id} file is missing",
            "metrics": {}
        }
        run.config_json["degraded_reason"] = degraded_result["reason"]
        run_repo.save(run)
        conn.commit()
        return degraded_result

    input_refs = art.metadata_json.get("input_refs", {}) if art.metadata_json else {}
    input_artifact_id = input_refs.get("source_artifact_id") or art.source_artifact_id or art.parent_artifact_id
    reference_artifact_id = input_refs.get("reference_artifact_id") or art.parent_artifact_id

    # Compute mock metrics (Objective Evaluation)
    metrics = {
        "speaker_similarity": 0.84,
        "wer": 0.06,
        "noise_level": 0.015,
        "degradation_score": 0.0
    }
    metric_meta = {
        "metric_source": "mock",
        "adapter_mode": run.config_json.get("adapter_mode", "mock"),
        "quality_gate_eligible": False,
        "reason": "first-build objective placeholder; not real quality evidence",
    }
    
    # Write to eval_metrics
    for m_name, m_val in metrics.items():
        conn.execute(
            """
            INSERT INTO eval_metrics (run_id, metric_name, metric_value, metric_json)
            VALUES (?, ?, ?, ?);
            """,
            (run_id, m_name, m_val, json.dumps(metric_meta))
        )
        
    # Link to eval_samples
    sample_id = f"sample_{run_id}_{uuid_hex()}"
    conn.execute(
        """
        INSERT INTO eval_samples (
            id, run_id, prompt, audio_artifact_id, input_artifact_id,
            output_artifact_id, reference_artifact_id, scores_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            sample_id,
            run_id,
            "Standard evaluation prompt text",
            rendered_art_id,
            input_artifact_id,
            rendered_art_id,
            reference_artifact_id,
            json.dumps(metric_meta),
        )
    )
    
    # Save status
    run.config_json["objective_eval_completed"] = True
    run_repo.save(run)
    conn.commit()
    
    return {
        "status": "success",
        "reason": "Evaluation completed successfully",
        "metrics": metrics,
        "sample_id": sample_id
    }

def uuid_hex() -> str:
    import uuid
    return uuid.uuid4().hex[:12]
