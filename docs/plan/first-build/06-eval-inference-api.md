# Nano-Agent 行动计划：P6 Evaluation + Inference API

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P6 Evaluation + Inference API`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/06-eval-inference-api.md`
> 上游前序 / closure:
> - `04-quick-baselines.md`
> - `05-long-train-sovits.md`（仅 P5 长训模型评估补齐依赖；P6 API/CLI/eval skeleton 可在 P4 后开始）
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:201`
> 下游交接:
> - `07-security-governance-retrofit.md`
> - `08-ops-handoff.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:629`（接口设计）
> 冻结决策来源:
> - `final-execution-plan.md:505`（Q4）
> - `final-execution-plan.md:507`（Q6）
> grounding 来源:
> - `final-execution-plan.md:205`、`:440`、`:631`、`:652`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P6 将前面 P1-P4 的能力先暴露为稳定的 HTTP API、CLI、inference job、objective/subjective eval 和 audit trace，并在 P5 长训产物可用后补齐长训模型评估。它必须保持 API/CLI 调 service/job，不直接调外部模型工具；同时把 reports、metrics、rendered artifacts 统一纳入可审计链路。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P6 Evaluation + Inference API`
- **本次计划解决的问题**：
  - 缺少统一 API/CLI 入口。
  - inference 和 eval 需要 job 化、artifact 化。
  - 用户需要通过 audit endpoint 查询 recording/job/dataset/run 全链路。
- **本次计划的直接产出**：
  - FastAPI app/routes/schemas
  - Typer CLI
  - objective/subjective eval modules
  - inference service and audit trace endpoint
- **本计划不重新讨论的设计结论**：
  - FastAPI + Typer，HTTP/CLI 调 service/job（来源：`final-execution-plan.md:505`）。
  - 所有步骤记录状态、日志、artifact、report、metrics（来源：`final-execution-plan.md:507`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先 app factory 和 schema，再 routes，再 CLI，再 inference/eval/report/audit”的方式。所有 routes 使用 dependency injection 指向 tmp DB/service，TestClient 和 CliRunner 必须能在无真实模型环境下测试。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | App factory + schemas | M | FastAPI DI 与 Pydantic contract | P1 |
| Phase 2 | Routes | L | recordings/segments/datasets/jobs/runs/reports/inference/audit | Phase 1 |
| Phase 3 | CLI | M | Typer commands 调用 service/job | Phase 2 |
| Phase 4 | Inference | M | VC/TTS/batch render job | P4；P5 产物可后补 |
| Phase 5 | Eval/report/audit | L | objective metrics、subjective report、trace endpoint | Phase 4；长训评估依赖 P5 |

### 1.3 Phase 说明

1. **Phase 1 — App factory + schemas**
   - **核心目标**：让 API 可测试、可注入 tmp DB。
   - **为什么先做**：routes 都依赖 schema/DI。
2. **Phase 2 — Routes**
   - **核心目标**：实现 final §15.1 的 HTTP surface。
   - **为什么放在这里**：统一外部入口。
3. **Phase 3 — CLI**
   - **核心目标**：本地批处理入口与 API 共享 service。
   - **为什么放在这里**：开发者 first-build 主要通过 CLI 操作。
4. **Phase 4 — Inference**
   - **核心目标**：VC/TTS 渲染作为 job 和 artifact 运行。
   - **为什么放在这里**：P7 要基于 rendered artifact 接安全 metadata。
5. **Phase 5 — Eval/report/audit**
   - **核心目标**：可量化评估、主观报告、审计查询。
   - **为什么放在这里**：release/handoff 需要 evidence。

### 1.4 执行策略说明

- **执行顺序原则**：schema/app factory 先于 routes，routes/CLI 只调 service/job。
- **风险控制原则**：不使用 FastAPI BackgroundTasks 执行真实长任务。
- **测试推进原则**：TestClient + CliRunner + fake adapters。
- **文档同步原则**：OpenAPI snapshot 写入 `docs/api/openapi.md`。
- **回滚 / 降级原则**：route 创建 job 后如果 runner 失败，API 只报告 job failed，不伪造成功。

### 1.5 本次 action-plan 影响结构图

