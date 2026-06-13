import json
import sqlite3
from typing import Dict, Any, List
from myvoiceclone.config import load_local_config

def is_security_enabled() -> bool:
    try:
        config = load_local_config()
        return config.get("security", {}).get("enabled", False)
    except Exception:
        return False

def check_release_policy(conn: sqlite3.Connection, model_run_id: str) -> Dict[str, Any]:
    """
    Checks if a model run is allowed to be released.
    If security is disabled, passes unconditionally.
    If security is enabled, checks consent for all speakers in the dataset.
    """
    if not is_security_enabled():
        return {
            "passed": True,
            "reason": "Security policy checks are disabled by configuration.",
            "unauthorized_speakers": []
        }

    # Fetch dataset ID for the model run
    cursor = conn.cursor()
    cursor.execute("SELECT dataset_id FROM model_runs WHERE id = ?;", (model_run_id,))
    row = cursor.fetchone()
    if not row:
        return {
            "passed": False,
            "reason": f"Model run {model_run_id} not found.",
            "unauthorized_speakers": []
        }
    
    dataset_id = row["dataset_id"]
    if not dataset_id:
        return {
            "passed": True,
            "reason": "Model run is not associated with any dataset (consent checks skipped).",
            "unauthorized_speakers": []
        }

    # Get distinct speakers in the dataset
    cursor.execute(
        """
        SELECT DISTINCT s.speaker_id 
        FROM dataset_segments ds
        JOIN segments s ON ds.segment_id = s.id
        WHERE ds.dataset_id = ? AND s.speaker_id IS NOT NULL AND s.speaker_id != '';
        """,
        (dataset_id,)
    )
    speakers = [r["speaker_id"] for r in cursor.fetchall()]

    if not speakers:
        return {
            "passed": True,
            "reason": "No speakers found in the dataset segments.",
            "unauthorized_speakers": []
        }

    unauthorized_speakers = []
    for spk in speakers:
        cursor.execute("SELECT granted, status FROM consent_ledger WHERE speaker_id = ?;", (spk,))
        consent_rows = cursor.fetchall()
        has_consent = any(r["granted"] == 1 and (r["status"] in (None, "active")) for r in consent_rows)
        if not has_consent:
            unauthorized_speakers.append(spk)

    if unauthorized_speakers:
        reason = f"Missing consent for speakers: {', '.join(unauthorized_speakers)}"
        # Log policy event
        details_json = json.dumps({
            "model_run_id": model_run_id,
            "unauthorized_speakers": unauthorized_speakers,
            "reason": reason
        })
        conn.execute(
            """
            INSERT INTO policy_events (event_type, status, details_json, subject_type, subject_id, policy_name, decision, reason, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("consent_check", "failed", details_json, "model_run", model_run_id, "consent_check", "failed", reason, details_json)
        )
        return {
            "passed": False,
            "reason": reason,
            "unauthorized_speakers": unauthorized_speakers
        }

    # Log successful policy event
    details_json = json.dumps({
        "model_run_id": model_run_id,
        "speakers": speakers
    })
    conn.execute(
        """
        INSERT INTO policy_events (event_type, status, details_json, subject_type, subject_id, policy_name, decision, reason, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("consent_check", "passed", details_json, "model_run", model_run_id, "consent_check", "passed", "All speakers have granted consent.", details_json)
    )
    return {
        "passed": True,
        "reason": "All speakers have granted consent.",
        "unauthorized_speakers": []
    }
