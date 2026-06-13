import sqlite3
import pytest
from myvoiceclone.storage.sqlite import get_connection

@pytest.mark.unit
def test_sqlite_in_memory_connection():
    conn = get_connection(":memory:", load_vec=False)
    
    # Check Foreign Keys is ON
    fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk == 1, "Foreign keys should be enabled"
    
    # Check Row Factory works
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO test (name) VALUES ('alice');")
    row = conn.execute("SELECT * FROM test;").fetchone()
    assert row["name"] == "alice", "Row factory should allow dictionary-like lookup"
    
    conn.close()

@pytest.mark.unit
def test_sqlite_file_connection(tmp_path):
    db_file = str(tmp_path / "test.db")
    conn = get_connection(db_file, load_vec=False)
    
    # Check journal mode is WAL
    journal = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert journal.lower() == "wal", "Journal mode should be WAL"
    
    conn.close()
