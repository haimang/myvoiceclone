# Nano-Agent 行动计划：P7 Security & Governance Retrofit

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P7 Security & Governance Retrofit`
> 类型: `upgrade`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/07-security-governance-retrofit.md`
> 上游前序 / closure:
> - `06-eval-inference-api.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:213`
> 下游交接:
> - `08-ops-handoff.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:213`（P7 工作台账）
> - `final-execution-plan.md:503`（Q2）
> 冻结决策来源:
> - `final-execution-plan.md:503`（Q2）
> grounding 来源:
> - `final-execution-plan.md:217`、`:408`、`:405`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P7 是 first-build 的安全与治理后置接入阶段。根据冻结 Q2，P0-P6 不实现授权/安全拦截，但 P1 已预留 security placeholder schema，P6 已有 inference artifact 和 report/audit trace。P7 在不破坏早期开发流的前提下，启用 consent policy、release gate 和 synthetic output metadata。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P7 Security & Governance Retrofit`
- **本次计划解决的问题**：
  - P0-P6 产物需要在 release 前接入 consent/release policy。
  - inference rendered artifacts 需要 synthetic metadata/watermark placeholder。
  - 本地 SOP 需要说明允许/禁止用途。
- **本次计划的直接产出**：
  - `domain/policies.py` policy implementation。
  - release gate route/service tests。
  - security/authorization SOP docs。
- **本计划不重新讨论的设计结论**：
  - 安全/授权初期后置，P7 才启用（来源：`final-execution-plan.md:503`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先 feature flag，再 policy service，再 release gate，再 artifact metadata，再 SOP”的方式。P7 不回改 P1-P6 的核心流；它只在 release/inference metadata 层启用治理控制。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Policy feature flag | S | P7 前 off，P7 后可启用 | P6 |
| Phase 2 | Consent policy | M | recording/speaker/model release 前校验 | Phase 1 |
| Phase 3 | Release gate | M | model_run -> release_candidate policy pass | Phase 2 |
| Phase 4 | Synthetic metadata | S | rendered output 标记合成属性 | Phase 3 |
| Phase 5 | SOP docs | S | 安全/授权操作说明 | Phase 4 |

### 1.3 Phase 说明

1. **Phase 1 — Policy feature flag**
   - **核心目标**：确保治理可启用但不破坏 P0-P6。
   - **为什么先做**：避免 retrofitting 造成全链回归。
2. **Phase 2 — Consent policy**
   - **核心目标**：消费 P1 的 consent placeholder。
   - **为什么放在这里**：release gate 需要 policy result。
3. **Phase 3 — Release gate**
   - **核心目标**：release_candidate 前检查 policy。
   - **为什么放在这里**：训练/评估可以完成，发布需治理。
4. **Phase 4 — Synthetic metadata**
   - **核心目标**：推理产物记录 synthetic flag。
   - **为什么放在这里**：P6 inference artifact 已存在。
5. **Phase 5 — SOP docs**
   - **核心目标**：让开发者知道何时启用和如何处理失败。
   - **为什么放在这里**：P8 handoff 需要引用。

### 1.4 执行策略说明

- **执行顺序原则**：feature flag 先于 enforcement。
- **风险控制原则**：P7 前所有 tests 继续通过；P7 policy tests 只在 enabled flag 下检查阻断。
- **测试推进原则**：包含攻击/滥用向量用例，不只测 happy path。
- **文档同步原则**：SOP 写明 P0-P6 与 P7 的边界。
- **回滚 / 降级原则**：policy 可通过 feature flag 关闭，但 release gate 状态要记录 waived reason。

### 1.5 本次 action-plan 影响结构图

```text
P7 Security Retrofit
├── src/myvoiceclone/domain/policies.py
├── db/migrations/005_security_placeholders.sql
├── src/myvoiceclone/api/routes_reports.py / release gate service
├── artifacts rendered metadata
├── docs/ops/security-governance.md
└── tests/unit/domain + tests/api
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** consent/release policy feature flag。
- **[S2]** release gate status and policy_events。
- **[S3]** rendered artifact synthetic metadata placeholder。
- **[S4]** security/authorization SOP。

### 2.2 Out-of-Scope

