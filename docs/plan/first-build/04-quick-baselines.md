# Nano-Agent 行动计划：P4 Quick Baselines

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P4 Quick Baselines`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/04-quick-baselines.md`
> 上游前序 / closure:
> - `03-corpus-dataset-freeze.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:180`
> 下游交接:
> - `05-long-train-sovits.md`
> - `06-eval-inference-api.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:180`（P4 工作台账）
> 冻结决策来源:
> - `final-execution-plan.md:502`（Q1）
> - `final-execution-plan.md:507`（Q6）
> grounding 来源:
> - `final-execution-plan.md:184`、`:384`、`:437`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P4 用 frozen dataset 快速验证声线可学性和接口完整性。它不是最终质量收口，而是通过 RVC quick baseline、TTS smoke、固定 eval pack 和 baseline report，判断数据与训练 adapter 是否足以进入 P5 长训。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P4 Quick Baselines`
- **本次计划解决的问题**：
  - 训练前缺少快速反馈环。
  - RVC/TTS baseline 需要走同一 model_run/artifact/report 合同。
  - P5 长训需要明确 gate，而不是盲目启动。
- **本次计划的直接产出**：
  - `rvc_adapter.py`, `xtts_adapter.py`, `pipelines/train.py`
  - baseline eval pack and report
  - `long_train_ready` gate report
- **本计划不重新讨论的设计结论**：
  - VC/SVC 主线 + TTS baseline 可选（来源：`final-execution-plan.md:502`）。
  - 所有训练和报告必须可审计（来源：`final-execution-plan.md:507`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先训练 adapter contract，再 fake baseline，再固定 eval pack，再 gate report”的方式。真实 RVC/XTTS 可作为 live marker，但默认测试只用 fake adapters 证明 model_run、checkpoint、rendered artifacts、report 流转正确。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Training adapter contract | M | 统一 train/synth/convert DTO | P3 |
| Phase 2 | RVC quick baseline | M | 快速 VC baseline run | Phase 1 |
| Phase 3 | TTS smoke baseline | M | 可选文字转语音 smoke | Phase 1 |
| Phase 4 | Eval pack + report + gate | M | baseline report 和 long train gate | Phase 2/3 |

### 1.3 Phase 说明

1. **Phase 1 — Training adapter contract**
   - **核心目标**：让 RVC/TTS 适配器返回标准 TrainResult/InferenceResult。
   - **为什么先做**：P4/P5/P6 都依赖统一 run/artifact 合同。
2. **Phase 2 — RVC quick baseline**
   - **核心目标**：用 frozen manifest 验证 VC 可学性。
   - **为什么放在这里**：它是进入 P5 长训前的最快反馈。
3. **Phase 3 — TTS smoke baseline**
   - **核心目标**：验证 TTS 路线是否值得保留。
   - **为什么放在这里**：不与 SVC 主线混淆。
4. **Phase 4 — Eval pack + report + gate**
   - **核心目标**：输出可比较报告和 P5 gate。
   - **为什么放在这里**：长训必须基于 evidence。

### 1.4 执行策略说明

- **执行顺序原则**：adapter contract 先于具体模型，report 先于 gate。
- **风险控制原则**：baseline 只做 quick smoke，不将 RVC 作为 20h 主线结论。
- **测试推进原则**：fake trainer 默认，live trainer 单独 marker。
- **文档同步原则**：固定 prompts/reference clips 写入 eval pack manifest。
- **回滚 / 降级原则**：TTS smoke 失败不阻塞 VC 长训，但必须写入 report。

### 1.5 本次 action-plan 影响结构图

```text
P4 Quick Baselines
├── configs/pipelines/train.rvc.yaml
├── src/myvoiceclone/adapters/training/{rvc_adapter,xtts_adapter}.py
├── src/myvoiceclone/pipelines/train.py
├── data/artifacts/eval/baseline-pack.*
├── data/artifacts/reports/baseline-report.*
└── tests/unit/{adapters,eval}
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** RVC adapter contract and fake quick baseline。
- **[S2]** TTS adapter contract and fake synth smoke。
- **[S3]** baseline eval pack manifest。
- **[S4]** baseline report and long-train gate conclusion。

