# first-test —— proposed-planning（by GPT）

> **stage**：`proposed`
> **作者**：`GPT / Codex`（panel / 跨模型 handoff：`none`）
> **时间**：`2026-06-13`
> **文档性质（自宣告 role）**：`proposed` = **取代 initial-planning**，作 pre-charter-qna 前**唯一精炼工作基线**
> **上游权威输入**：
> - `docs/eval/first-test/initial-planning-by-GPT.md` — 初步阶段划分与 `FT1-01..FT1-30` first-cut 工作项
> - `docs/eval/first-test/reference-anchor.md` — 8 个业务簇、web/reference anchors、TR 过滤、反例坑表
> - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md` — after first-build readiness snapshot 与 gap study
> - `docs/closure/first-build/deferred-items-ledger.md` — first-build deferred ledger
> **phase 命名 & 工作项 ID 方案**：`FT1..FT8` 为阶段；工作项使用 `FTx.y`；测试项使用 `T-FTx.y`
> **裁定动词 rubric（§2 用）**：`KEEP / REFRAME / CLOSED / NEW`
> **文档状态**：`draft`
> **下游消费者**：`first-test final-execution-plan`、`first-test pre-charter-qna`、`docs/action-plan/first-test/FT*.md`

---

## 0. TL;DR

- **核心论点**：reference-anchor 将 first-test 从 6 个粗 phase 精炼为 8 个业务簇。proposed 态据此废弃旧的 phase 命名，改为 `FT1..FT8`，并把“真实 e2e”拆成可验证链路：准入收敛 → schema/observability → 真实预处理 → 真实推理 → 真实评估 → FastAPI e2e → live capstone → closure/deferred。
- **一句话**：本态把 initial 的工作重新分配为 8 个 FT 阶段，每个阶段绑定 reference-anchor、反例和测试面，尤其把数据库 drift 与可观测性提前为 `FT2` 的硬前置。
- **本态相对上一态做了什么**：旧 6-phase 命名作废；所有工作重排到 `FT1..FT8`，并新增 schema drift、observability contract、adapter metadata、API evidence、live skip denominator 等测试要求。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `initial-planning-by-GPT.md` | `上一态 plan` | 原始 30 项工作、开放 gate、测试草案 | `docs/eval/first-test/initial-planning-by-GPT.md:44-61`, `docs/eval/first-test/initial-planning-by-GPT.md:121-187` |
| `reference-anchor.md` | `eval / reference-anchor` | 8 个业务簇、外部来源、TR 过滤、反例坑表 | `docs/eval/first-test/reference-anchor.md:37-48`, `docs/eval/first-test/reference-anchor.md:183-215` |
| `state-analysis-after-FB-by-GPT.md` | `eval / state-analysis` | current blocker、schema/observability 不足、真实测试层级 | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:119-154`, `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:180-206` |
| `deferred-items-ledger.md` | `closure / deferred` | deferred reopen 条件与边界 | `docs/closure/first-build/deferred-items-ledger.md:22-29` |

- **纪律继承**：本文仍是 eval/planning，冻结零决策；但它取代 initial，成为后续 final/action-plan 的唯一规划基线。
- **reference-anchor 继承**：本文采用 `reference-anchor.md` §5 的 TR-1..TR-7：本地单机 SQLite/DB job、证据落 DB/artifact/evidence pack、禁止 mock silent fallback、FastAPI 不强行引入生产任务队列、模型/token/license/provenance 前置、live tests gated、大文件不入 repo。

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

### 2.B Δ 审核 vs initial-planning

