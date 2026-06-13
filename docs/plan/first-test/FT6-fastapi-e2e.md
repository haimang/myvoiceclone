# FT6 FastAPI E2E Action Plan

> 服务业务簇: `FT6 · FastAPI e2e surface 与前端可消费合同`
> 计划对象: `run surface, upload artifact, job orchestration, status/report/trace API`
> 类型: `new`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT6-fastapi-e2e.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT2-schema-observability.md`
> - `docs/plan/first-test/FT4-real-inference.md`
> - `docs/plan/first-test/FT5-real-evaluation.md`
> 下游交接:
> - `docs/plan/first-test/FT7-live-capstone.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT6`, `reference-anchor axis E/F/G/H`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT6 把 first-test 能力暴露为真实前端可消费的 FastAPI surface。它不引入生产任务队列，也不冻结全局 API envelope；本阶段只冻结 `create run -> upload/register audio -> start preprocess/infer/eval -> poll status -> query artifacts/report/release/trace` 所需字段。

- **服务业务簇**：`FastAPI e2e surface`
- **计划对象**：API routes, schemas, artifact upload, DB job orchestration, status/trace query
- **本次计划解决的问题**：
  - 当前 API 更像 job wrapper，缺 first-test run surface。
  - `UploadFile` 长任务若不立即落 artifact，会失去可恢复性。
  - 前端无法一次性理解 step events、artifact summary、failure summary 和 report trace。
- **本次计划的直接产出**：
  - first-test run API contract。
  - upload/register audio 立即写 artifact。
  - start endpoints 只创建/触发 DB job。
  - status/report/release/trace 查询接口。
  - TestClient coverage 与 live HTTP spike。
- **本计划不重新讨论的设计结论**：
  - FastAPI surface 是 first-test e2e 接口，不是生产级队列（来源：`docs/eval/first-test/reference-anchor.md:189-195`）。
  - 不在本阶段强行冻结全局 response envelope（来源：`docs/eval/first-test/reference-anchor.md:125-128`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先定义 run surface 和 response contract，再补 upload artifact 与 start job endpoints，最后用 status/report/trace API 串成 TestClient 与 live HTTP 分层验证。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | API contract | M | run/status/artifact/report 字段冻结；route skeleton 可在 FT1 后预备 | FT1；成功语义依赖 FT2 |
| Phase 2 | Upload and job start | L | upload 写 artifact，start 创建 DB jobs | Phase 1 / FT4 / FT5 |
| Phase 3 | Query and live smoke | M | status/report/release/trace + live HTTP spike | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — API contract**
   - **核心目标**：前端能依赖本阶段字段。
   - **为什么先做**：避免 endpoint 实现后再次大改响应形状。
2. **Phase 2 — Upload and job start**
   - **核心目标**：所有长任务输入都从 artifact/DB job 恢复，不依赖 request 临时对象。
   - **为什么放在这里**：这是 e2e 可恢复和可观测的基础。
3. **Phase 3 — Query and live smoke**
   - **核心目标**：前端能轮询状态、展示失败、下载/追踪证据。
   - **为什么放在这里**：FT7 capstone 需要直接消费这些接口。

### 1.4 执行策略说明

- **执行顺序原则**：schema contract → route skeleton → artifact upload → job orchestration → status/trace queries。
- **风险控制原则**：上传后立即写 artifact；长任务只引用 artifact id/path。
- **测试推进原则**：TestClient 为主，uvicorn live HTTP 只做 gated spike。
- **文档同步原则**：接口字段变更需更新 contract fixture。
- **回滚 / 降级原则**：队列不可用时仍使用本地 DB job 同步触发；不引入外部 broker。

### 1.5 影响结构图

```text
FT6 FastAPI E2E
├── API contract
│   ├── src/myvoiceclone/api/schemas.py
│   └── contract fixtures
├── routes
│   ├── routes_recordings.py
│   ├── routes_jobs.py
│   ├── routes_inference.py
│   ├── routes_reports.py
│   └── new routes_runs.py
├── persistence
│   ├── storage/artifact_store.py
│   └── jobs/events.py
└── tests
    ├── api/TestClient
    └── live/http
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** first-test create run API。
- **[S2]** upload/register audio 写 artifact。
- **[S3]** start preprocess/infer/eval endpoints 创建/触发 DB job。
- **[S4]** status API 返回 step events、artifact summary、failure summary、mode/source。
- **[S5]** artifacts/eval/report/release/trace 查询 API。
- **[S6]** response contract snapshot。

### 2.2 Out-of-Scope

