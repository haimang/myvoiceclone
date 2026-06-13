import os
import re
import subprocess

import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FIRST_TEST_CLOSURE_DIR = os.path.join(REPO_ROOT, "docs", "closure", "first-test")


def read_doc(*parts):
    path = os.path.join(REPO_ROOT, *parts)
    with open(path, encoding="utf-8") as handle:
        return path, handle.read()


@pytest.mark.unit
def test_first_test_closure_docs_exist():
    required = [
        "FT1-preflight-closure.md",
        "FT2-schema-observability-closure.md",
        "FT3-real-preprocess-closure.md",
        "FT4-real-inference-closure.md",
        "FT5-real-evaluation-closure.md",
        "FT6-fastapi-e2e-closure.md",
        "FT7-live-capstone-closure.md",
        "FT8-closure-deferred-closure.md",
        "first-test-closure.md",
        "deferred-items-ledger.md",
    ]

    missing = [name for name in required if not os.path.exists(os.path.join(FIRST_TEST_CLOSURE_DIR, name))]

    assert missing == []


@pytest.mark.unit
def test_first_test_deferred_items_have_triggers_and_targets():
    _, text = read_doc("docs", "closure", "first-test", "deferred-items-ledger.md")

    for item_id in [f"FTD-{idx:02d}" for idx in range(1, 11)]:
        assert item_id in text
    assert text.count("触发器") >= 10
    assert text.count("目标阶段") >= 10
    assert "pending-live" in text
    assert "RUN_FIRST_TEST_CAPSTONE=1" in text


@pytest.mark.unit
def test_first_build_reconciliation_snapshot_exists():
    _, text = read_doc("docs", "closure", "first-build", "deferred-items-ledger.md")

    assert "first-test reconciliation snapshot" in text
    for item_id in [f"DEF-{idx:02d}" for idx in range(1, 16)]:
        assert item_id in text
    assert "retained" in text
    assert "partially closed" in text


@pytest.mark.unit
def test_final_input_pack_references_existing_repo_files():
    _, text = read_doc("docs", "eval", "first-test", "final-input-pack.md")
    refs = sorted(set(re.findall(r"`((?:docs|src|tests|scripts)/[^`]+)`", text)))
    missing = []
    for ref in refs:
        path = ref.split("#", 1)[0]
        if not os.path.exists(os.path.join(REPO_ROOT, path)):
            missing.append(ref)

    assert missing == []
    assert "tests/api/contracts/first_test_run_create.json" in text
    assert "src/myvoiceclone/evidence.py" in text
    assert "/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z" in text


@pytest.mark.unit
def test_first_test_overall_closure_matches_live_pending_evidence():
    _, text = read_doc("docs", "closure", "first-test", "first-test-closure.md")

    assert "Close-type: `implementation-complete-awaiting-live-verification`" in text
    assert "不是 `full-close`" in text
    assert "pending-live" in text


@pytest.mark.unit
def test_first_test_closure_head_anchors_match_current_head():
    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    stale = []
    for name in os.listdir(FIRST_TEST_CLOSURE_DIR):
        if not name.endswith(".md"):
            continue
        path = os.path.join(FIRST_TEST_CLOSURE_DIR, name)
        text = open(path, encoding="utf-8").read()
        for match in re.findall(r"HEAD ([0-9a-f]{7,12})", text):
            if match != head:
                stale.append((name, match))

    assert stale == []
