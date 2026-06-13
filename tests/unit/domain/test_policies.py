import os
import pytest
import sqlite3
import json
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations
from myvoiceclone.domain.policies import check_release_policy

@pytest.fixture
def db_conn(tmp_path):
    db_file = str(tmp_path / "test.db")
    # Resolve project root path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    migrations_dir = os.path.join(project_root, "db", "migrations")
    run_migrations(db_file, migrations_dir)
    conn = get_connection(db_file, load_vec=True)
    yield conn
    conn.close()

def setup_test_data(conn: sqlite3.Connection):
    # Insert a speaker
    conn.execute("INSERT INTO speakers (id, display_name, role) VALUES ('spk_1', 'Test Speaker', 'owner');")
    # Insert a recording
    conn.execute("INSERT INTO recordings (id, source_uri, sha256, duration_sec, sample_rate, channels, status) VALUES ('rec_1', 'uri_1', 'sha_1', 10.0, 16000, 1, 'completed');")
    # Insert a segment
    conn.execute(
        """
        INSERT INTO segments (id, recording_id, speaker_id, start_sec, end_sec, status)
        VALUES ('seg_1', 'rec_1', 'spk_1', 0.0, 5.0, 'completed');
        """
    )
    # Insert a dataset
    conn.execute("INSERT INTO datasets (id, name, status) VALUES ('ds_1', 'Test Dataset', 'active');")
    # Link dataset and segment
    conn.execute("INSERT INTO dataset_segments (dataset_id, segment_id, split) VALUES ('ds_1', 'seg_1', 'train');")
    # Insert a model run
    conn.execute("INSERT INTO model_runs (id, name, dataset_id, status) VALUES ('run_1', 'Test Run', 'ds_1', 'completed');")
    conn.commit()

@pytest.mark.unit
def test_policy_disabled_by_default(monkeypatch, db_conn):
    # Mock config to have security disabled
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": False}}
    )
    setup_test_data(db_conn)
    
    # Policy should pass even without consent in ledger
    res = check_release_policy(db_conn, "run_1")
    assert res["passed"] is True
    assert "disabled" in res["reason"]

@pytest.mark.unit
def test_policy_blocked_when_enabled_and_no_consent(monkeypatch, db_conn):
    # Mock config to have security enabled
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": True}}
    )
    setup_test_data(db_conn)
    
    # Missing consent should fail policy check
    res = check_release_policy(db_conn, "run_1")
    assert res["passed"] is False
    assert "Missing consent" in res["reason"]
    assert "spk_1" in res["unauthorized_speakers"]
    
    # Check that policy event is recorded
    cursor = db_conn.cursor()
    cursor.execute("SELECT event_type, status, details_json FROM policy_events ORDER BY id DESC LIMIT 1;")
    event = cursor.fetchone()
    assert event is not None
    assert event["event_type"] == "consent_check"
    assert event["status"] == "failed"
    details = json.loads(event["details_json"])
    assert details["model_run_id"] == "run_1"
    assert "spk_1" in details["unauthorized_speakers"]

@pytest.mark.unit
def test_policy_passes_when_consent_granted(monkeypatch, db_conn):
    monkeypatch.setattr(
        "myvoiceclone.domain.policies.load_local_config",
        lambda: {"security": {"enabled": True}}
    )
    setup_test_data(db_conn)
    
    # Grant consent
    db_conn.execute("INSERT INTO consent_ledger (id, speaker_id, recording_id, granted) VALUES ('c_1', 'spk_1', 'rec_1', 1);")
    db_conn.commit()
    
    res = check_release_policy(db_conn, "run_1")
    assert res["passed"] is True
    assert "All speakers have granted consent" in res["reason"]
    
    # Check policy event is recorded as passed
    cursor = db_conn.cursor()
    cursor.execute("SELECT event_type, status, details_json FROM policy_events ORDER BY id DESC LIMIT 1;")
    event = cursor.fetchone()
    assert event is not None
    assert event["event_type"] == "consent_check"
    assert event["status"] == "passed"