### 2.2 Out-of-Scope

- **[O1]** So-VITS-SVC 长训，交给 P5。
- **[O2]** HTTP/CLI inference routes，交给 P6。
- **[O3]** 主观 ABX/MOS 完整流程，交给 P6。
- **[O4]** 安全 release gate，交给 P7。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| fake baseline | in-scope | unit suite 不依赖真实模型 | live smoke |
| RVC 最终主线 | out-of-scope | proposed/final 已定位 quick baseline | owner 改 Q1 |
| long_train_ready gate | in-scope | P5 依赖 | gate report 缺失 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P4-01 | Phase 2 | RVC quick baseline | add | `adapters/training/rvc_adapter.py`, `pipelines/train.py` | mock train creates model_run + checkpoint | P4-T01 | medium |
| P4-02 | Phase 3 | TTS smoke baseline | add | `adapters/training/xtts_adapter.py` | fake synth creates rendered artifact | P4-T02 | medium |
| P4-03 | Phase 4 | Baseline eval pack | add | `data/artifacts/eval/`, `eval/report.py` | eval pack manifest reusable | P4-T03 | medium |
| P4-04 | Phase 4 | Baseline report | add | `eval/report.py`, `reports` table | JSON/Markdown report 入库 | P4-T04 | medium |
| P4-05 | Phase 4 | Long-train gate | add | `eval/report.py` | report includes `long_train_ready` conclusion | P4-T05 | high |

---

## 4. Phase 业务表格

### 4.1 Phase 1/2 — Training contract + RVC baseline

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P4-01 | RVC quick baseline | a) 定义 TrainRequest/TrainResult；b) adapter 读取 frozen manifest；c) 创建 model_run；d) fake checkpoint artifact；e) fake convert rendered artifact；f) 失败写 job/model_run error | `rvc_adapter.py`, `pipelines/train.py` | RVC quick flow 可审计 | P4-T01 | fake train/convert PASS |

### 4.2 Phase 3 — TTS smoke

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P4-02 | TTS smoke baseline | a) 定义 SynthRequest/SynthResult；b) fake TTS adapter 生成 rendered artifact；c) 结果写 model_run 或 inference artifact；d) 失败不阻塞 RVC report | `xtts_adapter.py` | TTS 可选轨被接口化 | P4-T02 | fake synth PASS |

### 4.3 Phase 4 — Eval pack + report + gate

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P4-03 | Baseline eval pack | a) 固定 prompts；b) 固定 source/reference clips URI；c) 写 eval pack artifact；d) pack hash 可复用 | `data/artifacts/eval/`, `eval/report.py` | eval 输入稳定 | P4-T03 | pack checksum PASS |
| P4-04 | Baseline report | a) 汇总 RVC/TTS fake outputs；b) 写 metrics placeholder；c) 输出 JSON+Markdown；d) report row 按 `draft -> generated` 写状态事件 | `eval/report.py` | baseline 可比较 | P4-T04 | report fixture PASS |
| P4-05 | Long-train gate | a) 读取 corpus audit + baseline report；b) 判断数据质量、baseline 可学性、环境可运行；c) 输出 `long_train_ready` true/false/reason；d) false 时阻止 P5 live long train | `eval/report.py` | P5 有 evidence gate | P4-T05 | gate logic PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2/3 — baseline adapters

- **Phase 目标**：为快速模型验证建立统一训练/推理合同。
- **本 Phase 对应编号**：P4-01 / P4-02
- **本 Phase 新增文件**：`rvc_adapter.py`, `xtts_adapter.py`, `pipelines/train.py`
- **具体功能预期**：
  1. adapter 不暴露模型仓库私有路径给 domain/API。
  2. 每次 baseline 创建 model_run。
  3. checkpoint/rendered samples 作为 artifacts。
  4. TTS smoke 失败不自动否决 VC 主线。
  5. baseline 不直接读取非 frozen dataset。
