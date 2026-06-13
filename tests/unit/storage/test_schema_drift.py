import os

import pytest

from myvoiceclone.storage.migrations import get_file_checksum, run_migrations
from myvoiceclone.storage.sqlite import get_connection


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "db", "migrations")


@pytest.mark.unit
def test_first_test_schema_inventory(tmp_path):
    db_file = str(tmp_path / "schema.db")
    run_migrations(db_file, MIGRATIONS_DIR)
    conn = get_connection(db_file, load_vec=False)
    try:
        expected_columns = {
            "jobs": {"id", "name", "status", "payload_json", "params_json", "error_msg"},
            "job_events": {"id", "job_id", "event_type", "status_from", "status_to", "message", "metadata_json"},
            "artifacts": {"id", "artifact_type", "kind", "job_id", "created_by_job_id", "metadata_json"},
            "eval_metrics": {"run_id", "metric_name", "metric_value", "metric_json", "report_id"},
            "eval_samples": {"run_id", "audio_artifact_id", "input_artifact_id", "output_artifact_id", "scores_json"},
            "release_gates": {"model_run_id", "passed", "status", "details_json", "decision_json"},
            "policy_events": {"subject_type", "subject_id", "policy_name", "decision", "payload_json"},
        }

        for table, columns in expected_columns.items():
            rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
            actual = {row["name"] for row in rows}
            assert columns <= actual, f"{table} missing {columns - actual}"

        indexes = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index';")}
        assert {"idx_job_events_job", "idx_job_events_type", "idx_eval_metrics_run_name"} <= indexes
    finally:
        conn.close()


@pytest.mark.unit
def test_migration_order_and_checksum_inventory():
    migration_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql") and f[:3].isdigit())
    versions = [int(f[:3]) for f in migration_files]

    assert versions == sorted(versions)
    assert versions == list(range(1, max(versions) + 1))
    checksums = {f: get_file_checksum(os.path.join(MIGRATIONS_DIR, f)) for f in migration_files}
    assert checksums["008_first_test_observability.sql"]
