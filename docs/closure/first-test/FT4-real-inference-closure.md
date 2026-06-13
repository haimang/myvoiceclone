# [FT4 / Real Inference] Closure

> 阶段: `first-test/FT4 — 真实推理 substrate 与 artifact contract`
> 范围: `FT4-P1..P3`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT4-real-inference.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT4 推理合同、no mock fallback、XTTS wrapper、model manifest、API/CLI real inference surface 与 artifact metadata 已完成并通过 fake-real 短途测试；真实 Coqui/XTTS live 模型推理未在本环境执行。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT4-P1-01 推理输入输出合同 | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/pipelines/test_real_inference_wrapper.py::test_inference_contract_requires_text_and_reference` + `2026-06-13 08:38 UTC` |
| FT4-P1-02 no mock fallback | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/adapters/test_xtts_adapter.py::test_xtts_real_mode_no_mock_fallback` + `2026-06-13 08:38 UTC` |
| FT4-P2-01 real adapter wrapper | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/pipelines/test_real_inference_wrapper.py::test_real_inference_wrapper_writes_artifact_metadata` + `2026-06-13 08:38 UTC` |
| FT4-P2-02 model manifest/cache/license | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/adapters/test_xtts_adapter.py::test_xtts_model_manifest_records_license` + `2026-06-13 08:38 UTC` |
| FT4-P2-03 inference artifact metadata | ✅ closed | `working tree @ 4e4ca3b` + `tests/unit/pipelines/test_real_inference_wrapper.py` + `2026-06-13 08:38 UTC` |
| FT4-P3-01 CLI inference smoke | ✅ closed | `working tree @ 4e4ca3b` + `tests/cli/test_cli.py::test_cli_real_inference_smoke` + `2026-06-13 08:38 UTC` |
| FT4-P3-02 live/slow real inference smoke | ⏸ pending | code present; live model/cache not executed in this environment |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT4 targeted tests | `./venv/bin/python -m pytest tests/unit/adapters/test_xtts_adapter.py tests/unit/adapters/test_rvc_adapter.py tests/unit/pipelines/test_real_inference_wrapper.py tests/api/test_inference_routes.py tests/cli/test_cli.py tests/unit/test_scripts_dry_run.py tests/unit/storage/test_artifact_store.py tests/unit/test_architecture_boundaries.py -q` | `22 passed, 2 warnings` | FT4-T01..T06 |
| FT1-FT4 regression | `./venv/bin/python -m pytest ... -q` over FT1-FT4 target files | `61 passed, 1 skipped, 4 warnings` | DAG regression |
| Syntax check | `python3 -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| input contract | 缺 text/reference/model 报明确错误 | contract tests pass | ✅ PASS |
| no silent fallback | `MOCK_ADAPTERS=false` 不返回 fake bytes | adapter tests pass | ✅ PASS |
| artifact contract | 输出为 `rendered_audio` artifact 且含 input refs/model/license/provenance | wrapper tests pass | ✅ PASS |
| API/CLI surface | `/api/inference/real` 与 `myvoiceclone infer real` 可触发 service contract | API/CLI tests pass | ✅ PASS |
| live real model | 有 Coqui/XTTS 依赖和模型缓存时产真实 wav | 未执行 | ⏸ PENDING |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Coqui/XTTS live smoke | C | 代码完成，需真实模型/cache/live deps | FT7 live capstone | next FT owner |
| Real RVC/SoVITS training | A | out of first-test scope | Owner 明确训练为硬目标时 reopen | future owner |
| 发布许可裁定 | C | license/provenance 已记录，不裁定发布 | FT5/FT8 release governance | next FT owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure`，fake-real 短途测试已通过；live 标 pending |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `working tree @ 4e4ca3b`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 改动限 FT4 AP 指定 adapters/inference/service/API/CLI/scripts/tests |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |
