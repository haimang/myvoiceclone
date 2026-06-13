# myvoiceclone after first-build · first-test 状态分析

> **对象**：`after first-build（P0-P8）→ first-test readiness`
> **日期**：`2026-06-13`
> **作者**：`GPT / Codex`（panel：`main + sub-agents: storage-observability, pipeline-adapters, cli-api-ops`）
> **文档性质**：`eval / state-analysis + gap-study`（本文是现状快照 + 真实测试缺口研究；不是 closure / verdict / charter）
> **文档状态**：`snapshot`
> **对照基线**：`docs/code-review/first-build/P0-P8-2nd-review-VF-ledger.md`、`docs/closure/first-build/deferred-items-ledger.md`
> **上游权威输入**：
> - `docs/eval/first-build/final-execution-plan.md`
> - `docs/code-review/first-build/P0-P8-review-VF-ledger.md`
> - `docs/code-review/first-build/P0-P8-2nd-review-VF-ledger.md`
> - `docs/closure/first-build/deferred-items-ledger.md`
> - `src/myvoiceclone/**`、`db/migrations/**`、`tests/**`、`infra/docker/**`、`configs/**`
> **下游消费者**：`first-test owner decision / next charter`

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：当前项目已经可以支持 `mock e2e` 和一轮受控的 `真实预处理 smoke`，但还不能支持“真实音频 → 真实训练 → 真实推理 → 真实评估”的完整真实 e2e。
- **核心结论**：第一轮真实测试可以开，但必须重新定义边界：建议第一轮只做 `T0 mock capstone 回归` + `T1 真实 FFmpeg/PyAnnote/Demucs/Whisper 预处理 smoke` + `T2 mock train/eval/治理闭环`。不要把真实 SoVITS/RVC/XTTS 训练和真实推理纳入同一轮，因为相关 adapter 在 `MOCK_ADAPTERS=false` 时仍显式 `NotImplementedError`。

**当前是否能支持第一轮真实测试？**

| 测试层级 | 当前支持度 | 裁定 |
|----------|------------|------|
| `mock e2e`（现有 capstone） | `ready` | 可以作为回归基线 |
| 真实音频 ingest/normalize | `mostly-ready` | 需安装 `ffmpeg/ffprobe` 并关闭 mock |
| 真实 diarize/clean/transcribe | `conditional` | 需 `HUGGINGFACE_TOKEN`、Demucs、Whisper 模型/依赖 |
| dataset freeze | `partial` | 能生成 manifest；但缺空数据集 guard，且扫描全局符合条件 segments |
| mock SoVITS/RVC/XTTS train/infer | `ready-for-mock` | 可记录 model_run/artifact/metrics，但产物是假的 |
| 真实 SoVITS/RVC/XTTS train/infer | `not-ready` | adapter 明确未实现 |
| objective/subjective eval | `partial/mock` | 指标硬编码或人工输入函数存在，但不是自动真实评估 |
| 可观测性/审计 | `partial` | DB trace 基础够用；step-level/event/log 仍不足 |

---

## 1. 方法与可采信证据基线

- **方法**：主 agent 读取模板、review/closure/deferred 文档、关键源码；同时使用 3 个 sub-agent 分区核查：
  - `storage-observability`：DB schema、artifact lineage、job events、audit trace。
  - `pipeline-adapters`：真实音频、训练、推理、评估链路。
  - `cli-api-ops`：CLI/API/Docker/config/scripts 入口。
- **可采信证据**：当前 HEAD 文件内容、`file:line` 证据、现有测试结构、二轮 VF/deferred 台账。
- **范围围栏**：不评价模型质量，不假设未实现的真实训练可用；不把 mock 结果解释为真实语音质量。
- **复现入口**：见附录 A。

---

## 2. 回看清单（交付快照）

### 2.1 我们当前有什么

| 单元 | 声称/目标 | 真实落地（代码核） | 评级 | 锚点 |
|------|-----------|--------------------|------|------|
| Python package / CLI | 本地 workbench CLI | console script 是 `myvoiceclone`；`init-db/vec-health/ingest/dataset/train/eval/infer/report/audit` 已定义 | `partial` | `pyproject.toml:27-28`, `src/myvoiceclone/cli.py:40-324` |
| API app | FastAPI 服务 | app factory + routers 已挂载；health endpoint 存在 | `partial` | `src/myvoiceclone/api/app.py:10-28` |
| SQLite schema | P0-P8 schema 骨架 | recordings/speakers/segments/datasets/jobs/events/artifacts/model_runs/reports/eval/security 表存在 | `delivered-for-first-build` | `db/migrations/001_core_schema.sql:10-73`, `db/migrations/002_state_jobs_artifacts.sql:3-69`, `db/migrations/004_reports_metrics.sql:3-33`, `db/migrations/005_security_placeholders.sql:3-30` |
| DB connection | 本地 SQLite + vec | FK、WAL、busy_timeout 开启；尝试加载 sqlite-vec | `partial` | `src/myvoiceclone/storage/sqlite.py:21-37` |
| Artifact store | 文件与 DB artifact 记录 | 写 content、sha256、bytes、artifact_type/kind、parent/job 关联；可取 absolute path | `delivered` | `src/myvoiceclone/storage/artifact_store.py:15-104` |
| Job runner | 同步 job 执行 | 支持 `preprocess_all/ingest/train_sovits` 和若干 step dispatch；写 start/complete/fail/cancel events | `partial` | `src/myvoiceclone/jobs/runner.py:68-123` |
| Real FFmpeg ingest | 真实音频 probe/normalize | `MOCK_ADAPTERS=false` 时检查 ffmpeg/ffprobe 并调用 subprocess | `conditional` | `src/myvoiceclone/adapters/audio/ffmpeg.py:16-22`, `src/myvoiceclone/adapters/audio/ffmpeg.py:37-70`, `src/myvoiceclone/adapters/audio/ffmpeg.py:88-104` |
| Real PyAnnote | 真实 diarization | 有 PyAnnote Pipeline 调用，但依赖 `HUGGINGFACE_TOKEN` 与模型下载 | `conditional` | `src/myvoiceclone/adapters/diarization/pyannote_adapter.py:17-28` |
| Real Demucs | 真实 vocal separation | 调用外部 `demucs` 命令 | `conditional` | `src/myvoiceclone/adapters/separation/demucs_adapter.py:21-43` |
| Real Whisper | 真实 ASR | 调 `whisper.load_model()` 并 transcribe | `conditional` | `src/myvoiceclone/adapters/asr/whisper_adapter.py:16-29` |
| Dataset freeze | manifest artifact | 生成 JSONL manifest、sha256、frozen_at | `partial` | `src/myvoiceclone/pipelines/export_dataset.py:126-145` |
| Mock training | RVC/SoVITS/XTTS mock | mock adapter 可生成 checkpoint/model/sample/metrics/env_digest | `delivered-for-mock` | `src/myvoiceclone/pipelines/train.py:331-437` |
| Real training | RVC/SoVITS/XTTS | 真实路径显式未实现 | `missing` | `src/myvoiceclone/adapters/training/rvc_adapter.py:19-32`, `src/myvoiceclone/adapters/training/sovits_adapter.py:27-48`, `src/myvoiceclone/adapters/training/xtts_adapter.py:17-18` |
| Eval | objective/subjective skeleton | objective metrics 是 mock；subjective report 需人工传入 MOS/ABX | `partial/mock` | `src/myvoiceclone/eval/objective.py:43-80`, `src/myvoiceclone/eval/subjective.py:8-80` |
| Audit trace | API trace endpoint | 按 recording/dataset/job/run/report 聚合部分 DB 记录 | `partial` | `src/myvoiceclone/api/routes_reports.py:190-284` |
| Docker ops | preprocess/train containers | volumes 指向 `/mnt/usb/workspace/myvoiceresearch`；默认仍 `MOCK_ADAPTERS=true` | `partial` | `infra/docker/compose.yaml:25-66` |

### 2.2 我们为真实 e2e 测试进行了哪些准备

| 准备项 | 当前状态 | 价值 | 仍缺 |
|--------|----------|------|------|
| 外部数据目录隔离 | compose 使用 `/mnt/usb/workspace/myvoiceresearch/{db,data,models}` | 避免大文件进入 repo | 本地 CLI 默认 config 仍是 `db/`, `data/`, `models`，需测试时显式 env |
| env-aware resolver | `DB_PATH/ARTIFACT_ROOT/MODELS_DIR` 已被 `config.py` 消费 | 可把 DB/artifacts/models 切到 USB 目录 | `.env.example` 仍写 `DATABASE_URL`，与代码不一致 |
| 真实音频 adapter 入口 | FFmpeg/PyAnnote/Demucs/Whisper 有真实分支 | 可做真实预处理 smoke | 依赖、token、模型缓存、GPU 未自动检测 |
| DB event/artifact lineage | jobs/job_events/artifacts/model_runs/eval_metrics 等表存在 | 能记录基本流转、产物、指标 | step-level event、stderr、模型版本、耗时缺失 |
| 现有 mock capstone | integration test 覆盖 ingest→preprocess→dataset→train→gate→audit | 可作为 first-test 前回归基线 | 不是 live test；默认不跑 `live/gpu/slow` |
| release gate skeleton | consent/policy/release tables + API | 可以做治理占位验证 | audit trace 不汇总 policy_events/release_gates |

