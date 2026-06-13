# FT5 Real Evaluation Action Plan

> 服务业务簇: `FT5 · 真实评估与 release gate`
> 计划对象: `smoke metrics, objective proxy, subjective intake, release gate`
> 类型: `upgrade`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT5-real-evaluation.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT4-real-inference.md`
> 下游交接:
> - `docs/plan/first-test/FT6-fastapi-e2e.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT5`, `reference-anchor axis D/F/H`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT5 把 first-test 从“产出真实音频”推进到“能判断真实音频是否可继续流转”。它不把代理指标当成最终音质结论，而是建立三层评估：可机械验证的 smoke metrics、可选 objective proxy、本地人工 MOS/ABX 录入，并让 release gate 明确区分 `smoke pass`、`quality pass`、`manual waived`。

- **服务业务簇**：`Evaluation / release gate`
- **计划对象**：evaluation services, reports, release gates, subjective intake
- **本次计划解决的问题**：
  - 当前 objective/scoring 路径多为 mock，缺 metric source 标记。
  - release gate 无法表达 smoke、quality、manual waiver 的不同语义。
  - subjective eval 已有报告骨架，但未成为真实评估输入。
- **本次计划的直接产出**：
  - smoke evaluator 与 deterministic wav fixture 测试。
  - objective proxy unavailable 语义。
  - subjective MOS/ABX service/API 与 release gate 分层。
  - eval report 关联 input/output artifact、adapter mode、metric source。
- **本计划不重新讨论的设计结论**：
  - 代理指标不能替代主观听感（来源：`docs/eval/first-test/reference-anchor.md:136-140`）。
  - 真实证据必须落 DB/artifact/evidence pack（来源：`docs/eval/first-test/reference-anchor.md:189-195`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先定义指标来源和报告字段，再实现 smoke evaluator 与 proxy runner，最后接入人工评分和 gate 语义。FT5 的收口不是“音质达标”，而是“质量判断过程可追溯、可复核、不会把 mock/proxy 冒充真实结论”。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Metric taxonomy | S | 固定 smoke/proxy/manual/release 字段语义 | FT2/FT4 |
| Phase 2 | Evaluators | M | 实现 smoke metrics 与可选 objective proxy | Phase 1 |
| Phase 3 | Subjective and gate | M | 主观录入、report、release gate trace | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Metric taxonomy**
   - **核心目标**：冻结 `metric_source`、`adapter_mode`、artifact refs 的语义和 canonical 落点；当前 DB 没有同名顶层列，优先落 `eval_metrics.metric_json`、report summary 与 `eval_samples.*_artifact_id`。
   - **为什么先做**：后续 API/report/release 依赖这些字段解释评估可信度。
2. **Phase 2 — Evaluators**
   - **核心目标**：给真实 wav 产出基础健康指标，并让 proxy 缺依赖时显式 unavailable。
   - **为什么放在这里**：先有机械证据，再进入人工判断。
3. **Phase 3 — Subjective and gate**
   - **核心目标**：人工 MOS/ABX 和 release gate 形成可追溯判定。
   - **为什么放在这里**：release 只能消费已经分层的评估结果。

### 1.4 执行策略说明

- **执行顺序原则**：taxonomy → smoke evaluator → proxy gating → subjective intake → release gate。
- **风险控制原则**：`mock`、`objective_proxy`、`manual_mos` 必须在 metadata/report 中显式区分。
- **测试推进原则**：先用短 wav fixture 做 deterministic unit，再用 TestClient 覆盖 report/gate 查询。
- **文档同步原则**：评估报告必须写明“不代表生产发布许可”。
- **回滚 / 降级原则**：proxy 缺依赖只标 unavailable；不得写 fake real score。

### 1.5 影响结构图

```text
FT5 Real Evaluation
├── eval taxonomy
│   ├── src/myvoiceclone/eval/objective.py
│   ├── src/myvoiceclone/eval/report.py
│   └── src/myvoiceclone/api/schemas.py
├── evaluators
│   ├── new smoke evaluator
│   └── optional proxy runner
├── subjective / gate
│   ├── src/myvoiceclone/eval/subjective.py
│   └── src/myvoiceclone/api/routes_reports.py
└── tests
    ├── unit/eval
    ├── db/unit
    └── api/TestClient
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** smoke metrics：loudness、silence、clipping、duration、transcript sanity。
- **[S2]** 可选 objective proxy runner，缺依赖时标 unavailable。
- **[S3]** subjective MOS/ABX/comment/reviewer/sample artifact 录入。
- **[S4]** release gate 分层语义。
- **[S5]** eval report 关联 input artifact、inference artifact、metric source、adapter mode。

### 2.2 Out-of-Scope