| item-ID | 裁定（KEEP/REFRAME/CLOSED/NEW） | 重分配 phase | 复用判定（✅ 复用 / ♻️ 重 substrate / 🆕 净新） | 理由 / 新证据 |
|---------|--------------------------------|--------------|------------------------------------------|----------------|
| `FT1-01` | KEEP | `FT1` | ✅ | preflight first 来自 reference 轴 A；命令漂移仍是 day-1 失败点 |
| `FT1-02` | KEEP | `FT1` | ✅ | extras/live bootstrap 属准入项；与真实模型接入分离 |
| `FT1-03` | KEEP | `FT1` | ✅ | env 键是准入合同；后续 tests 用 monkeypatch 隔离 |
| `FT1-04` | REFRAME | `FT1` + `FT6` | ♻️ | CLI preprocess 修复归 FT1；API orchestration 归 FT6 |
| `FT1-05` | REFRAME | `FT6` | ♻️ | reference 轴 E 要求 FastAPI e2e surface，不只是 job creation |
| `FT1-06` | KEEP | `FT1` + `FT2` | ✅ | empty manifest guard 属准入；schema drift/DB 验证归 FT2 |
| `FT1-07` | KEEP | `FT1` | ✅ | API runner config resolver 是准入项 |
| `FT1-08` | REFRAME | `FT2` | ♻️ | observability 从辅助项提升为真实 e2e 前置 substrate |
| `FT1-09` | KEEP | `FT2` | ✅ | reference 轴 F 要求 adapter/tool/model/device/cache/stderr metadata |
| `FT1-10` | KEEP | `FT2` | ✅ | 防止 job completed 掩盖 segment failure |
| `FT1-11` | KEEP | `FT2` + `FT6` | ✅ | trace 汇总由 FT2 定义 contract，FT6 暴露 API |
| `FT1-12` | REFRAME | `FT7` | ♻️ | evidence pack 应由 capstone 阶段固化，不在观测底座中孤立完成 |
| `FT1-13` | REFRAME | `FT2` | ♻️ | pipeline_runs 不默认升级为硬依赖；先做 schema drift 与 event contract |
| `FT1-14` | REFRAME | `FT4` | ♻️ | 忽略 owner-gate 后，proposed 直接给工作形态：优先预训练真实推理 substrate，仍不冻结具体模型 |
| `FT1-15` | KEEP | `FT4` | ✅ | adapter 实现仍是核心 |
| `FT1-16` | KEEP | `FT3` + `FT4` | ✅ | dataset/reference artifact contract 横跨预处理与推理 |
| `FT1-17` | KEEP | `FT4` + `FT7` | ✅ | 推理 smoke 单测归 FT4；live/capstone 归 FT7 |
| `FT1-18` | KEEP | `FT4` | ✅ | 模型下载/缓存/license/provenance 是 TR-5 |
| `FT1-19` | REFRAME | `FT5` | ♻️ | reference 轴 D 将指标拆成 smoke、proxy、manual 三层 |
| `FT1-20` | KEEP | `FT5` | ✅ | objective eval runner 与 `eval_metrics` 写入保留 |
| `FT1-21` | KEEP | `FT5` | ✅ | subjective MOS/ABX 录入保留，但降级为本地小样本表单 |
| `FT1-22` | KEEP | `FT5` + `FT6` | ✅ | release gate 规则归 FT5，查询/trace API 归 FT6 |
| `FT1-23` | KEEP | `FT2` + `FT5` | ✅ | mock/real 标记既是 metadata contract，也是 report contract |
| `FT1-24` | REFRAME | `FT6` | ♻️ | 采用 FastAPI upload→artifact→DB job→status/trace 的 surface；不借 BackgroundTasks 做长任务承载 |
| `FT1-25` | KEEP | `FT6` | ✅ | status API 绑定 FT2 step events |
| `FT1-26` | KEEP | `FT6` | ✅ | artifact/eval/report/release 查询保留 |
| `FT1-27` | REFRAME | `FT6` | ♻️ | 不在 proposed 冻结 envelope；先冻结 first-test API response contract |
| `FT1-28` | REFRAME | `FT7` | ♻️ | live HTTP/API e2e 统一归 capstone/live harness |
| `FT1-29` | KEEP | `FT7` | ✅ | capstone 证据形态保留 |
| `FT1-30` | KEEP | `FT8` | ✅ | closure/deferred reconciliation 单独成阶段 |
| `NEW-DB-01` | NEW | `FT2` | 🆕 | reference 轴 F/H + state-analysis 指出 schema 支持主体对象但日志语义不足；新增 DB drift test inventory |
| `NEW-DB-02` | NEW | `FT2` | 🆕 | SQLite WAL 可借但非多 worker 保证；新增 migration/order/default/check 测试面 |
| `NEW-OBS-01` | NEW | `FT2` | 🆕 | OTel 只借 vocabulary；新增 `job_events`/trace JSON contract test |
| `NEW-API-01` | NEW | `FT6` | 🆕 | FastAPI UploadFile 必须立即落 artifact，避免长任务依赖 request temp object |
| `NEW-LIVE-01` | NEW | `FT7` | 🆕 | live/gpu/slow 必须 skip with reason 并计入 denominator |

- **本态核心转向（一句话）**：从“6 个粗 phase 的 first-cut”转为“8 个业务 FT 阶段 + reference-bound + test-bound 的 proposed 工作基线”。

---

## 3. 范围与非范围（In/Out-Scope）

### 3.1 In-Scope

