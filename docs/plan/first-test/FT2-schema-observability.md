# FT2 Schema Observability Action Plan

> 服务业务簇: `FT2 · Schema drift 与 observability contract`
> 计划对象: `schema drift guard, job_events contract, trace completeness`
> 类型: `upgrade`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT2-schema-observability.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT1-preflight.md`
> 下游交接:
> - `docs/plan/first-test/FT3-real-preprocess.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT2`, `reference-anchor axis F/H`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT2 把数据库 drift 与可观测性提升为真实 e2e 的硬前置。first-test 不能只知道 job 成败，还必须知道每个 step、artifact、adapter mode、metric source、release/policy trace 是否完整。

- **服务业务簇**：`Observability / evidence` + `Deferred boundaries`
- **计划对象**：DB schema inventory、job events、adapter metadata、audit trace、mock/real evidence separation
- **本次计划解决的问题**：
  - schema 漂移无集中断言。
  - `job_events` 只有 start/complete/fail/cancel，缺 step-level 语义。
  - audit trace 不含 policy/release/eval 的完整链。
- **本次计划的直接产出**：
  - schema drift inventory 与测试。
  - step-level observability contract。
  - audit trace completeness tests。
- **本计划不重新讨论的设计结论**：
  - 不先建设完整 OTel 平台，只借 vocabulary 落 DB events/trace JSON（来源：`docs/eval/first-test/reference-anchor.md:108-111`）。
  - SQLite WAL 是本地单机边界，不代表多 worker 平台（来源：`docs/eval/first-test/reference-anchor.md:179-195`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先建 schema inventory 和 drift tests，再定义/扩展 job_events metadata 合同，最后扩 audit trace 与 mock/real evidence separation。FT2 产出的 contract 是 FT3-FT7 的公共验收面。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Schema drift inventory | M | migration/order/table/column/FK/WAL drift guard | FT1 |
| Phase 2 | Observability event contract | M | step events、adapter metadata、failure summary | Phase 1 |
| Phase 3 | Trace and evidence contract | M | audit trace、mock/real separation、pipeline_runs boundary | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Schema drift inventory**
   - **核心目标**：把 current schema 的关键合同变成测试。
   - **为什么先做**：后续新增 metadata/trace 不能破坏 DB 基线。
2. **Phase 2 — Observability event contract**
   - **核心目标**：每个 major step 可被追踪、诊断和汇总。
   - **为什么放在这里**：真实 adapter 失败需要机器可读 evidence。
3. **Phase 3 — Trace and evidence contract**
   - **核心目标**：API trace 可串联 job/artifact/eval/policy/release。
   - **为什么放在这里**：FT6/FT7 需要前端可消费状态。

### 1.4 执行策略说明

- **执行顺序原则**：schema tests → event writer contract → runner/pipeline instrumentation → trace API。
- **风险控制原则**：优先用现有 JSON 字段；`job_events` 当前没有 `metadata_json`，若 step evidence 需要结构化字段，必须通过新增 migration 或明确的 JSON payload convention 承接。
- **测试推进原则**：DB unit 和 TestClient trace tests 是硬闸。
- **文档同步原则**：输出 schema inventory 与 observability contract。
- **回滚 / 降级原则**：如果 metadata 字段不足，先退到 JSON payload，不破坏现有表。

### 1.5 影响结构图

```text
FT2 Schema/Observability
├── schema drift
│   ├── db/migrations/*.sql
│   ├── src/myvoiceclone/storage/migrations.py
│   └── tests/unit/storage/*
├── job events
│   ├── src/myvoiceclone/jobs/events.py
│   ├── src/myvoiceclone/jobs/runner.py
│   └── pipelines/*
└── trace/evidence
    ├── src/myvoiceclone/api/routes_reports.py
    ├── eval/report/objective/subjective
    └── tests/api/test_audit_trace.py
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** schema drift inventory and tests.
- **[S2]** `job_events` step-level metadata contract.
- **[S3]** adapter metadata and failure summary.
- **[S4]** audit trace completeness for job/artifact/eval/policy/release.
- **[S5]** mock/real metric and artifact source separation.

### 2.2 Out-of-Scope

- **[O1]** Full OTel SDK/platform integration.
- **[O2]** Multi-worker queue and concurrency hardening.
- **[O3]** Real adapter implementation, handled by FT3/FT4.
- **[O4]** Full new workflow engine around `pipeline_runs`.

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `job_events` structured metadata contract | in-scope | 当前 `job_events` 只有 `id/job_id/event_type/status_from/status_to/message/created_at`，需要新增 `metadata_json` 或明确 JSON message convention | 字段缺失无法表达 step evidence |
| `pipeline_runs` production wiring | defer | 当前可用 job_events 降级 | FT6 UI/resume 需要 |
| OTel SDK | out-of-scope | 过重 | 多服务或外部监控需要 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT2-P1-01 | Phase 1 | schema drift inventory | add | `tests/unit/storage/test_schema_drift.py`, `db/migrations/*.sql` | 核心表/列/CHECK/FK/索引/顺序漂移会失败 | FT2-T01 | medium |
| FT2-P1-02 | Phase 1 | SQLite pragma boundary | update | `src/myvoiceclone/storage/sqlite.py:21-37` | FK/WAL/busy_timeout 可断言 | FT2-T02 | low |
| FT2-P2-01 | Phase 2 | step-level job_events | update | `src/myvoiceclone/jobs/events.py:5-20`, `src/myvoiceclone/jobs/runner.py:132-163` | 每步有 start/success/fail event | FT2-T03 | medium |
| FT2-P2-02 | Phase 2 | failure summary 上卷 | update | `src/myvoiceclone/pipelines/clean.py`, `transcribe.py`, `jobs/runner.py:103-123` | 局部失败不被 completed 掩盖 | FT2-T04 | medium |
| FT2-P2-03 | Phase 2 | adapter metadata contract | update | `src/myvoiceclone/adapters/*`, `src/myvoiceclone/storage/artifact_store.py` | metadata 有 tool/model/version/device/cache/mode/license | FT2-T05 | medium |
| FT2-P3-01 | Phase 3 | audit trace completeness | update | `src/myvoiceclone/api/routes_reports.py:190-284` | trace 包含 release/policy/eval/artifacts | FT2-T06 | medium |
| FT2-P3-02 | Phase 3 | mock/real evidence separation | update | `src/myvoiceclone/eval/objective.py:43-80`, reports/eval | mock 不可当 real pass | FT2-T07 | low |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT2.1` | FT2-P1-01 | `T-FT2.1` | FT2-T01 |
| `FT2.2` | FT2-P1-02 | `T-FT2.2` | FT2-T02 |
| `FT2.3` | FT2-P2-03 | `T-FT2.3` | FT2-T05 |
| `FT2.4` | FT2-P2-01 | `T-FT2.4` | FT2-T03 |
| `FT2.5` | FT2-P2-02 | `T-FT2.5` | FT2-T04 |
| `FT2.6` | FT2-P3-01 | `T-FT2.6` | FT2-T06 |
| `FT2.7` | FT2-P3-02 / FT2-P1-01 | `T-FT2.7` | FT2-T07 / FT2-T01 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Schema drift inventory

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT2-P1-01 | schema drift inventory | a) 枚举核心表和列；b) 断言 CHECK/FK/索引/default；c) 断言 migration 顺序和 checksum drift；d) 维护 expected schema snapshot fixture；e) 标注 vec0 128-d mock 边界。 | `db/migrations/*.sql`, `src/myvoiceclone/storage/migrations.py:33-84` | schema drift 可被单测发现 | FT2-T01 | drift guard pass |
| FT2-P1-02 | SQLite pragma boundary | 断言 `foreign_keys`, file DB WAL, `busy_timeout=5000`；明确不是多 worker 保证。 | `src/myvoiceclone/storage/sqlite.py:21-37` | SQLite runtime 边界可验证 | FT2-T02 | pragma test pass |

### 4.2 Phase 2 — Observability event contract

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT2-P2-01 | step-level job_events | a) 为 `job_events` 新增 `metadata_json` migration 或定义 JSON message convention；b) runner 在 ingest/diarize/slice/clean/transcribe/score 前后写事件；c) failed step 写 error。 | `src/myvoiceclone/jobs/events.py:5-20`, `src/myvoiceclone/jobs/runner.py:138-163`, `db/migrations/002_state_jobs_artifacts.sql:13-22` | 每步可追踪 | FT2-T03 | event contract pass |
| FT2-P2-02 | failure summary 上卷 | 汇总 segment-level failed count 和 reasons 到 job error/metadata/report。 | `src/myvoiceclone/jobs/runner.py:103-123`, `src/myvoiceclone/pipelines/clean.py`, `src/myvoiceclone/pipelines/transcribe.py` | job success 不掩盖局部失败 | FT2-T04 | failure summary pass |
| FT2-P2-03 | adapter metadata contract | 在 artifact/job metadata 写 adapter mode、tool/model/version/device/cache/license/stderr summary。 | `src/myvoiceclone/adapters/*`, `src/myvoiceclone/storage/artifact_store.py` | 真实失败可诊断 | FT2-T05 | metadata pass |

### 4.3 Phase 3 — Trace and evidence contract

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT2-P3-01 | audit trace completeness | 扩展 `/audit/trace` 聚合 policy_events、release_gates、eval_metrics、eval_samples、artifacts。 | `src/myvoiceclone/api/routes_reports.py:190-284` | trace 可支撑 FT6/FT7 | FT2-T06 | trace test pass |
| FT2-P3-02 | mock/real evidence separation | 所有 eval/report/artifact metadata 明确 `adapter_mode` 与 `metric_source`；优先落 `eval_metrics.metric_json` / report summary / artifact metadata，mock metric 不可 quality pass。 | `src/myvoiceclone/eval/objective.py:43-80`, `src/myvoiceclone/eval/report.py`, `db/migrations/007_reconcile_to_plan.sql:175-189` | no mock-as-real | FT2-T07 | separation test pass |

---

## 5. Phase 详情

### 5.1 Phase 1 — Schema drift inventory

- **目标**：让 DB 漂移成为测试失败，而不是 capstone 才暴露。
- **新增文件**：`tests/unit/storage/test_schema_drift.py`
- **修改文件**：如需补 migration metadata，限定在 `db/migrations/*`
- **具体功能预期**：
  1. 空 DB 全量 migration 可执行。
  2. 核心表和列存在且类型、CHECK、FK、索引、default 与 expected snapshot 一致。
  3. migration checksum drift 被捕获。
  4. SQLite pragma 被断言。
  5. vec0 128-d mock boundary 被记录，不误判为真实 embedding ready。
- **测试项**：FT2-T01 / FT2-T02
- **收口标准**：schema-drift-gate 通过。
- **风险提醒**：不要为了测试方便放宽约束。

### 5.2 Phase 2 — Observability event contract

- **目标**：每个真实 pipeline step 都有机器可读诊断证据。
- **修改文件**：`jobs/events.py`, `jobs/runner.py`, relevant pipelines/adapters
- **具体功能预期**：
  1. step start/success/fail 有统一 event_type；结构化 metadata 通过新增 `job_events.metadata_json` 或 JSON message convention 明确承接。
  2. duration、error、artifact refs、adapter_mode 可查询。
  3. segment-level failures 汇总。
  4. metadata 不含长 stderr，全量 stderr 进入 evidence pack 或摘要。
  5. mock/real mode 始终显式。
- **测试项**：FT2-T03 / FT2-T04 / FT2-T05
- **收口标准**：observability-gate 通过。
- **风险提醒**：不要把日志字符串当唯一 evidence。

### 5.3 Phase 3 — Trace and evidence contract

- **目标**：API trace 能解释一次 first-test run。
- **修改文件**：`src/myvoiceclone/api/routes_reports.py`, eval/report modules
- **具体功能预期**：
  1. job trace 包含 events/artifacts。
  2. run/report trace 包含 eval_metrics/eval_samples。
  3. release/policy trace 可查。
  4. missing subject 有明确 404。
  5. trace events 稳定排序。
- **测试项**：FT2-T06 / FT2-T07
- **收口标准**：trace completeness 和 mock-real gate 通过。
- **风险提醒**：trace 不应暴露真实 token 或完整 secret env。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Owner-gate non-blocking for AP drafting | 当前用户消息 + proposed planning | 不等待 owner-gate 制作 AP，但不把 gate 当已关闭 evidence | final 前按 evidence 复核 |
| TR-1/2/3/4 | `docs/eval/first-test/reference-anchor.md:187-195` | DB job/evidence/no mock fallback/no full OTel | 回 reference-anchor |
| FT2 proposed baseline | `docs/eval/first-test/proposed-planning.md:170-194` | 定义工作项与测试 | 回 proposed |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT2-1 | `src/myvoiceclone/storage/migrations.py:33-84` | migration runner | FT2-P1-01 | ✅ 复用 | checksum drift |
| A-FT2-2 | `src/myvoiceclone/storage/sqlite.py:21-37` | SQLite connection pragmas | FT2-P1-02 | ✅ 复用 | FK/WAL/busy_timeout |
| A-FT2-3 | `src/myvoiceclone/jobs/events.py:5-20` | job event writer | FT2-P2-01 | ♻️ 重 substrate | add metadata contract |
| A-FT2-4 | `src/myvoiceclone/jobs/runner.py:132-163` | preprocess step sequence | FT2-P2-01 | ✅ 复用 | step instrumentation |
| A-FT2-5 | `src/myvoiceclone/api/routes_reports.py:190-284` | audit trace endpoint | FT2-P3-01 | ♻️ 重 substrate | trace completeness |
| A-FT2-6 | `src/myvoiceclone/eval/objective.py:43-80` | mock objective metrics | FT2-P3-02 | ♻️ 重 substrate | metric_source |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 |
|----|--------------|--------|
| ⛔1 | 先接完整 OTel 平台 | reference-anchor 明确只借 vocabulary |
| ⛔2 | job completed 等于所有 segment succeeded | state-analysis 已指出局部失败可能被吞 |
| ⛔3 | mock metric 进入 quality pass | 会误判真实 e2e |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-test/reference-anchor.md`。
- **威胁模型锚**：trace/evidence 不能泄露 token、absolute secret path 或完整 stderr secret。锚定 `TR-2/TR-3/TR-5` 与 `src/myvoiceclone/api/routes_reports.py:190-284`。

---

## 8. 测试台账

### 8.1 测试清单

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据 |
|---------|--------|------|----|------|------|-----------|
| FT2-T01 | migration/schema inventory + expected snapshot | 短途 | db/unit | 🆕 新增 `tests/unit/storage/test_schema_drift.py` | FT2-P1-01 → tables/columns/CHECK/FK/index/default/order drift guard | commit + pytest + run-time |
| FT2-T02 | SQLite pragma boundary | 短途 | db/unit | 🔱 fork `tests/unit/storage/test_sqlite_connection.py` | FT2-P1-02 → pragmas | commit + pytest + run-time |
| FT2-T03 | step job_events metadata | 短途 | unit/jobs | 🔱 fork `tests/unit/jobs/test_runner.py` | FT2-P2-01 → step events | commit + pytest + run-time |
| FT2-T04 | failure summary | 短途 | unit/jobs | 🆕 新增 `tests/unit/jobs/test_failure_summary.py` | FT2-P2-02 → no swallowed failures | commit + pytest + run-time |
| FT2-T05 | adapter metadata contract | 短途 | unit/adapters | 🔱 fork adapter tests | FT2-P2-03 → metadata + license | commit + pytest + run-time |
| FT2-T06 | audit trace completeness | 短途 | api/TestClient | 🔱 fork `tests/api/test_audit_trace.py` | FT2-P3-01 → complete trace | commit + pytest + run-time |
| FT2-T07 | mock/real evidence separation | 短途 | unit/eval | 🔱 fork `tests/unit/eval/test_objective.py` | FT2-P3-02 → no mock-as-real | commit + pytest + run-time |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |

---

## 9. 执行工作日志

- `2026-06-13 08:31 UTC` — [代码制作] 完成 FT2-P1/P2/P3：新增 `008_first_test_observability.sql`，为 `job_events` 增加 `metadata_json` 与 event index；扩展 `JobEvent`、`JobRepository.add_event()`、`write_job_event()` 与 `write_step_event()`；`preprocess_all` 六步增加 `step_started/step_succeeded/step_failed` 事件与 duration/error metadata；新增 preprocess failure summary event；artifact metadata 默认写入 `adapter_mode/metric_source/metadata_contract_version` 与 adapter metadata keys；objective mock metrics 写 `metric_json.metric_source=mock` 且 `quality_gate_eligible=false`；audit trace 扩展 job artifact、run eval/release/policy、report eval/policy 与 release_gate subject。
- `2026-06-13 08:31 UTC` — [代码审查，测试与文档回填] 新增/扩展 schema drift、SQLite pragma、runner event metadata、artifact metadata、objective mock separation、audit trace completeness tests；执行 `./venv/bin/python -m pytest tests/unit/storage/test_schema_drift.py tests/unit/storage/test_sqlite_connection.py tests/unit/jobs/test_runner.py tests/unit/storage/test_artifact_observability.py tests/unit/eval/test_objective.py tests/api/test_audit_trace.py -q`，结果 `13 passed, 1 warning`；执行 FT1+FT2 合并短途 suite，结果 `39 passed, 3 warnings`；执行 `python3 -m compileall -q src tests` 通过。
|----------|------|------|------------|
| `tests/unit/storage/test_migrations.py` | ♻️ 沿用 | 纳入 regression | 已存在 |
| `tests/api/test_audit_trace.py` | 🔱 fork | 加 policy/release/eval links | 已存在 |
| `tests/unit/jobs/test_runner.py` | 🔱 fork | 加 step event assertions | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest tests/unit/storage tests/unit/jobs tests/api -q` | db/unit/api | 每次 FT2 变更 |

### 8.4 测试缺口

- 不覆盖真实 adapter live execution → FT3/FT4。
- 不覆盖 full API capstone → FT7。

### 8.5 测试保真

- schema-drift-gate 与 observability-gate 是 e2e 前置。
- trace 不得包含 token/secret。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| schema test 太脆 | 合法 migration 也会失败 | medium | 用 explicit inventory 并同步更新 |
| metadata_json 过载 | 字段语义不稳定 | medium | final 前评估 migration |
| trace 泄露 secret | stderr/env 可能有 token | high | 摘要化与 redaction |

### 9.2 约束与前提

- **技术前提**：SQLite schema 先不大改。
- **运行时前提**：unit DB 可以用 temp file 运行 migrations。
- **组织协作前提**：FT2 contract 下游必须遵守。
- **上线 / 合并前提**：schema-drift-gate 与 observability-gate 通过。

### 9.3 文档同步要求

- `docs/eval/first-test/proposed-planning.md` 若 schema strategy 变化需回注。
- 可新增 `docs/eval/first-test/schema-observability-contract.md` 作为实现附录。

### 9.4 完成后的预期状态

1. DB schema drift 可被单测捕获。
2. preprocess major steps 有 event evidence。
3. adapter metadata 能解释真实依赖失败。
4. audit trace 可支撑 FastAPI e2e 和 capstone。

---

## 10. 收口

### 10.1 收口硬闸

1. `schema-drift-gate` PASS（FT2-T01/FT2-T02）。
2. `observability-gate` PASS（FT2-T03..FT2-T05）。
3. trace/mock-real gates PASS（FT2-T06/FT2-T07）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| schema drift 被捕获 | FT2-P1-01..02 | FT2-T01..02 | commit + pytest + run-time | 未观察 |
| step observability 完整 | FT2-P2-01..03 | FT2-T03..05 | commit + pytest + run-time | 未观察 |
| trace 与 mock-real 隔离 | FT2-P3-01..02 | FT2-T06..07 | commit + pytest + run-time | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | schema/event/trace contracts 可用 |
| 测试 | §8 全 PASS |
| 文档 | contract 与 deferred 边界同步 |
| 风险收敛 | 不靠日志人工猜失败 |
| 可交付性 | 可进入 FT3/FT4/FT6 |

### 10.4 NOT-成功识别

若 capstone 前仍无法从 DB/API 看出 step failure、artifact refs 或 metric source，则 FT2 不得标 `executed`。