```text
P6 API/Eval/Inference
├── src/myvoiceclone/api/*
├── src/myvoiceclone/cli.py
├── src/myvoiceclone/eval/{objective,subjective,report}.py
├── src/myvoiceclone/pipelines/evaluate.py
├── docs/api/openapi.md
└── tests/{api,cli,unit/eval}
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** FastAPI app factory、schemas、routes。
- **[S2]** Typer CLI commands。
- **[S3]** inference job for VC/TTS/batch render。
- **[S4]** objective/subjective eval, report, audit trace。

### 2.2 Out-of-Scope

- **[O1]** 授权/安全 gate，交给 P7。
- **[O2]** 真实 UI 前端。
- **[O3]** 云端任务队列。
- **[O4]** 真实模型质量保证，交给 live/gpu/subjective evidence。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| FastAPI routes | in-scope | Q4 冻结 | API 框架变更 |
| Auth middleware | out-of-scope | Q2 后置 | P7 |
| Audit endpoint | in-scope | Q6 审计要求 | 无 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P6-01 | Phase 1 | FastAPI app factory + DI | add | `api/app.py` | TestClient 可注入 tmp DB | P6-T01 | medium |
| P6-02 | Phase 2 | HTTP routes | add | `api/routes_*.py`, `api/schemas.py` | OpenAPI schema stable | P6-T02 | high |
| P6-03 | Phase 3 | Typer CLI | add | `cli.py` | CliRunner tests PASS | P6-T03 | medium |
| P6-04 | Phase 4 | Inference service | add | `routes_inference.py`, adapters | fake render artifact | P6-T04 | high |
| P6-05 | Phase 5 | Objective eval | add | `eval/objective.py`, `pipelines/evaluate.py` | metrics rows/report | P6-T05 | medium |
| P6-06 | Phase 5 | Subjective report | add | `eval/subjective.py`, `eval/report.py` | report bundle | P6-T06 | medium |
| P6-07 | Phase 5 | Audit trace endpoint | add | `routes_reports.py`, `jobs/events.py` | recording/job/dataset/run trace | P6-T07 | high |

---

## 4. Phase 业务表格

### 4.1 Phase 1/2 — API app and routes

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P6-01 | FastAPI app factory + DI | a) `create_app(settings, services)`；b) tmp DB dependency override；c) router registration；d) health/version endpoint | `api/app.py` | TestClient 可控 | P6-T01 | app factory test PASS |
| P6-02 | HTTP routes | a) 实现 final §15.1 routes；b) schemas 验证 request/response；c) POST routes 创建 job 或 resource；d) GET routes 返回 artifact/event summary；e) error mapping | `api/routes_*.py`, `api/schemas.py` | API surface stable | P6-T02 | route tests PASS |

### 4.2 Phase 3 — CLI

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P6-03 | Typer CLI | a) 实现 final §15.2 commands；b) commands 调 service/job；c) `--dry-run` 用于 scripts；d) 输出 job/report ids；e) 不直接调 adapter | `cli.py` | 本地批处理入口 | P6-T03 | CliRunner PASS |

### 4.3 Phase 4/5 — Inference/eval/audit

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P6-04 | Inference service | a) VC/TTS request -> job；b) fake adapter render；c) rendered audio artifact；d) failed render 写 error；e) P7 synthetic metadata 预留 | `routes_inference.py` | rendered artifact | P6-T04 | fake render PASS |
| P6-05 | Objective eval | a) speaker similarity/WER/duration/noise metric contracts；b) metrics rows；c) eval_samples linkage；d) report linkage；e) missing metric 标 degraded reason；f) P5 长训模型可用后补跑同一 suite | `eval/objective.py` | metrics 可查询并可审计 | P6-T05 | metric tests PASS |
| P6-06 | Subjective report | a) ABX/MOS schema；b) sample bundle；c) JSON/Markdown report；d) 不要求 UI | `eval/subjective.py`, `report.py` | subjective report bundle | P6-T06 | report fixture PASS |
| P6-07 | Audit trace endpoint | a) 聚合 subject 的 jobs/events/artifacts/reports/model_runs/eval_metrics/eval_samples；b) 按时间排序；c) 支持 recording/job/dataset/run/report；d) 缺失返回 404 | `routes_reports.py`, `jobs/events.py` | 全链路可审计 | P6-T07 | trace endpoint PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2/3 — API and CLI

- **Phase 目标**：提供稳定外部入口，但不泄漏 adapter 实现。
- **本 Phase 对应编号**：P6-01 / P6-02 / P6-03
- **本 Phase 新增文件**：`api/app.py`, `api/schemas.py`, `api/routes_*.py`, `cli.py`
- **具体功能预期**：
  1. TestClient 能使用 tmp DB。
  2. OpenAPI schema 可 snapshot。
  3. CLI 与 HTTP 创建同类 job payload。
  4. route 不直接调用 pyannote/Demucs/RVC/So-VITS。
  5. 错误响应不吞掉 job_id/error。
- **对应测试台账项**：P6-T01..P6-T03
- **收口标准**：API/CLI route/command tests PASS。
- **本 Phase 风险提醒**：不要用 BackgroundTasks 执行长训。

### 5.2 Phase 4/5 — Inference/eval/audit

- **Phase 目标**：把模型输出、指标和审计链路产品化为接口。
- **本 Phase 对应编号**：P6-04..P6-07
- **本 Phase 新增文件**：`eval/objective.py`, `eval/subjective.py`, `pipelines/evaluate.py`
- **具体功能预期**：
  1. inference 输出一定是 artifact。
  2. objective metrics 缺失时有 degraded reason。
  3. subjective report 可导出但不要求 UI。
  4. audit trace 能跨 jobs/events/artifacts/reports/model_runs/eval_metrics/eval_samples 聚合。
  5. P7 可在 inference artifact 上接 synthetic/security metadata。
- **对应测试台账项**：P6-T04..P6-T07
- **收口标准**：render/eval/report/audit mock flow PASS。
- **本 Phase 风险提醒**：API 成功创建 job 不等于 job 成功。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q4 | `final-execution-plan.md:505` | FastAPI + Typer | 重开接口方案 |
| Q6 | `final-execution-plan.md:507` | audit trace/report 必填 | 不得只返回文件路径 |
| Q7 | `final-execution-plan.md:508` | API/CLI tests 默认 fake | live tests 单独 marker |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-1 | `final-execution-plan.md:201` | P6 工作台账 | P6-01..07 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:440` | API files | P6-01..07 | ✅ 复用 | source |
| A-3 | `final-execution-plan.md:631` | HTTP routes | P6-02/P6-04/P6-07 | ✅ 复用 | contract |
| A-4 | `final-execution-plan.md:652` | CLI commands | P6-03 | ✅ 复用 | contract |
| A-5 | `final-execution-plan.md:277` | P6 tests | P6-T* | ✅ 复用 | tests |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | API route 直接调训练仓库 | Q4/Q5 要 service/job |
| ⛔2 | FastAPI BackgroundTasks 执行长训 | final 反例明确禁止 |
| ⛔3 | inference 输出不入 artifacts | Q6 要可审计 |
| ⛔4 | audit endpoint 只查单表 | 需要全链路 trace |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：P6 预留 metadata，不实现 auth；P7 锚为 `final-execution-plan.md:213`。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据（四元组） |
|---------|--------|------|----|------|------|-----------|
| P6-T01 | app factory dependency override | 短途 | unit | 🆕 新增 `tests/api/test_app_factory.py` | P6-01 → tmp DB 注入 | commit {sha} + pytest tests/api/test_app_factory.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P6-T02 | route validation/status codes/OpenAPI | 短途 | unit | 🆕 新增 `tests/api/test_routes_*.py` | P6-02 → route stable | commit {sha} + pytest tests/api/test_routes_*.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P6-T03 | CLI commands via CliRunner | 短途 | unit | 🆕 新增 `tests/cli/test_cli_*.py` | P6-03 → CLI 可用 | commit {sha} + pytest tests/cli/test_cli_*.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P6-T04 | fake VC/TTS render job | 短途 | 集成 | 🆕 新增 `tests/api/test_inference_routes.py` | P6-04 → rendered artifact | commit {sha} + pytest tests/api/test_inference_routes.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P6-T05 | objective metrics rows/report/eval_samples | 短途 | unit | 🆕 新增 `tests/unit/eval/test_objective.py` | P6-05 → metrics 可查 | commit {sha} + pytest tests/unit/eval/test_objective.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P6-T06 | subjective report bundle | 短途 | unit | 🆕 新增 `tests/unit/eval/test_subjective.py` | P6-06 → report bundle | commit {sha} + pytest tests/unit/eval/test_subjective.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P6-T07 | audit trace endpoint | 短途 | unit | 🆕 新增 `tests/api/test_audit_trace.py` | P6-07 → 全链路 trace | commit {sha} + pytest tests/api/test_audit_trace.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P1 tmp DB fixtures | ♻️ 沿用 | TestClient DI | P1 完成后可用 |
| P4 fake model fixtures | ♻️ 沿用 | inference/eval inputs | P4 完成后可用；P5 后补长训模型评估 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m \"api or cli or unit\" tests/api tests/cli tests/unit/eval` | api·cli·unit | 每次 P6 改动 |
| spike | API live server smoke | live | 可选 |
| mega | mock journey | integration | P8 |
| soak | 不适用 | - | P6 无长稳 |