### 2.3 Deferred / Carried-over 台账

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|------|------|--------------|----------------|--------|
| D-01 | 真实 SoVITS/RVC/XTTS training/inference | adapter 明确未实现；first-build 只交付 mock lifecycle | 要跑真实训练/真实推理 | training-phase |
| D-02 | 真实 embedding 与 vec0 维度 | 当前 embedder 全 128-d mock；vec0 表也是 128 | 接入真实 speaker/audio/text embedder | second-build |
| D-03 | 真实 scoring / objective eval | quality/noise/speaker_similarity/wer 多处为固定或 mock | 要发布真实客观指标 | training/eval phase |
| D-04 | API response envelope | 会破坏现有 API 响应形状 | 前端或外部 API consumer contract freeze | api-contract-pass |
| D-05 | pipeline_runs / recording 级进度 | 表存在但生产写入未接入 | 需要 audit UI、resume UI、多步 workflow 可视化 | second-build |
| D-06 | policies 分层下沉 | 当前可工作但 domain 直接 SQL/config | security hardening | security-hardening |
| D-07 | live/gpu/slow 测试 | 真实 live adapter/GPU path 尚未接入测试 | live adapter 或 GPU training path 接入 | second-build |

---

## 3. 对账诚实

| 声称/直觉 | 真实 | 偏差类型 | 证据 | 影响 |
|-----------|------|----------|------|------|
| “first-build e2e 已完成，因此可以跑真实 e2e” | 现有 capstone 是 mock journey，训练注释明确 fake | `over-claim` | `tests/integration/test_first_build_journey.py:15-87` | 真实训练/推理会失败或只产生假产物 |
| “Live GPU Mode 可按 docs 使用” | `bootstrap_env.sh` 只 `pip install -e .`，未安装 extras；模型下载脚本仍 placeholder | `frozen≠done` | `scripts/bootstrap_env.sh:16-20`, `scripts/download_models.sh:16-19` | 真实依赖和权重不会就绪 |
| “README 的 `mvc` 命令可用” | pyproject 只暴露 `myvoiceclone` entry point | `docs drift` | `README.md:17-55`, `pyproject.toml:27-28` | 测试操作者按 README 会直接找不到命令 |
| “`myvoiceclone run diarize RECORDING_ID` 可跑 preprocess” | CLI 创建 `preprocess_all` 但 payload 是 `recording_id`；runner 要求 `filepath` | `runtime gap` | `src/myvoiceclone/cli.py:92-95`, `src/myvoiceclone/jobs/runner.py:132-136` | 按该入口真实测试会失败 |
| “API create recording 会跑完整预处理” | `POST /api/recordings` 只创建 ingest job | `under-delivery` | `src/myvoiceclone/api/routes_recordings.py:26-35` | 真实完整 preprocess 需手工插 `preprocess_all` job 或补入口 |
| “Dataset freeze 表示数据集有效” | 空 rows 也会生成空 manifest 并 frozen | `fake-zero` | `src/myvoiceclone/pipelines/export_dataset.py:46-64`, `src/myvoiceclone/pipelines/export_dataset.py:126-145` | 真实测试可能得到空数据集但状态成功 |
| “preprocess job completed 代表每步都成功” | `clean`/`transcribe` 捕获 segment-level 异常并标 failed，不一定抛给 runner | `observability gap` | `src/myvoiceclone/pipelines/clean.py:63-66`, `src/myvoiceclone/pipelines/transcribe.py:67-69`, `src/myvoiceclone/jobs/runner.py:103-106` | job success 可能掩盖部分 step 失败 |
| “Audit trace 足够完整” | trace 不汇总 `policy_events/release_gates`，没有 step-level stderr/model version | `partial observability` | `src/myvoiceclone/api/routes_reports.py:190-284` | release/waive/consent 和长流程排障链断开 |
| “Docker 可做真实训练” | compose 默认 `MOCK_ADAPTERS=true`；train service 只跑 CLI，真实 SoVITS adapter 未实现 | `placeholder` | `infra/docker/compose.yaml:52-66`, `src/myvoiceclone/adapters/training/sovits_adapter.py:27-48` | Docker 只能做 mock/CLI smoke |

- **诚实结论**：当前状态是“工程骨架可跑 + 部分真实预处理可探针”，不是“真实 voice clone 系统”。第一轮真实测试必须以发现真实链路断点为目标，而不是以验证音色质量为目标。

---

## 4. 分区状态分析

### 4.1 Storage / Schema / Observability

**当前能力**

