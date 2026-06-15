import os
import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from myvoiceclone.api.dependencies import get_db
from myvoiceclone.api.schemas import ArtifactResponse
from myvoiceclone.config import resolve_artifact_root
from myvoiceclone.errors import ResourceNotFoundError, ValidationError
from myvoiceclone.storage.artifact_store import ArtifactStore

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _get_artifact_or_404(db: sqlite3.Connection, artifact_id: str):
    store = ArtifactStore(db, resolve_artifact_root())
    artifact = store.get_artifact(artifact_id)
    if not artifact:
        raise ResourceNotFoundError("Artifact not found", code="artifact_not_found", detail={"artifact_id": artifact_id})
    return store, artifact


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: str, db: sqlite3.Connection = Depends(get_db)):
    _, artifact = _get_artifact_or_404(db, artifact_id)
    return artifact


@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: str, db: sqlite3.Connection = Depends(get_db)):
    store, artifact = _get_artifact_or_404(db, artifact_id)
    root = os.path.abspath(store.root_dir)
    path = os.path.abspath(store.get_absolute_path(artifact))
    if not path.startswith(root + os.sep) and path != root:
        raise ValidationError("Artifact path is outside artifact root", code="download_not_found")
    if not os.path.exists(path) or not os.path.isfile(path):
        raise ResourceNotFoundError("Artifact file not found", code="download_not_found", detail={"artifact_id": artifact_id})
    return FileResponse(path, media_type="application/octet-stream", filename=artifact.name or os.path.basename(path))
