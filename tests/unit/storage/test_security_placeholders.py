import os
import pytest
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations

@pytest.fixture
def db_conn(tmp_path):
    db_file = str(tmp_path / "test.db")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    migrations_dir = os.path.join(project_root, "db", "migrations")
    run_migrations(db_file, migrations_dir)
    conn = get_connection(db_file, load_vec=True)
    yield conn
    conn.close()

@pytest.mark.unit
def test_security_tables_exist(db_conn):
    cursor = db_conn.cursor()
    
    # Check tables exist
    required_tables = ["consent_ledger", "policy_events", "release_gates"]
    for table in required_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
        assert cursor.fetchone() is not None, f"Security table {table} should exist as a placeholder"