- **[O1]** 众包 P.808 平台。
- **[O2]** 生产级音质结论。
- **[O3]** 模型许可最终裁定，FT5 只消费 FT4 provenance。
- **[O4]** 完整 OTel trace，仍由 DB/evidence 降级承接。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| smoke metrics | in-scope | first-test 必须发现空音频/静音/爆音 | fixture 无法稳定 |
| objective proxy | conditional | 依赖模型/库可能不可用 | live env 具备后转 pass |
| subjective eval | in-scope | release gate 不能只靠代理指标 | 需要多人众包时另开 |
| crowd MOS | defer | 超出 first-test 本地闭环 | production quality gate |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT5-P1-01 | Phase 1 | metric taxonomy | update | `src/myvoiceclone/eval/objective.py:43-80`, `src/myvoiceclone/eval/report.py:8-164` | 指标来源和 artifact refs 可解释 | FT5-T01 | medium |
| FT5-P1-02 | Phase 1 | report schema fields | update | `src/myvoiceclone/api/schemas.py:87-107`, `db/migrations/004_reports_metrics.sql` | API/DB 能表达 source/mode | FT5-T04 | medium |
| FT5-P2-01 | Phase 2 | smoke evaluator | add | `src/myvoiceclone/eval/smoke.py`, `src/myvoiceclone/storage/artifact_store.py:15-104` | 短 wav fixture 产 deterministic fields | FT5-T01 | medium |
| FT5-P2-02 | Phase 2 | objective proxy gating | update | `src/myvoiceclone/eval/objective.py:16-41` | 缺依赖不写 real score | FT5-T02 | medium |
| FT5-P3-01 | Phase 3 | subjective eval service/API | update | `src/myvoiceclone/eval/subjective.py:8-80`, `src/myvoiceclone/api/routes_reports.py:96-127` | MOS/ABX payload 可校验可查询 | FT5-T03 / FT5-T06 | medium |
| FT5-P3-02 | Phase 3 | release gate layering | update | `src/myvoiceclone/api/routes_reports.py:96-179`, `src/myvoiceclone/domain/policies.py` | smoke/quality/waived 语义清楚 | FT5-T05 | high |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT5.1` | FT5-P1-01 / FT5-P1-02 | `T-FT5.1` | FT5-T01 |
| `FT5.2` | FT5-P2-01 | `T-FT5.2` | FT5-T01 |
| `FT5.3` | FT5-P2-02 | `T-FT5.3` | FT5-T02 |
| `FT5.4` | FT5-P3-01 | `T-FT5.4` | FT5-T03 / FT5-T06 |
| `FT5.5` | FT5-P3-02 | `T-FT5.5` | FT5-T05 |
| `FT5.6` | FT5-P1-02 / FT5-P3-01 | `T-FT5.6` | FT5-T04 / FT5-T06 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Metric taxonomy

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT5-P1-01 | metric taxonomy | 定义 `smoke_metric`、`objective_proxy`、`manual_mos`、`release_gate`；所有指标写 source/mode。 | `src/myvoiceclone/eval/objective.py:43-80`, `src/myvoiceclone/eval/report.py:8-164` | report 可区分真实/代理/mock | FT5-T01 | 字段断言通过 |
| FT5-P1-02 | report schema fields | API/DB 写入包含 `metric_source`、`adapter_mode`、input/output artifact refs；canonical 落点为 `eval_metrics.metric_json.metric_source/adapter_mode`、`eval_samples.input_artifact_id/output_artifact_id/reference_artifact_id` 与 report summary，若要顶层字段需另补 migration/schema。 | `src/myvoiceclone/api/schemas.py:87-107`, `db/migrations/004_reports_metrics.sql:13-31`, `db/migrations/007_reconcile_to_plan.sql:175-189` | 下游 API 可消费 | FT5-T04 | DB integrity pass |

### 4.2 Phase 2 — Evaluators

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT5-P2-01 | smoke evaluator | 读取 wav artifact/path，输出 duration、peak/clipping、silence ratio、loudness proxy、transcript sanity。 | `src/myvoiceclone/eval/smoke.py`, `src/myvoiceclone/storage/artifact_store.py:15-104` | 机械健康指标可重复 | FT5-T01 | fixture deterministic |
| FT5-P2-02 | objective proxy gating | SQUIM/DNSMOS 等缺依赖时标 `unavailable`，有依赖时标 `objective_proxy`。 | `src/myvoiceclone/eval/objective.py:16-41` | 不产生假真实分 | FT5-T02 | unavailable test pass |

### 4.3 Phase 3 — Subjective and gate

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT5-P3-01 | subjective eval service/API | 校验 MOS 范围、ABX 选择、reviewer、comment、sample artifact id；写 report/eval rows。 | `src/myvoiceclone/eval/subjective.py:8-80`, `src/myvoiceclone/api/routes_reports.py` | 人工评估可录入 | FT5-T03 / FT5-T06 | TestClient pass |
| FT5-P3-02 | release gate layering | gate 在 `decision_json`/`details_json` 中输出 `smoke_pass`、`quality_pass`、`manual_waived`、`blocked_reasons` 和 trace link；若需顶层响应字段，另补 migration + `ReleaseGateResponse`。 | `src/myvoiceclone/api/routes_reports.py:96-179`, `src/myvoiceclone/domain/policies.py` | release 判定可审计 | FT5-T05 | gate semantics pass |

---

## 5. Phase 详情

### 5.1 Phase 1 — Metric taxonomy

- **目标**：让所有评估结果具备来源语义。
- **新增文件**：可新增 enum/constant module。
- **修改文件**：`src/myvoiceclone/eval/objective.py`, `src/myvoiceclone/eval/report.py`, `src/myvoiceclone/api/schemas.py`, migrations/fixtures。
- **具体功能预期**：
  1. mock score 不可进入 `quality_pass`。
  2. proxy score 必须标 `objective_proxy`。
  3. manual MOS/ABX 必须带 reviewer 和 artifact id。
  4. report 中同时出现 inference artifact 和 input artifact。
  5. adapter mode 从 FT4 metadata 透传。
- **测试项**：FT5-T01 / FT5-T04
- **收口标准**：report/DB 字段断言通过。
- **风险提醒**：字段扩展如需 migration，必须纳入 FT2 drift inventory。

### 5.2 Phase 2 — Evaluators

- **目标**：为真实 wav 提供可自动验证的健康指标。
- **具体功能预期**：
  1. 短 wav fixture 输出稳定 duration。
  2. 静音/爆音/空文件能 fail。
  3. transcript sanity 只做存在性/长度/空白检查，不冒充 ASR 质量。
  4. proxy 缺依赖返回 unavailable + reason。
  5. proxy 有依赖时写版本/device/cache metadata。
- **测试项**：FT5-T01 / FT5-T02
- **收口标准**：smoke deterministic；proxy unavailable 不污染 score。
- **风险提醒**：FFmpeg/torchaudio 行为差异需要在 evidence 中记录版本。

### 5.3 Phase 3 — Subjective and gate

- **目标**：让人工评估与 release gate 成为真实 e2e 的可查询节点。
- **具体功能预期**：
  1. MOS 范围校验。
  2. ABX 必须绑定样本 artifact。
  3. release gate 可因 smoke fail 阻断。
  4. release gate 可因 manual waiver 放行，但必须有 reason。
  5. trace API 能看到 report/gate/policy event。
- **测试项**：FT5-T03 / FT5-T05 / FT5-T06
- **收口标准**：API 查询返回 eval + manual + gate + trace links。
- **风险提醒**：manual waiver 不是质量通过；report 文案必须区分。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Proxy metrics not final quality | `docs/eval/first-test/reference-anchor.md:136-140` | report 分层显示，不让 proxy 单独 release | 回 reference-anchor |
| Real evidence lands DB/artifact/evidence pack | `docs/eval/first-test/reference-anchor.md:189-195` | metrics/report/gate 必须可追溯 | 阻断 FT7 |
| FT5 proposed scope | `docs/eval/first-test/proposed-planning.md:250-266` | 本 AP 覆盖 FT5.1..FT5.6/T-FT5.1..6 | 回 proposed planning |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT5-1 | `docs/eval/first-test/reference-anchor.md:85-93` | Evaluation axis | FT5-P1/P2/P3 | ✅ 复用 | 分层评估 |
| A-FT5-2 | `src/myvoiceclone/eval/objective.py:16-41` | degraded handling | FT5-P2-02 | ♻️ 重 substrate | proxy unavailable |
| A-FT5-3 | `src/myvoiceclone/eval/objective.py:43-80` | mock metrics | FT5-P1-01 | ♻️ 重 substrate | mock source 标记 |
| A-FT5-4 | `src/myvoiceclone/eval/subjective.py:8-80` | subjective report | FT5-P3-01 | ✅ 复用 | 扩展录入 |
| A-FT5-5 | `src/myvoiceclone/eval/report.py:8-164` | reports/eval pack | FT5-P1-01 | ✅ 复用 | report link |
| A-FT5-6 | `src/myvoiceclone/api/routes_reports.py:96-179` | release gate/waive | FT5-P3-02 | ♻️ 重 substrate | gate layering |
| A-FT5-7 | `src/myvoiceclone/api/schemas.py:87-107` | Report/Gate response | FT5-P1-02 | ♻️ 重 substrate | API contract |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 | 本 AP 的规避 |
|----|-------------|--------|--------------|
| ⛔1 | 把 mock score 当 quality pass | 会让假评估进入 release | `metric_source=mock` 不允许 release pass |
| ⛔2 | 把 DNSMOS/SQUIM 当最终主观质量 | proxy 不等于人工听感 | report 分层显示 |
| ⛔3 | waiver 无 reason | audit 不可复核 | waiver 必填 reason/reviewer |
| ⛔4 | eval 只写 stdout | FT7 无 evidence | DB/report/artifact 全链写入 |

### 7.3 威胁模型锚

- **评估污染**：mock/proxy 分数被误用为真实质量结论。
- **人工评估滥用**：reviewer 或样本 artifact 缺失导致无法复核。
- **release 越权**：smoke fail 后仍通过，或 waiver 无原因。

---

## 8. 测试与复用策略

### 8.1 测试台账

| Test-ID | 验证点 | 层级 | marker | 复用 / 新增 | 映射工作项 | evidence |
|---------|--------|------|--------|-------------|------------|----------|
| FT5-T01 | smoke metrics 对短 wav fixture 输出 deterministic fields | unit | unit | 🆕 新增 `tests/unit/eval/test_smoke_metrics.py` | FT5-P2-01 | pytest PASS |
| FT5-T02 | proxy metric 缺依赖时 skip/mark unavailable，不写 real score | unit | unit | ♻️ 扩展 objective tests | FT5-P2-02 | pytest PASS |
| FT5-T03 | MOS/ABX payload validation | service | unit/api | 🆕 新增 subjective tests | FT5-P3-01 | pytest PASS |
| FT5-T04 | `eval_metrics`/report 记录 metric_source、adapter_mode、artifact refs | db/unit | unit | ♻️ 扩展 report tests | FT5-P1-02 | pytest PASS |
| FT5-T05 | release gate 区分 smoke pass、quality pass、manual waived | domain | unit | ♻️ 扩展 policy/gate tests | FT5-P3-02 | pytest PASS |
| FT5-T06 | eval report API 返回指标、人工分、release gate 与 trace links | API | api | ♻️ 扩展 TestClient | FT5-P3-01/P3-02 | pytest PASS |

### 8.2 复用策略

| 可复用对象 | 复用方式 | 改动要求 |
|------------|----------|----------|
| `src/myvoiceclone/eval/objective.py` | 复用 degraded result 形态 | 增加 source/mode 字段 |
| `src/myvoiceclone/eval/subjective.py` | 复用报告结构 | 增加 payload validation 与 artifact refs |
| `src/myvoiceclone/api/routes_reports.py` | 复用 release/waive endpoint | 扩展 gate semantics |
| `src/myvoiceclone/storage/artifact_store.py` | 复用 artifact bytes/sha/path | eval 输入输出均通过 artifact |

### 8.3 运行策略

- 默认 suite 跑 unit/api，不跑 live。
- proxy live 依赖可选；缺依赖必须有 skip/unavailable reason。
- FT7 capstone 才消费 FT5 输出作为 e2e evidence。

### 8.4 未覆盖与后延测试

- 不覆盖众包 MOS。
- 不覆盖长期听感一致性。
- 不覆盖生产发布许可裁定。

---

## 9. 风险、依赖与完成状态

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| proxy 依赖不可用 | objective proxy 无法跑 | medium | unavailable + reason |
| release gate 语义过载 | 前端误读状态 | medium | schema 字段显式分层 |
| 人工评分样本少 | 不能代表真实质量 | high | report 写明本地 first-test sample |
| DB 字段不足 | trace 不完整 | medium | 与 FT2 drift inventory 同步 |

- **外部依赖**：FFmpeg/torchaudio/proxy model 可选。
- **组织协作前提**：reviewer 需提供人工评估输入。
- **完成状态**：`planned`

---

## 10. DoD 与 Closure 映射

| DoD | 对应工作项 | 对应测试 | 关闭标准 |
|-----|------------|----------|----------|
| smoke evaluator 可重复 | FT5-P2-01 | FT5-T01 | deterministic fixture PASS |
| proxy 不假写真实分 | FT5-P2-02 | FT5-T02 | unavailable 语义 PASS |
| subjective eval 可录入 | FT5-P3-01 | FT5-T03/FT5-T06 | API/service PASS |
| release gate 分层 | FT5-P3-02 | FT5-T05 | semantics PASS |
| report 可追溯 | FT5-P1-01/P1-02 | FT5-T04/FT5-T06 | artifact refs/source/mode 完整 |

FT5 关闭时必须把 mock/proxy/manual/release 的解释写入 FT7 evidence pack；任何未跑的 proxy/live 项不得被标为质量通过。
