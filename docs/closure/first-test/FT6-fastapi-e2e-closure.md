# [FT6 / FastAPI E2E Surface] Closure

> 阶段: `first-test/FT6 — FastAPI e2e surface 与前端可消费合同`
> 范围: `FT6-P1..P3`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT6-fastapi-e2e.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT6 first-test run/upload/start/status API surface、contract fixture、artifact-backed upload 与 live HTTP gated spike 已完成并通过 TestClient/全量默认 suite；真实 socket e2e 需在 `RUN_LIVE_HTTP=1` 的 FT7 capstone 环境执行。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT6-P1-01 first-test run contract | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_first_test_runs.py::test_create_run_contract_snapshot` + `2026-06-13 08:47 UTC` |
| FT6-P1-02 response contract fixture | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/contracts/first_test_run_create.json` + `2026-06-13 08:47 UTC` |
| FT6-P2-01 upload audio artifact | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_first_test_runs.py::test_upload_audio_immediately_writes_artifact` + `2026-06-13 08:47 UTC` |
| FT6-P2-02 start preprocess/infer/eval jobs | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_first_test_runs.py::test_start_jobs_reference_artifact_ids` + `2026-06-13 08:47 UTC` |
| FT6-P3-01 status API | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_first_test_runs.py::test_run_status_aggregates_events_artifacts_and_failures` + `2026-06-13 08:47 UTC` |
| FT6-P3-02 report/release/trace reuse | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_audit_trace.py` + `2026-06-13 08:47 UTC` |
| FT6-P3-03 live HTTP spike | ⏸ pending | `working tree @ 4e4ca3b` + `tests/integration/test_first_test_http_smoke.py -m live -q -rs` -> `1 skipped: RUN_LIVE_HTTP=1 is required...` + `2026-06-13 08:47 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT6 targeted tests | `./venv/bin/python -m pytest tests/api/test_first_test_runs.py tests/api/test_app_factory.py tests/unit/test_architecture_boundaries.py tests/integration/test_first_test_http_smoke.py -q` | `7 passed, 1 deselected, 1 warning` | FT6-T01..T06 + default live deselection |
| FT6 live gated smoke | `./venv/bin/python -m pytest tests/integration/test_first_test_http_smoke.py -m live -q -rs` | `1 skipped` with explicit `RUN_LIVE_HTTP=1` reason | FT6-T07 skip denominator |
| FT1-FT6/default regression | `./venv/bin/python -m pytest -q` | `127 passed, 1 skipped, 1 deselected, 14 warnings` | all default unit/api/integration tests |
| Syntax check | `./venv/bin/python -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| run contract | create run response has stable id/status/config/links | contract snapshot test pass | ✅ PASS |
| upload persistence | uploaded file immediately becomes artifact with bytes/sha/metadata | upload TestClient test pass | ✅ PASS |
| job orchestration | start endpoints create DB jobs with artifact refs | payload contract test pass | ✅ PASS |
| status aggregation | status includes jobs/events/artifacts/failure summary | status test pass | ✅ PASS |
| architecture boundary | API routes do not import pipeline/eval/adapter internals | architecture guard pass | ✅ PASS |
| live HTTP socket | uvicorn/socket smoke with real env | gated test skipped with explicit reason | ⏸ PENDING |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Live HTTP socket execution | C | gated spike exists, skipped locally without `RUN_LIVE_HTTP=1` | FT7 capstone evidence run | next FT owner |
| Production task queue / worker pool | A | out of first-test scope; DB job ledger used | production concurrency target appears | future owner |
| Resumable/chunked large uploads | A | out of first-test scope; short audio upload supported | large-file UX/API requirement appears | future owner |
| Global response envelope | B | deferred; first-test fields only frozen | final API contract freeze / frontend integration review | future owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure`，TestClient/default suite 已通过；live socket 明确 pending |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `working tree @ 4e4ca3b`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ FT6 新增/修改集中在 API schemas/routes/tests/pyproject 与阶段文档 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |
