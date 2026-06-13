import sqlite3
from typing import Dict, Any
from myvoiceclone.storage.artifact_store import ArtifactStore
from myvoiceclone.eval.objective import evaluate_objective_metrics

def run_evaluation(
    conn: sqlite3.Connection,
    artifact_store: ArtifactStore,
    run_id: str
) -> Dict[str, Any]:
    # Dispatch to objective metrics evaluation
    return evaluate_objective_metrics(conn, artifact_store, run_id)