- **[O1]** 多用户认证系统。
- **[O2]** 云端权限和租户隔离。
- **[O3]** 强音频水印算法实现。
- **[O4]** 法律合规判断自动化。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| release gate | in-scope | Q2 后置接入点 | 发布流程变化 |
| auth middleware | out-of-scope | first-build 本地单用户 | SaaS 化 |
| synthetic metadata | in-scope | inference artifact 需要标记 | 水印算法阶段 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P7-01 | Phase 2 | Consent policy | add/update | `domain/policies.py`, `consent_ledger` | flag on 后 release 前校验 | P7-T01 | high |
| P7-02 | Phase 3 | Release gate | add | `release_gates`, `policy_events`, API/service | policy failure blocks release only | P7-T02 | high |
| P7-03 | Phase 4 | Synthetic metadata | update | `artifacts.metadata_json`, inference output | rendered artifact 记录 synthetic flag | P7-T03 | medium |
| P7-04 | Phase 5 | Security SOP docs | add | `docs/ops/security-governance.md` | SOP 完成且不阻塞 earlier pipeline | P7-T04 | medium |

---

## 4. Phase 业务表格

### 4.1 Phase 1/2 — Feature flag + consent policy

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P7-01 | Consent policy | a) 增 `security.enabled` flag；b) flag off 时 P1-P6 行为不变；c) flag on 时读取 consent_ledger；d) 未授权 speaker 阻断 release_candidate；e) 写 policy_events reason | `domain/policies.py`, `consent_ledger` | policy 可启用可关闭 | P7-T01 | on/off tests PASS |

### 4.2 Phase 3 — Release gate

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P7-02 | Release gate | a) 创建 release_gates pending；b) 跑 consent/report checks；c) passed/failed/waived 三态；d) failed 不影响已有训练 artifacts；e) waived 必须 reason | `release_gates`, `routes_reports.py` | release 前可控 | P7-T02 | failure blocks release PASS |

### 4.3 Phase 4/5 — Metadata + docs

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P7-03 | Synthetic metadata | a) inference artifact metadata 加 `synthetic=true`；b) 记录 source model_run；c) watermark placeholder 字段；d) 不实现强水印算法 | `routes_inference.py`, `artifact_store.py` | 输出可识别为合成 | P7-T03 | metadata tests PASS |
| P7-04 | Security SOP docs | a) 写允许/禁止用途；b) 写 consent evidence 录入；c) 写 gate failed/waived 操作；d) 写 P0-P6 无拦截边界 | `docs/ops/security-governance.md` | handoff 可用 | P7-T04 | doc review PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2/3 — Policy and release gate

- **Phase 目标**：启用本地 release 前治理，不破坏训练和评估。
- **本 Phase 对应编号**：P7-01 / P7-02
- **本 Phase 新增 / 修改文件**：`domain/policies.py`, release gate service/API, security tables
- **具体功能预期**：
  1. policy disabled 时 P0-P6 tests 不改变。
  2. policy enabled 时未授权 speaker 不能 release_candidate。
  3. failed gate 只阻止 release，不删除 model_run。
  4. waived gate 需要 reason 并入 policy_events。
  5. policy result 可被 audit trace 查到。
- **对应测试台账项**：P7-T01 / P7-T02
- **收口标准**：攻击向量和 happy path 都通过测试。
- **本 Phase 风险提醒**：不要把 P7 变成完整用户权限系统。

### 5.2 Phase 4/5 — Metadata and SOP

- **Phase 目标**：合成输出具备最小治理标记和操作说明。
- **本 Phase 对应编号**：P7-03 / P7-04
- **本 Phase 新增文件**：`docs/ops/security-governance.md`
- **具体功能预期**：
  1. rendered artifact metadata 记录 synthetic flag。
  2. metadata 不替代强水印。
  3. SOP 说明如何开启/关闭 policy。
  4. SOP 说明 consent evidence 记录方式。
  5. SOP 说明 release gate failed/waived 处理。
