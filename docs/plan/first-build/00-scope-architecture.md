# Nano-Agent 行动计划：P0 Scope Freeze & Architecture Charter

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P0 Scope Freeze & Architecture Charter`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/00-scope-architecture.md`
> 上游前序 / closure:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:132`
> 下游交接:
> - `01-storage-vec0-skeleton.md`
> 关联设计 / 调研文档:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`
> 冻结决策来源:
> - `final-execution-plan.md:498`（Q1/Q2/Q5/Q7/Q8）
> grounding 来源:
> - `final-execution-plan.md:132`、`:240`、`:373`、`:481`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `frozen`

---

## 0. 执行背景与目标

P0 是 first-build 的执行入口，用来把目标、边界、分层原则和测试分类先冻结下来。它不实现业务代码，但要为 P1-P8 提供不可再漂移的 architecture charter 和执行约束，避免后续在数据库、pipeline、API、训练适配器之间反复改口。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P0 Scope Freeze & Architecture Charter`
- **本次计划解决的问题**：
  - 明确 first-build 是本地单用户 voice clone 工作台，不是云端多租户产品。
  - 明确 P0-P6 不做授权/安全拦截，P7 后置接入。
  - 固化 domain/storage/vector/artifact/pipeline/adapter/job/api/cli/eval 分层和测试 marker。
- **本次计划的直接产出**：
  - `docs/plan/first-build/00-scope-architecture.md`
  - `docs/architecture/layers.md`
  - `pytest.ini` marker 计划
- **本计划不重新讨论的设计结论**：
  - VC/SVC 主线 + TTS baseline 可选（来源：`final-execution-plan.md:502`）
  - 初期不实现授权安全，P7 再接入（来源：`final-execution-plan.md:503`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先冻结边界，再写架构约束，最后固化测试分类”的方式执行。P0 的产物是文档和配置入口，不创建业务实现；它的价值是给 P1-P8 提供统一约束。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Scope charter | S | 固化 first-build 目标和非目标 | final plan |
| Phase 2 | Layer charter | S | 写明分层依赖边界和反向依赖禁令 | Phase 1 |
| Phase 3 | Test taxonomy | XS | 定义 pytest markers 和默认测试边界 | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Scope charter**
   - **核心目标**：把本地工作台、VC/SVC 主线、TTS baseline 可选写成执行边界。
   - **为什么先做**：P1 的 skeleton 和依赖配置依赖该边界。
2. **Phase 2 — Layer charter**
   - **核心目标**：冻结 domain/storage/pipeline/adapter/api/job/eval 的职责与禁止依赖。
   - **为什么放在这里**：后续代码生成必须按此分层落文件。
3. **Phase 3 — Test taxonomy**
   - **核心目标**：定义 unit/api/cli/integration/live/gpu/slow markers。
   - **为什么放在这里**：P1 起所有 AP 都要引用相同测试语义。

### 1.4 执行策略说明

- **执行顺序原则**：先文档边界，再架构边界，再测试边界。
- **风险控制原则**：所有安全/授权讨论只保留 P7 接入点，不在 P0 引入阻塞。
- **测试推进原则**：P0 只定义 markers 与架构边界测试，不跑真实模型。
- **文档同步原则**：P0 完成后，P1-P8 AP 必须引用本文件和 final plan。
- **回滚 / 降级原则**：如后续 owner 改变目标形态，回到 final plan 级别重开，不在 P0 局部改口。

### 1.5 本次 action-plan 影响结构图

```text
P0 Scope Freeze
├── docs/plan/first-build/00-scope-architecture.md
├── docs/architecture/layers.md
├── pytest.ini marker plan
└── downstream P1-P8 execution constraints
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** first-build 目标、非目标和阶段边界。
- **[S2]** 分层职责和禁止依赖。
- **[S3]** 测试 marker 分类和默认跑法。
- **[S4]** P0 对 P1-P8 的交接条件。

### 2.2 Out-of-Scope

