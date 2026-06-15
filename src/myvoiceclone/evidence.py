import argparse
import json
import os
import platform
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from myvoiceclone.config import (
    resolve_artifact_root,
    resolve_db_path,
    resolve_evidence_root,
    resolve_models_dir,
)
from myvoiceclone.ids import is_mvc_id, new_id
from myvoiceclone.storage.repositories import json_to_dict


DEFAULT_EVIDENCE_ROOT = resolve_evidence_root()
REQUIRED_EVIDENCE_FILES = [
    "manifest.json",
    "env.json",
    "commands.json",
    "db_summary.json",
    "artifact_manifest.json",
    "trace.json",
    "skips.json",
    "README.md",
]
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}


@dataclass
class EvidenceValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_run_id(prefix: str = "first-test") -> str:
    return new_id()


def _git_value(args: List[str], cwd: Optional[Path] = None) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unavailable"


def _json_write(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_query(conn: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    try:
        cur = conn.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error:
        return []


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    rows = _safe_query(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return bool(rows)


def _db_summary(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"db_path": str(db_path), "exists": False, "tables": {}}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables: Dict[str, Dict[str, Any]] = {}
        for table in [
            "jobs",
            "job_events",
            "artifacts",
            "recordings",
            "segments",
            "datasets",
            "model_runs",
            "eval_metrics",
            "reports",
            "release_gates",
            "policy_events",
        ]:
            if not _table_exists(conn, table):
                tables[table] = {"exists": False, "count": 0}
                continue
            count = _safe_query(conn, f"SELECT COUNT(*) AS count FROM {table};")[0]["count"]
            tables[table] = {"exists": True, "count": count}
        return {"db_path": str(db_path), "exists": True, "tables": tables}
    finally:
        conn.close()


def _artifact_manifest(db_path: Path, artifact_root: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"artifact_root": str(artifact_root), "artifacts": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "artifacts"):
            return {"artifact_root": str(artifact_root), "artifacts": []}
        rows = _safe_query(
            conn,
            """
            SELECT id, name, uri, sha256, bytes, artifact_type, kind,
                   parent_artifact_id, source_artifact_id, job_id, created_by_job_id,
                   metadata_json, created_at
            FROM artifacts
            ORDER BY created_at, id;
            """,
        )
        artifacts = []
        for row in rows:
            item = dict(row)
            item["metadata_json"] = json_to_dict(item.get("metadata_json"))
            item["absolute_path"] = str((artifact_root / item["uri"]).resolve()) if item.get("uri") else None
            artifacts.append(item)
        return {"artifact_root": str(artifact_root), "artifacts": artifacts}
    finally:
        conn.close()


def _trace_summary(db_path: Path, trace: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = trace.copy() if trace else {}
    if not db_path.exists():
        payload.setdefault("job_events", [])
        payload.setdefault("reports", [])
        payload.setdefault("release_gates", [])
        payload.setdefault("policy_events", [])
        return payload

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if "job_events" not in payload and _table_exists(conn, "job_events"):
            events = _safe_query(conn, "SELECT * FROM job_events ORDER BY created_at, id;")
            for event in events:
                event["metadata_json"] = json_to_dict(event.get("metadata_json"))
            payload["job_events"] = events
        if "reports" not in payload and _table_exists(conn, "reports"):
            reports = _safe_query(conn, "SELECT * FROM reports ORDER BY created_at, id;")
            for report in reports:
                report["summary_json"] = json_to_dict(report.get("summary_json"))
            payload["reports"] = reports
        if "release_gates" not in payload and _table_exists(conn, "release_gates"):
            gates = _safe_query(conn, "SELECT * FROM release_gates ORDER BY created_at, id;")
            for gate in gates:
                gate["details_json"] = json_to_dict(gate.get("details_json"))
                gate["decision_json"] = json_to_dict(gate.get("decision_json"))
            payload["release_gates"] = gates
        if "policy_events" not in payload and _table_exists(conn, "policy_events"):
            events = _safe_query(conn, "SELECT * FROM policy_events ORDER BY created_at, id;")
            for event in events:
                event["details_json"] = json_to_dict(event.get("details_json"))
            payload["policy_events"] = events
        return payload
    finally:
        conn.close()


def collect_evidence_pack(
    *,
    run_id: Optional[str] = None,
    output_root: Optional[str] = None,
    db_path: Optional[str] = None,
    artifact_root: Optional[str] = None,
    commands: Optional[List[Dict[str, Any]]] = None,
    trace: Optional[Dict[str, Any]] = None,
    skip_reason: Optional[str] = None,
    adapter_mode: str = "real",
    status: str = "collected",
) -> Path:
    run_id = run_id if is_mvc_id(run_id) else default_run_id()
    output_dir = Path(output_root or DEFAULT_EVIDENCE_ROOT) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    db = Path(db_path or resolve_db_path()).expanduser()
    artifacts = Path(artifact_root or resolve_artifact_root()).expanduser()
    models_dir = Path(resolve_models_dir()).expanduser()
    skipped = bool(skip_reason)
    command_entries = commands or []
    timestamp = utc_now()

    manifest = {
        "run_id": run_id,
        "status": "skipped" if skipped else status,
        "adapter_mode": adapter_mode,
        "created_at": timestamp,
        "db_path": str(db),
        "artifact_root": str(artifacts),
        "skip_denominator": {"live": 1 if skipped else 0, "reasons": [skip_reason] if skip_reason else []},
        "files": REQUIRED_EVIDENCE_FILES,
    }
    env = {
        "created_at": timestamp,
        "cwd": os.getcwd(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_value(["rev-parse", "--short", "HEAD"]),
        "git_status_short": _git_value(["status", "--short"]),
        "env": {
            key: os.getenv(key)
            for key in [
                "DB_PATH",
                "ARTIFACT_ROOT",
                "MODELS_DIR",
                "EVIDENCE_ROOT",
                "MOCK_ADAPTERS",
                "RUN_LIVE_HTTP",
                "RUN_FIRST_TEST_CAPSTONE",
                "FIRST_TEST_AUDIO_PATH",
            ]
            if os.getenv(key) is not None
        },
        "resolved": {
            "DB_PATH": str(db),
            "ARTIFACT_ROOT": str(artifacts),
            "MODELS_DIR": str(models_dir),
            "EVIDENCE_ROOT": str(Path(output_root or DEFAULT_EVIDENCE_ROOT).expanduser()),
        },
    }
    skips = {"skipped": skipped, "reason": skip_reason, "denominator": manifest["skip_denominator"]}

    _json_write(output_dir / "manifest.json", manifest)
    _json_write(output_dir / "env.json", env)
    _json_write(output_dir / "commands.json", {"commands": command_entries})
    _json_write(output_dir / "db_summary.json", _db_summary(db))
    _json_write(output_dir / "artifact_manifest.json", _artifact_manifest(db, artifacts))
    _json_write(output_dir / "trace.json", _trace_summary(db, trace))
    _json_write(output_dir / "skips.json", skips)
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                f"# first-test evidence pack: {run_id}",
                "",
                f"- status: `{manifest['status']}`",
                f"- adapter_mode: `{adapter_mode}`",
                f"- db_path: `{db}`",
                f"- artifact_root: `{artifacts}`",
                f"- skip_reason: `{skip_reason or 'N/A'}`",
                "",
                "This folder stores lightweight evidence only. Real audio/model artifacts stay in the artifact root and are referenced by manifest paths.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_dir


def validate_evidence_pack(pack_dir: str, *, repo_root: Optional[str] = None, max_repo_audio_bytes: int = 5 * 1024 * 1024) -> EvidenceValidationResult:
    root = Path(pack_dir)
    errors: List[str] = []
    warnings: List[str] = []
    for filename in REQUIRED_EVIDENCE_FILES:
        if not (root / filename).exists():
            errors.append(f"missing required evidence file: {filename}")

    def read_json(filename: str, default: Dict[str, Any]) -> Dict[str, Any]:
        path = root / filename
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in {filename}: {exc}")
            return default

    manifest = read_json("manifest.json", {})
    artifacts = read_json("artifact_manifest.json", {"artifacts": []})
    trace = read_json("trace.json", {})
    skips = read_json("skips.json", {"skipped": False})

    skipped = bool(skips.get("skipped") or manifest.get("status") == "skipped")
    skip_reason = skips.get("reason")
    if skipped and not skip_reason:
        errors.append("skipped evidence pack must include a skip reason")
    if not skipped and not artifacts.get("artifacts"):
        errors.append("non-skipped evidence pack has an empty artifact manifest")

    declared_real = manifest.get("adapter_mode") == "real"
    for artifact in artifacts.get("artifacts", []):
        metadata = artifact.get("metadata_json") or {}
        if declared_real and metadata.get("adapter_mode") == "mock":
            errors.append(f"mock artifact appears in real evidence pack: {artifact.get('id')}")
        if declared_real and metadata.get("metric_source") == "mock":
            errors.append(f"mock metric source appears in real evidence pack: {artifact.get('id')}")

        absolute_path = artifact.get("absolute_path")
        if repo_root and absolute_path:
            try:
                resolved = Path(absolute_path).resolve()
                repo = Path(repo_root).resolve()
                if resolved.is_relative_to(repo) and artifact.get("bytes", 0) > max_repo_audio_bytes:
                    errors.append(f"large artifact is inside repo: {resolved}")
            except OSError:
                warnings.append(f"artifact path could not be resolved: {absolute_path}")

    trace_counts = sum(len(trace.get(key) or []) for key in ["trace_events", "job_events", "reports", "release_gates", "policy_events"])
    if not skipped and trace_counts == 0:
        errors.append("non-skipped evidence pack has no trace events/reports/release gates")

    if repo_root:
        repo = Path(repo_root)
        ignored = {".git", "venv", ".venv", "__pycache__", ".pytest_cache"}
        for path in repo.rglob("*"):
            if any(part in ignored for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                try:
                    if path.stat().st_size > max_repo_audio_bytes:
                        errors.append(f"large audio file found inside repo: {path}")
                except OSError:
                    warnings.append(f"repo file could not be inspected: {path}")

    return EvidenceValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _main() -> int:
    parser = argparse.ArgumentParser(description="Collect or validate myvoiceclone first-test evidence packs.")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect")
    collect.add_argument("--run-id")
    collect.add_argument("--output-root")
    collect.add_argument("--db-path")
    collect.add_argument("--artifact-root")
    collect.add_argument("--skip-reason")
    collect.add_argument("--adapter-mode", default="real")
    collect.add_argument("--status", default="collected")

    validate = sub.add_parser("validate")
    validate.add_argument("pack_dir")
    validate.add_argument("--repo-root")
    validate.add_argument("--max-repo-audio-bytes", type=int, default=5 * 1024 * 1024)

    args = parser.parse_args()
    if args.command == "collect":
        path = collect_evidence_pack(
            run_id=args.run_id,
            output_root=args.output_root,
            db_path=args.db_path,
            artifact_root=args.artifact_root,
            skip_reason=args.skip_reason,
            adapter_mode=args.adapter_mode,
            status=args.status,
        )
        print(path)
        return 0

    result = validate_evidence_pack(args.pack_dir, repo_root=args.repo_root, max_repo_audio_bytes=args.max_repo_audio_bytes)
    print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings}, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
