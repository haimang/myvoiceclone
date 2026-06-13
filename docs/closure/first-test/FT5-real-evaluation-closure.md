# [FT5 / Real Evaluation] Closure

> 阶段: `first-test/FT5 — 真实评估与 release gate`
> 范围: `FT5-P1..P3`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT5-real-evaluation.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT5 smoke metrics、objective proxy unavailable、manual MOS/ABX intake、metric source separation 与 layered release gate 已完成并通过短途测试；真实听感样本和 live release evidence 等待 FT7 capstone。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT5-P1-01 metric taxonomy | ✅ closed | `uncommitted working tree on HEAD 31b4a04` + `tests/unit/eval/test_objective.py` + `2026-06-13 08:41 UTC` |
| FT5-P1-02 report schema fields | ✅ closed | `uncommitted working tree on HEAD 31b4a04` + `tests/api/test_routes.py::test_subjective_report_endpoint` + `2026-06-13 08:41 UTC` |
| FT5-P2-01 smoke evaluator | ✅ closed | `uncommitted working tree on HEAD 31b4a04` + `tests/unit/eval/test_smoke_metrics.py` + `2026-06-13 08:41 UTC` |
| FT5-P2-02 objective proxy gating | ✅ closed | `uncommitted working tree on HEAD 31b4a04` + `tests/unit/eval/test_objective.py::test_objective_proxy_unavailable_is_explicit` + `2026-06-13 08:41 UTC` |
| FT5-P3-01 subjective eval service/API | ✅ closed | `uncommitted working tree on HEAD 31b4a04` + `tests/unit/eval/test_subjective.py` + `tests/api/test_routes.py::test_subjective_report_endpoint` + `2026-06-13 08:41 UTC` |
| FT5-P3-02 release gate layering | ✅ closed | `uncommitted working tree on HEAD 31b4a04` + `tests/api/test_release_gate.py::test_release_gate_blocks_mock_metrics` + `2026-06-13 08:41 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT5 targeted tests | `./venv/bin/python -m pytest tests/unit/eval/test_smoke_metrics.py tests/unit/eval/test_objective.py tests/unit/eval/test_subjective.py tests/api/test_release_gate.py tests/api/test_routes.py tests/api/test_audit_trace.py -q` | `23 passed, 2 warnings` | FT5-T01..T06 |
| FT1-FT5 regression | `./venv/bin/python -m pytest ... -q` over FT1-FT5 target files | `76 passed, 1 skipped, 4 warnings` | DAG regression |
| Syntax check | `python3 -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| smoke metrics | short wav fixture outputs deterministic health fields | smoke tests pass | ✅ PASS |
| proxy 不冒充主观质量 | optional proxy unavailable 不写 fake score | objective tests pass | ✅ PASS |
| manual MOS/ABX | validates ranges/reviewer and links sample/report | subjective tests pass | ✅ PASS |
| release layering | mock metrics cannot produce real quality pass | release gate tests pass | ✅ PASS |
| live/manual evidence | real sample listening/reviewer evidence in run pack | 未执行 | ⏸ PENDING |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Real objective proxy model | B | explicit unavailable semantics complete | SQUIM/DNSMOS dependency/model configured | future owner |
| Real manual listening evidence | C | API/service complete，真实样本未录入 | FT7 live capstone evidence | next FT owner |
| Crowdsourced MOS platform | A | out of first-test scope | 发布级外部评审成为目标时 reopen | future owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure`，短途测试已通过；live/manual evidence 标 pending |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `uncommitted working tree on HEAD 31b4a04`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 改动限 FT5 AP 指定 eval/report/policy/API/tests |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |
