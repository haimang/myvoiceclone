# myvoiceclone first-build —— Final Execution Plan（by Codex）

> **stage**：`final`
> **作者**：`Codex`（panel / 跨模型 handoff：`none`）
> **时间**：`2026-06-13`
> **文档性质（自宣告 role）**：**取代 initial + proposed 两份**，作 action-plan 制作前**唯一执行基线**；不再在前两份上增量
> **上游权威输入**：
> - `myvoiceclone/initial-thoughts.md` — 20+ 小时真实会话数据、高保真 voice clone、So-VITS-SVC 倾向、清洗流水线必要性
> - `myvoiceclone/docs/eval/first-build/proposed-planning.md` — proposed 基线：双轨模型、SQLite + vec0、本地工作台、P0-P6 phase
> - 本轮 owner directive — 要求 final 态重写，细化 phase、数据库/插件、接口、抽象层、日志报告状态、文件定位、unit tests；初期暂不考虑授权与安全，开发到一定阶段再考虑
> - web reference anchors — sqlite-vec/vec0、SQLite vec1、SQLite WAL/foreign keys/JSON、FastAPI、pytest、Typer、pyannote、Demucs、Whisper、Python logging、MLflow/DVC
> **[仅 final] 输入权威次序**：`本轮 owner directive > proposed-planning > initial-thoughts > web reference anchors > 当前 HEAD 文件实测`
> **phase 命名 & 工作项 ID 方案**：`MVC-P0..P8 / DB-001..006 / API-R* / T-*`（P0-P6 沿用 proposed，新增 P7 安全后置、P8 打包交付）
> **裁定动词 rubric（§2 用）**：`CONFIRM / CORRECT / REFINE / RESIZE / GAP / SCOPE↑↓`
> **文档状态**：`frozen`
> **下游消费者**：`docs/plan/first-build/*.md`、first-build repo scaffold

---

## 0. TL;DR

- **核心论点**：`myvoiceclone` first-build 的执行基线是一个本地、可审计、低耦合的 voice clone 工程工作台：原始音频和大产物留在文件系统，关系事实、状态、血缘、日志索引进入 SQLite，embedding 检索默认使用 `sqlite-vec/vec0`，`vec1` 只做后期 ANN probe；业务能力通过 domain service、pipeline step、adapter、job runner、API/CLI 分层隔离。初期不实现授权/安全拦截，但保留 `consent/security` schema 与 P7 接入点，避免后续重构。
- **一句话**：先建一个能把“20+ 小时真实录音”稳定转成“可追溯 clean dataset + baseline model + eval report”的本地流水线，再接长训和安全治理。
- **本态相对上一态做了什么**：将 proposed 的策略性设计冻结为逐 phase 执行台账、数据库迁移、插件安装计划、接口合同、抽象层职责、状态/日志/报告模型、全文件定位和 unit test 套件。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `myvoiceclone/initial-thoughts.md` | owner anchor | 20h+ 会话数据、RVC 局限、So-VITS-SVC 倾向、预处理必要性 | `myvoiceclone/initial-thoughts.md` |
| `proposed-planning.md` | 上一态 plan | P0-P6、项目树、SQLite + vec0、接口草案 | `myvoiceclone/docs/eval/first-build/proposed-planning.md` |
| 本轮 owner directive | owner directive | final 态、细化 phase、暂缓授权安全、完整 unit tests | 当前对话 |
| sqlite-vec | positive reference | Python 安装 `pip install sqlite-vec`，`sqlite_vec.load()`，`vec0` 虚表；项目标注 pre-v1 需防 breaking changes | https://github.com/asg017/sqlite-vec / https://alexgarcia.xyz/sqlite-vec/python.html |
| SQLite `vec1` | positive/probe reference | SQLite 官方 ANN virtual table extension，支持 L2/cosine，便携 C，无外部依赖 | https://sqlite.org/vec1 |
| SQLite WAL / foreign keys / JSON | DB reference | WAL、FK enforcement、JSON functions 的官方行为 | https://sqlite.org/wal.html / https://sqlite.org/foreignkeys.html / https://sqlite.org/json1.html |
| FastAPI BackgroundTasks | positive/negative reference | 轻量后台任务可用；长训练/可取消任务不应只依赖它 | https://fastapi.tiangolo.com/tutorial/background-tasks/ |
| FastAPI TestClient / request body | API test reference | HTTP route unit tests、Pydantic body validation | https://fastapi.tiangolo.com/tutorial/testing/ / https://fastapi.tiangolo.com/tutorial/body/ |
| pytest `tmp_path` | unit test reference | 每个测试唯一临时目录，适合 DB/artifact isolation | https://docs.pytest.org/en/stable/how-to/tmp_path.html |
| Typer testing | CLI test reference | `CliRunner` 调用 CLI 并检查 exit/output | https://typer.tiangolo.com/tutorial/testing/ |
| pyannote.audio | preprocess reference | speaker diarization toolkit / pretrained pipelines | https://github.com/pyannote/pyannote-audio |
| Demucs | preprocess reference | vocals/source separation，适配 denoise/separation step | https://github.com/facebookresearch/demucs |
| Whisper | ASR reference | 命令行和 Python ASR 基线，用于 transcript/QC/WER | https://github.com/openai/whisper |
| Python logging cookbook | logging reference | structured/queued logging patterns | https://docs.python.org/3/howto/logging-cookbook.html |
| MLflow / DVC | report/lineage reference | run metadata、metrics、artifacts、data/model versioning 的正例；first-build 不强依赖 | https://mlflow.org/docs/latest/ml/tracking/ / https://doc.dvc.org/start |

- **纪律继承**：本文是 eval / planning final 态；它冻结执行基线和 contract surface，不直接生成代码，不取代后续 action-plan 的逐步实施。
- **正例提炼**：嵌入式向量扩展用 `sqlite-vec`，API contract 用 FastAPI/Pydantic，测试用 pytest tmp_path/TestClient/CliRunner，ML run 用 metadata/metrics/artifacts 三件套。
- **反例提炼**：不要用 FastAPI `BackgroundTasks` 承担 24h 训练；不要把 `vec1` 当 first-build 默认；不要把外部模型仓库内部路径泄漏到 domain/API；不要把日志只写文本文件而不入 DB 索引。

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

### 2.C [仅 final] critique vs proposed-planning

| item-ID | 裁定（CONFIRM/CORRECT/REFINE/RESIZE/GAP/SCOPE↑↓） | 处置 | 依据（冻结 Q / HEAD 锚） |
|---------|---------------------------------------------------|------|---------------------------|
| MVC-P0 | `CORRECT` | proposed 将授权放在早期强门禁；本 final 按 owner directive 改为“P0 只记录项目目标，P7 再接授权/安全实现”。 | [Q2] |
| MVC-P1 | `REFINE` | SQLite schema 从概念表扩展为 DB-001..006 迁移、安装步骤、连接 PRAGMA、向量表加载、状态/日志/报告表。 | [Q3], sqlite-vec/SQLite anchors |
| MVC-P2 | `CONFIRM` | 预处理主链仍是 ingest -> diarize -> slice -> clean -> transcribe -> score。 | proposed §6.3, pyannote/Demucs/Whisper anchors |
| MVC-P3 | `REFINE` | corpus curation 增加 review queue、dedupe decisions、dataset manifest checksum、split policy tests。 | [Q6] |
| MVC-P4 | `RESIZE` | baseline 不只跑模型，还必须产出固定 eval pack、样本渲染和 report bundle。 | [Q6], MLflow run/artifact pattern |
| MVC-P5 | `REFINE` | So-VITS-SVC 长训以 adapter/job/run contract 包住，不把训练仓库作为业务核心。 | [Q1], initial-thoughts |
| MVC-P6 | `SCOPE↑` | eval/inference packaging 增加 API/CLI 合同、状态机、报告生成、artifact lineage。 | [Q4], [Q6] |
| MVC-P7 | `GAP` | proposed 早期讨论安全但没有“后置接入 phase”；新增 P7 Security & Governance Retrofit。 | [Q2] |
| MVC-P8 | `GAP` | proposed 缺少打包交付 phase；新增 P8 Ops Packaging & Developer Handoff。 | [Q8] |
| MVC-TEST | `GAP` | proposed 测试只给概要；本 final 按每个 phase 定位 unit test、API/CLI test、fixture 和 artifact test。 | [Q7] |
| MVC-FILES | `GAP` | proposed 给了项目树但未把每个文件落到工作台账；本 final 增加 §12 文件定位矩阵。 | [Q8] |

---

## 3. 范围与非范围（In/Out-Scope）

### 3.1 In-Scope

- **[S1] 本地 first-build 工程骨架** — Python package、configs、SQLite migrations、API/CLI、tests、Docker/script/docs 全部可定位。
- **[S2] 数据库与插件安装** — SQLite WAL/FK/JSON 基线，`sqlite-vec/vec0` 默认安装与加载，`vec1` 后期 probe。
- **[S3] 解耦 pipeline** — 每个 step 只读上一步 artifact 和 DB 状态，写新 artifact 与状态事件；外部工具全部经 adapter。
- **[S4] 接口化业务流转** — CLI、HTTP API、job payload、artifact contract、report contract、状态机。
- **[S5] 日志/报告/状态审计** — `jobs/job_events/artifacts/reports/eval_metrics` 形成可审计链路。
- **[S6] Phase-by-phase tests** — unit tests 覆盖 domain、storage、vector、artifact、job、pipeline、adapter mock、API、CLI、report。
- **[S7] 后置安全治理接入点** — 初期不阻塞开发；P7 接入 consent、watermark、release policy。

### 3.2 Out-of-Scope / 延后

- **[O1] 生产级多租户权限系统** — first-build 不做；P7 仅实现本地策略与 release gate。
- **[O2] 云端训练队列 / Celery / Kubernetes** — 本地 job runner 先行；重评条件：需要多机 GPU 或远程任务。
- **[O3] `vec1` 作为默认向量库** — 延后到 DB-006 probe；重评条件：`vec0` 在 100k+ segment 查询明显不足。
- **[O4] 实时语音通话替身** — 延后；先完成 batch inference 和 report。
- **[O5] 自动下载闭源/受限权重** — 只做配置占位和手动下载脚本，不把 license/token 写死。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线**：domain/API 不依赖 RVC/So-VITS-SVC 仓库结构；训练主线不读取 raw audio；所有训练读取 frozen manifest；所有外部工具走 adapter。
- **治理冻结面**：P0-P6 不实现授权拦截；P1 预留 `consent_ledger` / `policy_events`；P7 再启用安全策略、合成输出标记、release gate。
- **migration inventory**：`DB-001_core_schema`、`DB-002_state_jobs_artifacts`、`DB-003_vec0_embeddings`、`DB-004_reports_metrics`、`DB-005_security_placeholders`、`DB-006_optional_vec1_probe`。
- **日志与审计**：每个 job 必须写 `jobs`、`job_events`、`artifacts`；每个报告必须写 `reports`；每个模型 run 必须写 `model_runs` 和 `eval_metrics`。
- **低耦合原则**：`domain` 只含业务规则和实体；`storage` 只管 persistence；`pipelines` 编排步骤；`adapters` 包外部工具；`api/cli` 只是入口；`jobs` 只管执行和状态。
- **测试纪律**：任何外部模型/FFmpeg/GPU 调用默认 mock；live smoke 单独 marker；unit tests 必须在无 GPU、无网络、无真实音频时通过。

---

## 5. DAG（关键路径 + 并行窗）

```text
P0 Scope Freeze
  └─▶ P1 Skeleton + SQLite + vec0
        ├─▶ P2 Preprocess Pipeline
        │     └─▶ P3 Corpus Curation + Dataset Freeze
        │           ├─▶ P4 Quick Baselines
        │           │     └─▶ P6 Eval + Inference API
        │           └─▶ P5 Long-run So-VITS-SVC Track
        │                 └─▶ P6 Eval + Inference API
        └─▶ P8 Ops/Dev Packaging
P7 Security Retrofit ─────────────▶ P8 Release Handoff
```

关键路径：`P0 -> P1 -> P2 -> P3 -> P4 smoke -> P5 long train -> P6 eval -> P8 handoff`。

并行窗：`P8` 的 README、Docker skeleton、developer docs 可与 P1-P3 并行；`P7` 在 P6 API/Inference 可运行后接入；`DB-006 vec1` 不阻塞主线。

---

## 6. 逐 phase 工作台账

> `来源 [Qn]` 来自 §13 owner-decision-freeze。`migration` 为空表示不改 DB schema。

### 6.1 P0 `Scope Freeze & Architecture Charter`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P0-01 | docs | 固化 first-build 目标：本地单用户工作台、VC/SVC 主线、TTS baseline 可选 | ♻️ | `docs/plan/first-build/00-scope-architecture.md` 完成 | scope charter |  | [Q1] |
| MVC-P0-02 | docs | 将授权/安全实现移出 P0-P6，保留 P7 接入 | 🆕 | charter 明确“early no auth enforcement” | gate closure table |  | [Q2] |
| MVC-P0-03 | arch | 冻结分层原则：domain/storage/vector/artifact/pipeline/adapter/job/api/cli/eval | ✅ | layer dependency diagram 完成 | `docs/architecture/layers.md` |  | [Q5] |
| MVC-P0-04 | test | 建立测试分类与 marker：unit/api/cli/live/gpu/slow | 🆕 | pytest marker 文档完成 | `pytest.ini` plan |  | [Q7] |

### 6.2 P1 `Repo Skeleton + SQLite/vec0 Foundation`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P1-01 | scaffold | 创建项目树与 Python package skeleton | 🆕 | §12 全部 source/test/docs 路径存在或有 placeholder | tree snapshot |  | [Q8] |
| MVC-P1-02 | deps | `pyproject.toml` 定义 runtime/dev extras | 🆕 | `pip install -e .[dev,api,vec]` 设计可执行 | lock notes |  | [Q3] |
| MVC-P1-03 | db | SQLite connection manager：WAL、FK ON、busy_timeout、row_factory | 🆕 | unit test 证明 PRAGMA 生效 | DB smoke output | DB-001 | [Q3] |
| MVC-P1-04 | db | core schema：recordings/speakers/segments/datasets/dataset_segments | ♻️ | migration idempotent，FK/check 通过 | migration report | DB-001 | [Q3] |
| MVC-P1-05 | db | job/artifact/run/event/review schema | 🆕 | job 状态、review 审计和 artifact 血缘可查询 | schema dump | DB-002 | [Q6] |
| MVC-P1-06 | vector | 安装 `sqlite-vec`，实现 `vec0_store.py`，创建 embedding metadata + vec0 virtual tables | 🆕 | `SELECT vec_version()` 或等价 healthcheck 通过，embedding_jobs 可审计 | vector healthcheck | DB-003 | [Q3] |
| MVC-P1-07 | vector | `VectorStore` protocol + `NullVectorStore` test double | 🆕 | domain tests 不依赖 sqlite-vec | unit tests | DB-003 | [Q5] |
| MVC-P1-08 | reports | reports/eval_metrics schema | 🆕 | report summary 可入库、可查 | report fixture | DB-004 | [Q6] |
| MVC-P1-09 | security | consent/security placeholder schema，不启用拦截 | ♻️ | 表存在但 API 不校验 | schema dump | DB-005 | [Q2] |
| MVC-P1-10 | vec1 | `vec1` probe 文件与 feature flag，占位不默认启用 | 🆕 | 默认测试不加载 vec1 | skipped/probe note | DB-006 | [Q4] |

