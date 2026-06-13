import os
import pytest
from typer.testing import CliRunner
from myvoiceclone.cli import app
from myvoiceclone.config import get_project_root

runner = CliRunner()

@pytest.mark.unit
def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "MyVoiceClone CLI" in result.output

@pytest.mark.unit
def test_cli_init_db(tmp_path):
    db_file = tmp_path / "cli_test.db"
    result = runner.invoke(app, ["init-db", "--db", str(db_file)])
    assert result.exit_code == 0
    assert "Initializing database" in result.output
    assert os.path.exists(str(db_file))

@pytest.mark.unit
def test_cli_vec_health_error(monkeypatch):
    import sqlite3
    def mock_get_connection(*args, **kwargs):
        raise sqlite3.OperationalError("Mocked load extension failure")
    monkeypatch.setattr("myvoiceclone.cli.get_connection", mock_get_connection)
    
    result = runner.invoke(app, ["vec-health"])
    assert result.exit_code == 1
    assert "Error" in result.output

@pytest.mark.unit
def test_cli_ingest_dry_run():
    result = runner.invoke(app, ["ingest", "fake_path.wav", "--dry-run"])
    assert result.exit_code == 0
    assert "[Dry-run] Would ingest" in result.output
