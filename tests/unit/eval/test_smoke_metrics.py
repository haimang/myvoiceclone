import pytest

from myvoiceclone.eval.smoke import evaluate_wav_smoke


@pytest.mark.unit
def test_smoke_metrics_for_wav_fixture(artifact_store, synthetic_wav):
    metrics = evaluate_wav_smoke(artifact_store, filepath=synthetic_wav, transcript="hello")

    assert metrics["metric_source"] == "smoke_metric"
    assert metrics["duration_sec"] == 1.0
    assert metrics["sample_rate"] == 16000
    assert metrics["channels"] == 1
    assert metrics["transcript_sanity"] is True
    assert metrics["quality_gate_eligible"] is True


@pytest.mark.unit
def test_smoke_metrics_transcript_sanity_failure(artifact_store, synthetic_wav):
    metrics = evaluate_wav_smoke(artifact_store, filepath=synthetic_wav, transcript=" ")

    assert metrics["transcript_sanity"] is False
    assert metrics["smoke_pass"] is False
