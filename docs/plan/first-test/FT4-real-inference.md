# FT4 Real Inference Action Plan

> 服务业务簇: `FT4 · 真实推理 substrate 与 artifact contract`
> 计划对象: `real inference adapter, model manifest, no-mock-fallback contract`
> 类型: `new`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT4-real-inference.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT2-schema-observability.md`
> - `docs/plan/first-test/FT3-real-preprocess.md`
> 下游交接:
> - `docs/plan/first-test/FT5-real-evaluation.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT4`, `reference-anchor axis C/F/G/H`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT4 是 first-test 的关键跃迁：从 mock inference 变成至少一条真实推理 substrate。本 AP 按 proposed/reference 的 non-blocking baseline 设计：先定义统一 adapter contract，再优先评估可本地运行、预训练、短 reference、输出 wav artifact 的真实路径；具体 substrate 选择仍以实现证据和 license/provenance 记录为准。

- **服务业务簇**：`Real inference substrate / 真实推理`
- **计划对象**：inference adapter wrapper, model cache/license manifest, artifact metadata
- **本次计划解决的问题**：
  - XTTS/RVC/SoVITS 真实路径当前 `NotImplementedError` 或 mock。
  - 推理输出缺真实 artifact contract。
  - mock fallback 会污染真实 e2e。
- **本次计划的直接产出**：
  - `text/source/reference/model -> wav artifact` contract。
  - 一条真实预训练推理 adapter path。
  - model/license/provenance metadata 与 live smoke。
- **本计划不重新讨论的设计结论**：
  - first-test 可先以预训练推理 substrate 闭环，不把真实训练作为 FT4 前置（来源：`docs/eval/first-test/proposed-planning.md:220-242`）。
  - 外部 CLI/库只借 adapter shape，不直接暴露为 myvoiceclone API contract（来源：`docs/eval/first-test/reference-anchor.md:197-213`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先定义统一推理合同和 no-fallback 行为，再实现真实 adapter wrapper 与模型 manifest，最后补 CLI smoke、artifact metadata 和 live/slow gated test。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Inference contract | M | 统一 input/output/error contract；可用 fixture/reference artifact 先行 | FT2；formal pass 依赖 FT3 artifact |
| Phase 2 | Real adapter wrapper | L | 接入一条真实预训练推理路径 | Phase 1 |
| Phase 3 | CLI/live smoke | M | CLI 与 live/slow gated 验证 | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Inference contract**
   - **核心目标**：固定 `text/source/reference/model -> wav artifact`。
   - **为什么先做**：避免模型实现污染 API/DB contract。
2. **Phase 2 — Real adapter wrapper**
   - **核心目标**：真实输出 wav，并写 model/license/provenance metadata。
   - **为什么放在这里**：这是 first-test “真实推理”的交付核心。
3. **Phase 3 — CLI/live smoke**
   - **核心目标**：命令行和 live test 能证明确实产出真实 wav。
   - **为什么放在这里**：给 FT5/FT7 提供可信输入。

### 1.4 执行策略说明

- **执行顺序原则**：contract → adapter → artifact metadata → CLI/live tests。
- **风险控制原则**：真实 mode 缺依赖必须 fail/skip，不回退 mock。
- **测试推进原则**：unit fake real-wrapper + gated live smoke。
- **文档同步原则**：模型 manifest、license、cache path 必须记录。
- **回滚 / 降级原则**：adapter live unavailable 时保留 contract tests，但不得声称 real pass。

### 1.5 影响结构图

```text
FT4 Real Inference
├── domain contract
│   ├── domain/entities.py
│   └── api/schemas.py
├── adapters
│   ├── adapters/training/xtts_adapter.py
│   ├── adapters/training/rvc_adapter.py
│   └── new inference wrapper
├── services/pipelines
│   ├── services/__init__.py
│   ├── api/routes_inference.py
│   └── cli.py
└── tests
    ├── unit/adapters
    ├── cli
    └── live/slow
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** 一条真实推理 substrate contract。
- **[S2]** 真实 adapter wrapper 和 output artifact。
- **[S3]** model cache/license/provenance manifest。
- **[S4]** no mock fallback enforcement.
- **[S5]** CLI smoke 与 live/slow test。

### 2.2 Out-of-Scope