- **[O1]** 创建 Python package skeleton，交给 P1。
- **[O2]** 实现 SQLite schema，交给 P1。
- **[O3]** 实现授权/安全策略，交给 P7。
- **[O4]** 跑模型训练或音频处理，交给 P2-P5。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 本地单用户工作台 | in-scope | Q1 冻结 | owner 改成 SaaS |
| 授权安全实现 | out-of-scope | Q2 冻结为 P7 后置 | P7 启动 |
| 分层依赖规则 | in-scope | Q5 冻结 | 出现无法按层实现的硬约束 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P0-01 | Phase 1 | 固化 first-build 目标 | add | `docs/plan/first-build/00-scope-architecture.md` | 目标和非目标可被 P1-P8 引用 | P0-T01 | low |
| P0-02 | Phase 1 | 后置授权/安全边界 | add | `docs/plan/first-build/00-scope-architecture.md` | 明确 P0-P6 不做安全拦截，P7 接入 | P0-T02 | medium |
| P0-03 | Phase 2 | 分层架构说明 | add | `docs/architecture/layers.md` | domain/storage/vector/artifact/pipeline/adapter/job/api/cli/eval 职责与禁止依赖写明 | P0-T03 | medium |
| P0-04 | Phase 3 | 测试 marker 计划 | add | `pytest.ini` | markers 语义可被 P1-P8 测试引用 | P0-T04 | low |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Scope charter

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P0-01 | 固化 first-build 目标 | a) 摘录 Q1/Q8；b) 写明本地工作台、VC/SVC 主线、TTS baseline 可选；c) 写明 P1-P8 的消费关系 | `docs/plan/first-build/00-scope-architecture.md` | 目标不会在后续 AP 中重复争论 | P0-T01 | downstream AP 能引用目标段 |
| P0-02 | 后置授权/安全边界 | a) 摘录 Q2；b) 写明 P0-P6 不做拦截；c) 写明 P1 只预留 schema、P7 启用策略；d) 标明不得在早期 API 加 auth gate | `docs/plan/first-build/00-scope-architecture.md` | 安全边界清晰且不阻塞 P1-P6 | P0-T02 | P1-P6 AP 均不引入 auth blocker |

### 4.2 Phase 2 — Layer charter

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P0-03 | 分层架构说明 | a) 建 `docs/architecture/layers.md`；b) 按 final §12.3 写 domain/storage/vector/artifact/pipeline/adapter/job/api/cli/eval 允许依赖/禁止依赖；c) 写 import boundary 规则；d) 列出后续文件所属层 | `docs/architecture/layers.md` | 所有 source 文件能归属唯一主层 | P0-T03 | boundary 文档可直接转为 import test |

### 4.3 Phase 3 — Test taxonomy

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P0-04 | 测试 marker 计划 | a) 在 `pytest.ini` 规划 unit/api/cli/integration/live/gpu/slow；b) 写明默认排除 live/gpu/slow；c) 对齐 final §8.1 | `pytest.ini` | P1 起测试台账可稳定引用 markers | P0-T04 | marker 文档与 final 测试分类一致 |

---

## 5. Phase 详情

### 5.1 Phase 1 — Scope charter

- **Phase 目标**：冻结 P0-P8 的共同目标与早期安全边界。
- **本 Phase 对应编号**：P0-01 / P0-02
- **本 Phase 新增文件**：`docs/plan/first-build/00-scope-architecture.md`
- **具体功能预期**：
  1. 明确 first-build 不是 SaaS，不设计多租户权限。
  2. 明确模型路线：VC/SVC 主线，TTS baseline 可选。
  3. 明确 P0-P6 不实现授权/安全拦截。
  4. 明确 P7 是安全治理接入 phase。
  5. 明确任何后续 AP 若改变以上结论，必须回到 final plan 层级。
- **对应测试台账项**：P0-T01 / P0-T02
- **收口标准**：P1-P8 AP 能引用 P0 边界，无新增 OPEN gate。
- **本 Phase 风险提醒**：安全边界容易被误读为“永远不做安全”；文档必须写成“后置接入”。

### 5.2 Phase 2 — Layer charter

- **Phase 目标**：建立低耦合高内聚的分层执行约束。
- **本 Phase 对应编号**：P0-03
- **本 Phase 新增文件**：`docs/architecture/layers.md`
- **具体功能预期**：
  1. domain 不 import storage/vector/artifact/api/adapters/FastAPI。
  2. storage/vector/artifact 不 import adapters/FastAPI。
  3. adapters 不写 repository，不泄漏外部工具私有格式。
  4. api/cli 调 service/job，不直连外部工具。
  5. eval/report 不依赖训练仓库内部结构。
- **对应测试台账项**：P0-T03
- **收口标准**：后续可实现 `tests/unit/test_architecture_boundaries.py`。
- **本 Phase 风险提醒**：过早抽象会拖慢 P1；只冻结边界，不写复杂框架。

### 5.3 Phase 3 — Test taxonomy

- **Phase 目标**：为所有后续 AP 定义统一测试分类。
- **本 Phase 对应编号**：P0-04
- **本 Phase 新增 / 修改 / 删除文件**：`pytest.ini`
- **具体功能预期**：
  1. 默认 unit/api/cli/integration mock tests 可运行。
  2. live/gpu/slow 必须显式选择。
  3. 测试台账 PASS 证据使用 commit + test + run-time。