### 8.4 测试缺口

- 不覆盖前端 UI（理由：first-build 无 UI scope）→ 后续产品阶段。
- 不覆盖真实模型渲染质量（理由：fake adapter 默认）→ live/gpu/subjective evidence。

### 8.5 测试保真

- API 202/created job 不代表 job succeeded。
- Objective metric degraded 必须带 reason。
- Audit trace 必须覆盖 jobs/events/artifacts/reports/model_runs/eval_metrics/eval_samples 中至少四类数据。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| API 过早固化 | 后续 P7 需要 policy | medium | metadata/feature flag 预留 |
| 长任务误放 BackgroundTasks | 不可取消不可恢复 | high | 所有长任务走 jobs.runner |
| CLI 绕过 service | 行为不一致 | medium | CLI tests 对比 API job payload |

### 9.2 约束与前提

- **技术前提**：P1 DB + P4 fake adapters；P5 产物后续补入长训模型评估。
- **运行时前提**：无 auth middleware。
- **组织协作前提**：OpenAPI contract 后续由 docs/api 跟踪。
- **上线 / 合并前提**：P6-T01..P6-T07 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/api/openapi.md`
- 需要同步更新的说明文档 / README：P8 quickstart
- 需要同步更新的测试说明：API/CLI tests

### 9.4 完成后的预期状态

1. 本地用户可通过 API/CLI 操作核心流程。
2. Inference 和 eval 结果可审计。
3. P7 能接入 release/security policy。

---

## 10. 收口

### 10.1 收口硬闸

1. API/CLI tests PASS。
2. Inference/eval/report/audit mock flow PASS。
3. Route/CLI 不直接调用 adapters。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组） | 状态 |
|----------|--------|---------|-----------|------|
| app factory | P6-01 | P6-T01 | commit MVC-P6-complete + pytest tests/api/test_app_factory.py PASS + 2026-06-13 11:32 UTC | verified |
| routes | P6-02 | P6-T02 | commit MVC-P6-complete + pytest tests/api/test_routes.py PASS + 2026-06-13 11:32 UTC | verified |
| CLI | P6-03 | P6-T03 | commit MVC-P6-complete + pytest tests/cli/test_cli.py PASS + 2026-06-13 11:32 UTC | verified |
| inference | P6-04 | P6-T04 | commit MVC-P6-complete + pytest tests/api/test_inference_routes.py PASS + 2026-06-13 11:32 UTC | verified |
| metrics | P6-05 | P6-T05 | commit MVC-P6-complete + pytest tests/unit/eval/test_objective.py PASS + 2026-06-13 11:32 UTC | verified |
| subjective report | P6-06 | P6-T06 | commit MVC-P6-complete + pytest tests/unit/eval/test_subjective.py PASS + 2026-06-13 11:32 UTC | verified |
| audit trace | P6-07 | P6-T07 | commit MVC-P6-complete + pytest tests/api/test_audit_trace.py PASS + 2026-06-13 11:32 UTC | verified |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | API/CLI/inference/eval/audit 可用 |
| 测试 | P6-T01..P6-T07 全 PASS |
| 文档 | OpenAPI snapshot 更新 |
| 风险收敛 | 长任务不在 BackgroundTasks 中执行 |
| 可交付性 | 可进入 P7/P8 |

### 10.4 NOT-成功识别

API route 直调 adapter、inference 不生成 artifact、或 audit trace 不跨表，均不得标 `executed`。