- **[O1]** 真实训练 RVC/SoVITS/XTTS。
- **[O2]** 同时支持所有 voice clone engines。
- **[O3]** 发布许可裁定，FT4 只记录 license/provenance。
- **[O4]** 质量评估，交 FT5。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| Pretrained inference | in-scope | 满足真实推理闭环 | license/cache 不可用 |
| Real training | out-of-scope | first-test 先闭环推理 | Owner 后续要求训练 |
| RVC WebUI workflow | out-of-scope | reference 反例 | 仅借 model/input/output |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT4-P1-01 | Phase 1 | 推理输入输出合同 | add/update | `src/myvoiceclone/domain/entities.py`, `src/myvoiceclone/api/schemas.py:82-85` | contract 校验缺参/输出 | FT4-T01 | medium |
| FT4-P1-02 | Phase 1 | no mock fallback | update | `src/myvoiceclone/adapters/training/xtts_adapter.py:9-18`, `rvc_adapter.py:24-32` | real mode 不产 mock | FT4-T02 | high |
| FT4-P2-01 | Phase 2 | real adapter wrapper | add/update | `src/myvoiceclone/adapters/*`, `src/myvoiceclone/api/routes_inference.py:10-22` | 真实 wav artifact | FT4-T03 | high |
| FT4-P2-02 | Phase 2 | model manifest/cache/license | update | `scripts/download_models.sh`, `src/myvoiceclone/config.py:63-68` | model preflight 可审计 | FT4-T04 | medium |
| FT4-P2-03 | Phase 2 | inference artifact metadata | update | `src/myvoiceclone/storage/artifact_store.py`, `src/myvoiceclone/api/routes_inference.py` | output refs/model metadata 完整 | FT4-T05 | medium |
| FT4-P3-01 | Phase 3 | CLI inference smoke | update | `src/myvoiceclone/cli.py:271-282` | CLI 支持 real mode smoke | FT4-T06 | medium |
| FT4-P3-02 | Phase 3 | live/slow real inference smoke | add | `tests/integration/test_real_inference_smoke.py` | 有缓存时产真实 wav | FT4-T07 | high |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT4.1` | FT4-P1-01 | `T-FT4.1` | FT4-T01 |
| `FT4.2` | FT4-P1-02 | `T-FT4.2` | FT4-T02 |
| `FT4.3` | FT4-P2-01 | `T-FT4.3` | FT4-T03 |
| `FT4.4` | FT4-P2-02 | `T-FT4.4` | FT4-T04 |
| `FT4.5` | FT4-P2-03 | `T-FT4.5` | FT4-T05 |
| `FT4.6` | FT4-P3-01 / FT4-P3-02 | `T-FT4.6` | FT4-T06 / FT4-T07 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Inference contract

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT4-P1-01 | 推理输入输出合同 | a) 定义 text/source/reference/model fields；b) 输出 wav artifact id/path/duration/model metadata；c) 缺参明确错误。 | `src/myvoiceclone/api/schemas.py:82-85`, `src/myvoiceclone/domain/entities.py` | contract 稳定 | FT4-T01 | schema test pass |
| FT4-P1-02 | no mock fallback | `MOCK_ADAPTERS=false` 时依赖缺失必须 failed/skip；不得返回 fake bytes。 | `src/myvoiceclone/adapters/training/xtts_adapter.py:9-18`, `src/myvoiceclone/adapters/training/rvc_adapter.py:24-32` | real mode 可信 | FT4-T02 | no fallback test pass |

### 4.2 Phase 2 — Real adapter wrapper

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT4-P2-01 | real adapter wrapper | a) 封装 selected pretrained engine；b) 输入 reference artifact；c) 输出 wav bytes/file；d) 捕获 dependency/model errors。 | `src/myvoiceclone/adapters/*`, `src/myvoiceclone/api/routes_inference.py:10-22` | 真实 wav artifact | FT4-T03 | adapter unit pass |
| FT4-P2-02 | model manifest/cache/license | 写 manifest：model_id/version/cache_path/license/source/provenance；替换 placeholder download note。 | `scripts/download_models.sh`, `src/myvoiceclone/config.py:63-68` | 模型前置可审计 | FT4-T04 | preflight test pass |
| FT4-P2-03 | inference artifact metadata | output artifact metadata 写 input refs、adapter mode、model、device、duration、license。 | `src/myvoiceclone/storage/artifact_store.py`, inference service | artifact 可追溯 | FT4-T05 | metadata test pass |

### 4.3 Phase 3 — CLI/live smoke

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT4-P3-01 | CLI inference smoke | 扩展 `myvoiceclone infer` 支持 real mode 参数和 artifact output，不只写 fake file。 | `src/myvoiceclone/cli.py:271-282` | CLI 可触发真实推理 | FT4-T06 | CLI smoke pass |
| FT4-P3-02 | live/slow smoke | 有模型缓存时跑短文本+reference；无依赖 skip with reason。 | `tests/integration/test_real_inference_smoke.py` | live 可信证据 | FT4-T07 | live pass/skip reason |

---

## 5. Phase 详情

### 5.1 Phase 1 — Inference contract

- **目标**：稳定 FT4/FT5/FT6 共享合同。
- **新增文件**：可新增 `src/myvoiceclone/pipelines/infer_real.py` 或 service module。
- **修改文件**：`src/myvoiceclone/api/schemas.py`, `src/myvoiceclone/domain/entities.py`, existing adapters。
- **具体功能预期**：
  1. 缺 text/source/reference/model 时校验失败。
  2. output 必须是 artifact，不是裸路径。
  3. `adapter_mode=real` 与 mock 明确区分。
  4. real dependency missing 不生成 fake bytes。
  5. error reason 可写 job_event/metadata。
- **测试项**：FT4-T01 / FT4-T02
- **收口标准**：contract and no-fallback tests pass。
- **风险提醒**：不要把外部 CLI 参数直接变成 API contract。

### 5.2 Phase 2 — Real adapter wrapper

- **目标**：产出真实 wav artifact。
- **具体功能预期**：
  1. 支持短 reference audio。
  2. 支持指定 model/cache path。
  3. 捕获 license/provenance 信息。
  4. 写 output artifact bytes/sha/duration。
  5. 写 input_refs 供 trace 查询。
  6. 模型不可用时返回可诊断错误。
- **测试项**：FT4-T03..FT4-T05
- **收口标准**：unit fake wrapper pass，live smoke 可 pass 或 skip reason。
- **风险提醒**：XTTS-v2 license 不能默认发布；只做 first-test 研究用途。

### 5.3 Phase 3 — CLI/live smoke

- **目标**：操作者可以通过 CLI 和 live test 证明确有真实输出。
- **具体功能预期**：
  1. CLI 支持 real/mock 显式 mode。
  2. CLI 缺依赖 exit code 清楚。
  3. live test 不默认跑。
  4. live skip reason 记录模型/token/cache 缺失。
  5. artifact 不落 repo。
- **测试项**：FT4-T06 / FT4-T07
- **收口标准**：CLI smoke pass；live pass 或 skipped with reason。
- **风险提醒**：真实模型耗时/VRAM 不稳定，必须 gated。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Owner-gate non-blocking for AP drafting | 当前用户消息 + proposed planning | 不等待 owner-gate 制作 AP，但 substrate 选择仍需 evidence/license 复核 | final 前按 evidence 复核 |
| Coqui/RVC references are partial borrow only | `docs/eval/first-test/reference-anchor.md:74-83`, `docs/eval/first-test/reference-anchor.md:197-213` | wrapper 不暴露外部 CLI contract | 回 reference |
| FT4 proposed baseline | `docs/eval/first-test/proposed-planning.md:220-242` | 定义 work/test | 回 proposed |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT4-1 | `src/myvoiceclone/adapters/training/xtts_adapter.py:9-18` | XTTS mock/real placeholder | FT4-P1-02/FT4-P2-01 | ♻️ 重 substrate | real implementation |
| A-FT4-2 | `src/myvoiceclone/adapters/training/rvc_adapter.py:24-32` | RVC conversion placeholder | FT4-P1-02 | ♻️ 重 substrate | no fallback |
| A-FT4-3 | `src/myvoiceclone/api/routes_inference.py:10-22` | inference API | FT4-P2-01 | ♻️ 重 substrate | service path |
| A-FT4-4 | `src/myvoiceclone/cli.py:271-282` | mock infer CLI | FT4-P3-01 | ♻️ 重 substrate | real mode |
| A-FT4-5 | `scripts/download_models.sh` | placeholder model download | FT4-P2-02 | ♻️ 重 substrate | manifest/cache |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 |
|----|--------------|--------|
| ⛔1 | RVC WebUI whole workflow as substrate | reference-anchor says too many implicit assets |
| ⛔2 | XTTS model ability = release permission | CPML/license must be recorded |
| ⛔3 | `MOCK_ADAPTERS=false` returns fake bytes | destroys real e2e evidence |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-test/reference-anchor.md`。
- **威胁模型锚**：model license/provenance, source/reference audio rights, and cache path are trust boundaries. Do not log tokens; artifact metadata must record license/source without secrets.

---

## 8. 测试台账

### 8.1 测试清单

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据 |
|---------|--------|------|----|------|------|-----------|
| FT4-T01 | inference contract validation | 短途 | unit/contract | 🆕 新增 `tests/unit/adapters/test_inference_contract.py` | FT4-P1-01 | commit + pytest + run-time |
| FT4-T02 | no mock fallback | 短途 | unit/config | 🔱 fork `tests/unit/adapters/test_xtts_adapter.py` | FT4-P1-02 | commit + pytest + run-time |
| FT4-T03 | real wrapper artifact | 短途 | unit/adapter | 🆕 新增 `tests/unit/adapters/test_real_inference_wrapper.py` | FT4-P2-01 | commit + pytest + run-time |
| FT4-T04 | model manifest/cache/license | 短途 | unit/script | 🔱 fork `tests/unit/test_scripts_dry_run.py` | FT4-P2-02 | commit + pytest + run-time |
| FT4-T05 | output artifact metadata | 短途 | unit/storage | 🔱 fork `tests/unit/storage/test_artifact_store.py` | FT4-P2-03 | commit + pytest + run-time |
| FT4-T06 | CLI real inference smoke | 短途 | cli | 🆕 新增 `tests/cli/test_real_inference_cli.py` | FT4-P3-01 | commit + pytest + run-time |
| FT4-T07 | live real inference smoke | spike | live/slow | 🆕 新增 `tests/integration/test_real_inference_smoke.py` | FT4-P3-02 | commit + pytest -m live + run-time |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/adapters/test_xtts_adapter.py` | 🔱 fork | assert NotImplemented/no fake in real mode | 已存在 |
| `tests/unit/storage/test_artifact_store.py` | 🔱 fork | assert output metadata | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest tests/unit/adapters tests/cli -q` | unit/cli | 每 PR |
| spike | `pytest -m live tests/integration/test_real_inference_smoke.py -q` | live/slow | Phase 收口 |

### 8.4 测试缺口

- 不评估音质好坏 → FT5。
- 不跑完整 API e2e → FT6/FT7。

### 8.5 测试保真

- live output 必须是 real mode artifact；mock bytes 不允许通过。
- license/cache missing 必须 skip/failed reason。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| License uncertainty | XTTS/other model may restrict use | high | metadata + release gate |
| Model download/VRAM | live path may not run locally | high | gated live + skip reason |
| Contract mismatch | external library shape changes | medium | wrapper boundary |

### 9.2 约束与前提

- **技术前提**：FT2 metadata/event contract exists。
- **运行时前提**：model cache optional; live tests gated。
- **组织协作前提**：source/reference audio provenance known。
- **上线 / 合并前提**：unit contract/no-fallback tests pass。

### 9.3 文档同步要求

- model manifest instructions。
- inference CLI/API usage notes。
- license/provenance caveat。

### 9.4 完成后的预期状态

1. 至少一条真实推理 path 可产生 wav artifact。
2. real mode 不会 silent fallback mock。
3. model/license/provenance 可审计。
4. FT5 可基于真实 output artifact 做评估。

---

## 10. 收口

### 10.1 收口硬闸

1. Contract/no-fallback tests PASS（FT4-T01/FT4-T02）。
2. Adapter artifact/metadata tests PASS（FT4-T03..FT4-T05）。
3. CLI/live smoke PASS 或 skip reason 完整（FT4-T06/FT4-T07）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| inference contract stable | FT4-P1-01..02 | FT4-T01..02 | commit + pytest + run-time | 未观察 |
| real artifact output | FT4-P2-01..03 | FT4-T03..05 | commit + pytest + run-time | 未观察 |
| CLI/live smoke | FT4-P3-01..02 | FT4-T06..07 | commit + pytest + run-time | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | real inference output artifact exists |
| 测试 | §8 all pass/skip reason |
| 文档 | model/license/provenance documented |
| 风险收敛 | no mock fallback |
| 可交付性 | FT5 can evaluate real output |

### 10.4 NOT-成功识别

若 `MOCK_ADAPTERS=false` 仍返回 fake bytes，或 output artifact 缺 model/license/input refs，不得标 `executed`。
