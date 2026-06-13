import os
import shutil
import pytest
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations, get_applied_migrations

@pytest.mark.unit
def test_migration_runner(tmp_path):
    db_file = str(tmp_path / "test.db")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    migrations_dir = os.path.join(project_root, "db", "migrations")
    
    # 1. Run migrations first time
    applied_first = run_migrations(db_file, migrations_dir)
    assert len(applied_first) > 0, "Migrations should be applied"
    
    # 2. Run migrations second time (idempotent check)
    applied_second = run_migrations(db_file, migrations_dir)
    assert len(applied_second) == 0, "No migrations should be applied on second run"
    
    # 3. Check table exists
    conn = get_connection(db_file, load_vec=True)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='speakers';")
    assert cursor.fetchone() is not None, "speakers table should exist"
    conn.close()

@pytest.mark.unit
def test_migration_checksum_drift(tmp_path):
    db_file = str(tmp_path / "test.db")
    
    # Create fake migrations directory
    fake_migrations_dir = tmp_path / "migrations"
    os.makedirs(fake_migrations_dir)
    
    m1_path = fake_migrations_dir / "001_first.sql"
    m1_path.write_text("CREATE TABLE foo (id INTEGER PRIMARY KEY);")
    
    # Run first migration
    applied = run_migrations(db_file, str(fake_migrations_dir))
    assert len(applied) == 1
    
    # Modify migration file
    m1_path.write_text("CREATE TABLE foo (id INTEGER PRIMARY KEY, extra TEXT);")
    
    # Run migrations again, should raise checksum ValueError
    with pytest.raises(ValueError) as exc_info:
        run_migrations(db_file, str(fake_migrations_dir))
        
    assert "Checksum drift detected" in str(exc_info.value)
