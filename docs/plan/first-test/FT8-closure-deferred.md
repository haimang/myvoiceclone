# FT8 Closure Deferred Action Plan

> 服务业务簇: `FT8 · Closure 与 deferred reconciliation`
> 计划对象: `first-build deferred ledger, first-test closure, final input pack`
> 类型: `closure`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT8-closure-deferred.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT7-live-capstone.md`
> 下游交接:
> - `docs/closure/first-test/*`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> - `docs/closure/first-build/deferred-items-ledger.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT8`, `reference-anchor axis H`, `first-build deferred ledger`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT8 是 first-test 的治理收口层。它不新增 runtime 能力，而是把 FT1-FT7 的真实完成状态映射回 first-build deferred ledger，创建 first-test closure ledger，并整理 proposed→final 的输入包。核心要求是：已解决项必须有证据关闭，未解决项必须有触发器和目标阶段，不能用“后续处理”替代台账。

- **服务业务簇**：`Closure / deferred reconciliation`
- **计划对象**：deferred ledgers, closure docs, final input pack
- **本次计划解决的问题**：
  - first-build deferred 项需要按 first-test 执行结果关闭、保留或 reopen。
  - first-test 需要自己的 closure/deferred ledger。
  - final 输入包需要索引 reference anchors、test matrix、schema inventory、API contract。
- **本次计划的直接产出**：
  - 更新 first-build deferred ledger 状态。
  - 新建 first-test closure/deferred ledger。
  - retained deferred 边界说明。
  - proposed→final input pack index。
- **本计划不重新讨论的设计结论**：
  - vec0/embedder、SQLite 多 worker、完整 OTel、众包 MOS 不是 first-test 主路；vec0/embedder 由 first-build deferred ledger 承接，OTel/crowd MOS 由 reference-anchor 明确降级（来源：`docs/closure/first-build/deferred-items-ledger.md:22-29`, `docs/eval/first-test/reference-anchor.md:108-111`, `docs/eval/first-test/reference-anchor.md:136-141`, `docs/eval/first-test/reference-anchor.md:179-195`）。
  - first-test 关闭必须依赖 FT7 evidence，而不是口头完成。

---

## 1. 执行综述

### 1.1 总体执行方式

先读取 FT7 evidence，再逐项对账 first-build deferred ledger，随后创建 first-test closure/deferred 文档，最后整理 final 输入包索引并做 docs/check。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Deferred reconciliation | S | close/reopen/retain first-build deferred | FT7 |
| Phase 2 | First-test closure ledger | S | 创建 first-test closure/deferred 台账 | Phase 1 |
| Phase 3 | Final input pack | S | reference/test/schema/API 索引 | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Deferred reconciliation**
   - **核心目标**：first-build deferred 项不丢失、不误关。
   - **为什么先做**：first-test closure 需要知道哪些遗留已被解决。
2. **Phase 2 — First-test closure ledger**
   - **核心目标**：为 first-test 本阶段创建 closed/deferred/reopened 分类。
   - **为什么放在这里**：FT7 evidence 已经提供真实依据。
3. **Phase 3 — Final input pack**
   - **核心目标**：把下一阶段需要的设计输入收齐。
   - **为什么放在这里**：避免 final planning 时重新考古。

### 1.4 执行策略说明

- **执行顺序原则**：evidence review → first-build deferred reconciliation → first-test ledger → final input pack。
- **风险控制原则**：无 evidence 不关闭；真实 deferred 必须有 reopen trigger。
- **测试推进原则**：docs/check 验证文档存在、分类完整、引用完整。
- **文档同步原则**：closure 状态不得高于 FT7 evidence。
- **回滚 / 降级原则**：FT7 skipped 时 first-test 可标 implementation-complete-awaiting-live-verification，但不能 full-close。

### 1.5 影响结构图

```text
FT8 Closure Deferred
├── first-build reconciliation
│   └── docs/closure/first-build/deferred-items-ledger.md
├── first-test closure
│   ├── docs/closure/first-test/deferred-items-ledger.md
│   └── docs/closure/first-test/first-test-closure.md
├── final input pack
│   └── docs/eval/first-test/final-input-pack.md
└── docs checks
    └── tests/docs or scripts/check_first_test_closure.*
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** 更新 first-build deferred ledger：closed / reopened / retained。
- **[S2]** 新建 first-test closure/deferred ledger。
- **[S3]** 保留 vec0/embedder、多 worker、完整 OTel、众包 MOS 等真实 deferred 边界。
- **[S4]** proposed→final 输入包整理。
- **[S5]** docs/check 验证 closure/deferred 完整性。

### 2.2 Out-of-Scope

- **[O1]** 修复 FT1-FT7 未完成 runtime 代码。
- **[O2]** 将 deferred 项偷偷关闭。
- **[O3]** 生产发布验收。
- **[O4]** second-build 详细 action-plan。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| first-build deferred reconciliation | in-scope | first-test 目标之一是收敛遗留 | FT7 evidence 不存在 |
| first-test closure ledger | in-scope | 本阶段必须可审查 | closure 模板变更 |
| runtime fixes | out-of-scope | 应回对应 FT 阶段 | closure 发现 blocker |
| final input pack | in-scope | 提供下一阶段 planning 输入 | final planning 已独立完成 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT8-P1-01 | Phase 1 | first-build deferred reconciliation | update | `docs/closure/first-build/deferred-items-ledger.md:20-29` | 已解决/保留/reopen 分类 | FT8-T01 | medium |
| FT8-P1-02 | Phase 1 | retained deferred boundary | update | `docs/closure/first-build/deferred-items-ledger.md:35-180`, `docs/eval/first-test/reference-anchor.md:108-111`, `docs/eval/first-test/reference-anchor.md:136-141`, `docs/eval/first-test/reference-anchor.md:179-195` | 每项有触发器/阶段 | FT8-T02 | medium |
| FT8-P2-01 | Phase 2 | first-test closure ledger | add | `docs/closure/first-test/first-test-closure.md` | closure 状态匹配 FT7 evidence | FT8-T01 | medium |
| FT8-P2-02 | Phase 2 | first-test deferred ledger | add | `docs/closure/first-test/deferred-items-ledger.md` | 新 deferred 可继承 | FT8-T02 | medium |
| FT8-P3-01 | Phase 3 | final input pack index | add | `docs/eval/first-test/final-input-pack.md`, `docs/eval/first-test/reference-anchor.md` | final planning 输入完整 | FT8-T03 | low |
| FT8-P3-02 | Phase 3 | docs/check | add | `tests/docs/test_first_test_closure_docs.py` 或 `scripts/check_first_test_closure.sh` | closure 文档可机检 | FT8-T01..T03 | low |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT8.1` | FT8-P1-01 | `T-FT8.1` | FT8-T01 |
| `FT8.2` | FT8-P2-01 / FT8-P2-02 | `T-FT8.1` | FT8-T01 |
| `FT8.3` | FT8-P1-02 | `T-FT8.2` | FT8-T02 |
| `FT8.4` | FT8-P3-01 / FT8-P3-02 | `T-FT8.3` | FT8-T03 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Deferred reconciliation

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT8-P1-01 | first-build deferred reconciliation | 对 DEF-01..08 标 closed/retained/reopened；closed 必须引用 FT evidence。 | `docs/closure/first-build/deferred-items-ledger.md:20-29` | 遗留不丢失 | FT8-T01 | docs/check PASS |
| FT8-P1-02 | retained deferred boundary | vec0/embedder、多 worker、完整 OTel、众包 MOS 等保留项写触发器和目标阶段。 | `docs/closure/first-build/deferred-items-ledger.md:35-180`, `docs/eval/first-test/reference-anchor.md:108-111`, `docs/eval/first-test/reference-anchor.md:136-141`, `docs/eval/first-test/reference-anchor.md:179-195` | defer 有边界 | FT8-T02 | trigger 完整 |

### 4.2 Phase 2 — First-test closure ledger

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT8-P2-01 | first-test closure ledger | 新建 closure，总结 FT1-FT7 evidence、未完成项和 close type。 | `docs/closure/first-test/first-test-closure.md` | closure 可审查 | FT8-T01 | 文档存在且分类 |
| FT8-P2-02 | first-test deferred ledger | 新建/更新本阶段 deferred ledger；每项有来源、触发器、目标阶段。 | `docs/closure/first-test/deferred-items-ledger.md` | 后续可承接 | FT8-T02 | trigger 完整 |

### 4.3 Phase 3 — Final input pack

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT8-P3-01 | final input pack index | 索引 reference-anchor、test matrix、schema inventory、API contract、evidence pack。 | `docs/eval/first-test/final-input-pack.md` | 下一阶段不用重建上下文 | FT8-T03 | references 完整 |
| FT8-P3-02 | docs/check | 检查 closure/deferred 文档存在、分类、trigger、final input refs。 | `tests/docs/test_first_test_closure_docs.py` 或 script | 文档质量可机检 | FT8-T01..T03 | docs/check PASS |

---

## 5. Phase 详情

### 5.1 Phase 1 — Deferred reconciliation

- **目标**：把 first-build 遗留按 first-test 真实结果重新归档。
- **新增文件**：无。
- **修改文件**：`docs/closure/first-build/deferred-items-ledger.md`。
- **具体功能预期**：
  1. 每个 DEF 项有 `closed/retained/reopened` 状态。
  2. closed 必须引用 FT test/evidence。
  3. retained 必须有 reopen trigger。
  4. reopened 必须指向 first-test/second-build 承接位置。
  5. 不因 planning 存在而关闭项。
- **测试项**：FT8-T01 / FT8-T02
- **收口标准**：docs/check pass。
- **风险提醒**：FT7 skipped 的真实能力不得关闭。

### 5.2 Phase 2 — First-test closure ledger

- **目标**：形成 first-test 自己的 closure 事实记录。
- **具体功能预期**：
  1. closure 写 FT1-FT8 状态。
  2. 引用 FT7 evidence pack。
  3. 列出 blockers/known issues。
  4. deferred ledger 用 append-only 结构。
  5. 每项 deferred 有 owner-independent trigger。
- **测试项**：FT8-T01 / FT8-T02
- **收口标准**：closure/deferred 文档存在且分类完整。
- **风险提醒**：如果 capstone 只是 skipped，close type 只能是 pending/live-verification 类。

### 5.3 Phase 3 — Final input pack

- **目标**：整理 first-test 后续 final planning 的输入索引。
- **具体功能预期**：
  1. 引用 reference-anchor。
  2. 引用 test matrix。
  3. 引用 schema inventory/drift results。
  4. 引用 API contract fixture。
  5. 引用 evidence pack 和 deferred ledger。
- **测试项**：FT8-T03
- **收口标准**：final input refs 全部存在。
- **风险提醒**：input pack 是索引，不替代原始 evidence。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Deferred requires trigger | `docs/closure/first-build/deferred-items-ledger.md:14` | 每项 retained 必须有 reopen 条件 | docs/check fail |
| vec0/embedder/multi-worker/OTel/crowd MOS can remain deferred | `docs/closure/first-build/deferred-items-ledger.md:22-29`, `docs/eval/first-test/reference-anchor.md:108-111`, `docs/eval/first-test/reference-anchor.md:136-141`, `docs/eval/first-test/reference-anchor.md:179-195` | 不塞入 first-test closure blocker | 保留触发器 |
| FT8 proposed scope | `docs/eval/first-test/proposed-planning.md:322-333` | 覆盖 FT8.1..FT8.4/T-FT8.1..3 | 回 proposed planning |
| Closure depends on FT7 evidence | `FT7 AP` | 无证据不 full-close | 降级 close type |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT8-1 | `docs/closure/first-build/deferred-items-ledger.md:20-29` | DEF overview | FT8-P1-01 | ✅ 复用 | reconciliation source |
| A-FT8-2 | `docs/closure/first-build/deferred-items-ledger.md:35-180` | DEF details | FT8-P1-02 | ✅ 复用 | triggers |
| A-FT8-3 | `docs/eval/first-test/reference-anchor.md:108-111`, `docs/eval/first-test/reference-anchor.md:136-141`, `docs/eval/first-test/reference-anchor.md:179-195` | deferred boundaries | FT8-P1/P2 | ✅ 复用 | retained scope |
| A-FT8-4 | `docs/eval/first-test/proposed-planning.md:322-333` | FT8 plan/tests | FT8 全部 | ✅ 复用 | scope |
| A-FT8-5 | `docs/plan/first-test/FT7-live-capstone.md` | evidence handoff | FT8-P2/P3 | ✅ 复用 | closure evidence |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 | 本 AP 的规避 |
|----|-------------|--------|--------------|
| ⛔1 | 只因 action-plan 存在就关闭 deferred | planning 不是 evidence | closed 必须引用 test/evidence |
| ⛔2 | 裸 defer | 后续无法触发 | 每项必须有 reopen trigger |
| ⛔3 | FT7 skipped 却 full-close | 虚假完成 | close type 降级 |
| ⛔4 | final input pack 复制原始文档 | 造成漂移 | 只做索引和引用 |

### 7.3 威胁模型锚

- **治理漂移**：遗留项被静默丢失。
- **完成度夸大**：未 live 验证项被 full-close。
- **后续不可承接**：deferred 缺 trigger/owner/阶段。

---

## 8. 测试与复用策略

### 8.1 测试台账

| Test-ID | 验证点 | 层级 | marker | 复用 / 新增 | 映射工作项 | evidence |
|---------|--------|------|--------|-------------|------------|----------|
| FT8-T01 | closure/deferred 文档存在、含 reopened/closed/deferred 分类 | docs/check | unit | 🆕 新增 docs/check | FT8-P1-01/P2-01 | pytest/script PASS |
| FT8-T02 | 每个 retained deferred 有触发器和目标阶段 | docs/check | unit | 🆕 新增 docs/check | FT8-P1-02/P2-02 | pytest/script PASS |
| FT8-T03 | final 输入包引用 reference-anchor、schema inventory、test matrix、API contract | docs/check | unit | 🆕 新增 docs/check | FT8-P3-01/P3-02 | pytest/script PASS |

### 8.2 复用策略

| 可复用对象 | 复用方式 | 改动要求 |
|------------|----------|----------|
| first-build deferred ledger | 作为 reconciliation source | append/update status，不删除历史 |
| closure template | 作为 first-test closure shape | close type 必须匹配 evidence |
| FT7 evidence pack | closure evidence source | 引用路径和 validator 结果 |
| reference-anchor | deferred boundary | 不重新裁定 web refs |

### 8.3 运行策略

- docs/check 可进默认 unit suite。
- closure 写入前先检查 FT7 evidence 是否存在。
- 若 live capstone skipped，closure 状态降级。

### 8.4 未覆盖与后延测试

- 不覆盖 second-build action-plan 细化。
- 不覆盖生产发布验收材料。
- 不覆盖外部审计格式。

---

## 9. 风险、依赖与完成状态

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| FT7 evidence 不完整 | closure 无法 full-close | medium | close type 降级 |
| deferred 分类争议 | 后续承接混乱 | medium | trigger/阶段写清 |
| docs/check 过弱 | 漏掉裸 defer | low | 检查 required headings/columns |
| input pack 引用失效 | final planning 返工 | low | 路径存在性检查 |

- **外部依赖**：无 runtime 外部依赖；依赖 FT7 evidence。
- **组织协作前提**：owner-gate 不阻塞 AP 制作；closure 以 evidence 为准。
- **完成状态**：`planned`

---

## 10. DoD 与 Closure 映射

| DoD | 对应工作项 | 对应测试 | 关闭标准 |
|-----|------------|----------|----------|
| first-build deferred 已对账 | FT8-P1-01/P1-02 | FT8-T01/T02 | 每项 closed/retained/reopened |
| first-test closure 存在 | FT8-P2-01 | FT8-T01 | close type 匹配 FT7 evidence |
| first-test deferred ledger 存在 | FT8-P2-02 | FT8-T02 | 每项有 trigger/阶段 |
| final input pack 完整 | FT8-P3-01 | FT8-T03 | refs 存在且覆盖四类输入 |
| docs/check 可执行 | FT8-P3-02 | FT8-T01..T03 | PASS |

FT8 关闭时必须给出 first-test 的真实 close type；若 FT7 只有 skipped evidence，本阶段只能产出 `implementation-complete-awaiting-live-verification` 或等价状态，不得标 full-close。
