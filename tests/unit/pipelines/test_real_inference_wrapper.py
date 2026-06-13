import os

import pytest

from myvoiceclone.pipelines.infer_real import RealInferenceRequest, run_real_inference, validate_inference_request


class FakeRealXttsAdapter:
    def synth_to_file(self, text, reference_wav, output_path, *, language="en"):
        assert os.path.exists(reference_wav)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"RIFFfake-real-wav")
        return {
            "adapter_mode": "real",
            "duration_sec": 1.25,
            "tool": "coqui-tts",
            "model": "tts_models/multilingual/multi-dataset/xtts_v2",
            "device": "cpu",
            "cache": "/models",
            "license": "Coqui Public Model License",
            "source": "https://huggingface.co/coqui/XTTS-v2",
            "version": "test",
        }


@pytest.mark.unit
def test_inference_contract_requires_text_and_reference():
    with pytest.raises(ValueError, match="text"):
        validate_inference_request(RealInferenceRequest(text="", reference_artifact_id="art_ref"))
    with pytest.raises(ValueError, match="reference_artifact_id"):
        validate_inference_request(RealInferenceRequest(text="hello", reference_artifact_id=""))


@pytest.mark.unit
def test_inference_contract_rejects_unsupported_model_id():
    with pytest.raises(ValueError, match="Unsupported first-test real inference model_id"):
        validate_inference_request(
            RealInferenceRequest(text="hello", reference_artifact_id="art_ref", model_id="rvc/non_xtts")
        )


@pytest.mark.unit
def test_real_inference_wrapper_writes_artifact_metadata(db_conn, artifact_store):
    db_conn.execute(
        """
        INSERT INTO jobs (id, name, status, payload_json)
        VALUES ('job_infer', 'infer_real', 'running', '{}');
        """
    )
    db_conn.commit()
    reference = artifact_store.create_artifact(
        name="reference.wav",
        content=b"RIFFreference",
        artifact_type="cleaned",
        metadata_json={"adapter_mode": "real", "tool": "demucs"},
    )

    artifact = run_real_inference(
        db_conn,
        artifact_store,
        RealInferenceRequest(
            text="hello world",
            reference_artifact_id=reference.id,
            source_artifact_id="art_source",
            config={"seed": 1},
        ),
        adapter=FakeRealXttsAdapter(),
        job_id="job_infer",
    )

    assert artifact.artifact_type == "rendered_audio"
    assert artifact.parent_artifact_id == reference.id
    assert artifact.metadata_json["adapter_mode"] == "real"
    assert artifact.metadata_json["model"] == "tts_models/multilingual/multi-dataset/xtts_v2"
    assert artifact.metadata_json["input_refs"]["reference_artifact_id"] == reference.id
    assert artifact.metadata_json["license"] == "Coqui Public Model License"
    assert artifact.metadata_json["duration_sec"] == 1.25


@pytest.mark.unit
def test_real_inference_rejects_non_reference_artifact_kind(db_conn, artifact_store):
    uploaded = artifact_store.create_artifact(
        name="upload.wav",
        content=b"RIFFupload",
        artifact_type="uploaded_audio",
        metadata_json={"adapter_mode": "real"},
    )

    with pytest.raises(ValueError, match="unsupported kind"):
        run_real_inference(
            db_conn,
            artifact_store,
            RealInferenceRequest(text="hello", reference_artifact_id=uploaded.id),
            adapter=FakeRealXttsAdapter(),
        )