- schema 足够记录 first-test 的基本对象：recordings、segments、datasets、jobs、job_events、artifacts、model_runs、reports/eval/security。
- artifacts 有 `sha256/bytes/metadata/job/parent`，能追文件产物 lineage。
- model_runs 已可记录 `model_family/checkpoint_artifact_id/env_digest/git_commit/finished_at`。
- SQLite 打开 WAL 与 busy_timeout，适合本地单机顺序测试。

**不足**

- `pipeline_runs` 表仍未被生产路径使用。
- `job_events` 只有 job start/complete/fail/cancel，缺 preprocess 每一步事件。
- audit trace 不包含 `policy_events` 和 `release_gates`。
- 没有 request_id/correlation_id、结构化日志、stderr 捕获、资源/GPU 指标。
- 状态 CHECK 仍保留兼容值；适合 first-build 迁移，但不是收紧后的生产状态机。

**数据库是否足够支持测试/日志记录？**

足够支持第一轮 `mock e2e` 和 `真实预处理 smoke` 的结果记录；不足以支持可诊断的真实长训测试。真实长训前至少需要补 step-level job_events、adapter/model metadata、stderr/耗时记录、policy/release trace 汇总。

### 4.2 Pipeline / Adapter / Model

**当前能力**

- `FFmpegAdapter`、`PyannoteAdapter`、`DemucsAdapter`、`WhisperAdapter` 有真实分支。
- ingest/diarize/slice/clean/transcribe/score 可把 recording/segment/artifact/score 写入 DB。
- SoVITS mock training 可以制造 feature cache、checkpoint、loss metrics、registry artifact、rendered sample 和 env digest。

**不足**

- RVC、SoVITS、XTTS 真实训练/转换/合成均未实现。
- embedder 全是 deterministic 128-d mock。
- scoring 是固定 mock 值。
- objective eval 是 mock metrics；subjective eval 是人工分数报告函数，不是测试采集系统。
- dataset freeze 不拒绝空 manifest，也不严格使用 dataset create 时绑定的 dataset_segments。

### 4.3 CLI / API / Docker / Ops

**当前能力**

- `myvoiceclone` CLI entry point 可用。
- FastAPI app 可启动；routers 已挂载。
- Docker compose volumes 已指向外部 USB 数据根。
- pyproject extras 已声明 API/CLI/DB/audio/preprocess/test 依赖。

**不足**

- docs 仍多处写 `mvc`，与 `myvoiceclone` entry point 不一致。
- `bootstrap_env.sh` 不安装 extras，不适合真实测试。
- `.env.example` 写 `DATABASE_URL`，但代码读 `DB_PATH`。
- compose 默认 `MOCK_ADAPTERS=true`，没有 API service。
- `run diarize` CLI 入口 payload 错误，不适合作为真实 preprocess 入口。
- API 没有一等 `preprocess_all` job creation endpoint；需要手工插 job 或先补入口。

---

## 5. 真实测试预期会碰到的问题

| 编号 | 问题 / 断点 | 严重度 | 证据 | 影响 |
|------|-------------|--------|------|------|
| B1 | 真实训练/推理 adapter 未实现 | `blocker` | `src/myvoiceclone/adapters/training/sovits_adapter.py:27-48`, `src/myvoiceclone/adapters/training/rvc_adapter.py:19-32`, `src/myvoiceclone/adapters/training/xtts_adapter.py:17-18` | 完整真实 e2e 无法跑通 |
| B2 | 真实依赖未由 bootstrap 安装 | `blocker` | `scripts/bootstrap_env.sh:16-20`, `pyproject.toml:15-21` | 按脚本装环境会缺 Typer/FastAPI/sqlite-vec/音频依赖 |
| B3 | 文档命令名错误 | `high` | `README.md:17-55`, `pyproject.toml:27-28` | 测试执行者按文档无法启动 |
| B4 | `run diarize` 入口实际不能跑完整 preprocess | `high` | `src/myvoiceclone/cli.py:92-95`, `src/myvoiceclone/jobs/runner.py:132-136` | 真实 preprocess 需绕开 CLI 或先修入口 |
| B5 | API 没有创建 `preprocess_all` 的一等入口 | `high` | `src/myvoiceclone/api/routes_recordings.py:26-35`, `src/myvoiceclone/api/routes_jobs.py:26-46` | 真实完整预处理需手工插 DB job |
| B6 | Dataset freeze 可能产出空 manifest 但仍成功 | `high` | `src/myvoiceclone/pipelines/export_dataset.py:46-64`, `src/myvoiceclone/pipelines/export_dataset.py:126-145` | 测试会误判为 dataset ready |
| B7 | step-level observability 不足 | `high` | `src/myvoiceclone/jobs/runner.py:138-163`, `src/myvoiceclone/jobs/events.py:5-20` | 真实失败难定位 |
| B8 | clean/transcribe segment failure 可能不让 job failed | `medium` | `src/myvoiceclone/pipelines/clean.py:63-66`, `src/myvoiceclone/pipelines/transcribe.py:67-69` | job completed 不能等于所有 segment succeeded |
| B9 | audit trace 不含 policy/release gate | `medium` | `src/myvoiceclone/api/routes_reports.py:190-284` | 治理链路测试记录不完整 |
| B10 | sqlite-vec 失败只 warning | `medium` | `src/myvoiceclone/storage/sqlite.py:8-19` | vec-health 外的真实流程可能晚失败 |
| B11 | compose 默认 mock | `medium` | `infra/docker/compose.yaml:35-40`, `infra/docker/compose.yaml:52-56` | Docker run 不等于真实测试 |
| B12 | `.env.example` 配置键漂移 | `low` | `.env.example:2`, `src/myvoiceclone/config.py:49-52` | 环境变量配置易错 |