- **对应测试台账项**：P4-T01 / P4-T02
- **收口标准**：fake adapters 产出 model_run + artifacts。
- **本 Phase 风险提醒**：不要将 RVC quick result 误写成最终质量评估。

### 5.2 Phase 4 — eval pack/report/gate

- **Phase 目标**：形成进入 P5 的 evidence gate。
- **本 Phase 对应编号**：P4-03 / P4-04 / P4-05
- **本 Phase 新增文件**：`eval/report.py` 扩展, `data/artifacts/eval/*`
- **具体功能预期**：
  1. eval pack 可跨 runs 复用。
  2. report 记录 baseline 配置、dataset id、artifact ids。
  3. gate 结果包含机器可读 reason。
  4. gate false 不删除 baseline artifacts。
  5. P5 AP 明确消费 gate。
- **对应测试台账项**：P4-T03..P4-T05
- **收口标准**：`long_train_ready` 结论可查询。
- **本 Phase 风险提醒**：gate 不应只基于单一指标。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q1 | `final-execution-plan.md:502` | RVC baseline + TTS smoke | 重开模型路线 |
| Q6 | `final-execution-plan.md:507` | model_run/artifact/report 必填 | 不得只跑脚本 |
| Q7 | `final-execution-plan.md:508` | fake tests 默认 | live model 单独 marker |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-1 | `final-execution-plan.md:180` | P4 工作台账 | P4-01..05 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:384` | `train.rvc.yaml` | P4-01 | ✅ 复用 | config |
| A-3 | `final-execution-plan.md:437` | `rvc_adapter.py` | P4-01 | ✅ 复用 | adapter |
| A-4 | `final-execution-plan.md:439` | `xtts_adapter.py` | P4-02 | ✅ 复用 | adapter |
| A-5 | `final-execution-plan.md:398` | eval artifacts | P4-03..05 | ✅ 复用 | reports/eval |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 训练读取非 frozen manifest | P3 输出是训练唯一合同 |
| ⛔2 | RVC baseline 成为长训主线 | Q1 只保留 quick baseline |
| ⛔3 | baseline report 不入库 | Q6 要可审计 |
| ⛔4 | gate false 仍启动长训 | P5 依赖 gate |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：P4 不启用安全 gate；P7 锚为 `final-execution-plan.md:213`。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据（四元组） |
|---------|--------|------|----|------|------|-----------|
| P4-T01 | RVC fake train/convert creates run/artifacts | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_rvc_adapter.py` | P4-01 → run rows | commit {sha} + pytest tests/unit/adapters/test_rvc_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P4-T02 | TTS fake synth creates rendered artifact | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_xtts_adapter.py` | P4-02 → rendered artifact | commit {sha} + pytest tests/unit/adapters/test_xtts_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P4-T03 | eval pack checksum stable | 短途 | unit | 🆕 新增 `tests/unit/eval/test_eval_pack.py` | P4-03 → reusable pack | commit {sha} + pytest tests/unit/eval/test_eval_pack.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P4-T04 | baseline report入库 | 短途 | unit | 🆕 新增 `tests/unit/eval/test_baseline_report.py` | P4-04 → report row | commit {sha} + pytest tests/unit/eval/test_baseline_report.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P4-T05 | long_train_ready gate logic | 短途 | unit | 🆕 新增 `tests/unit/eval/test_long_train_gate.py` | P4-05 → gate report | commit {sha} + pytest tests/unit/eval/test_long_train_gate.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P3 frozen manifest fixture | ♻️ 沿用 | 作为 training input | P3 完成后可用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit tests/unit/adapters tests/unit/eval` | unit | 每次 P4 改动 |
| spike | `pytest -m live` | live | 真实 RVC/TTS smoke 可选 |
| mega | 不适用 | - | P8 |
| soak | 不适用 | - | P4 无长稳 |