### 6.3 P2 `Preprocess Pipeline`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P2-01 | ingest | `ingest.py` 计算 sha256、登记 recording、生成 normalized artifact | 🆕 | 同一文件重复 ingest 不重复入库 | artifact rows |  | [Q6] |
| MVC-P2-02 | audio | 标准 adapter DTO + `ffmpeg.py` adapter：probe/normalize/extract_segment 命令构造 | 🆕 | DTO serialization 与 mock subprocess tests 通过 | command snapshot |  | [Q5] |
| MVC-P2-03 | diarize | `pyannote_adapter.py` 输出标准 speaker turn JSON/RTTM | ✅ | adapter 输出转 segments draft | diarization artifact |  | [Q5] |
| MVC-P2-04 | slice | VAD/slicing step 生成 2-10s segment artifact | ✅ | segment duration/check overlap 通过 | segment rows |  | [Q6] |
| MVC-P2-05 | clean | `demucs_adapter.py` / `uvr_adapter.py` 生成 cleaned artifact | ✅ | before/after artifact lineage 完整 | artifact lineage |  | [Q6] |
| MVC-P2-06 | transcribe | `whisper_adapter.py` 生成 transcript artifact 和 segment transcript | 🆕 | ASR result schema 固定 | transcript JSON |  | [Q6] |
| MVC-P2-07 | score | 质量评分：duration、clip、speech_ratio、noise、speaker_similarity | 🆕 | score updater 可重复运行 | segment score table |  | [Q6] |
| MVC-P2-08 | job | 每个 pipeline step 均可作为 job 运行、失败可重试 | 🆕 | failed job 有 error 和 events | job_events rows | DB-002 | [Q6] |

### 6.4 P3 `Corpus Curation + Dataset Freeze`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P3-01 | curate | review queue：keep/drop/needs_review/fixed 标签 | 🆕 | PATCH 或 CLI 可更新 segment status | review log | DB-002 | [Q6] |
| MVC-P3-02 | vector | embedding upsert jobs：speaker/audio/text namespace | 🆕 | vec0 search 返回 stable ordered results | vector test report | DB-003 | [Q3] |
| MVC-P3-03 | dedupe | embedding 相似去重 decision 表/metadata | 🆕 | 重复片段不会进入同一 manifest | dedupe report | DB-004 | [Q6] |
| MVC-P3-04 | split | 按 recording/source 分组 train/val/test split | 🆕 | split leak detector 通过 | split report |  | [Q6] |
| MVC-P3-05 | manifest | `export_dataset.py` 生成 `manifest.jsonl` 和 checksum | 🆕 | frozen dataset 不可变更 | manifest hash |  | [Q6] |
| MVC-P3-06 | report | corpus audit report：时长、speaker purity、噪声分布、drop reasons | 🆕 | HTML/JSON/Markdown 三份报告 | report artifact | DB-004 | [Q6] |

### 6.5 P4 `Quick Baselines`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P4-01 | training | `rvc_adapter.py` 封装 quick train/convert | ♻️ | mock train creates model_run + checkpoint artifact | run rows | DB-002 | [Q1] |
| MVC-P4-02 | training | `xtts_adapter.py` 或 TTS baseline adapter contract | 🆕 | synth smoke 可通过 fake adapter | rendered artifact | DB-002 | [Q1] |
| MVC-P4-03 | eval | baseline eval pack：固定 prompts、source clips、reference clips | 🆕 | eval pack manifest 可复用 | eval pack artifact | DB-004 | [Q6] |
| MVC-P4-04 | report | baseline report 比较 RVC/TTS smoke | 🆕 | Markdown + JSON report 入库 | report row | DB-004 | [Q6] |
| MVC-P4-05 | gate | 长训 gate：数据质量、baseline 可学性、环境可运行 | 🆕 | `long_train_ready` report conclusion | gate report |  | [Q6] |

### 6.6 P5 `Long-run So-VITS-SVC Track`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P5-01 | infra | `Dockerfile.train` + env digest capture | ♻️ | build plan 和 env digest 记录 | env report |  | [Q3] |
| MVC-P5-02 | adapter | `sovits_adapter.py` 封装 prepare/train/resume/export | ✅ | fake adapter 证明命令和 artifact contract | adapter unit tests |  | [Q5] |
| MVC-P5-03 | features | feature cache：content units/F0/spec/speaker stats artifact | 🆕 | cache 可命中、可失效 | cache manifest |  | [Q6] |
| MVC-P5-04 | runner | long job checkpoint/resume/cancel 状态 | ♻️ | resume 后同 run lineage 不断链 | job events | DB-002 | [Q6] |
| MVC-P5-05 | registry | model registry：manifest id、config、checkpoint、score、notes | 🆕 | model_run 查询可复现实验 | model registry rows | DB-002/004 | [Q6] |
| MVC-P5-06 | report | long-train report：loss 曲线、checkpoint、样本、失败原因 | 🆕 | report 入库并链接 artifacts | report row | DB-004 | [Q6] |

### 6.7 P6 `Evaluation + Inference API`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P6-01 | api | FastAPI app factory + dependency injection | 🆕 | TestClient 可注入 tmp DB | API tests |  | [Q4] |
| MVC-P6-02 | api | routes：recordings/segments/datasets/jobs/runs/reports/inference | 🆕 | OpenAPI schema stable | route tests |  | [Q4] |
| MVC-P6-03 | cli | Typer CLI 与 service 层共享，不绕过 domain | 🆕 | CliRunner tests 通过 | CLI test output |  | [Q4] |
| MVC-P6-04 | infer | inference service：VC/TTS/batch render job | 🆕 | fake adapter 生成 rendered artifact | rendered audio fixture | DB-002 | [Q1] |
| MVC-P6-05 | eval | objective metrics：speaker similarity/WER/duration/noise | 🆕 | metric rows and report generated | eval metrics | DB-004 | [Q6] |
| MVC-P6-06 | report | ABX/MOS subjective report schema 和导出模板 | 🆕 | report bundle 完成 | subjective report | DB-004 | [Q6] |
| MVC-P6-07 | state | 状态查询 API 返回 recording/job/dataset/run 全链路 | 🆕 | audit trace endpoint test 通过 | trace JSON | DB-002/004 | [Q6] |

### 6.8 P7 `Security & Governance Retrofit`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P7-01 | policy | 启用 consent policy：recording/speaker/model release 前校验 | ♻️ | P7 前默认 off，P7 后 feature flag on | policy tests | DB-005 | [Q2] |
| MVC-P7-02 | policy | release gate：model_run -> release_candidate 需 policy pass | 🆕 | policy failure blocks release only | gate tests | DB-005 | [Q2] |
| MVC-P7-03 | artifact | rendered output metadata/watermark placeholder | 🆕 | inference artifact 记录 synthetic flag | artifact metadata | DB-005 | [Q2] |
| MVC-P7-04 | docs | 安全/授权 SOP 文档 | 🆕 | docs 完成，不影响 earlier pipeline | SOP doc |  | [Q2] |

