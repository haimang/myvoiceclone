# FT7 Live Capstone Action Plan

> 服务业务簇: `FT7 · Live tests、capstone 与 evidence pack`
> 计划对象: `marker policy, first-test capstone, evidence exporter, validation`
> 类型: `new`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT7-live-capstone.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT1-preflight.md`
> - `docs/plan/first-test/FT2-schema-observability.md`
> - `docs/plan/first-test/FT3-real-preprocess.md`
> - `docs/plan/first-test/FT4-real-inference.md`
> - `docs/plan/first-test/FT5-real-evaluation.md`
> - `docs/plan/first-test/FT6-fastapi-e2e.md`
> 下游交接:
> - `docs/plan/first-test/FT8-closure-deferred.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT7`, `reference-anchor axis F/G/H`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT7 是 first-test 的证据收口层。它不再新增业务能力，而是把 FT1-FT6 的入口、schema、真实预处理、真实推理、评估和 API surface 串成一个可审查的 capstone，并导出 evidence pack。关键纪律是：live/gpu/slow 必须 gated，缺依赖必须 skip with reason，且 skip 计入 denominator；任何 mock-as-real、empty manifest、repo 大文件都必须被 validator 拒绝。

- **服务业务簇**：`Live tests / capstone / evidence`
- **计划对象**：pytest markers, capstone test, evidence exporter, evidence validator
- **本次计划解决的问题**：
  - first-build capstone 是 mock journey，不能代表真实 first-test。
  - live 测试缺依赖时容易假绿。
  - 真实 evidence 需要离开 stdout，落 run folder + DB/artifact/trace。
- **本次计划的直接产出**：
  - live/slow/gpu marker policy 与 denominator。
  - first-test run folder exporter。
  - API capstone：真实音频 → preprocess → real inference → eval → release → trace。
  - evidence review checklist 与 validator。
- **本计划不重新讨论的设计结论**：
  - 大文件和 run evidence 目标路径模式为 `/mnt/usb/workspace/myvoiceresearch/test-runs/RUN_ID/`，真实路径由 evidence exporter 创建（来源：`docs/eval/first-test/reference-anchor.md:189-195`）。
  - live/gpu/slow 默认不跑（来源：`pytest.ini:1-11`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先固定 marker/skip 规则，再实现 evidence exporter 和 validator，最后把 FT1-FT6 gates 串成 live capstone。FT7 的核心不是多跑，而是把“跑了什么、跳过了什么、为什么可信”记录清楚。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Marker and gate policy | S | live/slow/gpu skip denominator 与前置 gate | FT1-FT6 |
| Phase 2 | Evidence pack | M | 导出 env/commands/db/artifacts/trace | Phase 1 |
| Phase 3 | API capstone | L | 真实 e2e live chain 与 validator | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Marker and gate policy**
   - **核心目标**：默认 suite 与 live suite 的边界可审计。
   - **为什么先做**：capstone 需要依赖 skip/pass 语义。
2. **Phase 2 — Evidence pack**
   - **核心目标**：把运行证据落到固定 run folder。
   - **为什么放在这里**：capstone 运行前应知道证据要收哪些文件。
3. **Phase 3 — API capstone**
   - **核心目标**：通过 FastAPI surface 完成真实输入到 trace 的闭环。
   - **为什么放在这里**：它消费 FT1-FT6 全部交付。

### 1.4 执行策略说明

- **执行顺序原则**：markers → required tests gate → evidence exporter → validator → capstone。
- **风险控制原则**：live dependency missing 只能 skip with reason，不能 pass。
- **测试推进原则**：validator/unit 先绿；capstone live 单独跑。
- **文档同步原则**：run folder 结构写入 evidence pack README。
- **回滚 / 降级原则**：live capstone 缺依赖时输出 skipped evidence，不标 closed。

### 1.5 影响结构图

```text
FT7 Live Capstone
├── test policy
│   ├── pytest.ini
│   └── tests/unit/test_pytest_markers.py
├── evidence
│   ├── scripts/collect_first_test_evidence.sh
│   ├── evidence manifest JSON
│   └── validator
├── capstone
│   ├── tests/integration/test_first_test_capstone.py
│   └── API live HTTP smoke
└── external run folder
    └── /mnt/usb/workspace/myvoiceresearch/test-runs/RUN_ID/
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** live/slow/gpu marker policy 与 skip denominator。
- **[S2]** first-test run folder exporter。
- **[S3]** FT1-FT6 required tests gate。
- **[S4]** API capstone live chain。
- **[S5]** evidence validator：mock-as-real、empty manifest、repo 大文件、trace 缺失。

