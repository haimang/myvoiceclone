import os
import pytest
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations
from myvoiceclone.storage.repositories import ReportRepository
from myvoiceclone.domain.entities import Report

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
def test_reports_schema_crud(db_conn):
    repo = ReportRepository(db_conn)
    
    report = Report(
        id="rpt_123",
        name="Preprocess Audit Report",
        report_type="audit",
        summary_json={"duration_total_sec": 7200.0, "speakers_count": 3},
        artifact_id=None
    )
    
    # Save report
    repo.save(report)
    db_conn.commit()
    
    # Retrieve report
    retrieved = repo.get_by_id("rpt_123")
    assert retrieved is not None
    assert retrieved.name == "Preprocess Audit Report"
    assert retrieved.report_type == "audit"
    assert retrieved.summary_json == {"duration_total_sec": 7200.0, "speakers_count": 3}
    assert retrieved.created_at is not None