### 6.9 P8 `Ops Packaging + Developer Handoff`

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| MVC-P8-01 | docs | README quickstart：install/initdb/ingest/preprocess/train/eval | 🆕 | 新开发者可按步骤跑 mock flow | README checklist |  | [Q8] |
| MVC-P8-02 | scripts | bootstrap/download/run scripts | 🆕 | scripts dry-run 输出命令计划 | script tests |  | [Q8] |
| MVC-P8-03 | docker | preprocess/train compose skeleton | 🆕 | docker build docs + env variables | ops docs |  | [Q3] |
| MVC-P8-04 | tests | capstone mock journey：P0/P1 gates -> raw -> dataset -> baseline -> report + audit trace + P7 policy-on variant | 🆕 | `tests/integration/test_first_build_journey.py` 通过 | capstone output | all | [Q7] |
| MVC-P8-05 | docs | action-plan 拆分并链接本文 | 🆕 | docs/plan 文件存在 | action-plan index |  | [Q8] |

---

## 7. Owner decision gates

### 7.B [仅 final] gate-closure map（全部由本轮 owner directive / final baseline 关闭）

| gate | 对应冻结 Q | 裁决结论（下游唯一口径） | 状态 |
|------|-----------|--------------------------|------|
| G-MVC-1 | [Q1] | first-build 保持双轨：VC/SVC 是主线，TTS baseline 作为可选 smoke，不在 P0 关闭模型路线。 | CLOSED |
| G-MVC-2 | [Q2] | 初期 P0-P6 不实现授权和安全拦截；P1 预留 schema，P7 后置接入。 | CLOSED |
| G-MVC-3 | [Q3] | 本地 DB 默认 SQLite + `sqlite-vec/vec0`；安装写入 P1；WAL/FK/JSON 是连接基线。 | CLOSED |
| G-MVC-4 | [Q4] | 接口初期以 FastAPI + Typer 为主；HTTP/CLI 都调用 service，不直接操作 adapter。 | CLOSED |
| G-MVC-5 | [Q5] | 抽象层按 domain/storage/vector/artifact/pipeline/adapter/job/api/eval 分层，禁止反向依赖。 | CLOSED |
| G-MVC-6 | [Q6] | 业务流转必须记录 jobs/job_events/artifacts/reports/eval_metrics，做到步骤解耦、可审计。 | CLOSED |
| G-MVC-7 | [Q7] | 每个 phase 都必须有 unit tests；live/GPU/model tests 单独 marker，不阻塞默认 unit suite。 | CLOSED |
| G-MVC-8 | [Q8] | 项目树所有文件必须在 §12 定位到具体 phase 和工作项。 | CLOSED |

- **结论**：设计阶段无 OPEN 决策项，可转入 action-plan；真实模型/硬件结果仍由 P4/P5 evidence gate 判断，不在本文预设质量结论。

---

## 8. 测试计划

### 8.1 Test taxonomy

| marker | 默认运行 | 目标 | 示例 |
|--------|----------|------|------|
| `unit` | 是 | 无网络、无 GPU、无真实模型，验证纯逻辑/DB/API/CLI | `pytest -m unit` |
| `api` | 是 | FastAPI TestClient route tests | `pytest -m api` |
| `cli` | 是 | Typer CliRunner tests | `pytest -m cli` |
| `integration` | 是，mock adapter | 端到端 mock journey | `pytest -m integration` |
| `live` | 否 | 真实 FFmpeg/pyannote/Demucs/Whisper smoke | `pytest -m live` |
| `gpu` | 否 | CUDA/训练 smoke | `pytest -m gpu` |
| `slow` | 否 | 长任务 rehearsal | `pytest -m slow` |

### 8.2 Phase unit suites

| Phase | test files | 覆盖内容 |
|-------|------------|----------|
| P0 | `tests/unit/test_architecture_boundaries.py` | 禁止 domain import adapters/api；marker 注册；docs gate metadata |
| P1 | `tests/unit/storage/test_migrations.py`、`test_sqlite_connection.py`、`test_vec0_store.py`、`test_artifact_store.py` | migrations idempotent、PRAGMA、FK/check、vec0 health/upsert/search、artifact hash |
| P2 | `tests/unit/pipelines/test_ingest.py`、`test_slice.py`、`test_score.py`、`tests/unit/adapters/test_ffmpeg_adapter.py`、`test_pyannote_adapter.py`、`test_demucs_adapter.py`、`test_whisper_adapter.py` | command construction、mock adapter outputs、segment creation、score update |
| P3 | `tests/unit/pipelines/test_curate.py`、`test_export_dataset.py`、`tests/unit/eval/test_corpus_report.py` | review transitions、dedupe decisions、split leak detection、manifest checksum |
| P4 | `tests/unit/adapters/test_rvc_adapter.py`、`test_xtts_adapter.py`、`tests/unit/eval/test_baseline_report.py` | baseline train/synth fake adapter、model_run/artifacts、report rows |
| P5 | `tests/unit/adapters/test_sovits_adapter.py`、`tests/unit/jobs/test_resume.py`、`tests/unit/eval/test_train_report.py` | long job resume/cancel、checkpoint lineage、feature cache metadata |
| P6 | `tests/api/test_routes_*.py`、`tests/cli/test_cli_*.py`、`tests/unit/eval/test_objective.py` | route validation/status codes、CLI commands、objective metrics |
| P7 | `tests/unit/domain/test_policies.py`、`tests/api/test_release_gate.py` | feature-flagged consent/release policy，P7 前不阻塞 P0-P6 |
| P8 | `tests/integration/test_first_build_journey.py`、`tests/unit/test_scripts_dry_run.py` | raw -> preprocess -> dataset -> baseline -> report mock capstone |

### 8.3 Fixtures and test data

- `tests/fixtures/audio/tone_16k.wav`：1-2 秒 synthetic wav，不含真实人声。
- `tests/fixtures/diarization/sample_turns.json`：pyannote 标准化输出。
- `tests/fixtures/asr/sample_transcript.json`：Whisper 标准化输出。
- `tests/fixtures/embeddings/*.json`：固定小向量，覆盖 `vec0` search。
- `tests/conftest.py`：`tmp_path` 创建 isolated SQLite + artifact root；所有 tests 不写真实 `data/`。
- `tests/fakes/*`：FakeDiarizer、FakeSeparator、FakeASR、FakeTrainer、FakeEmbedder、FakeInference。

### 8.4 长程 capstone

`tests/integration/test_first_build_journey.py`：

```text
A. init tmp DB and artifact root
B. ingest synthetic wav
C. fake diarize -> turns artifact
D. fake slice -> segment rows
E. fake clean -> cleaned artifacts
F. fake transcribe -> transcript rows
G. fake score + curate -> keep/drop states
H. export frozen dataset manifest
I. fake RVC baseline -> model_run + rendered samples
J. eval/report -> report rows + audit trace endpoint
```

### 8.5 Evidence pack + DoD

- **P0 DoD**：scope charter、layer diagram、test taxonomy。
- **P1 DoD**：migration report、DB schema dump、vec0 healthcheck、storage unit tests。
- **P2 DoD**：job event trace、artifact lineage、preprocess unit tests。
- **P3 DoD**：manifest checksum、corpus audit report、split leak test。
- **P4 DoD**：baseline report、model_run registry, sample rendered artifacts。
- **P5 DoD**：checkpoint lineage、resume test、long-train report。
- **P6 DoD**：OpenAPI schema snapshot、CLI help snapshot、eval report。
- **P7 DoD**：policy feature flag, release gate tests。
- **P8 DoD**：mock capstone green, README quickstart, action-plan index。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 初期不做授权/安全导致后续重构 | P0-P6 完全无 schema/contract 占位 | P7 破坏 API/DB | P1 建 placeholder，P7 只启用 policy，不重写核心流 |
| `sqlite-vec` pre-v1 breaking changes | 版本升级 | vector tests 失败 | pin version，`VectorStore` protocol 隔离，升级走 DB-003 test |
| `vec1` 过早引入 | 试图优化未出现的问题 | 构建复杂度上升 | `DB-006` feature flag，默认 off |
| FastAPI BackgroundTasks 承担长训 | 训练超过请求生命周期/无法取消 | 状态不可控 | 长任务全部走 `jobs.runner`，BackgroundTasks 只做轻量 dispatch |
| 外部模型工具污染 domain | adapter 返回私有格式 | API/DB 合同不稳定 | adapters 输出标准 DTO，pipeline 负责转换 |
| SQLite 锁竞争 | API + runner 并发写 | job 失败 | WAL、busy_timeout、短事务、runner 单写队列 |
| 真实音频测试污染 repo | unit tests 依赖私人录音 | 隐私和不可复现 | synthetic fixtures + live marker |
| 长训失败无法定位 | checkpoint/log/env 没记录 | 无法恢复 | job_events + env_digest + model_run + artifacts |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：first-build 可直接拆成 9 份 action-plan，每份有文件定位、退出条件和测试套件；实现后得到本地可审计 voice clone pipeline。

### 10.A [仅 final] action-plan 派生与排序

| phase 簇 | 派生的 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|--------------------------|--------------|-------------|
| P0 | `docs/plan/first-build/00-scope-architecture.md` | MVC-P0-01..04 | 先执行 |
| P1 | `docs/plan/first-build/01-storage-vec0-skeleton.md` | MVC-P1-01..10 | 依赖 P0 |
| P2 | `docs/plan/first-build/02-preprocess-pipeline.md` | MVC-P2-01..08 | 依赖 P1 |
| P3 | `docs/plan/first-build/03-corpus-dataset-freeze.md` | MVC-P3-01..06 | 依赖 P2 |
| P4 | `docs/plan/first-build/04-quick-baselines.md` | MVC-P4-01..05 | 依赖 P3 |
| P5 | `docs/plan/first-build/05-long-train-sovits.md` | MVC-P5-01..06 | 依赖 P3/P4 gate |
| P6 | `docs/plan/first-build/06-eval-inference-api.md` | MVC-P6-01..07 | P4 后可开始，P5 后补长训模型 |
| P7 | `docs/plan/first-build/07-security-governance-retrofit.md` | MVC-P7-01..04 | P6 inference 可用后执行 |
| P8 | `docs/plan/first-build/08-ops-handoff.md` | MVC-P8-01..05 | P8-prep 可与 P1-P6 并行；P8-closeout 依赖 P7 |

---

## 11. Final recommendation

- **推荐序列**：`P0 scope/layer freeze -> P1 SQLite+vec0 skeleton -> P2 mockable preprocess -> P3 dataset freeze -> P4 quick baselines -> P6 API/eval 可先接入 -> P5 long train -> P7 security retrofit -> P8 handoff`。
- **一句话总结**：first-build 的实现目标不是“跑通一个模型仓库”，而是让每个音频片段、每次训练、每个输出声音都能被定位、复现、评估和审计。

---

## 12. [仅 final] HEAD 代码实测 / 净新章节

### 12.1 HEAD facts

| # | HEAD 事实（实测锚） | 对前序前提的修正 | 处置 |
|---|----------------------|------------------|------|
| ARCH-1 | 当前 `myvoiceclone/` 只有 docs 与 `initial-thoughts.md`，未有代码 skeleton | proposed 的项目树仍是设计，不是现有实现 | P1 从零创建 skeleton |
| ARCH-2 | `proposed-planning.md` 已存在 | final 不回改 proposed | 新增本文件作为 superseding baseline |
| ARCH-3 | 未发现 QnA register | 模板 final 的 QnA closure 无正式 register | 以本轮 owner directive 作为 gate closure 来源，并在 §13 标明 |

### 12.2 完整项目树与文件定位矩阵