- **[S1] FT1 准入收敛** — 修命令、extras、env、preprocess CLI/API 创建口、empty dataset guard、artifact root resolver。
- **[S2] FT2 schema 与 observability contract** — 明确 schema drift 防线、step events、adapter metadata、failure summary、trace JSON 与 mock/real 标记。
- **[S3] FT3 真实音频预处理** — 真实 FFmpeg/PyAnnote/Demucs/Whisper 路径的 preflight、metadata、artifact、dataset manifest 合同。
- **[S4] FT4 真实推理 substrate** — 选择一条可本地运行的预训练真实推理路径，产出真实 wav artifact，并记录模型/license/provenance。
- **[S5] FT5 真实评估与 release gate** — smoke metrics、objective proxy、manual MOS/ABX、report、release gate 分层。
- **[S6] FT6 FastAPI e2e surface** — upload/register audio、create run、start steps、status、artifact/eval/report/release/trace 查询。
- **[S7] FT7 live tests 与 capstone** — gated live/slow、API e2e、evidence pack、skip denominator、真实 run folder。
- **[S8] FT8 closure/deferred reconciliation** — 关闭已修项，保留真实 embedder/vec0/多 worker 等必要 deferred。

### 3.2 Out-of-Scope / 延后

- **[O1] 同时实现 RVC/SoVITS/XTTS 全部真实训练** — first-test 先追求一条真实推理闭环；重评条件：final QnA 明确训练为硬目标。
- **[O2] 完整 ECAPA/CLAP/SBERT embedding 平台与 vec0 全维度迁移** — 除非 FT4/FT5 选择依赖真实 embedding；重评条件：embedding 进入关键路径。
- **[O3] 生产级任务队列与分布式 worker** — FastAPI 第一版只触发 DB job 与可查询状态；重评条件：长训或并发执行成为目标。
- **[O4] 完整 OTel 平台化接入** — 本阶段只借 OTel vocabulary 映射 DB events/trace JSON；重评条件：多服务或持续监控需要。
- **[O5] 众包平台 MOS 流程** — P.808/P.835 只借字段和流程思路；重评条件：需要外部评审面板或发布级质量评估。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线**：禁止 silent fallback 到 mock；FastAPI 上传必须先落 artifact；长任务以 DB job/status/trace 为真，不以 BackgroundTasks 内存对象为真；所有真实模型都必须记录 model/version/device/cache/license。
- **治理冻结面**：真实音频 source provenance、consent、license、release gate、manual waive 必须进入 trace/report；XTTS-v2 等模型能力不能自动等于可发布许可。
- **migration inventory（proposed）**：
  - `MIG-FT2-A`：优先不新增表，先用现有 `job_events.metadata_json`、`artifacts.metadata_json`、`eval_metrics`、`release_gates` 承载 first-test。
  - `MIG-FT2-B`：若现有 `job_events` 缺 metadata/error/duration 字段且 metadata_json 不足，final 前评估新增 migration。
  - `MIG-FT6-A`：若 API run 需要稳定 `test_runs` 或 `inference_runs` 主体，final 前提出 migration；proposed 不默认新增。
  - `MIG-FT8-A`：vec0 维度迁移仅在真实 embedding 进入关键路径时 reopen。
- **测试红线**：schema drift 与 observability tests 是 e2e 前置，不等到 capstone；live 依赖缺失必须 skip with reason，不能被当作 pass。

---

## 5. DAG（关键路径 + 并行窗）

```text
FT1 准入收敛
  ├──▶ FT2 Schema/Observability contract ──▶ FT6 FastAPI e2e surface ──▶ FT7 Live capstone
  └──▶ FT3 Real audio preprocess ─────────▶ FT4 Real inference ───────▶ FT5 Real evaluation ┘

FT8 Closure/deferred reconciliation 在 FT7 evidence pack 之后收口。

并行窗：
  FT2 与 FT3 可并行，但 FT3 产物必须满足 FT2 metadata/event contract。
  FT4 adapter spike 可在 FT3 之前用 fixture/reference audio 启动，但正式通过依赖 FT3 artifact contract。
  FT6 skeleton 可在 FT1 后启动，但 status/trace/report 的成功语义依赖 FT2/FT4/FT5。

关键路径：FT1 → FT2 → FT3 → FT4 → FT5 → FT6 → FT7 → FT8。
```

---

## 6. 逐 phase 工作台账

