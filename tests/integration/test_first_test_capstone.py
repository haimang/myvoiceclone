import os

import pytest

from myvoiceclone.evidence import collect_evidence_pack, validate_evidence_pack


REQUIRED_CLOSURES = [
    "FT1-preflight-closure.md",
    "FT2-schema-observability-closure.md",
    "FT3-real-preprocess-closure.md",
    "FT4-real-inference-closure.md",
    "FT5-real-evaluation-closure.md",
    "FT6-fastapi-e2e-closure.md",
]


@pytest.mark.integration
def test_first_test_capstone_requires_ft1_ft6_closures():
    missing = [
        filename
        for filename in REQUIRED_CLOSURES
        if not os.path.exists(os.path.join("docs", "closure", "first-test", filename))
    ]

    assert missing == []


@pytest.mark.live
def test_first_test_live_capstone_gated(tmp_path):
    if os.getenv("RUN_FIRST_TEST_CAPSTONE") != "1":
        reason = "RUN_FIRST_TEST_CAPSTONE=1 is required for live first-test capstone"
        output_root = os.getenv("EVIDENCE_ROOT", str(tmp_path / "test-runs"))
        pack = collect_evidence_pack(
            run_id="first-test-capstone-skipped",
            output_root=output_root,
            skip_reason=reason,
            commands=[{"cmd": "pytest -m live tests/integration/test_first_test_capstone.py", "status": "skipped"}],
        )
        result = validate_evidence_pack(str(pack), repo_root=os.getcwd())
        assert result.ok, result.errors
        pytest.skip(reason)

    audio_path = os.getenv("FIRST_TEST_AUDIO_PATH")
    if not audio_path or not os.path.exists(audio_path):
        reason = "FIRST_TEST_AUDIO_PATH must point to a legal short audio sample"
        output_root = os.getenv("EVIDENCE_ROOT", str(tmp_path / "test-runs"))
        pack = collect_evidence_pack(run_id="first-test-capstone-skipped", output_root=output_root, skip_reason=reason)
        result = validate_evidence_pack(str(pack), repo_root=os.getcwd())
        assert result.ok, result.errors
        pytest.skip(reason)

    reason = "live real-model capstone execution requires owner-provided model/cache/token configuration"
    output_root = os.getenv("EVIDENCE_ROOT", str(tmp_path / "test-runs"))
    pack = collect_evidence_pack(run_id="first-test-capstone-skipped", output_root=output_root, skip_reason=reason)
    result = validate_evidence_pack(str(pack), repo_root=os.getcwd())
    assert result.ok, result.errors
    pytest.skip(reason)