- **对应测试台账项**：P0-T04
- **收口标准**：P1-P8 AP 测试台账复用该 taxonomy。
- **本 Phase 风险提醒**：不要把真实模型 smoke 放进默认测试。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q1 | `final-execution-plan.md:502` | 决定 scope charter 的模型路线 | 回到 eval/final 重开 |
| Q2 | `final-execution-plan.md:503` | 决定安全后置 | 回到 eval/final 重开 |
| Q5 | `final-execution-plan.md:506` | 决定分层边界 | 后续代码不得绕过 |
| Q7 | `final-execution-plan.md:508` | 决定测试 marker | 后续 AP 复用 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `myvoiceclone/docs/eval/first-build/final-execution-plan.md:132` | P0 工作台账 | P0-01..04 | ✅ 复用 | P0 权威来源 |
| A-2 | `myvoiceclone/docs/eval/first-build/final-execution-plan.md:240` | gate closure | P0-01..02 | ✅ 复用 | Q1/Q2 |
| A-3 | `myvoiceclone/docs/eval/first-build/final-execution-plan.md:481` | 抽象层详细安排 | P0-03 | ✅ 复用 | 形成 layers.md |
| A-4 | `myvoiceclone/docs/eval/first-build/final-execution-plan.md:255` | test taxonomy | P0-04 | ✅ 复用 | 形成 pytest markers |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 在 P0 重开模型路线辩论 | Q1 已冻结 |
| ⛔2 | 在 P0 引入认证/授权实现 | Q2 已冻结为 P7 后置 |
| ⛔3 | 让 API 直接调用 pyannote/Demucs/RVC | Q5 要求 adapter/service 分层 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：`final-execution-plan.md:213` P7 Security Retrofit；P0 只后置安全实现，不执行安全控制。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| P0-T01 | scope charter 包含 Q1 目标与 P1-P8 交接 | 短途 | 文档 | 🆕 新增 `docs-review:P0-scope` | P0-01 → 目标可引用 | commit {sha} + docs-review:P0-scope PASS + {YYYY-MM-DD HH:MM UTC} |
| P0-T02 | early no auth enforcement 表述与 P7 接入一致 | 短途 | 文档 | 🆕 新增 `docs-review:P0-security-boundary` | P0-02 → 不阻塞 P1-P6 | commit {sha} + docs-review:P0-security-boundary PASS + {YYYY-MM-DD HH:MM UTC} |
| P0-T03 | layer 文档覆盖 final §12.3 所有层 | 短途 | 契约 | 🆕 新增 `tests/unit/test_architecture_boundaries.py` | P0-03 → 分层可测试 | commit {sha} + pytest tests/unit/test_architecture_boundaries.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P0-T04 | pytest markers 与 final §8.1 一致 | 短途 | 契约 | 🆕 新增 `tests/unit/test_pytest_markers.py` | P0-04 → marker 可复用 | commit {sha} + pytest tests/unit/test_pytest_markers.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| N/A | 🆕 新增 | P0 是首个执行边界计划 | 无既有测试 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit` + docs review | unit·文档 | P0 收口 |
| spike | 不适用 | - | P0 不跑 live |
| mega | 不适用 | - | 交给 P8 |
| soak | 不适用 | - | P0 无长稳 |

### 8.4 测试缺口

- 不覆盖真实 package import graph（理由：P1 尚未创建 package）→ 交 P1/P8。

### 8.5 测试保真

- PASS 必带四元组证据。
- P0 不能用“文档已写”替代 P0-T03/P0-T04 的可测试性。
- 安全项只验证后置边界，不伪造安全实现。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| 边界写得过抽象 | P1 无法消费 | medium | 每条边界都绑定后续文件/测试 |
| 安全后置被误解 | 后续忽略 P7 | medium | P0 明确 P7 是必须 phase |

### 9.2 约束与前提

- **技术前提**：仓库尚无代码 skeleton。
- **运行时前提**：P0 不运行外部模型。
- **组织协作前提**：后续 AP 不重开 Q1/Q2/Q5/Q7。
- **上线 / 合并前提**：P0 文档和 marker 计划被 P1 引用。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/architecture/layers.md`
- 需要同步更新的说明文档 / README：P8 统一接入 README
- 需要同步更新的测试说明：`pytest.ini` marker 注释

### 9.4 完成后的预期状态

1. P1 能直接开始 repo skeleton。
2. 后续 AP 对安全/授权没有早期阻塞。
3. 分层和测试分类有统一引用。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

1. Scope charter 与 Q1/Q2 一致（由 P0-T01/P0-T02 证明）。
2. Layer charter 可被 import boundary test 消费（由 P0-T03 证明）。
3. pytest marker taxonomy 可被 P1-P8 复用（由 P0-T04 证明）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 目标可引用 | P0-01 | P0-T01 | commit {sha} + docs-review:P0-scope PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| 安全后置明确 | P0-02 | P0-T02 | commit {sha} + docs-review:P0-security-boundary PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| 分层可测试 | P0-03 | P0-T03 | commit {sha} + pytest tests/unit/test_architecture_boundaries.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| markers 可复用 | P0-04 | P0-T04 | commit {sha} + pytest tests/unit/test_pytest_markers.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | P0 文档、layer charter、marker 计划完成 |
| 测试 | §8 测试台账全 PASS |
| 文档 | P1-P8 可引用 P0 边界 |
| 风险收敛 | 安全后置不再阻塞 P1-P6 |
| 可交付性 | 可进入 P1 |

### 10.4 NOT-成功识别

任一 P0-T 测试未观察或 P1 无法消费 P0 边界，不得标 `executed`。