| 路径 | 类型 | owner phase/work item | 责任 |
|------|------|-----------------------|------|
| `README.md` | docs | MVC-P8-01 | quickstart 与开发入口 |
| `pyproject.toml` | config | MVC-P1-02 | dependencies、extras、pytest markers、CLI entrypoint |
| `.env.example` | config | MVC-P1-02/P8-01 | 本地路径、token、feature flags 示例 |
| `pytest.ini` | config | MVC-P0-04 | markers 与默认测试策略 |
| `configs/local.yaml` | config | MVC-P1-02 | 本地 DB/artifact/model root |
| `configs/models.yaml` | config | MVC-P1-02/P5-01 | 外部模型路径、adapter 配置 |
| `configs/pipelines/preprocess.default.yaml` | config | MVC-P2-08 | preprocess DAG 参数 |
| `configs/pipelines/train.rvc.yaml` | config | MVC-P4-01 | RVC baseline 参数 |
| `configs/pipelines/train.sovits.yaml` | config | MVC-P5-02 | So-VITS-SVC 参数 |
| `configs/pipelines/eval.default.yaml` | config | MVC-P6-05 | eval suite 参数 |
| `data/raw/` | artifact dir | MVC-P2-01 | 原始录音，只读 |
| `data/staging/` | artifact dir | MVC-P2-01 | normalized audio |
| `data/processed/diarized/` | artifact dir | MVC-P2-03 | diarization JSON/RTTM |
| `data/processed/sliced/` | artifact dir | MVC-P2-04 | segment audio |
| `data/processed/cleaned/` | artifact dir | MVC-P2-05 | cleaned segment audio |
| `data/processed/transcripts/` | artifact dir | MVC-P2-06 | ASR JSON/text |
| `data/datasets/first-build/manifest.jsonl` | artifact | MVC-P3-05 | frozen dataset manifest |
| `data/datasets/first-build/train/` | artifact dir | MVC-P3-04 | train split materialization |
| `data/datasets/first-build/val/` | artifact dir | MVC-P3-04 | val split materialization |
| `data/datasets/first-build/test/` | artifact dir | MVC-P3-04 | test split materialization |
| `data/artifacts/jobs/` | artifact dir | MVC-P2-08 | job logs/stdout/stderr |
| `data/artifacts/eval/` | artifact dir | MVC-P4-03/P6-05 | eval packs and metrics artifacts |
| `data/artifacts/reports/` | artifact dir | MVC-P3-06/P6-06 | generated reports |
| `db/myvoiceclone.sqlite` | runtime db | MVC-P1-03 | local SQLite database |
| `db/migrations/001_core_schema.sql` | migration | MVC-P1-04 | recordings/speakers/segments/datasets |
| `db/migrations/002_state_jobs_artifacts.sql` | migration | MVC-P1-05 | jobs/job_events/artifacts/model_runs |
| `db/migrations/003_vec0_embeddings.sql` | migration | MVC-P1-06 | `vec0` virtual tables |
| `db/migrations/004_reports_metrics.sql` | migration | MVC-P1-08 | reports/eval_metrics |
| `db/migrations/005_security_placeholders.sql` | migration | MVC-P1-09 | consent/policy placeholders |
| `db/migrations/006_optional_vec1_probe.sql` | migration | MVC-P1-10 | optional vec1 probe |
| `docs/architecture/layers.md` | docs | MVC-P0-03 | layer dependency charter |
| `src/myvoiceclone/domain/entities.py` | source | MVC-P0-03 | dataclasses/enums/IDs |
| `src/myvoiceclone/domain/policies.py` | source | MVC-P7-01 | quality/release/consent policy |
| `src/myvoiceclone/domain/states.py` | source | MVC-P1-05/P6-07 | recording/job/dataset/run state machines |
| `src/myvoiceclone/domain/services.py` | source | MVC-P0-03/P6-07 | domain service orchestration |
| `src/myvoiceclone/storage/sqlite.py` | source | MVC-P1-03 | connection/session manager |
| `src/myvoiceclone/storage/migrations.py` | source | MVC-P1-04 | migration runner |
| `src/myvoiceclone/storage/repositories.py` | source | MVC-P1-04/P1-05 | CRUD repositories |
| `src/myvoiceclone/storage/vector_store.py` | source | MVC-P1-07 | VectorStore protocol |
| `src/myvoiceclone/storage/vec0_store.py` | source | MVC-P1-06 | sqlite-vec implementation |
| `src/myvoiceclone/storage/vec1_store.py` | source | MVC-P1-10 | optional probe implementation |
| `src/myvoiceclone/storage/artifact_store.py` | source | MVC-P1-05/P7-03 | filesystem artifact registry + synthetic metadata retrofit |
| `src/myvoiceclone/pipelines/ingest.py` | source | MVC-P2-01 | ingest step |
| `src/myvoiceclone/pipelines/diarize.py` | source | MVC-P2-03 | diarization step |
| `src/myvoiceclone/pipelines/slice.py` | source | MVC-P2-04 | VAD/slicing step |
| `src/myvoiceclone/pipelines/clean.py` | source | MVC-P2-05 | denoise/separation step |
| `src/myvoiceclone/pipelines/transcribe.py` | source | MVC-P2-06 | ASR step |
| `src/myvoiceclone/pipelines/score.py` | source | MVC-P2-07 | quality scoring |
| `src/myvoiceclone/pipelines/curate.py` | source | MVC-P3-01/P3-03 | review/dedupe |
| `src/myvoiceclone/pipelines/export_dataset.py` | source | MVC-P3-05 | manifest freeze |
| `src/myvoiceclone/pipelines/train.py` | source | MVC-P4-01/P5-02 | training dispatch |
| `src/myvoiceclone/pipelines/evaluate.py` | source | MVC-P6-05 | eval dispatch |
| `src/myvoiceclone/adapters/audio/ffmpeg.py` | source | MVC-P2-02 | FFmpeg command adapter |
| `src/myvoiceclone/adapters/audio/torchaudio_io.py` | source | MVC-P2-02 | audio metadata/load helper |
| `src/myvoiceclone/adapters/diarization/pyannote_adapter.py` | source | MVC-P2-03 | pyannote adapter |
| `src/myvoiceclone/adapters/separation/demucs_adapter.py` | source | MVC-P2-05 | Demucs adapter |
| `src/myvoiceclone/adapters/separation/uvr_adapter.py` | source | MVC-P2-05 | UVR adapter |
| `src/myvoiceclone/adapters/asr/whisper_adapter.py` | source | MVC-P2-06 | Whisper adapter |
| `src/myvoiceclone/adapters/embeddings/speaker_embedder.py` | source | MVC-P3-02 | speaker embeddings |
| `src/myvoiceclone/adapters/embeddings/audio_embedder.py` | source | MVC-P3-02 | audio embeddings |
| `src/myvoiceclone/adapters/embeddings/text_embedder.py` | source | MVC-P3-02 | transcript embeddings |
| `src/myvoiceclone/adapters/training/rvc_adapter.py` | source | MVC-P4-01 | RVC adapter |
| `src/myvoiceclone/adapters/training/sovits_adapter.py` | source | MVC-P5-02 | So-VITS-SVC adapter |
| `src/myvoiceclone/adapters/training/xtts_adapter.py` | source | MVC-P4-02 | TTS adapter |
| `src/myvoiceclone/api/app.py` | source | MVC-P6-01 | FastAPI app factory |
| `src/myvoiceclone/api/schemas.py` | source | MVC-P6-02 | Pydantic schemas |
| `src/myvoiceclone/api/routes_recordings.py` | source | MVC-P6-02 | recording routes |
| `src/myvoiceclone/api/routes_segments.py` | source | MVC-P6-02 | segment routes |
| `src/myvoiceclone/api/routes_datasets.py` | source | MVC-P6-02 | dataset routes |
| `src/myvoiceclone/api/routes_jobs.py` | source | MVC-P6-02 | job routes |
| `src/myvoiceclone/api/routes_training.py` | source | MVC-P6-02 | training routes |
| `src/myvoiceclone/api/routes_inference.py` | source | MVC-P6-04/P7-03 | inference routes + synthetic metadata retrofit |
| `src/myvoiceclone/api/routes_reports.py` | source | MVC-P6-06/P7-02 | report routes + release gate retrofit |
| `src/myvoiceclone/cli.py` | source | MVC-P6-03 | Typer CLI |
| `src/myvoiceclone/jobs/runner.py` | source | MVC-P2-08/P5-04 | job execution |
| `src/myvoiceclone/jobs/queue.py` | source | MVC-P2-08 | local job queue |
| `src/myvoiceclone/jobs/events.py` | source | MVC-P1-05/P6-07 | job event writer |
| `src/myvoiceclone/eval/objective.py` | source | MVC-P6-05 | objective metrics |
| `src/myvoiceclone/eval/subjective.py` | source | MVC-P6-06 | subjective report model |
| `src/myvoiceclone/eval/report.py` | source | MVC-P3-06/P4-04/P4-05/P5-06/P6-06 | corpus/baseline/gate/train/eval report generation |
| `models/pretrained/` | artifact dir | MVC-P8-02 | manually downloaded base weights |
| `models/checkpoints/` | artifact dir | MVC-P5-05 | checkpoints |
| `models/registry/` | artifact dir | MVC-P5-05 | registry snapshots |
| `notebooks/corpus_audit.ipynb` | notebook | MVC-P3-06 | optional manual corpus review |
| `notebooks/eval_review.ipynb` | notebook | MVC-P6-06 | optional eval review |
| `scripts/bootstrap_env.sh` | script | MVC-P8-02 | local env bootstrap |
| `scripts/download_models.sh` | script | MVC-P8-02 | model download placeholders |
| `scripts/run_preprocess.sh` | script | MVC-P8-02/P2 | preprocess wrapper |
| `scripts/run_train_sovits.sh` | script | MVC-P8-02/P5 | long train wrapper |
| `infra/docker/Dockerfile.preprocess` | infra | MVC-P8-03/P2 | preprocess image |
| `infra/docker/Dockerfile.train` | infra | MVC-P8-03/P5 | train image |
| `infra/docker/compose.yaml` | infra | MVC-P8-03 | local service composition |
| `infra/systemd/` | infra | MVC-P8-03 | optional local service files |
| `docs/eval/first-build/final-execution-plan.md` | docs | current | final baseline |
| `docs/plan/first-build/*.md` | docs | MVC-P8-05 | derived action plans |
| `docs/api/openapi.md` | docs | MVC-P6-02 | API surface docs |
| `docs/ops/local-setup.md` | docs | MVC-P8-01/P8-03 | ops guide |
| `tests/conftest.py` | tests | MVC-P1/P8 | shared fixtures |
| `tests/fixtures/**` | tests | MVC-P2/P3/P6 | synthetic fixtures |
| `tests/fakes/**` | tests | MVC-P2-P6 | fake adapters/services |
| `tests/unit/**` | tests | MVC-P0-P7 | unit suites |
| `tests/api/**` | tests | MVC-P6/P7 | API suites |
| `tests/cli/**` | tests | MVC-P6/P8 | CLI suites |
| `tests/integration/test_first_build_journey.py` | tests | MVC-P8-04 | capstone journey |

### 12.3 抽象层详细安排

| 层 | 允许依赖 | 禁止依赖 | 主要接口 |
|----|----------|----------|----------|
| `domain` | stdlib, typing | storage/api/adapters/FastAPI | `Recording`, `Segment`, `Dataset`, `Job`, `Policy`, state enums |
| `storage` | domain DTO, sqlite3/sqlalchemy | adapters/FastAPI | repositories, migrations, `VectorStore`, `ArtifactStore` |
| `pipelines` | domain, storage, adapters protocols | FastAPI route internals | step functions: `run_ingest(ctx)`, `run_clean(ctx)` |
| `adapters` | external tools/libs | storage repositories | normalized DTOs: `DiarizationResult`, `TranscriptResult`, `TrainResult` |
| `jobs` | domain, storage, pipelines | API response schemas | queue, runner, event writer |
| `api` | domain services, jobs | external tools directly | route handlers + Pydantic schemas |
| `cli` | domain services, jobs | external tools directly | Typer commands |
| `eval` | domain, storage, artifacts | training internals | metrics/report contracts |