- **[O1]** 生产级任务队列、worker pool、multi-tenant auth。
- **[O2]** 全局 API envelope breaking change。
- **[O3]** 前端 UI 实现。
- **[O4]** 大文件直接入 repo。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `UploadFile` endpoint | in-scope | FastAPI 标准上传入口 | 文件过大需 chunk/resumable |
| BackgroundTasks | limited | 可触发轻量 job，但状态以 DB 为准 | GPU 长任务进入生产队列 |
| response envelope | defer | breaking change 应在 final contract 冻结前处理 | 前端已集成并需要统一 |
| live HTTP spike | in-scope | 验证真实 socket + uvicorn | CI 无端口时 skip |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT6-P1-01 | Phase 1 | first-test run contract | add/update | `src/myvoiceclone/api/schemas.py:52-107`, `src/myvoiceclone/api/routes_jobs.py:13-46` | run/status 字段冻结 | FT6-T01 / FT6-T06 | medium |
| FT6-P1-02 | Phase 1 | response contract fixture | add | `tests/api/contracts/*` | breaking change 显式更新 | FT6-T06 | low |
| FT6-P2-01 | Phase 2 | upload audio artifact | add/update | `src/myvoiceclone/api/routes_recordings.py:26-38`, `src/myvoiceclone/storage/artifact_store.py:15-104` | upload 后立即有 artifact | FT6-T02 | high |
| FT6-P2-02 | Phase 2 | start preprocess/infer/eval jobs | add/update | `src/myvoiceclone/api/routes_jobs.py:13-46`, `src/myvoiceclone/api/routes_inference.py:10-22`, `src/myvoiceclone/api/routes_reports.py:96-127` | payload 引用 artifact ids | FT6-T03 | high |
| FT6-P3-01 | Phase 3 | status API | add/update | `src/myvoiceclone/jobs/events.py:5-20`, `src/myvoiceclone/api/routes_jobs.py:13-46` | status 含 events/failure/artifacts | FT6-T04 | medium |
| FT6-P3-02 | Phase 3 | report/release/trace API | update | `src/myvoiceclone/api/routes_reports.py:190-284` | 前端可查 eval/policy/release links | FT6-T05 | medium |
| FT6-P3-03 | Phase 3 | live HTTP spike | add | `tests/integration/test_first_test_http_smoke.py`, `pytest.ini:1-11` | uvicorn 路径可验证 | FT6-T07 | medium |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT6.1` | FT6-P1-01 | `T-FT6.1` | FT6-T01 |
| `FT6.2` | FT6-P2-01 | `T-FT6.2` | FT6-T02 |
| `FT6.3` | FT6-P2-02 | `T-FT6.3` | FT6-T03 |
| `FT6.4` | FT6-P3-01 | `T-FT6.4` | FT6-T04 |
| `FT6.5` | FT6-P3-02 | `T-FT6.5` | FT6-T05 |
| `FT6.6` | FT6-P1-02 | `T-FT6.6` | FT6-T06 |
| `FT6.7` | FT6-P3-03 | `T-FT6.7` | FT6-T07 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — API contract

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT6-P1-01 | first-test run contract | 定义 run id/status/config refs、artifact refs、mode/source、links。 | `src/myvoiceclone/api/schemas.py:52-107` | 前端字段稳定 | FT6-T01 | create run contract PASS |
| FT6-P1-02 | response fixture | 为 create/status/report/trace 建 snapshot fixture；变更需显式更新。 | `tests/api/contracts/*` | API drift 可见 | FT6-T06 | contract test PASS |

### 4.2 Phase 2 — Upload and job start

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT6-P2-01 | upload audio artifact | `UploadFile` 读入后立即写 artifact，response 返回 artifact id/sha/bytes，不暴露临时路径。 | `src/myvoiceclone/api/routes_recordings.py:26-38`, `src/myvoiceclone/storage/artifact_store.py:15-104` | 输入可恢复 | FT6-T02 | upload artifact PASS |
| FT6-P2-02 | start jobs | start preprocess/infer/eval 只创建/触发 DB job；payload 引用 artifact/model/report ids。 | `src/myvoiceclone/api/routes_jobs.py:13-46`, `src/myvoiceclone/api/routes_inference.py:10-22`, `src/myvoiceclone/api/routes_reports.py:96-127` | job orchestration 可轮询 | FT6-T03 | payload contract PASS |

### 4.3 Phase 3 — Query and live smoke

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT6-P3-01 | status API | 汇总 job status、step events、failed step、artifact summary、mode/source。 | `src/myvoiceclone/jobs/events.py:5-20`, `src/myvoiceclone/api/routes_jobs.py:13-46` | 前端可展示进度和失败 | FT6-T04 | status TestClient PASS |
| FT6-P3-02 | trace API | 当前 `/audit/trace` 只覆盖部分 subject；需扩为 report/release/trace endpoint，聚合 `policy_events`、`release_gates`、`eval_* by report_id/run_id`，并同时查 `artifacts.job_id` 与 `artifacts.created_by_job_id`。 | `src/myvoiceclone/api/routes_reports.py:190-284` | 证据链可查 | FT6-T05 | trace TestClient PASS |
| FT6-P3-03 | live HTTP spike | 启动 uvicorn 后跑 upload→start→poll→report；缺 live deps skip with reason。 | `tests/integration/test_first_test_http_smoke.py`, `pytest.ini:1-11` | socket 层被验证 | FT6-T07 | live pass/skip reason |

---

## 5. Phase 详情

### 5.1 Phase 1 — API contract

- **目标**：冻结 first-test 前端能消费的最小字段。
- **新增文件**：`src/myvoiceclone/api/routes_runs.py`、contract fixture 可新增。
- **修改文件**：`src/myvoiceclone/api/schemas.py`, app router registration。
- **具体功能预期**：
  1. create run 返回 id/status/config refs。
  2. status links 包含 jobs/artifacts/report/release/trace。
  3. response 不依赖全局 envelope。
  4. schema snapshot 能发现 breaking changes。
  5. run 与 job/artifact/report 可互相定位。
- **测试项**：FT6-T01 / FT6-T06
- **收口标准**：contract tests pass。
- **风险提醒**：不要在 FT6 顺手重构所有既有 API response。

### 5.2 Phase 2 — Upload and job start

- **目标**：长任务从 DB/artifact 恢复，不依赖 request lifetime。
- **具体功能预期**：
  1. upload 写 artifact bytes/sha/metadata。
  2. response 不暴露临时路径。
  3. start preprocess payload 含 audio artifact ref。
  4. start inference payload 含 text/reference/model refs。
  5. start eval payload 含 inference artifact/report refs。
  6. 所有 start endpoints 返回 job/run id。
- **测试项**：FT6-T02 / FT6-T03
- **收口标准**：TestClient payload contract pass。
- **风险提醒**：BackgroundTasks 只能作为触发机制，不能替代 job ledger。

### 5.3 Phase 3 — Query and live smoke

- **目标**：API surface 能支撑真实 e2e 的观测、展示和证据导出。
- **具体功能预期**：
  1. status 返回 step events。
  2. failed step 有 reason/stderr summary。
  3. artifact summary 有 type/bytes/sha/mode。
  4. trace 汇总 report/gate/policy。
  5. live HTTP spike 缺依赖时 skip reason 入 denominator。
- **测试项**：FT6-T04..FT6-T07
- **收口标准**：TestClient 全绿；live spike pass 或 skipped with reason。
- **风险提醒**：不要让 live skip 被误读为 e2e pass。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| FastAPI surface but no production queue | `docs/eval/first-test/reference-anchor.md:189-195` | 使用 DB job，不引入 broker | 另开 infra phase |
| UploadFile immediately becomes artifact | `docs/eval/first-test/reference-anchor.md:99-102` | 长任务只引用 artifact | 阻断 FT6-P2 |
| Response envelope deferred | `docs/eval/first-test/reference-anchor.md:125-128` | 只冻结 first-test fields | final contract 前重评 |
| FT6 proposed scope | `docs/eval/first-test/proposed-planning.md:274-292` | 覆盖 FT6.1..FT6.7/T-FT6.1..7 | 回 proposed planning |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT6-1 | `docs/eval/first-test/reference-anchor.md:95-102` | FastAPI axis | FT6 全部 | ✅ 复用 | e2e API surface |
| A-FT6-2 | `src/myvoiceclone/api/routes_recordings.py:26-38` | current upload/ingest | FT6-P2-01 | ♻️ 重 substrate | 扩为 artifact upload |
| A-FT6-3 | `src/myvoiceclone/api/routes_jobs.py:13-46` | job run/status | FT6-P2/P3 | ✅ 复用 | start/status base |
| A-FT6-4 | `src/myvoiceclone/api/routes_inference.py:10-22` | inference endpoint | FT6-P2-02 | ♻️ 重 substrate | 引入 artifact refs |
| A-FT6-5 | `src/myvoiceclone/api/routes_reports.py:190-284` | audit trace | FT6-P3-02 | ♻️ 重 substrate | 当前不聚合 policy/release links，需扩 trace aggregation |
| A-FT6-6 | `src/myvoiceclone/storage/artifact_store.py:15-104` | artifact write/read | FT6-P2-01 | ✅ 复用 | upload persistence |
| A-FT6-7 | `pytest.ini:1-11` | markers/default selection | FT6-P3-03 | ✅ 复用 | live HTTP marker |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 | 本 AP 的规避 |
|----|-------------|--------|--------------|
| ⛔1 | 长任务依赖 `UploadFile` 临时对象 | request 结束后不可恢复 | upload 立即写 artifact |
| ⛔2 | 只包一层 `/jobs/{id}/run` | 前端无法完成 e2e | 提供 run/upload/start/status/report/trace |
| ⛔3 | BackgroundTasks 当生产队列 | 不可恢复、缺 ledger | DB job 为准 |
| ⛔4 | 全局 envelope 仓促 breaking | 影响已有 API | 只冻结 first-test 字段 |

### 7.3 威胁模型锚

- **输入丢失**：上传文件未持久化导致 job 无法重试。
- **状态误报**：API 只返回 job completed，缺 step failure。
- **证据断链**：report/release/trace 无法追 input/output artifact。

---

## 8. 测试与复用策略

### 8.1 测试台账

| Test-ID | 验证点 | 层级 | marker | 复用 / 新增 | 映射工作项 | evidence |
|---------|--------|------|--------|-------------|------------|----------|
| FT6-T01 | create run 返回 id/status/config refs | API | api | 🆕 新增 TestClient | FT6-P1-01 | pytest PASS |
| FT6-T02 | upload audio 写 artifact；response 不暴露临时路径 | API | api | 🆕 新增 upload tests | FT6-P2-01 | pytest PASS |
| FT6-T03 | start preprocess/infer/eval 创建 DB job，payload 引用 artifact ids | API | api | ♻️ 扩展 job tests | FT6-P2-02 | pytest PASS |
| FT6-T04 | status 返回 step events、failed step、artifact summary | API | api | ♻️ 扩展 status tests | FT6-P3-01 | pytest PASS |
| FT6-T05 | report/release/trace endpoint 包含 eval + policy/release links | API | api | ♻️ 扩展 trace tests | FT6-P3-02 | pytest PASS |
| FT6-T06 | response schema snapshot；breaking change 需显式更新 fixture | contract | api | 🆕 新增 contract fixture | FT6-P1-02 | pytest PASS |
| FT6-T07 | uvicorn live smoke：upload→start→poll→report；缺 live deps skip with reason | live/http | live | 🆕 新增 gated spike | FT6-P3-03 | pass/skip reason |

### 8.2 复用策略

| 可复用对象 | 复用方式 | 改动要求 |
|------------|----------|----------|
| `src/myvoiceclone/api/routes_jobs.py` | 复用 run/status primitive | 增加 artifact/event summary |
| `src/myvoiceclone/api/routes_recordings.py` | 复用 ingest endpoint | 增加 upload artifact path |
| `src/myvoiceclone/api/routes_reports.py` | 复用 release/trace | 扩展 eval/policy links |
| `ArtifactStore` | 复用 sha/bytes/uri | upload metadata 必填 |

### 8.3 运行策略

- `pytest -m api` 跑默认 API coverage。
- `pytest -m live` 才跑 uvicorn HTTP spike。
- live HTTP evidence 交 FT7 evidence pack 收集。

### 8.4 未覆盖与后延测试

- 不覆盖并发多 worker。
- 不覆盖大文件 resumable upload。
- 不覆盖前端 UI snapshot。

---

## 9. 风险、依赖与完成状态

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| API contract 过早冻结 | 后续改动成本高 | medium | 只冻结 first-test fields |
| 上传大文件内存压力 | live 测试失败 | medium | first-test 限短音频；大文件外置 |
| job orchestration 边界不清 | status 与 runner 不一致 | high | payload contract tests |
| trace 数据不足 | FT7 evidence 不完整 | medium | FT2/FT5 trace 字段复用 |

- **外部依赖**：FastAPI/TestClient/uvicorn，live spike 可选。
- **组织协作前提**：真实前端消费者字段需求若新增，走 contract fixture 更新。
- **完成状态**：`planned`

---

## 10. DoD 与 Closure 映射

| DoD | 对应工作项 | 对应测试 | 关闭标准 |
|-----|------------|----------|----------|
| create run 可用 | FT6-P1-01 | FT6-T01 | TestClient PASS |
| upload artifact 可恢复 | FT6-P2-01 | FT6-T02 | artifact sha/bytes/id 完整 |
| start jobs 引用 artifact | FT6-P2-02 | FT6-T03 | payload contract PASS |
| status/report/trace 可消费 | FT6-P3-01/P3-02 | FT6-T04/T05 | API returns linked evidence |
| API drift 可见 | FT6-P1-02 | FT6-T06 | snapshot PASS |
| live HTTP 已验证或有 skip reason | FT6-P3-03 | FT6-T07 | pass/skip reason 入 evidence |

FT6 关闭时必须把 API contract fixture、live HTTP spike 结果和任何 skipped reason 交给 FT7 evidence pack。
