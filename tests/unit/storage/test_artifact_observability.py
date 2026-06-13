import pytest


@pytest.mark.unit
def test_artifact_metadata_observability_defaults(artifact_store, monkeypatch):
    monkeypatch.setenv("MOCK_ADAPTERS", "true")

    artifact = artifact_store.create_artifact(
        name="sample.wav",
        content=b"wav",
        artifact_type="rendered_audio",
        metadata_json={"tool": "unit-tool", "license": "test-only"},
    )

    assert artifact.metadata_json["adapter_mode"] == "mock"
    assert artifact.metadata_json["metric_source"] == "artifact"
    assert artifact.metadata_json["metadata_contract_version"] == "first-test-v1"
    assert artifact.metadata_json["tool"] == "unit-tool"
    assert artifact.metadata_json["license"] == "test-only"
