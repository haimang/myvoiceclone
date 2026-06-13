# [FT3 / Real Preprocess] Closure

> 阶段: `first-test/FT3 — 真实音频预处理与 dataset contract`
> 范围: `FT3-P1..P3`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT3-real-preprocess.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT3 真实预处理代码合同、adapter preflight/metadata、manifest lineage 与 reference selector 已完成并通过短途测试；真实 PyAnnote/Demucs/Whisper live smoke 仍需 FT7/live 环境验证。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT3-P1-01 FFmpeg metadata contract | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/adapters/test_ffmpeg_adapter.py` + `2026-06-13 08:34 UTC` |
| FT3-P1-02 PyAnnote preflight | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/adapters/test_pyannote_adapter.py` + `2026-06-13 08:34 UTC` |
| FT3-P1-03 Demucs optional path | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/adapters/test_demucs_adapter.py` + `2026-06-13 08:34 UTC` |
| FT3-P1-04 Whisper ASR contract | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/adapters/test_whisper_adapter.py` + `2026-06-13 08:34 UTC` |
| FT3-P2-01 preprocess all integration | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/jobs/test_runner.py` + `2026-06-13 08:34 UTC` |
| FT3-P3-01 dataset manifest contract | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/pipelines/test_export_dataset.py` + `2026-06-13 08:34 UTC` |
| FT3-P3-02 reference artifact selector | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/pipelines/test_reference_select.py` + `2026-06-13 08:34 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT3 targeted tests | `./venv/bin/python -m pytest tests/unit/adapters/test_ffmpeg_adapter.py tests/unit/adapters/test_pyannote_adapter.py tests/unit/adapters/test_demucs_adapter.py tests/unit/adapters/test_whisper_adapter.py tests/unit/pipelines/test_export_dataset.py tests/unit/pipelines/test_reference_select.py tests/unit/jobs/test_runner.py -q` | `16 passed, 1 skipped, 1 warning` | FT3-T01..T07 |
| FT1-FT3 regression | `./venv/bin/python -m pytest ... -q` over FT1-FT3 target files | `50 passed, 1 skipped, 3 warnings` | DAG regression |
| Syntax check | `python3 -m compileall -q src tests` | pass | edited Python files |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| adapter preflight | 缺 token/model/CLI 时有 explicit reason | adapter tests pass | ✅ PASS |
| no overclaim Demucs | metadata 标 source separation smoke，不等同 speech enhancement | Demucs tests pass | ✅ PASS |
| dataset lineage | manifest 非空且含 cleaned artifact sha/bytes/lineage | export dataset tests pass | ✅ PASS |
| reference selector | 只接受 cleaned artifact + transcript + duration 合格项 | selector tests pass | ✅ PASS |
| live external deps | 缺真实依赖时 skip，不记作 real pass | live FFmpeg test skipped with reason | ⏸ PENDING |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| PyAnnote/Demucs/Whisper live smoke | C | 代码与 preflight 完成，live 未跑 | FT7 live capstone，有 token/model/cache 后执行 | next FT owner |
| 真实语音质量评估 | C | FT3 只产 preprocess evidence | FT5 evaluation | next FT owner |
| 真实推理消费 reference artifact | C | selector 已提供合同 | FT4 real inference | next FT owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure`，短途测试已通过；live 标 pending |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `uncommitted working tree on HEAD 952fbc5`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 改动限 FT3 AP 指定 adapters/pipelines/dataset/reference/tests |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |
