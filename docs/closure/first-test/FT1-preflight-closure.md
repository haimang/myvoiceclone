# [FT1 / Preflight] Closure

> 阶段: `first-test/FT1 — 准入收敛与测试入口统一`
> 范围: `FT1-P1..P3`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT1-preflight.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT1 准入入口、环境键、preprocess job 创建、empty manifest guard 与 artifact root resolver 已按 first-test AP 完成并通过短途测试；无本阶段 known blocker。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT1-P1-01 命令与文档入口统一 | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/test_first_test_command_docs.py` + `2026-06-13 08:26 UTC` |
| FT1-P1-02 live bootstrap extras | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/test_scripts_dry_run.py::test_bootstrap_dry_run` + `2026-06-13 08:26 UTC` |
| FT1-P1-03 env 示例对齐 | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/test_project_config.py::test_runtime_env_resolvers` + `2026-06-13 08:26 UTC` |
| FT1-P2-01 CLI preprocess payload 修复 | ✅ closed | `working tree @ 4e4ca3b` + `tests/cli/test_cli.py::test_cli_preprocess_all_payload` + `2026-06-13 08:26 UTC` |
| FT1-P2-02 API preprocess job creation | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_routes.py::test_create_preprocess_job` + `2026-06-13 08:26 UTC` |
| FT1-P3-01 empty manifest guard | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/pipelines/test_export_dataset.py::test_export_dataset_refuses_empty_manifest` + `2026-06-13 08:26 UTC` |
| FT1-P3-02 API artifact root resolver | ✅ closed | `working tree @ 4e4ca3b` + `tests/api/test_first_test_preflight.py::test_run_job_uses_env_artifact_root` + `2026-06-13 08:26 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT1 targeted tests | `./venv/bin/python -m pytest tests/cli/test_cli.py tests/api/test_routes.py tests/api/test_first_test_preflight.py tests/unit/test_project_config.py tests/unit/test_scripts_dry_run.py tests/unit/pipelines/test_export_dataset.py tests/unit/test_first_test_command_docs.py -q` | `25 passed, 3 warnings` | FT1-T01..T07 |
| Architecture boundary | `./venv/bin/python -m pytest tests/unit/test_architecture_boundaries.py -q` | `1 passed` | API/CLI import boundary guard |
| Syntax check | `python3 -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 命令入口不漂移 | README 使用 `myvoiceclone`，CLI 有 `run preprocess-all` | command docs test pass | ✅ PASS |
| env/artifact root 不漂移 | resolver 尊重 env，API runner 使用 `ARTIFACT_ROOT` | config/API tests pass | ✅ PASS |
| fake-zero 防线 | 空 eligible segments 不写 frozen manifest artifact | empty manifest test pass | ✅ PASS |
| 真实证据不落 repo 默认路径 | `.env.example` 指向 `/mnt/usb/workspace/myvoiceresearch` 路径族 | config/docs tests pass | ✅ PASS |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实 FFmpeg/PyAnnote/Demucs/Whisper live execution | C | FT1 不执行真实模型/外部工具 | FT3 real preprocess | next FT owner |
| FastAPI complete e2e run surface | C | FT1 只新增 preprocess job creation | FT6 FastAPI e2e | next FT owner |
| live/gpu/slow denominator | C | FT1 bootstrap 只提供 probe 文案和 dry-run test | FT7 live capstone | next FT owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure`，短途测试已通过；未宣称 live |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `working tree @ 4e4ca3b`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 改动限 FT1 AP 指定入口/config/docs/tests |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |
