# [FT2 / Schema Observability] Closure

> 阶段: `first-test/FT2 — Schema drift 与 observability contract`
> 范围: `FT2-P1..P3`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT2-schema-observability.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT2 schema drift、job_events metadata、step-level observability、trace completeness 与 mock/real evidence separation 已完成并通过短途测试；未引入 OTel 平台或多 worker 语义。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT2-P1-01 schema drift inventory | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/storage/test_schema_drift.py` + `2026-06-13 08:31 UTC` |
| FT2-P1-02 SQLite pragma boundary | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/storage/test_sqlite_connection.py` + `2026-06-13 08:31 UTC` |
| FT2-P2-01 step-level job_events | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/jobs/test_runner.py` + `2026-06-13 08:31 UTC` |
| FT2-P2-02 failure summary 上卷 | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/jobs/test_runner.py::test_job_runner_success_preprocess` + `2026-06-13 08:31 UTC` |
| FT2-P2-03 adapter metadata contract | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/storage/test_artifact_observability.py` + `2026-06-13 08:31 UTC` |
| FT2-P3-01 audit trace completeness | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/api/test_audit_trace.py` + `2026-06-13 08:31 UTC` |
| FT2-P3-02 mock/real evidence separation | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/eval/test_objective.py` + `2026-06-13 08:31 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT2 targeted tests | `./venv/bin/python -m pytest tests/unit/storage/test_schema_drift.py tests/unit/storage/test_sqlite_connection.py tests/unit/jobs/test_runner.py tests/unit/storage/test_artifact_observability.py tests/unit/eval/test_objective.py tests/api/test_audit_trace.py -q` | `13 passed, 1 warning` | FT2-T01..T07 |
| FT1+FT2 regression | `./venv/bin/python -m pytest ... -q` over FT1+FT2 target files | `39 passed, 3 warnings` | DAG regression |
| Syntax check | `python3 -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| schema drift guard | 核心列/index/migration order/checksum 可测 | schema drift tests pass | ✅ PASS |
| SQLite local boundary | FK/WAL/busy_timeout 可断言 | sqlite tests pass | ✅ PASS |
| step evidence | 每个 preprocess major step 有 structured metadata | runner tests pass | ✅ PASS |
| trace completeness | job/run/report/release trace 可聚合 eval/release/policy/artifact | API tests pass | ✅ PASS |
| mock 不冒充 real | mock metric 标 `metric_source=mock` 且不可作为 quality pass | objective tests pass | ✅ PASS |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Full OTel SDK/platform | A | 明确不在 first-test P0 scope | 多服务/持续监控进入目标时 reopen | future owner |
| pipeline_runs production workflow | B | 保留 compatibility，不作为 first-test hard dependency | UI/resume 需要 recording-level timeline 时 reopen | future owner |
| 多 worker SQLite/queue 语义 | A | WAL 只声明本地边界 | 并发 worker 成为目标时另开 infra phase | future owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure`，短途测试已通过；未宣称 live |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `uncommitted working tree on HEAD 952fbc5`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 改动限 FT2 AP 指定 schema/event/trace/eval/tests |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |
