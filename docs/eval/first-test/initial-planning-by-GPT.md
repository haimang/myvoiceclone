# first-test —— 初步规划（by GPT）

> **stage**：`initial`
> **作者**：`GPT / Codex`（panel / 跨模型 handoff：`none`）
> **时间**：`2026-06-13`
> **文档性质（自宣告 role）**：`initial` = 设计流程**第 ① 步**；不是 charter，不是 action-plan，冻结零决策
> **上游权威输入**：
> - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md` — after first-build 的 first-test readiness snapshot 与 gap study
> - `docs/closure/first-build/deferred-items-ledger.md` — first-build 遗留项与 reopen 触发器
> **phase 命名 & 工作项 ID 方案**：`FT1-P0..P5` phase；`FT1-01..FT1-30` 工作项 ID，跨 initial/proposed/final 稳定
> **裁定动词 rubric（§2 用）**：`纳入 / refine / 不纳入 / 延后`
> **文档状态**：`draft`
> **下游消费者**：`first-test proposed-planning`、`first-test charter/qna`、`docs/action-plan/first-test/*`

---

## 0. TL;DR

- **核心论点**：first-test 不能只是把 first-build mock journey 再跑一遍；它必须把 first-build 遗留的入口、依赖、可观测性和 API contract 收敛到足以承载“真实音频 → 真实推理 → 真实评估”的最小闭环。本阶段的主线应从“验证骨架能跑”转为“建立一个可诊断、可复现、可由 FastAPI 驱动的真实 e2e 试验面”。
- **一句话**：先修 first-test preflight 阻塞项，再实现真实推理与真实评估闭环，最后把 CLI/API/observability/evidence 固化为可重复测试流程。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `state-analysis-after-FB-by-GPT.md` | `eval / state-analysis + gap-study` | 当前只能支持 mock e2e + 真实预处理 smoke；完整真实 e2e 的 blocker/gap 清单 | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md §0, §5, §9` |
| `state-analysis-after-FB-by-GPT.md` | `eval / testing guidance` | T0-T5 分层、first-test 前置条件、记录方式与 schema 支持度 | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md §6, §7, §8` |
| `deferred-items-ledger.md` | `closure / deferred ledger` | first-build 遗留项 DEF-01..DEF-15 与 reopen 触发条件 | `docs/closure/first-build/deferred-items-ledger.md §1, §4` |
| 用户目标 | `owner intent` | 本阶段核心目标：收敛遗留、真实音频→真实推理→真实评估、真实 FastAPI e2e、必要 observability | 当前请求 |

- **纪律继承**：本文是 eval/planning，不冻结方案；所有真实模型、API contract 和测试验收口径需要在 proposed/final 或 QnA 中关闭。
- **借用骨架**：使用 `docs/templates/eval-planning.md` 的 initial 态骨架，保留可升级到 proposed/final 的章节结构。

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

### 2.A 对原始 evals / owner 提案的整合裁定

| 来源项 | 整合裁定 | 落到哪个 phase | 备注 |
|--------|----------|----------------|------|
| `G2/G3/G9`：bootstrap 不装 extras、命令名漂移、env 示例漂移 | 纳入 | `FT1-P0` | 不先修会让真实测试在 day-1 命令层失败 |
| `G4`：完整 preprocess 缺一等 CLI/API 入口 | 纳入 | `FT1-P0` | 真实 e2e 不应依赖手工插 DB job |
| `G5`：dataset freeze 空 manifest 成功 | 纳入 | `FT1-P0` | 防止“空数据集成功”污染后续训练/推理验证 |
| `G6/G7/G10`：step-level observability、局部失败、audit trace 不完整 | 纳入 | `FT1-P1` | 本阶段目标明确包含必要接口输出和可观测性 |
| `B1/G1`：真实 SoVITS/RVC/XTTS 训练/推理未实现 | refine | `FT1-P2` | owner 目标写“真实推理”，不是必须一次完成全部训练栈；initial 建议先选择 1 条最小真实推理 substrate |
| `DEF-08/DEF-14`：真实 evaluation / subjective 集成 / objective metrics | 纳入 | `FT1-P3` | 真实评估是本阶段核心目标，不能继续只用 mock metrics |
| `DEF-12/DEF-15`：API envelope 与 CLI/API contract 对称化 | refine | `FT1-P4` | 必须提供真实 e2e FastAPI 面；统一 envelope 是否引入需 owner gate |
| `DEF-11`：pipeline_runs 与 recording 级进度 | refine | `FT1-P1/P4` | 不必一次做完整 workflow engine，但 API 需要可查询进度与 trace |
| `DEF-01/DEF-09`：vec0 真实维度迁移 | 延后/条件纳入 | `FT1-P5` | 仅在本阶段选择真实 embedding substrate 时 reopen；否则保持 deferred |
| `DEF-05`：真实 embedder adapter | 延后/条件纳入 | `FT1-P5` | 与 speaker matching/eval 质量相关，但不是“真实推理闭环”的最小必需 |
| `DEF-06`：真实 scoring | refine | `FT1-P3` | 需要至少一个真实或半真实客观指标，完整 DNSMOS 可分级实现 |
| `DEF-07`：SQLite 并发 WAL 测试 | 延后 | `FT1-P5` | 仅在引入多 worker 或并行 job runner 时 reopen |
| `DEF-10`：live/gpu/slow 真实测试 | 纳入 | `FT1-P5` | 一旦真实推理接入，应增加 gated live/slow 测试，不默认跑 |
| `DEF-13`：policies 分层下沉 | 延后/条件纳入 | `FT1-P5` | 若 first-test 要做 release gate 强治理，则进入 P4/P5；否则保留 hardening |
| 用户目标 1：进一步收敛上一阶段遗留问题 | 纳入 | `FT1-P0/P1/P5` | 按“阻断 first-test 的先修、观测必需、条件 reopen”三类处理 |
| 用户目标 2：真实音频 → 真实推理 → 真实评估完整 e2e | 纳入 | `FT1-P2/P3/P5` | 本阶段关键路径 |
| 用户目标 3：真实 e2e 的 FastAPI 接口 | 纳入 | `FT1-P4` | API 不只是 job run wrapper，需要 e2e orchestration surface |
| 用户目标 4：可观测性的必要接口输出 | 纳入 | `FT1-P1/P4` | DB event、trace endpoint、run evidence pack 三层输出 |

---

## 3. 范围与非范围（In/Out-Scope）

### 3.1 In-Scope

- **[S1] first-test preflight 收敛** — 修正环境安装、命令入口、配置键、空数据集 guard、API runner config 等会直接阻断真实测试的 gap。
- **[S2] 真实预处理可重复入口** — 从真实音频创建 recording、segments、cleaned audio、transcript、quality metadata，且可由 CLI/API 触发。
- **[S3] 最小真实推理闭环** — 选择并落地一条真实推理路径，使输入真实音频和目标文本/参考音频能产生真实 audio artifact；具体 substrate 待 gate 决策。
- **[S4] 真实评估闭环** — 至少输出可复现的客观检查指标、人工评估录入面、eval report 和 release gate 结果。
- **[S5] FastAPI e2e surface** — 提供创建测试 run、提交音频、运行 pipeline、查询状态、触发推理、提交/查询评估、获取 trace 的接口。
- **[S6] 必要 observability** — step-level job_events、duration/error/adapter metadata、artifact lineage、audit trace、test-run evidence pack。
- **[S7] gated live/slow 测试** — 增加不默认运行的真实依赖测试，覆盖真实预处理、真实推理、真实评估 API 面。

### 3.2 Out-of-Scope / 延后

- **[O1] 完整多模型训练平台** — 本阶段不承诺同时实现 RVC、SoVITS、XTTS 全部真实训练；重评条件：owner 冻结“本阶段必须训练哪类模型”。
- **[O2] 完整 embedding 平台与 vec0 维度重建** — 仅在真实推理/评估依赖真实 embedding 时 reopen；重评条件：选择 ECAPA/CLAP/SBERT 进入关键路径。
- **[O3] 多 worker 调度与 SQLite 并发硬化** — first-test 先以单 worker/同步 job runner 为基线；重评条件：引入后台队列或并行 job。
- **[O4] 全量安全治理重构** — 本阶段只做测试闭环所需 consent/policy/release trace；重评条件：进入 external-user 或 public release。
- **[O5] 生产级监控平台** — 不建设 Prometheus/Grafana 等大监控面；重评条件：长训、多机、持续运行成为目标。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线**：不能再把 mock train/mock eval 作为真实 e2e 成功证据；真实路径必须由 `MOCK_ADAPTERS=false` 或显式 live mode 运行，并记录 adapter/model/version。
- **治理冻结面**：真实音频输入必须有 source provenance 与 consent 记录；真实合成输出必须经过 eval report 与 release gate，哪怕第一版 gate 规则很窄。
- **API contract 面**：FastAPI surface 需要先满足可用 e2e；统一 response envelope 是否现在引入是 gate，不在 initial 冻结。
- **数据与 artifact 面**：所有大文件继续落在 `/mnt/usb/workspace/myvoiceresearch`；repo 只保留文档、测试、代码和小 fixture。
- **可观测性面**：优先补“能定位真实失败”的事件，不建设宽泛监控；每一步都要有 `job_id/run_id/artifact_id/duration/error` 可追。
- **migration inventory（initial 估计）**：可能需要新增 `008` 以后迁移；候选包括 step metadata、test_runs/eval_sessions、inference_runs 或 API contract 所需字段。final 前需用 HEAD schema 实测决定是否迁移。

---

## 5. DAG（关键路径 + 并行窗）

```text
FT1-P0 Preflight
  ├──▶ FT1-P1 Observability substrate ───────▶ FT1-P4 FastAPI e2e surface
  └──▶ FT1-P2 Real inference substrate ─────▶ FT1-P3 Real evaluation
                                             └▶ FT1-P5 Capstone + deferred reconciliation

并行窗：
  FT1-P1 可与 FT1-P2 并行，但 P2 必须使用 P1 定义的最小事件/metadata contract。
  FT1-P4 可在 P0 结束后启动 API skeleton，但 e2e endpoints 的成功语义依赖 P2/P3。

关键路径：FT1-P0 → FT1-P2 → FT1-P3 → FT1-P4 live route → FT1-P5 capstone。
```

---

## 6. 逐 phase 工作台账

### 6.1 `FT1-P0 · first-test preflight 收敛`

**first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `FT1-01` | 修正 README/ops/scripts 的 `mvc`/`myvoiceclone` 命令漂移，或显式增加兼容 alias | `README.md`, `docs/ops/*`, `pyproject.toml` | S | low |
| `FT1-02` | 修 `bootstrap_env.sh` 或新增 live bootstrap，安装 `.[cli,api,db,audio,preprocess,test]` | `scripts/bootstrap_env.sh`, `pyproject.toml` | S | low |
| `FT1-03` | 修 `.env.example` 与 runtime config 键漂移，明确 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR/MOCK_ADAPTERS` | `.env.example`, `src/myvoiceclone/config.py` | XS | low |
| `FT1-04` | 增加/修复 `preprocess_all` CLI 入口；修 `run diarize` payload 与 runner 期望不一致 | `src/myvoiceclone/cli.py`, `src/myvoiceclone/jobs/runner.py` | S/M | med |
| `FT1-05` | 增加 `preprocess_all` API job creation endpoint，移除手工插 DB 的测试路径 | `src/myvoiceclone/api/routes_*`, `jobs` | M | med |
| `FT1-06` | dataset freeze 空 manifest guard，并让错误可通过 CLI/API 明确暴露 | `src/myvoiceclone/pipelines/export_dataset.py`, tests | S | low |
| `FT1-07` | API job runner 使用 env-aware artifact root/config resolver | `src/myvoiceclone/api/routes_jobs.py`, `config.py` | S | low |

### 6.2 `FT1-P1 · 可观测性最小 substrate`

**first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `FT1-08` | 为 preprocess 每一步写 `job_events`，包含 step、status、duration、error、artifact refs | `src/myvoiceclone/jobs/events.py`, `jobs/runner.py`, `pipelines/*` | M | med |
| `FT1-09` | 捕获外部 adapter metadata：tool/model/version/device/cache path/stderr 摘要 | `adapters/*`, `pipelines/*`, `artifacts.metadata_json` | M | med |
| `FT1-10` | 让 segment-level failure 汇总到 job/report，避免 job completed 掩盖局部失败 | `pipelines/clean.py`, `transcribe.py`, `jobs/runner.py` | S/M | med |
| `FT1-11` | audit trace 纳入 `policy_events`、`release_gates`、eval/report/model artifacts | `src/myvoiceclone/api/routes_reports.py` | M | med |
| `FT1-12` | 定义 first-test run folder evidence pack 与自动导出命令 | `scripts/`, `docs/eval/first-test/*` | S | low |
| `FT1-13` | 评估是否接入 `pipeline_runs` 作为 recording 级进度 ledger | `db/migrations/*`, `jobs/runner.py`, `api/routes_*` | M | med |

### 6.3 `FT1-P2 · 真实推理 substrate`

**first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `FT1-14` | 冻结本阶段真实推理路线候选：真实 XTTS synthesis、外部 TTS/VC bridge、或最小 SoVITS inference | `adapters/training/*`, `pipelines/infer.py`, QnA | M | high |
| `FT1-15` | 实现所选真实推理 adapter 的模型加载、输入校验、输出 artifact、metadata/env_digest | `src/myvoiceclone/adapters/*`, `pipelines/infer.py` | L | high |
| `FT1-16` | 将真实预处理 dataset/reference audio 连接到真实推理输入，禁止 silent fallback 到 mock | `pipelines/export_dataset.py`, `infer.py`, config | M | high |
| `FT1-17` | 增加真实推理 CLI 命令与 smoke test，使用 gated `live/slow` marker | `src/myvoiceclone/cli.py`, `tests/*` | M | med |
| `FT1-18` | 明确模型权重下载/缓存策略，替换 placeholder download script | `scripts/download_models.sh`, `MODELS_DIR`, docs | M | med |

### 6.4 `FT1-P3 · 真实评估闭环`

**first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `FT1-19` | 定义 first-test 最小客观指标：duration/loudness/silence/clipping/transcript sanity/ASR-WER 候选 | `src/myvoiceclone/eval/*`, `pipelines/score.py` | M | med |
| `FT1-20` | 实现真实推理输出的 objective eval runner 与 `eval_metrics` 写入 | `eval/objective.py`, `eval/report.py`, DB | M | med |
| `FT1-21` | 实现 subjective eval 录入接口：MOS/ABX/备注/评审人/样本 artifact | `eval/subjective.py`, API routes | M | med |
| `FT1-22` | 将 eval report 接入 release gate，区分 smoke pass、quality pass、manual waived | `domain/policies.py`, `api/routes_reports.py` | M | med |
| `FT1-23` | 补真实评分与 mock 指标的显式标记，禁止 report 混淆 | `eval/*`, report schema/metadata | S | low |

### 6.5 `FT1-P4 · FastAPI 真实 e2e surface`

**first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `FT1-24` | 设计并实现 e2e run API：create run、upload/register audio、start preprocess、start infer、start eval | `src/myvoiceclone/api/routes_*`, service layer | L | high |
| `FT1-25` | 提供 job/run status API，返回 step events、artifact summary、failure summary | `api/routes_jobs.py`, `routes_reports.py` | M | med |
| `FT1-26` | 提供 artifacts/eval/report/release-gate 查询 API，满足前端真实 e2e 消费 | `api/routes_*`, `artifact_store.py` | M | med |
| `FT1-27` | 决定是否引入统一 response envelope；若不引入，至少冻结 first-test API 响应契约 | API routes, tests | M | high |
| `FT1-28` | 增加 live HTTP/API e2e 测试，覆盖真实或可跳过的 live dependency path | `tests/api/*`, `pytest.ini` | M | med |

### 6.6 `FT1-P5 · capstone、deferred reconciliation 与收口`

**first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `FT1-29` | 定义 first-test capstone：真实音频输入、真实推理输出、真实评估报告、API trace、evidence pack | `tests/integration/*`, `docs/eval/first-test/*` | M | high |
| `FT1-30` | 更新 deferred ledger：关闭已收敛项，保留真实 embedder/vec0/多 worker 等仍必要 deferred | `docs/closure/first-build/deferred-items-ledger.md`, new first-test closure docs | S | low |

---

## 7. Owner decision gates

### 7.A 开放 gates

| 编号 | 决策点 | 影响 | 当前建议 / 倾向 | 状态 |
|------|--------|------|------------------|------|
| `G-FT1-1` | 本阶段“真实推理”选择哪条 substrate：XTTS synthesis、SoVITS inference、RVC/VC、或外部 bridge | 决定 P2 的实现复杂度、依赖、测试形态 | 倾向选择最小可落地、可本地缓存权重、能产出真实 wav 的一条路径 | `OPEN` |
| `G-FT1-2` | 是否要求本阶段真实训练，还是允许使用预训练/外部模型完成真实推理闭环 | 决定是否 reopen 大量 training-phase deferred | 倾向不把真实训练作为 first-test 的硬入口；先完成真实推理+评估 | `OPEN` |
| `G-FT1-3` | FastAPI 是否引入统一 response envelope | 会改变 API 响应形状与测试断言 | 倾向先冻结 first-test surface，envelope 作为 proposed gate | `OPEN` |
| `G-FT1-4` | 真实评估的最低通过线是什么：smoke-only、objective thresholds、还是人工 MOS gate | 决定 release gate 与 capstone 成败语义 | 倾向分层：smoke pass 与 quality pass 分离 | `OPEN` |
| `G-FT1-5` | first-test 是否开启 consent/policy 强约束 | 影响录音输入、release gate 和 audit trace | 倾向至少记录 consent/provenance，不阻断本地 smoke | `OPEN` |
| `G-FT1-6` | 是否引入 schema migration 支持 test_runs/inference_runs/eval_sessions | 影响 DB schema 和 API surface | 倾向先做 minimal schema review，再决定是否新增 migration | `OPEN` |

- **结论**：initial 阶段仍有 6 个 OPEN 决策项；不能直接进入 action-plan，需先进入 proposed-planning 或 QnA 关闭 P2/P3/P4 的口径。

---

## 8. 测试计划

- **A 短途（in-worker route/unit）**：
  - preflight：config/env、CLI 参数、dataset empty guard、artifact root resolver。
  - observability：job_events step 写入、failure summary、audit trace 包含 release/policy。
  - eval：objective metrics 写入、subjective input validation、mock/real 标记。
- **B spike（live HTTP/WS，入 cap + denominator）**：
  - FastAPI 启动后，使用真实短音频创建 e2e run，触发 preprocess、infer、eval、report、trace。
  - live 依赖缺失时必须 `skip with reason`，不能假绿。
- **D mega（owner-triggered 长程）**：
  - 使用 1-3 条真实音频和选定真实推理模型，跑完整 API e2e。
  - 输出 run folder：env、commands、stdout/stderr、DB summary、artifact manifest、eval report、trace JSON。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 真实推理 substrate 选型过大 | 同时要求训练 RVC/SoVITS/XTTS 或 GPU 长训 | 本阶段无法形成闭环 | initial 阶段只开放 gate，proposed 必须收敛为 1 条主路 |
| 模型权重/许可证不可用 | XTTS/PyAnnote/Whisper/Demucs 下载失败或授权受限 | live test 无法跑 | 权重缓存 preflight + skip reason + provenance 记录 |
| API contract 过早统一 envelope | 大面积测试和客户端响应形状变化 | 牵连过大，拖慢真实 e2e | 先冻结 first-test API surface，再决定 envelope |
| 可观测性过度建设 | 引入复杂监控平台 | 偏离 first-test 关键路径 | 只做 step events、trace、evidence pack、stderr 摘要 |
| mock 与 real 混淆 | report 未标明 adapter mode | 误判真实 e2e 成功 | 所有 metrics/artifacts 必须记录 mode/model/version |
| 空数据集或局部失败被成功状态掩盖 | freeze 或 job completed 语义过宽 | capstone 假绿 | P0/P1 必须先修 guard 和 failure summary |
| SQLite schema 变更过多 | 新增 test_runs/inference_runs 过早 | migration 风险扩大 | final 前做 migration inventory，能用 metadata_json 的先用 metadata_json |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：真实 first-test charter、真实推理技术选型、FastAPI e2e contract、observability minimum contract、first-test capstone。

### 10.A 预期 action-plan 派生与排序（initial 估计）

| phase 簇 | 派生的 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|--------------------------|--------------|-------------|
| `FT1-P0` | `docs/action-plan/first-test/FT1-P0-preflight.md` | `FT1-01..07` | 最先执行 |
| `FT1-P1` | `docs/action-plan/first-test/FT1-P1-observability.md` | `FT1-08..13` | P0 后启动，可与 P2 并行 |
| `FT1-P2` | `docs/action-plan/first-test/FT1-P2-real-inference.md` | `FT1-14..18` | 依赖 `G-FT1-1/2` |
| `FT1-P3` | `docs/action-plan/first-test/FT1-P3-real-evaluation.md` | `FT1-19..23` | 依赖 P2 输出 artifact contract |
| `FT1-P4` | `docs/action-plan/first-test/FT1-P4-fastapi-e2e.md` | `FT1-24..28` | skeleton 可早开，成功语义依赖 P2/P3 |
| `FT1-P5` | `docs/action-plan/first-test/FT1-P5-capstone-closure.md` | `FT1-29..30` | 最后收口 |

---

## 11. Final recommendation

- **推荐序列**：`FT1-P0 preflight` → `QnA 关闭真实推理 substrate` → `FT1-P1 observability substrate` + `FT1-P2 real inference` → `FT1-P3 real evaluation` → `FT1-P4 FastAPI e2e` → `FT1-P5 capstone/closure`。
- **一句话总结**：first-test 的成功标准不是“跑完更多脚本”，而是让真实输入、真实推理产物、真实评估结果和 API/trace 证据形成同一条可复现链路。

---

## 12. 交叉引用与修订历史

- **交叉引用**：
  - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md`
  - `docs/closure/first-build/deferred-items-ledger.md`
  - `docs/templates/eval-planning.md`

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-13 | GPT / Codex | 初稿（stage=`initial`） |