### 2.2 Out-of-Scope

- **[O1]** 长训或生产发布验收。
- **[O2]** 多 GPU soak。
- **[O3]** 外部众包听感平台。
- **[O4]** 全量 observability platform。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| live capstone | in-scope | first-test 核心闭环 | live deps 缺失则 skipped |
| default unit gate | in-scope | capstone 前必须证明基线未坏 | suite 过慢需拆分 |
| evidence exporter | in-scope | stdout 不足以复核 | artifact store 已变更 |
| GPU soak | defer | 超出 first-test | FT4 选择 GPU-only substrate |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT7-P1-01 | Phase 1 | marker taxonomy and denominator | update | `pytest.ini:1-11`, `tests/unit/test_pytest_markers.py:17` | live/slow/gpu 默认不跑且可见 | FT7-T01 | low |
| FT7-P1-02 | Phase 1 | FT1-FT6 required test gate | add | `tests/integration/test_first_test_capstone.py` | capstone 前置不假过 | FT7-T04 | medium |
| FT7-P2-01 | Phase 2 | evidence exporter | add | `scripts/collect_first_test_evidence.sh`, `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:308-331` | run folder 证据完整 | FT7-T02 | medium |
| FT7-P2-02 | Phase 2 | evidence validator | add | `tests/unit/test_first_test_evidence_validator.py` | 拒绝坏证据 | FT7-T05 | medium |
| FT7-P3-01 | Phase 3 | API capstone live chain | add/update | `tests/integration/test_first_test_capstone.py`, `tests/integration/test_first_build_journey.py:16-103` | 真实 e2e 闭环 | FT7-T03 | high |
| FT7-P3-02 | Phase 3 | capstone trace/evidence indexing | add | planned path pattern: `docs/closure/first-test/*`, `/mnt/usb/workspace/myvoiceresearch/test-runs/RUN_ID/` | closure 可引用 | FT7-T05 | medium |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT7.1` | FT7-P1-01 | `T-FT7.1` | FT7-T01 |
| `FT7.2` | FT7-P2-01 | `T-FT7.2` | FT7-T02 |
| `FT7.3` | FT7-P3-01 | `T-FT7.3` | FT7-T03 |
| `FT7.4` | FT7-P1-02 | `T-FT7.4` | FT7-T04 |
| `FT7.5` | FT7-P2-02 / FT7-P3-02 | `T-FT7.5` | FT7-T05 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Marker and gate policy

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT7-P1-01 | marker taxonomy and denominator | 确认 live/slow/gpu markers；默认 addopts 不跑 live；记录 skip denominator。 | `pytest.ini:1-11`, `test_pytest_markers.py:17` | live 边界清楚 | FT7-T01 | marker test PASS |
| FT7-P1-02 | required test gate | capstone 前检查 FT1-FT6 required tests/evidence 状态；缺失则 fail/skip with reason。 | `test_first_test_capstone.py` | 不用 capstone 掩盖前序失败 | FT7-T04 | gate test PASS |

### 4.2 Phase 2 — Evidence pack

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT7-P2-01 | evidence exporter | 导出 env、commands、stdout/stderr、DB summary、artifact manifest、trace JSON。 | `scripts/collect_first_test_evidence.sh`, `state-analysis-after-FB-by-GPT.md:308-331` | run folder 可复核 | FT7-T02 | exporter test PASS |
| FT7-P2-02 | evidence validator | 检查 mock-as-real、empty manifest、repo 大文件、trace 缺失、skip reason 缺失。 | `test_first_test_evidence_validator.py` | 坏证据被拒绝 | FT7-T05 | validator PASS |

### 4.3 Phase 3 — API capstone

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT7-P3-01 | API capstone live chain | 通过 API 完成 upload→preprocess→infer→eval→release→trace；缺 live deps skip with reason。 | `test_first_test_capstone.py`, `test_first_build_journey.py:16-103` | 真实 e2e 证据 | FT7-T03 | live pass/skip reason |
| FT7-P3-02 | capstone trace/evidence indexing | 生成 evidence index，供 FT8 closure 引用。 | planned path pattern: `docs/closure/first-test/*`, run folder | closure 有证据入口 | FT7-T05 | validator PASS |

---

## 5. Phase 详情

### 5.1 Phase 1 — Marker and gate policy

- **目标**：让“默认测试”和“真实 live 测试”边界可审计。
- **新增文件**：可新增 capstone preflight helper。
- **修改文件**：`pytest.ini`, marker tests。
- **具体功能预期**：
  1. `pytest --markers` 包含 live/slow/gpu。
  2. 默认 addopts 不跑 live/slow/gpu。
  3. skip reason 必须说明缺 token/model/cache/GPU/ffmpeg 等。
  4. skipped count 进入 evidence denominator。
  5. FT1-FT6 gates 失败时 capstone 不继续。
- **测试项**：FT7-T01 / FT7-T04
- **收口标准**：marker/gate tests pass。
- **风险提醒**：不要把 live skipped 记作 capstone pass。

### 5.2 Phase 2 — Evidence pack

- **目标**：把 capstone 证据从 stdout 迁移到可审查 run folder。
- **具体功能预期**：
  1. run folder 路径模式为 `/mnt/usb/workspace/myvoiceresearch/test-runs/RUN_ID/`，实际 RUN_ID 由 exporter 生成。
  2. 记录 env、commit/status、commands。
  3. 保存 stdout/stderr。
  4. 导出 DB summary、artifact manifest、trace JSON。
  5. validator 拒绝 repo 内真实音频大文件。
- **测试项**：FT7-T02 / FT7-T05
- **收口标准**：exporter/validator tests pass。
- **风险提醒**：run folder 可包含敏感路径，不应提交真实音频。

### 5.3 Phase 3 — API capstone

- **目标**：以真实 API surface 完成 first-test 的端到端证据。
- **具体功能预期**：
  1. 使用真实短音频输入。
  2. 预处理和推理均标明 real/mock mode。
  3. eval report 关联 input/output artifacts。
  4. release gate 显示 smoke/quality/manual 结果。
  5. trace 能追到 job_events/artifacts/reports/policy。
  6. evidence pack 通过 validator。
- **测试项**：FT7-T03 / FT7-T05
- **收口标准**：live pass 或 skipped with reason；未真实 pass 时不得关闭 first-test。
- **风险提醒**：FT7 是收口验证，不应引入新业务修复，发现问题回对应 FT 阶段。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| live/gpu/slow gated | `docs/eval/first-test/reference-anchor.md:141`, `pytest.ini:1-11` | 默认不跑 live，skip reason 入 denominator | 阻断 FT7 close |
| evidence outside repo | `docs/eval/first-test/reference-anchor.md:189-195` | run folder 外置 | 阻断 validator |
| capstone evidence shape | `docs/eval/first-test/reference-anchor.md:113-117` | 必须含真实输入/推理/评估/API trace | 回 FT3-FT6 |
| FT7 proposed scope | `docs/eval/first-test/proposed-planning.md:300-314` | 覆盖 FT7.1..FT7.5/T-FT7.1..5 | 回 proposed planning |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT7-1 | `docs/eval/first-test/reference-anchor.md:104-117` | evidence/capstone axes | FT7-P2/P3 | ✅ 复用 | evidence shape |
| A-FT7-2 | `docs/eval/first-test/reference-anchor.md:189-195` | TR-1..TR-7 | FT7 全部 | ✅ 复用 | trust rules |
| A-FT7-3 | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:308-331` | run folder | FT7-P2-01 | ✅ 复用 | evidence pack |
| A-FT7-4 | `pytest.ini:1-11` | pytest markers | FT7-P1-01 | ✅ 复用 | marker policy |
| A-FT7-5 | `tests/unit/test_pytest_markers.py:17` | marker assertion | FT7-P1-01 | ✅ 复用 | marker tests |
| A-FT7-6 | `tests/integration/test_first_build_journey.py:16-103` | mock capstone | FT7-P3-01 | ♻️ 参照 | 不等于 real capstone |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 | 本 AP 的规避 |
|----|-------------|--------|--------------|
| ⛔1 | 缺外部依赖时让 live tests 绿过 | 会把不可运行误判为可运行 | skip with reason + denominator |
| ⛔2 | 用 mock capstone 宣称真实 e2e | first-build capstone 是 mock | FT7 新增 live capstone |
| ⛔3 | evidence 只写 stdout | 无法复核 DB/artifact/trace | exporter 固定文件 |
| ⛔4 | 真实大音频提交 repo | 泄露和仓库膨胀 | validator 拒绝 |

### 7.3 威胁模型锚

- **证据造假**：mock 结果被标 real。
- **跳过滥用**：skip 缺 reason 或不计 denominator。
- **隐私泄露**：真实音频进入 repo。
- **闭环断链**：capstone 缺 artifact/report/trace 任一环。

---

## 8. 测试与复用策略

### 8.1 测试台账

| Test-ID | 验证点 | 层级 | marker | 复用 / 新增 | 映射工作项 | evidence |
|---------|--------|------|--------|-------------|------------|----------|
| FT7-T01 | `pytest --markers` 包含 live/slow/gpu；默认不跑 live | config | unit | ♻️ 扩展 marker test | FT7-P1-01 | pytest PASS |
| FT7-T02 | evidence exporter 生成 env/commands/db/artifacts/trace 文件 | unit/script | unit | 🆕 新增 exporter test | FT7-P2-01 | pytest PASS |
| FT7-T03 | API capstone 真实短音频链路；缺依赖 skip with reason | integration/live | live | 🆕 新增 capstone | FT7-P3-01 | pass/skip reason |
| FT7-T04 | capstone 前检查 FT1-FT6 required tests status | integration | integration | 🆕 新增 preflight gate | FT7-P1-02 | pytest PASS |
| FT7-T05 | evidence pack validator 拒绝 mock-as-real、empty manifest、repo 大文件 | validation | unit | 🆕 新增 validator | FT7-P2-02/P3-02 | pytest PASS |

### 8.2 复用策略

| 可复用对象 | 复用方式 | 改动要求 |
|------------|----------|----------|
| `test_first_build_journey.py` | 参照 journey shape | 不复用为真实 capstone 结论 |
| `pytest.ini` | 复用 marker taxonomy | 增加 denominator discipline |
| state-analysis run folder | 复用目录结构 | exporter 固化 |
| FT6 API surface | capstone 主入口 | 不绕过 API 手工插 DB |

### 8.3 运行策略

- 默认：`pytest -m "unit or api or cli or integration"`。
- live：`pytest -m live tests/integration/test_first_test_capstone.py`。
- evidence：每次 live run 创建独立 run folder。

### 8.4 未覆盖与后延测试

- 不覆盖多小时 soak。
- 不覆盖多 GPU。
- 不覆盖生产部署端到端。

---

## 9. 风险、依赖与完成状态

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| live deps 缺失 | capstone skipped | high | skip reason + denominator |
| evidence 过大 | repo 污染/复制慢 | medium | 外置 run folder |
| 前序 FT 未绿 | capstone 无法跑 | medium | preflight gate 明确失败 |
| trace 字段不足 | validator fail | medium | 回 FT2/FT5/FT6 修 |

- **外部依赖**：真实音频样本、模型/cache/token/GPU/FFmpeg 视所选 substrate 而定。
- **组织协作前提**：owner 提供合法真实测试音频与人工评估输入。
- **完成状态**：`planned`

---

## 10. DoD 与 Closure 映射

| DoD | 对应工作项 | 对应测试 | 关闭标准 |
|-----|------------|----------|----------|
| marker policy 可审计 | FT7-P1-01 | FT7-T01 | markers/default PASS |
| evidence exporter 可用 | FT7-P2-01 | FT7-T02 | files generated |
| capstone 前置 gate 生效 | FT7-P1-02 | FT7-T04 | missing gate blocks |
| live capstone 有真实证据或明确 skipped | FT7-P3-01 | FT7-T03 | pass/skip reason |
| evidence validator 拒绝坏证据 | FT7-P2-02/P3-02 | FT7-T05 | validator PASS |

FT7 关闭时必须把 run folder 路径、DB/artifact manifest、trace JSON、skip denominator 和 validator 结果交给 FT8 closure。