---

## 6. 应该如何进行第一轮真实测试

### 6.1 建议测试分层

| 层级 | 名称 | 目标 | 是否现在可跑 | 成功判据 |
|------|------|------|--------------|----------|
| T0 | Mock capstone regression | 确认 first-build 骨架未坏 | `yes` | pytest integration/API/CLI 绿 |
| T1 | Real ingest smoke | 真实 WAV → FFmpeg probe/normalize → recording/artifacts | `yes, with env` | DB 有 recording，raw/staging artifacts 存在 |
| T2 | Real preprocess smoke | FFmpeg + PyAnnote + Demucs + Whisper + mock score | `conditional` | 非空 segments，存在 cleaned/transcript artifacts，失败能被记录 |
| T3 | Dataset freeze sanity | 从真实预处理产物创建非空 manifest | `conditional` | manifest 非空、dataset_segments 非空、frozen_at 存在 |
| T4 | Mock train/eval/gate continuation | 用真实 preprocess 产出的 dataset 接 mock SoVITS/eval/release gate | `yes` | model_run/artifacts/eval_metrics/release_gate/audit trace 存在 |
| T5 | Full real train/infer/eval | 真实 SoVITS/RVC/XTTS + 真指标 | `no` | 等 adapter 实现后再定义 |

### 6.2 first-test 前置条件

**必须完成或确认**

1. 安装环境必须使用 extras，而不是现有 bootstrap 默认：
   ```bash
   ./venv/bin/pip install -e '.[cli,api,db,audio,preprocess,test]'
   ```
2. 固定外部数据路径：
   ```bash
   export DB_PATH=/mnt/usb/workspace/myvoiceresearch/db/first-test.sqlite
   export ARTIFACT_ROOT=/mnt/usb/workspace/myvoiceresearch/data/artifacts
   export MODELS_DIR=/mnt/usb/workspace/myvoiceresearch/models
   ```
3. 明确 mock 开关：
   - T0/T4：`MOCK_ADAPTERS=true`
   - T1/T2/T3：`MOCK_ADAPTERS=false`
4. 准备真实音频输入：
   - WAV/FLAC/MP3 均可先经 FFmpeg 验证；建议第一轮使用 1-3 条短 WAV，每条 30-120 秒。
5. 准备外部依赖：
   - `ffmpeg` / `ffprobe`
   - `demucs`
   - `openai-whisper` 模型可下载或已缓存
   - `pyannote.audio` 与有效 `HUGGINGFACE_TOKEN`
   - 可选 CUDA；没有 CUDA 也可做小样本 smoke，但会慢。
6. 先单测外部依赖：
   ```bash
   ffmpeg -version
   ffprobe -version
   demucs --help
   ./venv/bin/python -c "import whisper; print('whisper ok')"
   ./venv/bin/python -c "from pyannote.audio import Pipeline; print('pyannote ok')"
   ```

**建议先补的最小代码/文档前置**

| 优先级 | 前置项 | 原因 |
|--------|--------|------|
| P0 | 修 README/ops/scripts 中 `mvc` → `myvoiceclone` 或增加 `mvc` alias | 避免测试命令第一步失败 |
| P0 | 修 `bootstrap_env.sh` 安装 extras，或新增 `bootstrap_live_env.sh` | 真实依赖不会自动安装 |
| P0 | 增加 `preprocess_all` CLI/API 一等入口，或修 `run diarize` payload | 当前完整真实预处理需手工插 DB |
| P0 | dataset freeze 空 manifest guard | 防止假成功 |
| P1 | 每个 preprocess step 写 `job_events` | first-test 需要定位失败 |
| P1 | audit trace 纳入 `policy_events/release_gates` | 治理测试记录完整性 |

### 6.3 推荐执行流程

**T0：回归基线**

```bash
cd /mnt/usb/workspace/myvoiceclone
./venv/bin/python -m pytest -q
./venv/bin/python -m pytest -m api -q
./venv/bin/python -m pytest -m cli -q
```

**T1：真实 ingest smoke**

```bash
export DB_PATH=/mnt/usb/workspace/myvoiceresearch/db/first-test.sqlite
export ARTIFACT_ROOT=/mnt/usb/workspace/myvoiceresearch/data/artifacts
export MODELS_DIR=/mnt/usb/workspace/myvoiceresearch/models
export MOCK_ADAPTERS=false

./venv/bin/myvoiceclone init-db
./venv/bin/myvoiceclone ingest /abs/path/to/real.wav
```

**T2：真实完整预处理 smoke（当前需要手工插 job）**

```bash
export HUGGINGFACE_TOKEN=...
./venv/bin/uvicorn 'myvoiceclone.api.app:create_app' --factory --host 127.0.0.1 --port 8000

sqlite3 "$DB_PATH" \
  "INSERT INTO jobs (id,name,status,payload_json)
   VALUES ('job_real_preprocess_001','preprocess_all','pending',
   '{\"filepath\":\"/abs/path/to/real.wav\",\"min_quality_score\":0.6}');"

curl -X POST http://127.0.0.1:8000/api/jobs/job_real_preprocess_001/run
curl 'http://127.0.0.1:8000/api/audit/trace?subject_id=job_real_preprocess_001&subject_type=job'
```

**T3/T4：freeze + mock train continuation**

```bash
export MOCK_ADAPTERS=true
./venv/bin/myvoiceclone dataset create first-test --filter-status keep
./venv/bin/myvoiceclone dataset freeze first-test
./venv/bin/myvoiceclone train sovits first-test long
```

> 注：现有 CLI 参数是 Typer 位置参数，不是 README 中的 `--dataset` 形式；正式 first-test 前应先用 `myvoiceclone train sovits --help` 确认当前命令签名。

---

## 7. 测试记录与可观测性

### 7.1 应如何记录测试

建议每次 first-test 创建一个 run folder，不把大文件放入 repo：

```text
/mnt/usb/workspace/myvoiceresearch/test-runs/YYYYMMDD-HHMM-first-test/
  env.txt
  commands.sh
  stdout.log
  stderr.log
  db-dump-summary.sql.txt
  artifacts-manifest.txt
  observations.md
```

**每次测试至少记录**

| 类别 | 记录内容 | 获取方式 |
|------|----------|----------|
| 环境 | git SHA、Python、CUDA、torch、ffmpeg、demucs、whisper、pyannote、env vars | `env.txt` + commands |
| 输入 | 音频文件路径、时长、sha256、许可/consent 说明 | `sha256sum` + manual note |
| DB | jobs/job_events/recordings/segments/artifacts/datasets/model_runs/eval_metrics/release_gates 快照 | sqlite 查询 |
| 产物 | artifact root 下新增文件列表、bytes、sha256 | DB artifacts + filesystem |
| 失败 | command exit code、stderr、job.error_msg、segment failed 状态 | logs + DB |
| 人工观察 | 是否有空 manifest、异常耗时、模型下载失败、质量主观备注 | `observations.md` |

### 7.2 当前是否具备足够可观测性

| 观察维度 | 当前能力 | 是否足够 | 说明 |
|----------|----------|----------|------|
| job 生命周期 | start/complete/fail/cancel event | `partial` | 没有 step-level event |
| artifact lineage | parent/job/sha/bytes/metadata | `yes-for-smoke` | 足够验证文件产物 |
| recording/segment 状态 | status + metadata_json | `partial` | recording 级进度不完整 |
| eval metrics | eval_metrics 表 | `partial/mock` | 指标多为 fake |
| audit trace | API trace endpoint | `partial` | 不含 policy/release gate |
| external stderr | 无结构化捕获 | `no` | 真实依赖失败时诊断弱 |
| long-train observability | loss/checkpoint mock | `no-for-real` | 真实训练不存在 |
| resource/GPU metrics | 无 | `no` | 真实 GPU 测试前需补或外部记录 |

**结论**：足够支撑 first-test 的 smoke 记录；不足以支撑真实长训排障。第一轮真实测试如果马上开跑，必须把 stdout/stderr 和外部命令版本手工记录到 run folder。

---

## 8. Schema 对测试/日志记录的支持度