### 8.4 测试缺口

- 不覆盖真实 RVC/TTS 音质（理由：unit suite 用 fake adapter）→ P4 live smoke 或 P6 subjective eval。

### 8.5 测试保真

- fake baseline 只能证明 contract，不证明模型质量。
- gate test 必须覆盖 false/degraded reason。
- report test 必须验证 artifacts 和 DB row 双写。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| baseline 质量被过度解读 | fake/live smoke 非最终质量 | medium | report 明确用途 |
| gate 过松 | 低质数据进入 P5 | high | gate reason + P3 corpus report |
| adapter 泄漏外部仓路径 | API/Domain 耦合 | medium | adapter DTO tests |

### 9.2 约束与前提

- **技术前提**：P3 frozen manifest 可用。
- **运行时前提**：默认 fake adapters。
- **组织协作前提**：真实模型路径可后续配置。
- **上线 / 合并前提**：P4-T01..T05 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：baseline report contract。
- 需要同步更新的说明文档 / README：P8 quickstart。
- 需要同步更新的测试说明：live baseline marker。

### 9.4 完成后的预期状态

1. P5 有明确 long-train gate。
2. P6 可读取 baseline run 和 report。
3. RVC/TTS baseline 均通过 adapter contract 接入。

---

## 10. 收口

### 10.1 收口硬闸

1. RVC/TTS fake baseline flows PASS。
2. Baseline report 入库且链接 artifacts。
3. `long_train_ready` gate 可查询且覆盖 false reason。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组） | 状态 |
|----------|--------|---------|-----------|------|
| RVC run | P4-01 | P4-T01 | commit {sha} + pytest tests/unit/adapters/test_rvc_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| TTS render | P4-02 | P4-T02 | commit {sha} + pytest tests/unit/adapters/test_xtts_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| eval pack | P4-03 | P4-T03 | commit {sha} + pytest tests/unit/eval/test_eval_pack.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| baseline report | P4-04 | P4-T04 | commit {sha} + pytest tests/unit/eval/test_baseline_report.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| long gate | P4-05 | P4-T05 | commit {sha} + pytest tests/unit/eval/test_long_train_gate.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | baseline run/report/gate 完成 |
| 测试 | P4-T01..P4-T05 全 PASS |
| 文档 | P5 可引用 gate |
| 风险收敛 | baseline 不被误作最终质量 |
| 可交付性 | 可进入 P5/P6 |

### 10.4 NOT-成功识别

未使用 frozen manifest、report 不入库、或 gate 缺失 false/degraded reason，不得标 `executed`。


## 11. 工作日志

- **2026-06-13**:
  - 重新梳理了 P4 Action-plan 背景与具体需求，梳理了 DTO 与分层规范。
  - 在 `src/myvoiceclone/domain/entities.py` 中添加了 `TrainRequest`, `TrainResult`, `SynthRequest`, `SynthResult`, `ConvertRequest`, `ConvertResult` DTO 实体。
  - 创建并实现了 `src/myvoiceclone/adapters/training/rvc_adapter.py` 和 `xtts_adapter.py`，提供 mock 支持。
  - 编写并实现 `src/myvoiceclone/pipelines/train.py`，建立了 RVC 和 XTTS 训练/合成流水线，实现 dataset 冻结状态校验与 artifacts 自动化注册。
  - 扩展了 `src/myvoiceclone/eval/report.py`，实现 `generate_eval_pack`, `generate_baseline_report` 和 `evaluate_long_train_gate`。
  - 编写了完整的测试套件 `test_rvc_adapter.py`, `test_xtts_adapter.py`, `test_train.py` 与 `test_baseline_report.py`。
  - 运行并跑通了所有 50 项单元测试，没有出现任何退化和冲突。

