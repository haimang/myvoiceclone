import os
import yaml
from typing import Dict, Any

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


def resolve_db_path(db_path: str = None) -> str:
    """Resolve a db_path (possibly relative) to an absolute path from project root.

    V14 fix: Centralizes the db_path resolution logic previously duplicated between
    cli.py (lines 40-42) and api/dependencies.py (which was missing the resolution).
    Both CLI and API should call this function.
    """
    if db_path is None:
        config = load_local_config()
        db_path = config.get("db_path", "db/myvoiceclone.sqlite")
    if not os.path.isabs(db_path):
        db_path = os.path.join(get_project_root(), db_path)
    return db_path