| 需求 | 当前 schema 支持 | 缺口 |
|------|------------------|------|
| 记录输入音频 | `recordings` + raw/staging artifacts | consent 与 source provenance 仍偏弱 |
| 记录 preprocess 产物 | `segments` + artifacts + metadata_json | step-level status/event 不完整 |
| 记录人工 review | `segment_reviews` | 足够 first-test |
| 记录 dataset freeze | `datasets`, `dataset_segments`, manifest artifact | 空 manifest guard 缺失；freeze 扫全局 segments |
| 记录训练 run | `model_runs`, checkpoints artifacts, `eval_metrics` | 真实训练字段够，但 adapter 未实现 |
| 记录模型环境 | `env_digest`, `git_commit` | 仅 mock train 写入；真实 adapter 参数未规范 |
| 记录 release gate | `release_gates`, `policy_events` | audit trace 未汇总；domain policies 仍直接 SQL |
| 记录 vector embedding | `embedding_jobs`, vec tables | 维度仍 mock 128；真实 embedding 不适配 |
| 并发写测试 | WAL/busy_timeout | 无并发测试 |

**schema 结论**：表结构“够记录 first-test 的主体对象”，但日志语义不够细。真实测试前不必大改 schema，但应补最小写入策略：step events、adapter metadata、empty manifest guard、policy/release trace。

---

## 9. Gap Study：真实 first-test 缺口台账

| 编号 | 缺口 / 断点 | 严重度 | 证据（file:line） | 影响 |
|------|-------------|--------|-------------------|------|
| G1 | 真实 SoVITS/RVC/XTTS 未实现 | `blocker` | `src/myvoiceclone/adapters/training/sovits_adapter.py:27-48`, `src/myvoiceclone/adapters/training/rvc_adapter.py:19-32`, `src/myvoiceclone/adapters/training/xtts_adapter.py:17-18` | 完整真实 e2e 无法跑 |
| G2 | bootstrap 不装 extras | `blocker` | `scripts/bootstrap_env.sh:16-20`, `pyproject.toml:15-21` | 真实测试环境不完整 |
| G3 | README/ops 命令与 entry point 漂移 | `high` | `README.md:17-55`, `pyproject.toml:27-28` | 操作者按文档失败 |
| G4 | 完整 preprocess 无一等可用入口 | `high` | `src/myvoiceclone/cli.py:92-95`, `src/myvoiceclone/jobs/runner.py:132-136`, `src/myvoiceclone/api/routes_recordings.py:26-35` | 需手工插 DB job |
| G5 | Dataset freeze 可空成功 | `high` | `src/myvoiceclone/pipelines/export_dataset.py:46-64`, `src/myvoiceclone/pipelines/export_dataset.py:126-145` | 假 ready |
| G6 | Step-level observability 不足 | `high` | `src/myvoiceclone/jobs/runner.py:138-163`, `src/myvoiceclone/jobs/events.py:5-20` | 真实失败难定位 |
| G7 | clean/transcribe 局部失败不一定使 job failed | `medium` | `src/myvoiceclone/pipelines/clean.py:63-66`, `src/myvoiceclone/pipelines/transcribe.py:67-69` | completed 状态可信度下降 |
| G8 | API job runner 使用 config 旧读取 | `medium` | `src/myvoiceclone/api/routes_jobs.py:33-34` | API run job 可能不尊重 `ARTIFACT_ROOT` env |
| G9 | `.env.example` 键漂移 | `low` | `.env.example:2`, `src/myvoiceclone/config.py:49-52` | 配置易错 |
| G10 | Audit trace 不含 policy/release | `medium` | `src/myvoiceclone/api/routes_reports.py:190-284` | 治理记录不完整 |

### 9.1 优先级建造建议

| 优先级 | 建造项 | 对应缺口 | 工作量 | 依赖 |
|--------|--------|----------|--------|------|
| P0 | 修文档/脚本命令名与 extras 安装 | G2,G3,G9 | S | 无 |
| P0 | 增加 `preprocess_all` CLI/API 入口并修 `run diarize` | G4 | S/M | 现有 JobRunner |
| P0 | dataset freeze 空 manifest guard | G5 | S | 现有 tests |
| P0 | API job runner 使用 `resolve_artifact_root()` | G8 | S | 无 |
| P1 | 每个 preprocess step 写 job_events + duration/error metadata | G6,G7 | M | job_events |
| P1 | audit trace 汇总 policy_events/release_gates | G10 | M | routes_reports |
| P2 | 真实 training adapter integration plan | G1 | L | 模型/权重/脚本选择 |

---

## 10. Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值 | `B` | mock workbench 生命周期完整，足以做工程回归和 smoke |
| 累积债务 | `C` | 真实训练、真实 eval、observability 和文档入口仍有明显债务 |
| 愿景/目标达成度 | `C+` | first-build 骨架达成；真实 voice clone 目标尚未达成 |
| **综合健康** | `C+/B-` | 可以进入受限 first-test，但不能宣称 ready for full real e2e |