---

## 13. [仅 final] 冻结槽（双填充，至少一个）

### 13.A owner-decision-freeze（QnA 裁决索引，NORMATIVE）

| Q | 主题 | 冻结结论（下游唯一口径） | 来源 |
|---|------|--------------------------|------|
| Q1 | 模型路线 | VC/SVC 主线 + TTS baseline 可选；模型可替换，经 adapter 接入。 | 本轮 directive + proposed |
| Q2 | 授权/安全 | 初期不用考虑授权和安全性问题；P7 再后置接入治理，不阻塞 P1-P6。 | 本轮 directive |
| Q3 | 本地 DB/插件 | SQLite + `sqlite-vec/vec0` 为默认；`vec1` 只做可选 probe；WAL/FK/JSON 是连接基线。 | 本轮 directive + web anchors |
| Q4 | 接口 | FastAPI + Typer；HTTP/CLI 调 service/job，不直接调外部模型工具。 | 本轮 directive |
| Q5 | 抽象层 | 低耦合高内聚：domain/storage/vector/artifact/pipeline/adapter/job/api/cli/eval 分层，禁止反向依赖。 | 本轮 directive |
| Q6 | 业务审计 | 所有步骤必须记录状态、日志、artifact、report 和 metrics。 | 本轮 directive |
| Q7 | 测试 | 每个 phase 必须有 unit tests；live/GPU/slow 不进默认 suite。 | 本轮 directive |
| Q8 | 文件定位 | 项目树全部文件必须映射到 phase/work item。 | 本轮 directive |

### 13.B contract-surface-freeze（如适用）

- **冻结的 surface（8 个）**：`DB migrations`、`VectorStore protocol`、`Artifact contract`、`Job contract`、`Pipeline step contract`、`HTTP API routes`、`CLI commands`、`Report contract`。
- **背书方式**：本 final 文档作为 execution baseline；后续 action-plan 必须引用 §6、§8、§12、§13，不得绕过。

---

## 14. 数据库与插件安装详细安排

### 14.1 Python dependencies

```toml
[project.optional-dependencies]
api = ["fastapi", "uvicorn", "pydantic"]
cli = ["typer"]
db = ["sqlite-vec"]
audio = ["soundfile", "torchaudio"]
preprocess = ["pyannote.audio", "openai-whisper"]
test = ["pytest", "httpx"]
dev = ["ruff", "mypy"]
```

### 14.2 sqlite-vec install/load

```bash
python -m pip install sqlite-vec
```

```python
import sqlite3
import sqlite_vec

conn = sqlite3.connect("db/myvoiceclone.sqlite")
conn.execute("PRAGMA foreign_keys=ON")
conn.execute("PRAGMA journal_mode=WAL")
sqlite_vec.load(conn)
```

Acceptance:

- `test_vec0_extension_loads` loads extension in a tmp DB.
- `test_vec0_upsert_and_search` inserts fixed vectors and returns deterministic nearest neighbors.
- `test_vector_store_protocol_can_use_null_store` proves domain tests do not depend on extension availability.

### 14.3 DB schema final baseline

Required tables:

- Core: `speakers`, `recordings`, `segments`, `segment_reviews`, `datasets`, `dataset_segments`.
- State/audit: `jobs`, `job_events`, `artifacts`, `model_runs`, `pipeline_runs`.
- Vector metadata: `embedding_models`, `embedding_jobs`.
- Reports: `reports`, `eval_metrics`, `eval_samples`.
- Security placeholders: `consent_ledger`, `policy_events`, `release_gates`.
- Migrations: `schema_migrations`.

Table structure baseline:

| table | primary key | required columns | important constraints / indexes | owner migration |
|-------|-------------|------------------|----------------------------------|-----------------|
| `schema_migrations` | `version` | `version`, `name`, `applied_at`, `checksum` | `version` monotonic; migration runner rejects checksum drift | DB-001 |
| `speakers` | `id` | `id`, `display_name`, `role`, `created_at`, `metadata_json` | `role IN ('owner','other','unknown')`; no auth enforcement before P7 | DB-001 |
| `recordings` | `id` | `id`, `source_uri`, `sha256`, `duration_sec`, `sample_rate`, `channels`, `status`, `metadata_json`, `created_at` | `sha256 UNIQUE`; index `status, created_at` | DB-001 |
| `segments` | `id` | `id`, `recording_id`, `speaker_id`, `start_sec`, `end_sec`, `audio_artifact_id`, `cleaned_artifact_id`, `transcript`, `status`, `quality_score`, `speaker_score`, `noise_score`, `overlap_score`, `metadata_json`, `created_at` | FK recording/speaker/artifacts; `end_sec > start_sec`; index `recording_id,start_sec`; index `status,quality_score` | DB-001 |
| `segment_reviews` | `id` | `id`, `segment_id`, `status_from`, `status_to`, `reason`, `reviewer`, `created_at` | append-only; FK segment | DB-002 |
| `datasets` | `id` | `id`, `name`, `status`, `manifest_artifact_id`, `manifest_sha256`, `filter_json`, `created_at`, `frozen_at` | `status IN ('draft','frozen','training','evaluated','rejected','release_candidate')`; frozen dataset immutable | DB-001 |
| `dataset_segments` | `dataset_id, segment_id` | `dataset_id`, `segment_id`, `split`, `created_at` | composite PK; `split IN ('train','val','test')`; no same recording leakage across split | DB-001 |
| `jobs` | `id` | `id`, `type`, `subject_type`, `subject_id`, `status`, `pipeline`, `params_json`, `requested_by`, `created_at`, `started_at`, `finished_at`, `error` | `status IN ('queued','running','succeeded','failed','canceled')`; index `status,type,created_at` | DB-002 |
| `job_events` | `id` | `id`, `job_id`, `event_type`, `level`, `message`, `payload_json`, `created_at` | append-only; index `job_id,created_at`; text logs also artifact-backed | DB-002 |
| `artifacts` | `id` | `id`, `kind`, `uri`, `sha256`, `bytes`, `source_artifact_id`, `created_by_job_id`, `pipeline_version`, `params_json`, `metadata_json`, `created_at` | FK self/job; index `created_by_job_id,kind`; audio/checkpoint/report/rendered outputs all use this table; P7 synthetic/watermark placeholders live in `metadata_json` | DB-002 |
| `pipeline_runs` | `id` | `id`, `pipeline_name`, `subject_type`, `subject_id`, `status`, `config_json`, `created_at`, `finished_at` | groups multiple jobs into one workflow trace | DB-002 |
| `model_runs` | `id` | `id`, `model_family`, `dataset_id`, `status`, `config_json`, `checkpoint_artifact_id`, `env_digest`, `git_commit`, `created_at`, `finished_at` | FK dataset/checkpoint; index `dataset_id,model_family,status` | DB-002 |
| `embedding_models` | `id` | `id`, `namespace`, `model_name`, `dimension`, `distance`, `version`, `created_at` | one namespace cannot mix dimensions | DB-003 |
| `embedding_jobs` | `id` | `id`, `namespace`, `subject_type`, `subject_id`, `embedding_model_id`, `status`, `created_at` | vector row must reference a completed embedding job in metadata | DB-003 |
| `reports` | `id` | `id`, `kind`, `subject_type`, `subject_id`, `artifact_id`, `status`, `summary_json`, `created_at` | `kind IN ('corpus_audit','baseline_eval','train_report','objective_eval','subjective_eval','release_gate')` | DB-004 |
| `eval_metrics` | `id` | `id`, `run_id`, `report_id`, `metric_name`, `metric_value`, `metric_json`, `created_at` | index `run_id,metric_name`; per-sample detail goes into artifact/report JSON | DB-004 |
| `eval_samples` | `id` | `id`, `report_id`, `input_artifact_id`, `output_artifact_id`, `reference_artifact_id`, `scores_json`, `created_at` | connects rendered audio to metrics and references | DB-004 |
| `consent_ledger` | `id` | `id`, `speaker_id`, `scope`, `status`, `evidence_uri`, `created_at`, `revoked_at` | P1 creates table; P7 turns policy checks on | DB-005 |
| `policy_events` | `id` | `id`, `subject_type`, `subject_id`, `policy_name`, `decision`, `reason`, `payload_json`, `created_at` | append-only release/policy audit | DB-005 |
| `release_gates` | `id` | `id`, `model_run_id`, `status`, `report_id`, `decision_json`, `created_at`, `decided_at` | `status IN ('pending','passed','failed','waived')`; only P7+ enforced | DB-005 |

