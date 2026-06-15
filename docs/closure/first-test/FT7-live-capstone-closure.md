# [FT7 / Live Capstone Evidence] Closure

> 阶段: `first-test/FT7 — Live tests、capstone 与 evidence pack`
> 范围: `FT7-P1..P3`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT7-live-capstone.md`
> 关联 evidence: `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT7 marker policy、FT1-FT6 pre-capstone gate、evidence exporter、validator 与 live capstone gated harness 已完成；本机未提供 `RUN_FIRST_TEST_CAPSTONE=1`/真实音频/模型缓存，因此 live capstone 以明确 skip reason 收口，真实闭环仍待 owner live 环境验证。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT7-P1-01 marker taxonomy and denominator | ✅ closed | `uncommitted working tree on HEAD {HEAD}` + `tests/unit/test_pytest_markers.py` + `2026-06-13 08:53 UTC` |
| FT7-P1-02 FT1-FT6 required test gate | ✅ closed | `uncommitted working tree on HEAD {HEAD}` + `tests/integration/test_first_test_capstone.py::test_first_test_capstone_requires_ft1_ft6_closures` + `2026-06-13 08:53 UTC` |
| FT7-P2-01 evidence exporter | ✅ closed | `uncommitted working tree on HEAD {HEAD}` + `tests/unit/test_first_test_evidence_validator.py::test_evidence_exporter_writes_required_files` + `2026-06-13 08:53 UTC` |
| FT7-P2-02 evidence validator | ✅ closed | `uncommitted working tree on HEAD {HEAD}` + `tests/unit/test_first_test_evidence_validator.py` + `2026-06-13 08:53 UTC` |
| FT7-P3-01 API capstone live chain | ⏸ pending | `uncommitted working tree on HEAD {HEAD}` + `tests/integration/test_first_test_capstone.py -m live -q -rs` -> `1 skipped: RUN_FIRST_TEST_CAPSTONE=1 is required...` + `2026-06-13 08:53 UTC` |
| FT7-P3-02 capstone trace/evidence indexing | ✅ closed | `uncommitted working tree on HEAD {HEAD}` + `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z/manifest.json` + `2026-06-13 08:53 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT7 targeted tests | `./venv/bin/python -m pytest tests/unit/test_pytest_markers.py tests/unit/test_first_test_evidence_validator.py tests/integration/test_first_test_capstone.py -q` | `8 passed, 1 deselected` | FT7-T01/T02/T04/T05 |
| FT7 live capstone gated | `./venv/bin/python -m pytest tests/integration/test_first_test_capstone.py -m live -q -rs` | `1 skipped, 1 deselected` with explicit reason | FT7-T03 denominator |
| Evidence pack export | `SKIP_REASON='RUN_FIRST_TEST_CAPSTONE=1 is required for live first-test capstone' RUN_ID='first-test-capstone-skipped-20260613T0850Z' ./scripts/collect_first_test_evidence.sh` | validator `ok=true` | FT7-P2/P3 indexing |
| FT1-FT7/default regression | `./venv/bin/python -m pytest -q` | `134 passed, 1 skipped, 2 deselected, 14 warnings` | all default unit/api/cli/integration tests |
| Syntax check | `./venv/bin/python -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| marker policy | live/gpu/slow markers exist and are not in default addopts | marker test pass | ✅ PASS |
| pre-capstone closure gate | FT1-FT6 closure files exist | integration gate pass | ✅ PASS |
| evidence exporter | required files generated under run folder | exporter test + shell run pass | ✅ PASS |
| evidence validator | rejects bad evidence classes | validator unit tests pass | ✅ PASS |
| live capstone | real audio/model/API chain executed | skipped; no owner live env | ⏸ PENDING |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Real live capstone execution | C | harness and skipped evidence complete; no live env | rerun with `RUN_FIRST_TEST_CAPSTONE=1`, legal `FIRST_TEST_AUDIO_PATH`, model/cache/token config | owner / next live runner |
| Multi-GPU / soak validation | A | out of first-test scope | long-running training or production SLO appears | future owner |
| Full production observability platform | A | out of first-test scope; evidence JSON used | multi-service tracing target appears | future owner |
| Non-skipped evidence pack with real artifacts | C | validator enforces it, but current pack is skipped | owner live run produces real artifacts/trace | FT8/future owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure` for marker/exporter/validator/gate；live capstone is `deferred/pending` |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `uncommitted working tree on HEAD {HEAD}`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ FT7 改动集中在 evidence module/script/tests 与阶段文档 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| ✅ live capstone 明确 pending |
