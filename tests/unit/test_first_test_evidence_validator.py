import json
import os
import sqlite3

import pytest

from myvoiceclone.evidence import collect_evidence_pack, validate_evidence_pack


@pytest.mark.unit
def test_evidence_exporter_writes_required_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    pack = collect_evidence_pack(
        run_id="run_skipped",
        output_root=str(tmp_path / "runs"),
        skip_reason="RUN_FIRST_TEST_CAPSTONE=1 is required",
    )

    expected = {
        "manifest.json",
        "env.json",
        "commands.json",
        "db_summary.json",
        "artifact_manifest.json",
        "trace.json",
        "skips.json",
        "README.md",
    }
    assert expected <= {path.name for path in pack.iterdir()}
    result = validate_evidence_pack(str(pack), repo_root=str(tmp_path))
    assert result.ok, result.errors


@pytest.mark.unit
def test_validator_rejects_skip_without_reason(tmp_path):
    pack = collect_evidence_pack(run_id="bad_skip", output_root=str(tmp_path / "runs"), skip_reason="missing model")
    skips = json.loads((pack / "skips.json").read_text(encoding="utf-8"))
    skips["reason"] = ""
    (pack / "skips.json").write_text(json.dumps(skips), encoding="utf-8")

    result = validate_evidence_pack(str(pack))

    assert not result.ok
    assert any("skip reason" in error for error in result.errors)


@pytest.mark.unit
def test_validator_rejects_empty_non_skipped_pack(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    pack = collect_evidence_pack(run_id="empty_real", output_root=str(tmp_path / "runs"))

    result = validate_evidence_pack(str(pack))

    assert not result.ok
    assert any("empty artifact manifest" in error for error in result.errors)
    assert any("no trace" in error for error in result.errors)


@pytest.mark.unit
def test_validator_rejects_mock_artifact_in_real_pack(tmp_path):
    db_path = tmp_path / "db.sqlite"
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE artifacts (
            id TEXT, name TEXT, uri TEXT, sha256 TEXT, bytes INTEGER,
            artifact_type TEXT, kind TEXT, parent_artifact_id TEXT, source_artifact_id TEXT,
            job_id TEXT, created_by_job_id TEXT, metadata_json TEXT, created_at TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE job_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT, event_type TEXT, metadata_json TEXT, created_at TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT INTO artifacts
        VALUES ('art_1', 'fake.wav', 'rendered_audio/fake.wav', 'sha', 10, 'rendered_audio',
                'rendered_audio', NULL, NULL, 'job_1', 'job_1',
                '{"adapter_mode":"mock","metric_source":"mock"}', '2026-06-13T00:00:00Z');
        """
    )
    conn.execute("INSERT INTO job_events (job_id, event_type, metadata_json, created_at) VALUES ('job_1', 'complete', '{}', '2026-06-13T00:00:00Z');")
    conn.commit()
    conn.close()

    pack = collect_evidence_pack(
        run_id="mock_real",
        output_root=str(tmp_path / "runs"),
        db_path=str(db_path),
        artifact_root=str(artifact_root),
        adapter_mode="real",
    )

    result = validate_evidence_pack(str(pack), repo_root=str(tmp_path))

    assert not result.ok
    assert any("mock artifact" in error for error in result.errors)
    assert any("mock metric source" in error for error in result.errors)


@pytest.mark.unit
def test_validator_rejects_large_repo_audio(tmp_path):
    audio = tmp_path / "real.wav"
    audio.write_bytes(b"0" * 32)
    pack = collect_evidence_pack(
        run_id="skipped",
        output_root=str(tmp_path / "runs"),
        skip_reason="external model cache missing",
    )

    result = validate_evidence_pack(str(pack), repo_root=str(tmp_path), max_repo_audio_bytes=16)

    assert not result.ok
    assert any("large audio file" in error for error in result.errors)


@pytest.mark.unit
def test_collect_first_test_evidence_script_contract():
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "scripts", "collect_first_test_evidence.sh")
    text = open(script, encoding="utf-8").read()

    assert "myvoiceclone.evidence collect" in text
    assert "myvoiceclone.evidence validate" in text
    assert "/mnt/usb/workspace/myvoiceresearch/test-runs" in text
