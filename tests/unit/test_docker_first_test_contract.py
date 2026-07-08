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
    voiceclone = read("infra/docker/Dockerfile.ai-voiceclone")

    assert "COPY db/migrations ./db/migrations" in preprocess
    assert "COPY db/migrations ./db/migrations" in train
    assert "COPY db/migrations ./db/migrations" in voiceclone


@pytest.mark.unit
def test_train_dockerfile_does_not_reinstall_unconstrained_torchaudio():
    train = read("infra/docker/Dockerfile.train")

    assert ".[cli,db,api,audio]" not in train
    assert ".[cli,db,api]" in train
    assert "soundfile" in train


@pytest.mark.unit
def test_ai_voiceclone_dockerfile_is_dedicated_runtime():
    voiceclone = read("infra/docker/Dockerfile.ai-voiceclone")

    assert "FROM docker-train:latest" not in voiceclone
    assert "ai-voiceclone" in voiceclone
    assert "ai-voiceclone-base:cu130" in voiceclone
    assert "COPY tests ./tests" in voiceclone
    assert "COPY docs ./docs" in voiceclone
    assert ".[cli,db,api,test]" in voiceclone
    assert 'EXPOSE 658' in voiceclone
    assert '"--port", "658"' in voiceclone


@pytest.mark.unit
def test_compose_mounts_configs_readonly_and_evidence_root():
    compose = read("infra/docker/compose.yaml")

    assert "../../configs:/app/configs:ro" in compose
    assert "runtime: nvidia" in compose
    assert ".data/db:/app/db" in compose
    assert ".data/artifacts:/app/data/artifacts" in compose
    assert ".data/models:/app/models" in compose
    assert ".data/test-runs:/app/test-runs" in compose
    assert "MOCK_ADAPTERS=${MOCK_ADAPTERS:-false}" in compose


@pytest.mark.unit
def test_ai_voiceclone_compose_exposes_only_658():
    compose = read("infra/docker/compose.voiceclone.yaml")

    assert "container_name: ai-voiceclone" in compose
    assert "image: ai-voiceclone:cu130" in compose
    assert "dockerfile: infra/docker/Dockerfile.ai-voiceclone" in compose
    assert "ai-voiceclone-base:cu130" in compose
    assert '"658:658"' in compose
    for forbidden in ['"22:', '"668:', '"669:', '"670:', "docker-train"]:
        assert forbidden not in compose
    assert ".data/db:/app/.data/db" in compose
    assert ".data/artifacts:/app/data/artifacts" in compose
    assert ".data/models:/app/models" in compose
    assert ".data/test-runs:/app/test-runs" in compose
    assert "../../configs:/app/configs:ro" in compose
    assert "../../.git:/app/.git:ro" in compose
    assert "runtime: nvidia" in compose


@pytest.mark.unit
def test_dockerignore_excludes_heavy_local_artifacts_but_keeps_migrations():
    dockerignore = read(".dockerignore")

    for pattern in [".git/", "venv/", ".venv/", ".data/", "*.wav", "*.pt", "*.ckpt"]:
        assert pattern in dockerignore
    assert "data/" not in dockerignore.splitlines()
    assert "models/" not in dockerignore.splitlines()
    assert "!db/migrations/" in dockerignore