### 6.1 `FT1 · 准入收敛与测试入口统一`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT1.1` | 统一命令与文档入口：`myvoiceclone` 为主，必要时加 alias；修 README/ops/scripts | 轴 A；HEAD `state-analysis:181-183`；TR-2 | ✅ | S |
| `FT1.2` | live bootstrap 安装 extras，并输出依赖版本探针 | 轴 A/B/G；`state-analysis:212-240`；pytest skip 规则 | ✅ | S |
| `FT1.3` | `.env.example` 与 config 对齐，固定 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR/MOCK_ADAPTERS` | 轴 A/G；pytest monkeypatch env isolation；TR-7 | ✅ | XS |
| `FT1.4` | 修 CLI `preprocess_all`/`run diarize` 输入合同，payload 必须包含 artifact/path | 轴 A/B；HEAD `state-analysis:183-184`；TR-2 | ♻️ | M |
| `FT1.5` | 增加 API 创建 preprocess job 的最小入口，但正式 e2e orchestration 留给 FT6 | 轴 E；FastAPI BackgroundTasks 降级；TR-1/TR-4 | ♻️ | M |
| `FT1.6` | dataset freeze 空 manifest guard；错误必须可被 CLI/API 测试断言 | 轴 A；HEAD `state-analysis:185`；TR-3 | ✅ | S |
| `FT1.7` | API job runner 使用 env-aware artifact root/config resolver | 轴 A/F；TR-2/TR-7 | ✅ | S |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT1.1` | unit/cli | `myvoiceclone --help`、关键子命令可解析；文档命令 smoke 可执行 | 命令漂移 |
| `T-FT1.2` | unit/script | bootstrap dry-run 或 shellcheck-style probe 确认安装 extras 字符串与依赖探针存在 | live env 准入 |
| `T-FT1.3` | unit/config | monkeypatch env 后 `load_local_config()` 解析 DB/artifact/models/mock 开关 | env drift |
| `T-FT1.4` | unit/jobs | CLI 创建 `preprocess_all` job payload 包含 `filepath` 或 artifact reference | payload drift |
| `T-FT1.5` | api/TestClient | `POST /api/...preprocess...` 返回 pending job，payload 可被 runner 消费 | API preprocess 创建 |
| `T-FT1.6` | unit/pipeline | 空 eligible segments 时 `dataset freeze` 抛明确错误，不写 frozen success | fake-zero 防线 |
| `T-FT1.7` | api/unit | API run job 使用 env artifact root，artifact 不落默认 repo path | artifact root drift |

