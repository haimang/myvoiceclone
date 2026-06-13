import os

import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def read(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as handle:
        return handle.read()


@pytest.mark.unit
def test_dockerfiles_include_db_migrations_for_init_db():
    preprocess = read("infra/docker/Dockerfile.preprocess")
    train = read("infra/docker/Dockerfile.train")

    assert "COPY db/migrations ./db/migrations" in preprocess
    assert "COPY db/migrations ./db/migrations" in train


@pytest.mark.unit
def test_train_dockerfile_does_not_reinstall_unconstrained_torchaudio():
    train = read("infra/docker/Dockerfile.train")

    assert ".[cli,db,api,audio]" not in train
    assert ".[cli,db,api]" in train
    assert "soundfile" in train


@pytest.mark.unit
def test_compose_mounts_configs_readonly_and_evidence_root():
    compose = read("infra/docker/compose.yaml")

    assert "../../configs:/app/configs:ro" in compose
    assert "/mnt/usb/workspace/myvoiceresearch/test-runs:/mnt/usb/workspace/myvoiceresearch/test-runs" in compose
    assert "runtime: nvidia" in compose


@pytest.mark.unit
def test_dockerignore_excludes_heavy_local_artifacts_but_keeps_migrations():
    dockerignore = read(".dockerignore")

    for pattern in [".git/", "venv/", ".venv/", "data/", "models/", "*.wav", "*.pt", "*.ckpt"]:
        assert pattern in dockerignore
    assert "!db/migrations/" in dockerignore