- **反镀金提醒**：不要先补大而全监控平台；第一轮真实测试前只补能阻断误判和定位失败的最小观测：step event、empty guard、正确入口、正确 env。

---

## 11. 前瞻交接

- **下一周期建议**：先开一个 `first-test-preflight` 小批次，修 P0 前置后跑 `T0-T4`；把完整真实训练拆到后续 `training-phase`。
- **start-gate 前置（first-test day-1 必须满足）**：
  1. 明确 first-test 范围：`real preprocess smoke + mock train continuation`。
  2. 修或绕开 `mvc`/`myvoiceclone` 文档漂移。
  3. 用 extras 安装环境，确认 ffmpeg/ffprobe/demucs/whisper/pyannote。
  4. 固定 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR` 到 `/mnt/usb/workspace/myvoiceresearch/test-runs/...`。
  5. 准备 1-3 条真实短音频和 consent 记录策略。
  6. 预先定义 SQL 验收查询：非空 recordings、segments、cleaned artifacts、transcripts、manifest、job_events、artifacts。
- **需 owner 拍板的问题**：
  - 第一轮“真实测试”是否接受 `真实预处理 + mock 训练/评估` 的定义？
  - 是否先修 P0 preflight gap，再跑测试？
  - 是否需要在 first-test 中开启 security policy，还是只记录 consent/waive 路径？

---

## 附录

### A. 复现命令

```bash
# Readiness baseline
cd /mnt/usb/workspace/myvoiceclone
./venv/bin/python -m pytest -q
./venv/bin/python -m pytest -m api -q
./venv/bin/python -m pytest -m cli -q

# Install live-capable deps in a clean env
python3 -m venv venv
./venv/bin/pip install -U pip
./venv/bin/pip install -e '.[cli,api,db,audio,preprocess,test]'

# External path setup
export DB_PATH=/mnt/usb/workspace/myvoiceresearch/db/first-test.sqlite
export ARTIFACT_ROOT=/mnt/usb/workspace/myvoiceresearch/data/artifacts
export MODELS_DIR=/mnt/usb/workspace/myvoiceresearch/models

# Mock baseline
export MOCK_ADAPTERS=true
./venv/bin/myvoiceclone init-db

# Real ingest/preprocess smoke
export MOCK_ADAPTERS=false
export HUGGINGFACE_TOKEN=...
ffmpeg -version
ffprobe -version
demucs --help
./venv/bin/python -c "import whisper; print('whisper ok')"
./venv/bin/python -c "from pyannote.audio import Pipeline; print('pyannote ok')"
./venv/bin/myvoiceclone ingest /abs/path/to/real.wav

# API runner path for preprocess_all, until first-class entry exists
./venv/bin/uvicorn 'myvoiceclone.api.app:create_app' --factory --host 127.0.0.1 --port 8000
sqlite3 "$DB_PATH" \
  "INSERT INTO jobs (id,name,status,payload_json)
   VALUES ('job_real_preprocess_001','preprocess_all','pending',
   '{\"filepath\":\"/abs/path/to/real.wav\",\"min_quality_score\":0.6}');"
curl -X POST http://127.0.0.1:8000/api/jobs/job_real_preprocess_001/run
curl 'http://127.0.0.1:8000/api/audit/trace?subject_id=job_real_preprocess_001&subject_type=job'

# Useful SQL checks
sqlite3 "$DB_PATH" "SELECT id,status,error_msg,created_at,updated_at FROM jobs ORDER BY created_at DESC LIMIT 10;"
sqlite3 "$DB_PATH" "SELECT job_id,event_type,status_from,status_to,message,created_at FROM job_events ORDER BY id;"
sqlite3 "$DB_PATH" "SELECT id,source_uri,duration_sec,status,metadata_json FROM recordings;"
sqlite3 "$DB_PATH" "SELECT id,recording_id,status,quality_score,cleaned_artifact_id,transcript FROM segments;"
sqlite3 "$DB_PATH" "SELECT id,name,artifact_type,kind,uri,bytes,sha256,job_id,created_by_job_id FROM artifacts ORDER BY created_at;"
sqlite3 "$DB_PATH" "SELECT id,name,status,manifest_artifact_id,manifest_sha256,frozen_at FROM datasets;"
```

### B. Sub-agent 分区摘要

| 分区 | 结论 |
|------|------|
| storage-observability | schema 足够记录主体对象，但 step-level event、policy/release trace、结构化日志不足 |
| pipeline-adapters | 真实预处理可 smoke；真实训练/推理/eval 不 ready |
| cli-api-ops | CLI/API/Docker 可做 mock 和 smoke；文档命令、extras、preprocess_all 入口、env 示例需修 |

### C. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-13 | GPT / Codex | 初稿：after first-build first-test readiness snapshot |
