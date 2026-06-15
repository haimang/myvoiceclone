import os
import yaml
from typing import Dict, Any, Optional

def get_project_root() -> str:
    # Walk up from current file to find the root containing pyproject.toml
    curr = os.path.abspath(__file__)
    while True:
        parent = os.path.dirname(curr)
        if parent == curr:
            # Reached root of file system, fallback to CWD
            return os.getcwd()
        if os.path.exists(os.path.join(parent, "pyproject.toml")):
            return parent
        curr = parent

def load_yaml(filepath: str) -> Dict[str, Any]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Config file not found at {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def load_local_config() -> Dict[str, Any]:
    path = os.path.join(get_project_root(), "configs", "local.yaml")
    return load_yaml(path)

def load_models_config() -> Dict[str, Any]:
    path = os.path.join(get_project_root(), "configs", "models.yaml")
    return load_yaml(path)

def load_pipeline_config() -> Dict[str, Any]:
    path = os.path.join(get_project_root(), "configs", "pipelines", "preprocess.default.yaml")
    return load_yaml(path)


def _resolve_project_path(path: str) -> str:
    if not os.path.isabs(path):
        return os.path.join(get_project_root(), path)
    return path


def resolve_db_path(db_path: Optional[str] = None) -> str:
    """Resolve the SQLite DB path, honoring DB_PATH before local.yaml.

    V14 fix: Centralizes the db_path resolution logic previously duplicated between
    cli.py (lines 40-42) and api/dependencies.py (which was missing the resolution).
    Both CLI and API should call this function.
    """
    if db_path is None:
        config = load_local_config()
        db_path = os.environ.get("DB_PATH") or config.get("db_path", ".data/db/myvoiceclone.sqlite")
    return _resolve_project_path(db_path)


def resolve_artifact_root(artifact_root: Optional[str] = None) -> str:
    """Resolve artifact storage root, honoring ARTIFACT_ROOT before local.yaml."""
    if artifact_root is None:
        config = load_local_config()
        artifact_root = os.environ.get("ARTIFACT_ROOT") or config.get("artifact_root", ".data/artifacts")
    return _resolve_project_path(artifact_root)


def resolve_models_dir(models_dir: Optional[str] = None) -> str:
    """Resolve model storage root, honoring MODELS_DIR before local.yaml."""
    if models_dir is None:
        config = load_local_config()
        models_dir = os.environ.get("MODELS_DIR") or config.get("models_dir", ".data/models")
    return _resolve_project_path(models_dir)


def resolve_evidence_root(evidence_root: Optional[str] = None) -> str:
    """Resolve evidence storage root, honoring EVIDENCE_ROOT before local.yaml."""
    if evidence_root is None:
        config = load_local_config()
        evidence_root = os.environ.get("EVIDENCE_ROOT") or config.get("evidence_root", ".data/test-runs")
    return _resolve_project_path(evidence_root)


def resolve_mock_adapters(default: bool = True) -> bool:
    """Resolve MOCK_ADAPTERS as a runtime boolean flag."""
    config = load_local_config()
    value = os.environ.get("MOCK_ADAPTERS", config.get("mock_adapters", default))
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