- **对应测试台账项**：P7-T03 / P7-T04
- **收口标准**：P8 handoff 可直接引用。
- **本 Phase 风险提醒**：不要承诺法律合规自动化。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q2 | `final-execution-plan.md:503` | P7 后置接入 | 若提前启用需重开 final |
| Q6 | `final-execution-plan.md:507` | policy_events/audit 必填 | 不得 silent block |
| Q7 | `final-execution-plan.md:508` | 安全测试含攻击向量 | 不得只测 happy path |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-1 | `final-execution-plan.md:213` | P7 工作台账 | P7-01..04 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:408` | `domain/policies.py` | P7-01 | ✅ 复用 | policy |
| A-3 | `final-execution-plan.md:405` | security placeholder migration | P7-01..02 | ✅ 复用 | DB-005 |
| A-4 | `final-execution-plan.md:217` | consent policy item | P7-01 | ✅ 复用 | threat anchor |
| A-5 | `final-execution-plan.md:218` | release gate item | P7-02 | ✅ 复用 | threat anchor |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | P7 回改 P2-P6 核心流程 | Q2 是后置 retrofit，不是重写 |
| ⛔2 | 只测授权通过，不测未授权阻断 | 安全项必须有攻击向量 |
| ⛔3 | waived gate 不记录 reason | Q6 审计要求 |
| ⛔4 | metadata 声称强水印 | P7 只做 placeholder |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：`final-execution-plan.md:217`、`:218`、`:219`。攻击向量：未授权 speaker 尝试 release；无 evidence 尝试 pass；waive 无 reason；合成输出无 metadata。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据（四元组） |
|---------|--------|------|----|------|------|-----------|
| P7-T01 | policy flag off/on + unauthorized block | 短途 | unit | 🆕 新增 `tests/unit/domain/test_policies.py` | P7-01 → policy 可控 | commit {sha} + pytest tests/unit/domain/test_policies.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P7-T02 | release gate passed/failed/waived | 短途 | 集成 | 🆕 新增 `tests/api/test_release_gate.py` | P7-02 → release 前阻断 | commit {sha} + pytest tests/api/test_release_gate.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P7-T03 | synthetic metadata on rendered artifact | 短途 | unit | 🆕 新增 `tests/unit/test_synthetic_metadata.py` | P7-03 → metadata 记录 | commit {sha} + pytest tests/unit/test_synthetic_metadata.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P7-T04 | SOP doc covers gate/waive/consent | 短途 | 文档 | 🆕 新增 `docs-review:P7-security-governance` | P7-04 → SOP 可交付 | commit {sha} + docs-review:P7-security-governance PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P6 inference artifact fixture | ♻️ 沿用 | 添加 synthetic metadata assertions | P6 完成后可用 |
| P1 security placeholder tables | ♻️ 沿用 | 启用 policy reads | P1 完成后可用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit tests/unit/domain tests/api/test_release_gate.py` | unit·api | P7 改动 |
| spike | 不适用 | - | 无 |
| mega | P8 capstone 含 policy-on 变体 | integration | P8 |
| soak | 不适用 | - | 无 |

### 8.4 测试缺口

- 不覆盖法律合规充分性（理由：需人工/legal 判断）→ 交 owner/法律评审。
- 不覆盖强音频水印鲁棒性（理由：P7 只做 metadata placeholder）→ 后续安全专项。

### 8.5 测试保真

- 安全测试必须包含 unauthorized、missing evidence、waive missing reason 三类攻击向量。
- policy disabled PASS 不代表系统安全，只证明后置边界。
- metadata PASS 不等同强水印。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| retrofit 破坏 P0-P6 | 加 gate 太早 | high | feature flag + regression |
| 安全能力被高估 | metadata 不是水印 | medium | SOP 明确限制 |
| waived 滥用 | 规避 gate | medium | reason + audit trace |

### 9.2 约束与前提

- **技术前提**：P1 security tables、P6 inference/report 已完成。
- **运行时前提**：本地单用户，无多租户 auth。
- **组织协作前提**：owner 提供 consent evidence 策略。
- **上线 / 合并前提**：P7-T01..T04 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：security/governance notes。
- 需要同步更新的说明文档 / README：P8 handoff。
- 需要同步更新的测试说明：security attack cases。

### 9.4 完成后的预期状态

1. Release candidate 前有本地 policy gate。
2. Synthetic outputs 有最小 metadata 标记。
3. SOP 解释安全边界和操作流程。

---

## 10. 收口

### 10.1 收口硬闸

1. Policy enabled/disabled 行为可测。
2. Unauthorized release 被阻断并记录 policy_event。
3. Synthetic metadata 写入 rendered artifacts。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组） | 状态 |
|----------|--------|---------|-----------|------|
| consent policy | P7-01 | P7-T01 | commit MVC-P7-complete + pytest tests/unit/domain/test_policies.py PASS + 2026-06-13 11:35 UTC | verified |
| release gate | P7-02 | P7-T02 | commit MVC-P7-complete + pytest tests/api/test_release_gate.py PASS + 2026-06-13 11:35 UTC | verified |
| synthetic metadata | P7-03 | P7-T03 | commit MVC-P7-complete + pytest tests/unit/test_synthetic_metadata.py PASS + 2026-06-13 11:35 UTC | verified |
| SOP | P7-04 | P7-T04 | commit MVC-P7-complete + docs/ops/security-governance.md written + 2026-06-13 11:35 UTC | verified |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | policy/release/metadata/SOP 完成 |
| 测试 | P7-T01..P7-T04 全 PASS |
| 文档 | SOP 可被 P8 引用 |
| 风险收敛 | 安全后置能力清晰不夸大 |
| 可交付性 | 可进入 P8 |

### 10.4 NOT-成功识别

只测 happy path、waive 无 reason、或把 metadata 宣称为强水印，均不得标 `executed`。