### 6.2 `FT2 · Schema drift 与 observability contract`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT2.1` | 建立 schema drift inventory：核心表、列、CHECK、FK、migration order、vec0 mock 边界 | 轴 F/H；HEAD `state-analysis:119-138`; SQLite WAL 只作本地边界 | 🆕 | M |
| `FT2.2` | 定义 step-level `job_events` contract：step/status/duration/error/artifact refs/mode | 轴 F；OTel events vocabulary 降级；TR-2/TR-3 | ♻️ | M |
| `FT2.3` | adapter metadata contract：tool/model/version/device/cache/stderr summary/license | 轴 F/B/C；Whisper/PyAnnote/XTTS references；TR-5 | ✅ | M |
| `FT2.4` | segment-level failure summary 上卷到 job/report/trace | 轴 F；HEAD `state-analysis:186-188` | ✅ | M |
| `FT2.5` | audit trace contract 纳入 policy/release/eval/artifacts/model/inference links | 轴 F/H；净新 trace 视图；TR-2 | 🆕 | M |
| `FT2.6` | mock/real evidence separation：metrics/artifacts/reports 必须标 `adapter_mode`/`metric_source` | 轴 D/F；反例“mock 与 real 混淆”；TR-3 | ✅ | S |
| `FT2.7` | pipeline_runs 只做兼容评估；不默认成为硬依赖 | 轴 H；deferred boundary | ♻️ | S |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT2.1` | db/unit | 全量 migration 在空 DB 顺序执行；断言核心表/列/FK/索引存在 | migration drift |
| `T-FT2.2` | db/unit | `PRAGMA foreign_keys/WAL/busy_timeout` 被设置；WAL 只声明单机边界 | SQLite drift |
| `T-FT2.3` | db/unit | `job_events` 可记录 step metadata、duration、error、artifact ids；缺字段时用 metadata_json | observability schema |
| `T-FT2.4` | unit/jobs | preprocess step 失败时 job_events 有 failed step，job/report 有 failure summary | 局部失败不吞 |
| `T-FT2.5` | api/TestClient | audit trace 包含 job、events、artifacts、eval、release/policy 分支 | trace completeness |
| `T-FT2.6` | unit/eval | mock metric 不能被标为 real quality pass；report 明确 `metric_source` | mock/real 隔离 |
| `T-FT2.7` | db/unit | schema snapshot 与 expected inventory 比对，新增/删除关键列会失败 | DB drift guard |

### 6.3 `FT3 · 真实音频预处理与 dataset contract`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT3.1` | FFmpeg probe/normalize contract：输入格式、sample rate、duration、loudnorm/silence smoke metrics | 轴 B；FFmpeg docs；TR-2 | ✅ | M |
| `FT3.2` | PyAnnote token/terms/cache preflight，失败时明确 skip/failed reason | 轴 B；pyannote HF model card；TR-5/TR-6 | ✅ | S |
| `FT3.3` | Demucs vocal extraction optional path，标记为 separation smoke，不等同 speech enhancement | 轴 B；Demucs reference + anti-overclaim | 🔶 | M |
| `FT3.4` | Whisper ASR contract：model name/device/duration/transcript artifact/segments | 轴 B；Whisper repo；TR-2/TR-5 | ✅ | M |
| `FT3.5` | dataset create/freeze 使用真实预处理产物，manifest 必须非空且含 artifact lineage | 轴 A/B/F；empty guard | ✅ | M |
| `FT3.6` | 预处理产物到推理 reference audio 的 artifact contract | 轴 C + 净新表；TR-2/TR-3 | 🆕 | M |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT3.1` | unit/adapter | mock subprocess 或 tiny fixture 验证 FFmpeg command、metadata parse、artifact write | normalize/probe |
| `T-FT3.2` | live/skip | 无 `HUGGINGFACE_TOKEN` 时 skip with reason；有 token 时跑短音频 diarization smoke | pyannote preflight |
| `T-FT3.3` | unit/adapter | Demucs path 不存在时错误可观测；mock output 写 artifact metadata | separation diagnosability |
| `T-FT3.4` | unit/live | Whisper model metadata 写入；transcript artifact/segment status 可查 | ASR contract |
| `T-FT3.5` | integration | 真实/fixture preprocess 后 freeze 生成非空 manifest，sha/bytes/artifact lineage 完整 | dataset contract |
| `T-FT3.6` | unit/pipeline | 推理 reference selector 只接受可追溯 cleaned/reference artifact | no silent input |

### 6.4 `FT4 · 真实推理 substrate 与 artifact contract`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT4.1` | 定义一条主推理 substrate contract：`text/source/reference/model -> wav artifact` | 轴 C；Coqui/RVC references；TR-3/TR-5 | ♻️ | M |
| `FT4.2` | 实现预训练真实推理 adapter wrapper，优先支持 speaker_wav/reference_wav 输出 wav | 轴 C；Coqui `tts_to_file`/VC docs；不直接暴露外部 CLI | ✅ | L |
| `FT4.3` | 模型下载/缓存/license/provenance manifest，替换 placeholder | 轴 C/H；XTTS license 反例；TR-5/TR-7 | ✅ | M |
| `FT4.4` | 禁止 mock fallback：真实 mode 缺依赖必须 failed/skip，不产假 artifact | 轴 F/G；TR-3/TR-6 | ✅ | S |
| `FT4.5` | 推理输出 artifact metadata：model, version, device, seed/config, duration, input refs, license | 轴 F/C；OTel attributes 降级为 metadata | ✅ | M |
| `FT4.6` | 推理 CLI smoke 和 adapter unit tests | 轴 G；pytest skip/monkeypatch | ✅ | M |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT4.1` | unit/contract | adapter input schema 校验：缺 text/source/reference/model 时报明确错误 | inference contract |
| `T-FT4.2` | unit/adapter | fake real-wrapper 生成 wav artifact，metadata 含 input refs 与 model id | artifact write |
| `T-FT4.3` | unit/script | model manifest/cache path/license 字段存在；不下载时给 skip reason | model preflight |
| `T-FT4.4` | unit/config | `MOCK_ADAPTERS=false` 且缺依赖时不允许回退 mock | no silent fallback |
| `T-FT4.5` | live/slow | 有模型缓存时跑短文本+短 reference，输出 wav 并写 artifact | real inference smoke |
| `T-FT4.6` | cli | `myvoiceclone infer ... --mode real` smoke；缺依赖 exit code 与错误可断言 | CLI real path |

### 6.5 `FT5 · 真实评估与 release gate`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT5.1` | 建立三层指标：smoke metrics、objective proxy、manual MOS/ABX | 轴 D；DNS/P.808/SQUIM references；反例不把 proxy 当主观质量 | ♻️ | M |
| `FT5.2` | 实现 loudness/silence/clipping/duration/transcript sanity smoke evaluator | 轴 B/D；FFmpeg filters；TR-2 | 🆕 | M |
| `FT5.3` | 接入可选 objective proxy runner，报告标 `objective_proxy` | 轴 D；TorchAudio-SQUIM/DNSMOS 参考 | ♻️ | M |
| `FT5.4` | subjective eval API/service：MOS/ABX/comment/reviewer/sample artifact | 轴 D；P.808 Toolkit 降级为本地表单 | ✅ | M |
| `FT5.5` | release gate 分层：smoke pass、quality pass、manual waived | 轴 D/H；policy/release trace | ✅ | M |
| `FT5.6` | eval report 关联 inference artifact、input artifact、metric source 与 adapter mode | 轴 F/D；TR-2/TR-3 | ✅ | M |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT5.1` | unit/eval | smoke metrics 对短 wav fixture 输出 deterministic fields | smoke evaluator |
| `T-FT5.2` | unit/eval | proxy metric 缺依赖时 skip/mark unavailable，不写 real score | proxy gating |
| `T-FT5.3` | unit/service | MOS/ABX payload validation：范围、reviewer、sample artifact id | subjective contract |
| `T-FT5.4` | db/unit | `eval_metrics`/report 记录 metric_source、adapter_mode、artifact refs | eval DB integrity |
| `T-FT5.5` | unit/domain | release gate 区分 smoke pass、quality pass、manual waived | gate semantics |
| `T-FT5.6` | api/TestClient | 查询 eval report 返回指标、人工分、release gate 与 trace links | eval API surface |

### 6.6 `FT6 · FastAPI e2e surface 与前端可消费合同`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT6.1` | 设计 first-test API run surface：create run、upload/register audio、start preprocess/infer/eval | 轴 E；FastAPI UploadFile；TR-2/TR-4 | ♻️ | L |
| `FT6.2` | upload 后立即写 artifact，不让长任务依赖 request `UploadFile` | 轴 E；BackgroundTasks 反例；TR-2/TR-7 | 🆕 | M |
| `FT6.3` | start endpoints 只创建/触发 DB job，返回 job/run id 与可查询状态 | 轴 E/F；BackgroundTasks 降级 | ♻️ | M |
| `FT6.4` | status API 返回 step events、artifact summary、failure summary、mode/source | 轴 E/F；FT2 contract | ✅ | M |
| `FT6.5` | artifacts/eval/report/release/trace 查询 API | 轴 E/D/F | ✅ | M |
| `FT6.6` | first-test API response contract：不冻结全局 envelope，但冻结本阶段字段 | 轴 H；API envelope deferred boundary | ♻️ | M |
| `FT6.7` | TestClient coverage + live HTTP spike 分层 | 轴 E/G；FastAPI TestClient + pytest skip | ✅ | M |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT6.1` | api/TestClient | create run 返回 id/status/config refs | run API |
| `T-FT6.2` | api/TestClient | upload audio 写 artifact；response 不暴露临时文件路径 | upload artifact |
| `T-FT6.3` | api/TestClient | start preprocess/infer/eval 创建 DB job，payload 引用 artifact ids | job orchestration |
| `T-FT6.4` | api/TestClient | status 返回 step events、failed step、artifact summary | observability API |
| `T-FT6.5` | api/TestClient | report/release/trace endpoint 包含 eval + policy/release links | trace API |
| `T-FT6.6` | contract | response schema snapshot；breaking change 需显式更新 contract fixture | API drift |
| `T-FT6.7` | live/http | uvicorn live smoke：upload→start→poll→report；缺 live deps skip with reason | API live e2e |

### 6.7 `FT7 · Live tests、capstone 与 evidence pack`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT7.1` | 定义 live/slow/gpu marker policy 与 skip denominator | 轴 G；pytest skip/xfail；TR-6 | ♻️ | S |
| `FT7.2` | first-test run folder exporter：env、commands、stdout/stderr、DB summary、artifact manifest、trace JSON | 轴 F/G；state-analysis evidence pack | ♻️ | M |
| `FT7.3` | API capstone：真实音频 → preprocess → real inference → eval → release → trace | 轴 G；capstone evidence shape | ✅ | L |
| `FT7.4` | e2e 前单元测试 gate：FT1-FT6 必须绿，live skipped reason 计数必须可见 | 轴 G；TR-6 | 🆕 | M |
| `FT7.5` | evidence review checklist：无 mock silent fallback、无空 manifest、trace 完整、artifact 外置 | 轴 F/H；反例坑表 | 🆕 | S |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT7.1` | pytest config | `pytest --markers` 包含 live/slow/gpu；默认不跑 live | marker taxonomy |
| `T-FT7.2` | unit/script | evidence exporter 生成 env/commands/db/artifacts/trace 文件 | evidence pack |
| `T-FT7.3` | integration/live | API capstone 真实短音频链路；缺依赖 skip with reason | full first-test |
| `T-FT7.4` | integration | capstone 前检查 FT1-FT6 required tests status | e2e gate |
| `T-FT7.5` | validation | evidence pack validator 拒绝 mock-as-real、empty manifest、repo 大文件 | evidence quality |

### 6.8 `FT8 · Closure 与 deferred reconciliation`

**重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|-----------------------------------------------|------|------|
| `FT8.1` | 更新 first-build deferred ledger：关闭已解决入口/observability/eval/API 项，保留未触发项 | 轴 H；DEF ledger | ✅ | S |
| `FT8.2` | 新建 first-test closure ledger：真实 e2e evidence、未完成项、reopen triggers | 轴 H；净新 closure 规则 | 🆕 | S |
| `FT8.3` | vec0/embedder、多 worker、完整 OTel、众包 MOS 等继续 deferred 的边界说明 | 轴 H；TR-1/TR-4/TR-5 | ✅ | S |
| `FT8.4` | proposed→final 输入包整理：reference anchors、test matrix、schema inventory、API contract | 全轴 | 🆕 | S |

**测试注入**

| 测试编号 | 测试类型 | 目标用例 | 覆盖点 |
|----------|----------|----------|--------|
| `T-FT8.1` | docs/check | closure/deferred 文档存在、含 reopened/closed/deferred 分类 | closure integrity |
| `T-FT8.2` | docs/check | 每个 retained deferred 有触发器和目标阶段 | deferred quality |
| `T-FT8.3` | docs/check | final 输入包引用 reference-anchor、schema inventory、test matrix | handoff completeness |

---

## 7. Owner decision gates

### 7.A 开放 gates

> 用户本轮要求“先忽略 owner-gate”。因此 proposed 态不让 gate 阻塞重排，但保留为 final 前需关闭的记录。

| 编号 | 决策点 | 影响 | 当前建议 / 倾向 | 状态 |
|------|--------|------|------------------|------|
| `G-FT-1` | first-test 主推理 substrate 选 XTTS/Coqui VC/RVC/其他 bridge | 决定 FT4 adapter 实现和 live test 依赖 | 倾向先选预训练、短 reference、可输出 wav、许可可记录的一条主路 | `OPEN / non-blocking for proposed` |
| `G-FT-2` | 是否要求真实训练进入 first-test | 会扩大到训练平台与 GPU 长程 | 倾向不要求真实训练，优先真实推理+真实评估闭环 | `OPEN / non-blocking for proposed` |
| `G-FT-3` | 是否引入全局 API envelope | 影响现有 API 响应兼容 | 倾向不在 first-test 强推全局 envelope，只冻结 first-test contract | `OPEN / non-blocking for proposed` |
| `G-FT-4` | release gate 通过线是 smoke、quality 还是 manual waive | 决定 FT5/FT7 成功语义 | 倾向分层：smoke pass 与 quality pass 分离 | `OPEN / non-blocking for proposed` |
| `G-FT-5` | 是否新增 `test_runs/inference_runs/eval_sessions` migration | 影响 DB schema | 倾向先用 metadata_json + artifacts/job_events，final 前按实测决定 | `OPEN / non-blocking for proposed` |

- **结论**：gate 不阻止 proposed 输出；final 前必须关闭 `G-FT-1/3/4/5`，其中 `G-FT-1` 对 FT4 action-plan 影响最大。

---

## 8. 测试计划

### 8.1 A 短途（in-worker route/unit）

| 测试组 | 覆盖范围 | 必须包含 |
|--------|----------|----------|
| `A-FT1` | CLI/config/preflight | command drift、env drift、bootstrap extras、empty manifest guard、artifact root resolver |
| `A-FT2` | DB/schema/observability | migration order、schema snapshot、FK/WAL/busy_timeout、job_events metadata、trace completeness |
| `A-FT3` | preprocess adapters | FFmpeg command/metadata、PyAnnote token skip、Demucs failure metadata、Whisper model metadata |
| `A-FT4` | inference adapter | input contract、no mock fallback、artifact metadata、model manifest/license |
| `A-FT5` | eval/release | smoke metrics、proxy unavailable handling、MOS validation、release gate semantics |
| `A-FT6` | FastAPI TestClient | upload artifact, start jobs, status/trace/report/release contract, response schema snapshot |

### 8.2 B spike（live HTTP，入 cap + denominator）

| 测试组 | 覆盖范围 | 必须包含 |
|--------|----------|----------|
| `B-FT3-live` | 真实短音频预处理 | FFmpeg/PyAnnote/Demucs/Whisper live smoke；缺依赖 skip reason |
| `B-FT4-live` | 真实推理 | 有模型缓存时输出真实 wav；缺模型/license/token skip reason |
| `B-FT6-live` | FastAPI HTTP | uvicorn live upload→start→poll→trace；真实依赖 skip denominator |

### 8.3 D mega（owner-triggered 长程）

| 测试组 | 覆盖范围 | 必须包含 |
|--------|----------|----------|
| `D-FT7-capstone` | first-test 完整链路 | 真实音频 → preprocess → real inference → eval → release → trace → evidence pack |

### 8.4 e2e 前置测试闸

| 闸 | 通过条件 |
|----|----------|
| `schema-drift-gate` | migration + schema snapshot + core table/column/FK/check assertions 通过 |
| `observability-gate` | 每个 major step 有 job_event、duration/error、artifact refs、mode/source |
| `mock-real-gate` | 所有 real report/artifact/metric 均不能来自 mock adapter |
| `api-contract-gate` | TestClient response schema snapshot 通过 |
| `evidence-gate` | run folder exporter 可生成完整 evidence pack |

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 主推理 substrate 迟迟不定 | FT4 adapter 无法开始 | 延误真实 e2e | proposed 先定义统一 adapter contract，具体模型 final 关闭 |
| schema 过早新增过多表 | migration 风险扩大 | 破坏 first-build 稳定性 | FT2 先用现有 metadata_json；新增表需 schema-drift-gate |
| 可观测性过度平台化 | 引入 OTel/队列/监控复杂度 | 偏离 first-test | 只借 OTel vocabulary，落 DB events/trace JSON |
| live 依赖不可用 | GPU/token/model 缺失 | capstone 无法跑 | live skip reason + denominator；preflight cache/license 探针 |
| API 上传临时文件被长任务引用 | request 生命周期结束 | 长任务失败或数据丢失 | upload 立即写 artifact，DB job 引用 artifact/path |
| 代理指标被误当真实主观质量 | SQUIM/DNSMOS/PESQ 等 proxy 分数过度解释 | 质量结论失真 | metric_source 分层，manual MOS/release gate 单独展示 |
| deferred 边界膨胀 | vec0/embedder/多 worker/训练平台一起进入 first-test | 阶段失控 | FT8 维护 reopen trigger，不触发则继续 deferred |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：first-test final-execution-plan、FT1-FT8 action-plan、schema drift test inventory、FastAPI first-test contract、real inference/eval design、live capstone test surface。

> proposed 阶段先给出预期派生图；final 阶段再冻结具体文件名。

| phase 簇 | 预期 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|------------------------|--------------|-------------|
| `FT1` | `docs/action-plan/first-test/FT1-preflight.md` | `FT1.1..FT1.7` | 最先执行 |
| `FT2` | `docs/action-plan/first-test/FT2-schema-observability.md` | `FT2.1..FT2.7` | FT1 后，FT3/FT4 前置 contract |
| `FT3` | `docs/action-plan/first-test/FT3-real-preprocess.md` | `FT3.1..FT3.6` | 依赖 FT1；遵守 FT2 contract |
| `FT4` | `docs/action-plan/first-test/FT4-real-inference.md` | `FT4.1..FT4.6` | 依赖 FT2 contract，可与 FT3 spike 并行 |
| `FT5` | `docs/action-plan/first-test/FT5-real-evaluation.md` | `FT5.1..FT5.6` | 依赖 FT4 output artifact contract |
| `FT6` | `docs/action-plan/first-test/FT6-fastapi-e2e.md` | `FT6.1..FT6.7` | skeleton 可早开，成功语义依赖 FT2/FT4/FT5 |
| `FT7` | `docs/action-plan/first-test/FT7-live-capstone.md` | `FT7.1..FT7.5` | FT1-FT6 test gates 后 |
| `FT8` | `docs/action-plan/first-test/FT8-closure-deferred.md` | `FT8.1..FT8.4` | FT7 evidence 后 |

---

## 11. Final recommendation

- **推荐序列**：`FT1` → `FT2` → `FT3` + `FT4 adapter spike` → `FT5` → `FT6` → `FT7` → `FT8`。
- **一句话总结**：first-test 的 proposed 基线是“先建立可诊断的真实链路 substrate，再把真实推理、真实评估和 FastAPI e2e 接上去”，不是把更多 mock 路径包装成真实完成。

---

## 12. 交叉引用与修订历史

- **交叉引用**：
  - `docs/eval/first-test/initial-planning-by-GPT.md`
  - `docs/eval/first-test/reference-anchor.md`
  - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md`
  - `docs/closure/first-build/deferred-items-ledger.md`
  - `docs/templates/eval-planning.md`

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-13 | GPT / Codex | proposed 初稿：阶段改为 `FT1..FT8`，重排工作项，绑定 reference-anchor 与测试面 |