Required virtual tables:

- `segment_audio_embeddings USING vec0(segment_id TEXT PRIMARY KEY, embedding FLOAT[768])`
- `speaker_embeddings USING vec0(speaker_id TEXT PRIMARY KEY, embedding FLOAT[192])`
- `transcript_embeddings USING vec0(segment_id TEXT PRIMARY KEY, embedding FLOAT[384])`

Indexes:

- `recordings(sha256)`
- `segments(recording_id, start_sec)`
- `segments(status, quality_score)`
- `jobs(status, type, created_at)`
- `artifacts(created_by_job_id, kind)`
- `model_runs(dataset_id, model_family, status)`
- `eval_metrics(run_id, metric_name)`

### 14.4 Status model

```text
recording: new -> ingested -> diarized -> sliced -> cleaned -> transcribed -> scored -> curated -> dataset_ready
segment: new -> needs_review -> keep | drop | fixed
dataset: draft -> frozen -> training -> evaluated -> rejected | release_candidate
job: queued -> running -> succeeded | failed | canceled
model_run: queued -> preparing -> training -> checkpointed -> succeeded | failed | canceled
report: draft -> generated -> archived
release_gate: pending -> passed | failed | waived
```

### 14.5 Logging/reporting rules

- Every business status transition writes one `job_events` row; P7 policy/release decisions additionally write `policy_events`.
- Dataset, model_run, report, segment review and recording transitions must use the same event writer so audit trace can reconstruct the full state path.
- Every file output writes one `artifacts` row before downstream steps can consume it.
- Every report has a stable `report_id`, `kind`, `subject_type`, `subject_id`, `artifact_id`, `summary_json`.
- Text logs are files under `data/artifacts/jobs/{job_id}/`; DB stores URI, sha256, and event summaries.
- Reports are generated as JSON + Markdown by default; HTML optional.

---

## 15. 接口设计详细安排

### 15.1 HTTP routes

| Method | Path | Handler work item | Request | Response |
|--------|------|-------------------|---------|----------|
| `POST` | `/recordings` | MVC-P6-02 | `{source_uri, metadata}` | `{recording_id, status}` |
| `GET` | `/recordings/{id}` | MVC-P6-02 | path | recording detail + artifacts |
| `POST` | `/jobs` | MVC-P6-02 | `{type, subject_id, params}` | `{job_id, status}` |
| `GET` | `/jobs/{id}` | MVC-P6-02 | path | job + events + artifacts |
| `GET` | `/segments` | MVC-P6-02 | filters | paged segments |
| `PATCH` | `/segments/{id}` | MVC-P6-02 | `{status, reason}` | updated segment |
| `POST` | `/datasets` | MVC-P6-02 | `{name, filters}` | dataset draft |
| `POST` | `/datasets/{id}/freeze` | MVC-P6-02 | path | manifest artifact |
| `GET` | `/datasets/{id}` | MVC-P6-02 | path | dataset + manifest |
| `POST` | `/runs/train` | MVC-P6-02 | `{model_family, dataset_id, config}` | `{run_id, job_id}` |
| `GET` | `/runs/{id}` | MVC-P6-02 | path | model run detail |
| `POST` | `/runs/eval` | MVC-P6-02 | `{run_id, suite}` | `{job_id}` |
| `GET` | `/reports/{id}` | MVC-P6-06 | path | report detail |
| `POST` | `/inference/vc` | MVC-P6-04 | `{model_id, input_uri, params}` | `{job_id}` |
| `POST` | `/inference/tts` | MVC-P6-04 | `{model_id, text, params}` | `{job_id}` |
| `GET` | `/audit/{subject_type}/{subject_id}` | MVC-P6-07 | path | state/event/artifact trace |

### 15.2 CLI commands

```bash
mvc init-db --db db/myvoiceclone.sqlite
mvc vec health
mvc ingest PATH
mvc run diarize RECORDING_ID
mvc run slice RECORDING_ID
mvc run clean RECORDING_ID
mvc run transcribe RECORDING_ID
mvc run score RECORDING_ID
mvc curate list --status needs_review
mvc curate mark SEGMENT_ID --status keep --reason "clean target speaker"
mvc dataset create first-build --filter keep
mvc dataset freeze first-build
mvc train rvc --dataset first-build --profile quick
mvc train sovits --dataset first-build --profile long
mvc eval RUN_ID --suite default
mvc infer vc --model MODEL_ID --input PATH --out PATH
mvc report show REPORT_ID
mvc audit recording RECORDING_ID
```

### 15.3 Job payload contract

```json
{
  "type": "clean",
  "subject_type": "recording",
  "subject_id": "rec_001",
  "pipeline": "preprocess.default",
  "params": {
    "adapter": "demucs",
    "device": "auto"
  },
  "requested_by": "local"
}
```

Rules:

- API returns quickly after creating job.
- Runner updates `jobs.status` and appends `job_events`.
- Long train is cancellable by status flag checked between steps/checkpoints.
- FastAPI `BackgroundTasks` may only enqueue lightweight dispatch; not execute training.

---

## 16. 交叉引用与修订历史

- **交叉引用**：
  - `myvoiceclone/initial-thoughts.md`
  - `myvoiceclone/docs/eval/first-build/proposed-planning.md`
  - `00-templates/eval-planning.md`
  - sqlite-vec: https://github.com/asg017/sqlite-vec
  - sqlite-vec Python: https://alexgarcia.xyz/sqlite-vec/python.html
  - SQLite vec1: https://sqlite.org/vec1
  - SQLite WAL: https://sqlite.org/wal.html
  - SQLite foreign keys: https://sqlite.org/foreignkeys.html
  - SQLite JSON: https://sqlite.org/json1.html
  - FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
  - FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
  - pytest tmp_path: https://docs.pytest.org/en/stable/how-to/tmp_path.html
  - Typer testing: https://typer.tiangolo.com/tutorial/testing/
  - pyannote.audio: https://github.com/pyannote/pyannote-audio
  - Demucs: https://github.com/facebookresearch/demucs
  - Whisper: https://github.com/openai/whisper
  - Python logging cookbook: https://docs.python.org/3/howto/logging-cookbook.html
  - MLflow tracking: https://mlflow.org/docs/latest/ml/tracking/
  - DVC start: https://doc.dvc.org/start

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v1.0 | 2026-06-13 | Codex | final execution baseline；细化 phase、DB/插件、接口、抽象层、状态日志报告、文件定位、unit tests |
