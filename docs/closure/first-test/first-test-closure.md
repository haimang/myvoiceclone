# [first-test / FT1-FT8] Closure

> 阶段: `first-test/FT1-FT8 — first-test implementation, evidence, deferred reconciliation`
> 范围: `FT1-preflight` through `FT8-closure-deferred`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/index.md`
> 关联 evidence: `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT1-FT8 的代码、API、测试、evidence exporter 和 closure/deferred 台账已按 DAG 完成；默认测试全绿，但 FT7 live capstone 只有 skipped evidence，因此 first-test 真实 close type 是 `implementation-complete-awaiting-live-verification`，不是 `full-close`。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `RUN_FIRST_TEST_CAPSTONE=1` 的真实音频/模型/cache live capstone 未在本机执行。
> 2. 当前 evidence pack 是 skipped pack，不含非空真实 artifact manifest/trace。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT1 preflight | ✅ closed | `working tree @ 4e4ca3b` + `docs/closure/first-test/FT1-preflight-closure.md` + `2026-06-13 08:26 UTC` |
| FT2 schema observability | ✅ closed | `working tree @ 4e4ca3b` + `docs/closure/first-test/FT2-schema-observability-closure.md` + `2026-06-13 08:32 UTC` |
| FT3 real preprocess contract | ✅ closed | `working tree @ 4e4ca3b` + `docs/closure/first-test/FT3-real-preprocess-closure.md` + `2026-06-13 08:35 UTC` |
| FT4 real inference substrate | ✅ closed | `working tree @ 4e4ca3b` + `docs/closure/first-test/FT4-real-inference-closure.md` + `2026-06-13 08:38 UTC` |
| FT5 real evaluation gate | ✅ closed | `working tree @ 4e4ca3b` + `docs/closure/first-test/FT5-real-evaluation-closure.md` + `2026-06-13 08:41 UTC` |
| FT6 FastAPI e2e surface | ✅ closed | `working tree @ 4e4ca3b` + `docs/closure/first-test/FT6-fastapi-e2e-closure.md` + `2026-06-13 08:47 UTC` |
| FT7 live capstone evidence | ⏸ pending-live | `working tree @ 4e4ca3b` + `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z` + `2026-06-13 08:53 UTC` |
| FT8 closure/deferred reconciliation | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/test_first_test_closure_docs.py` + `2026-06-13 08:57 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT1-FT7/default regression | `./venv/bin/python -m pytest -q` | `134 passed, 1 skipped, 2 deselected, 14 warnings` | all default unit/api/cli/integration tests after FT7 |
| FT7 evidence validation | `SKIP_REASON='RUN_FIRST_TEST_CAPSTONE=1 is required for live first-test capstone' RUN_ID='first-test-capstone-skipped-20260613T0850Z' ./scripts/collect_first_test_evidence.sh` | validator `ok=true` | evidence pack shape and skip denominator |
| FT7 live capstone marker | `./venv/bin/python -m pytest tests/integration/test_first_test_capstone.py -m live -q -rs` | `1 skipped, 1 deselected` | live gating discipline |
| FT8 docs/check | `./venv/bin/python -m pytest tests/unit/test_first_test_closure_docs.py -q` | `5 passed` | closure/deferred/final pack integrity |
| Final cross-phase review | `git diff --check`; `./venv/bin/python -m pytest -q`; `./venv/bin/python -m pytest tests/integration/test_first_test_http_smoke.py tests/integration/test_first_test_capstone.py -m live -q -rs`; `./venv/bin/python -m myvoiceclone.evidence validate /mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z --repo-root .`; `./venv/bin/python -m compileall -q src tests` | diff check pass; `139 passed, 1 skipped, 2 deselected, 14 warnings`; live `2 skipped, 1 deselected`; validator `ok=true`; compileall pass | FT1-FT8 final review |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| DAG sequence | FT1→FT8 closures/logs exist in order | FT1-FT7 closure files plus FT8 docs/check | ✅ PASS |
| default regression | default suite green | `134 passed, 1 skipped, 2 deselected` before FT8 docs | ✅ PASS |
| live capstone | real capstone evidence exists | skipped evidence only | ⏸ PENDING |
| deferred reconciliation | first-build and first-test ledgers classify retained/partial/pending items | ledgers created/updated | ✅ PASS |
| final input pack | next-stage references exist | `docs/eval/first-test/final-input-pack.md` | ✅ PASS |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Live capstone execution | C | pending-live | `docs/closure/first-test/deferred-items-ledger.md#ftd-01--live-capstone-真实执行` | owner / next live runner |
| Non-skipped evidence pack | C | retained | `docs/closure/first-test/deferred-items-ledger.md#ftd-02--非-skipped-evidence-pack` | owner / next live runner |
| Real objective/model/cache work | B | retained | `docs/closure/first-test/deferred-items-ledger.md#1-总览` | future owner |
| first-build retained deferred | B/C | retained/partial | `docs/closure/first-build/deferred-items-ledger.md#6-first-test-reconciliation-snapshot2026-06-13` | future owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ FT1-FT6/FT8 are `observed-OK-at-closure`; FT7 live is `pending-live/deferred` |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `working tree @ 4e4ca3b`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 改动集中在 FT1-FT8 action-plan 对应 code/tests/docs |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| ✅ live capstone 标 pending-live |

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| FT1-FT8 docs/closure present | ✅ | `docs/closure/first-test/` |
| final input pack present | ✅ | `docs/eval/first-test/final-input-pack.md` |
| live capstone real pass | ⏸ | skipped evidence only; must rerun with owner live env |
| deferred ledger available | ✅ | `docs/closure/first-test/deferred-items-ledger.md` |

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| mock/real separation | ✅ 保持 | FT2/FT5 tests and evidence validator reject mock-as-real |
| live/gpu/slow gated | ✅ 保持 | `pytest.ini` default addopts excludes live/gpu/slow; FT7 marker test |
| real evidence outside repo | ✅ 保持 | evidence path under `/mnt/usb/workspace/myvoiceresearch/test-runs/` |
| no full-close without live evidence | ✅ 保持 | close type is `implementation-complete-awaiting-live-verification` |
