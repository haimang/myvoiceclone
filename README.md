# MyVoiceClone：本地高保真声音克隆工作台

> 工程化、可审计、可治理的本地声音克隆研发工具链  
> 当前 HEAD：`9806d7e`（master 分支）

---

## 1. 项目说明

**MyVoiceClone** 是一款面向本地环境的工程化高保真声音克隆工作台。它不是面向终端消费者的 SaaS，而是把“数据准备 → 预处理 → 数据集管理 → 模型训练 → 推理 → 评估 → 发布闸”整条链路串联起来的研发工具，强调：

- **本地优先**：数据、模型、artifact、数据库默认落在本地或外置存储，不强制联网。
- **工程化 / 可审计**：每个操作都会产生 job、artifact、event，支持跨实体的 audit trace。
- **可治理**：通过 consent ledger、release gate、policy events 实现最小化的合规与授权检查。
- **Mock / Real 双模**：Docker 默认使用 `MOCK_ADAPTERS=false` 进入真实推理路径；需要离线开发时可显式设置 `MOCK_ADAPTERS=true` 跑通 mock 流程。

### 1.1 主要功能

| 阶段 | 功能 |
|------|------|
| 音频接入 | 通过 CLI/API 读取本地 WAV/MP3/FLAC/M4A，计算 SHA256，去重，落库 |
| 预处理 | ingest → diarize（说话人分割）→ slice（切片）→ clean（人声分离）→ transcribe（ASR）→ score（质量打分） |
| 数据策展 | 段审阅（keep/drop/needs_review/fixed）、去重、数据集创建与 freeze |
| 训练 | RVC 快速基线、So-VITS-SVC 长训，支持 resume/checkpoint/export |
| 推理 | XTTS-v2 真实推理（参考音频 + 文本生成语音）、RVC voice conversion |
| 评估 | objective proxy（占位）、smoke metrics、subjective MOS/ABX、baseline/train/gate report |
| 治理 | release gate（consent + quality + smoke）、waive 机制、policy events |
| 证据 | first-test evidence pack 收集与校验 |

### 1.2 适用场景

- 本地声音克隆算法研发与快速迭代
- 个人或团队在小规模授权语料上的模型训练实验
- 需要可审计、可追溯、带发布闸的合规研发流程
- 在无 GPU 环境下进行端到端集成测试与 CI

---

## 2. 项目的核心构件

### 2.1 架构分层

| 层 | 路径 | 职责 |
|---|---|---|
| `domain` | `src/myvoiceclone/domain/` | 纯领域模型：entities、states、policies |
| `storage` | `src/myvoiceclone/storage/` | SQLite 连接、迁移、repository、artifact store、向量存储 |
| `adapters` | `src/myvoiceclone/adapters/` | 外部工具/模型封装：FFmpeg、PyAnnote、Demucs、Whisper、RVC、So-VITS、XTTS |
| `pipelines` | `src/myvoiceclone/pipelines/` | 工作流编排：ingest、diarize、slice、clean、transcribe、score、curate、train、infer、evaluate |
| `jobs` | `src/myvoiceclone/jobs/` | 异步 job 队列、runner、events |
| `services` | `src/myvoiceclone/services/` | 应用服务层，CLI/API 与 pipelines/eval 之间的唯一桥梁 |
| `api` | `src/myvoiceclone/api/` | FastAPI HTTP 入口、Pydantic schemas、路由 |
| `cli` | `src/myvoiceclone/cli.py` | Typer 命令行入口 |
| `eval` | `src/myvoiceclone/eval/` | 客观/主观评估、报告生成 |
| `evidence` | `src/myvoiceclone/evidence.py` | first-test evidence pack 收集与校验 |

### 2.2 关键文件

| 文件 | 作用 |
|---|---|
| `pyproject.toml` | 项目元数据、依赖 extras、入口脚本 `myvoiceclone` |
| `src/myvoiceclone/cli.py` | CLI 全部命令实现 |
| `src/myvoiceclone/api/app.py` | FastAPI 工厂函数 `create_app()` |
| `src/myvoiceclone/config.py` | 配置解析：环境变量 > `configs/local.yaml` > 默认值 |
| `src/myvoiceclone/errors.py` | 统一异常体系 `VoiceCloneError` |
| `src/myvoiceclone/evidence.py` | evidence pack 收集/校验命令行入口 |
| `src/myvoiceclone/services/__init__.py` | 应用服务层，所有 pipeline/eval 调用必须经此 |
| `src/myvoiceclone/jobs/runner.py` | JobRunner，同步执行 job，含 step-level 事件 |
| `src/myvoiceclone/storage/migrations.py` | 带 checksum 的 SQL 迁移执行器 |

### 2.3 入口点

**CLI**

```bash
myvoiceclone --help
```

安装方式：`pip install -e ".[first-test]"`，入口脚本指向 `myvoiceclone.cli:app`。

**API**

```bash
uvicorn myvoiceclone.api.app:create_app --reload
```

或 Python：

```python
from myvoiceclone.api.app import create_app
app = create_app()
```

**Evidence 模块**

```bash
python -m myvoiceclone.evidence collect --run-id ...
python -m myvoiceclone.evidence validate /path/to/pack --repo-root .
```

### 2.4 数据流

```
本地音频文件
   ↓
ingest (FFmpeg probe + normalize) → raw/staging artifact → recordings 表
   ↓
diarize (PyAnnote/mock) → segments 表 + diarized artifact
   ↓
slice (FFmpeg extract) → sliced artifacts
   ↓
clean (Demucs/mock) → cleaned artifacts
   ↓
transcribe (Whisper/mock) → transcript artifacts
   ↓
score (mock) → quality_score + status
   ↓
curate (keep/drop + dedupe via vec0)
   ↓
dataset create + freeze → manifest.jsonl artifact
   ↓
train (RVC / So-VITS) → checkpoint + rendered_audio artifacts → model_runs 表
   ↓
inference (XTTS/RVC) → rendered_audio artifact
   ↓
evaluate → eval_metrics / eval_samples / reports
   ↓
release gate → release_gates + policy_events
   ↓
audit trace (job_events, artifacts, reports 串联)
```

### 2.5 关键抽象

- **Artifact**：所有二进制产物（音频、checkpoint、report、manifest、transcript JSON）的统一抽象，含 SHA256、bytes、lineage（parent/source artifact）。
- **Job / JobEvent**：可观测核心，所有耗时操作都走 JobRunner，记录 start/complete/fail/step 事件。
- **Segment**：音频切片，经历 draft → sliced → cleaned → transcribed → processed/needs_review/keep/drop 状态机。
- **Dataset**：ACTIVE → FROZEN，freeze 时按 recording 分组做 train/val/test split，防止 split leak。
- **ModelRun**：训练运行，状态机 pending/queued/preparing/training/checkpointed/completed/failed/cancelled。
- **Adapter**：所有外部工具/模型统一封装，通过 `MOCK_ADAPTERS` 环境变量切换 mock/real。

---

## 3. 项目的完整树状目录结构

```
/mnt/usb/workspace/myvoiceclone/
├── configs/                      # 配置文件
│   ├── local.yaml                # 本地路径配置（db/artifact/models）
│   ├── models.yaml               # 模型与预训练权重配置
│   └── pipelines/
│       └── preprocess.default.yaml   # 预处理默认参数
├── .data/                        # 运行时数据根目录（默认被 .gitignore 排除）
│   ├── db/                       # SQLite 运行库
│   ├── raw/                      # 用户提供的输入音频
│   ├── artifacts/                # 按类型分目录存放二进制产物
│   │   ├── raw/                  # 原始音频 artifact
│   │   ├── staging/              # 归一化音频
│   │   ├── sliced/               # 切片音频
│   │   ├── cleaned/              # 人声分离后音频
│   │   ├── diarized/             # diarization JSON
│   │   ├── transcript/           # ASR 结果 JSON
│   │   ├── checkpoint/           # 训练 checkpoint
│   │   ├── rendered_audio/       # 合成/转换结果
│   │   └── ...
│   ├── models/                   # 模型权重与注册产物
│   └── test-runs/                # first-test evidence
├── db/                           # SQLite 数据库与迁移
│   ├── migrations/               # 001-008 SQL 迁移脚本
│   └── myvoiceclone.sqlite       # 本地数据库（默认被 .gitignore 排除）
├── docs/                         # 全部文档
│   ├── api/openapi.md            # REST API 端点快照
│   ├── architecture/layers.md    # 分层架构与依赖规则
│   ├── baseline/device_stacks.md # 本机 GPU/CUDA 环境扫描
│   ├── closure/                  # 各阶段 closure 报告
│   │   ├── first-build/
│   │   └── first-test/
│   ├── code-review/              # 代码评审记录
│   ├── eval/                     # 执行计划与评估输入包
│   │   ├── first-build/
│   │   └── first-test/
│   ├── ops/                      # 运维/治理文档
│   │   ├── local-setup.md
│   │   ├── security-governance.md
│   │   └── error-handbook.md
│   ├── plan/                     # 行动计划
│   │   ├── first-build/
│   │   └── first-test/
│   └── templates/                # 文档模板
├── infra/                        # 基础设施
│   └── docker/
│       ├── compose.voiceclone.yaml # Docker Compose（ai-voiceclone，唯一 658 端口）
│       ├── compose.yaml          # 历史 preprocess/train compose（非 NF1 主入口）
│       ├── Dockerfile.preprocess # 预处理容器
│       └── Dockerfile.train      # 训练容器（NVIDIA NGC PyTorch）
├── scripts/                      # 便捷脚本
│   ├── bootstrap_env.sh          # 构建并启动 ai-voiceclone 容器
│   ├── collect_first_test_evidence.sh
│   ├── download_models.sh        # 仅生成模型 manifest，不下载真实权重
│   ├── run_preprocess.sh
│   └── run_train_sovits.sh
├── src/myvoiceclone/             # 主源码
│   ├── adapters/                 # 外部工具/模型适配器
│   │   ├── audio/
│   │   ├── diarization/
│   │   ├── separation/
│   │   ├── asr/
│   │   ├── embeddings/
│   │   └── training/
│   ├── api/                      # FastAPI
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   ├── schemas.py
│   │   └── routes_*.py
│   ├── domain/                   # 领域层
│   │   ├── entities.py
│   │   ├── states.py
│   │   ├── policies.py
│   │   └── services.py（兼容 shim）
│   ├── eval/                     # 评估
│   ├── jobs/                     # job 队列与 runner
│   ├── pipelines/                # 流水线
│   ├── services/                 # 应用服务层
│   ├── storage/                  # 持久化
│   ├── cli.py
│   ├── config.py
│   ├── errors.py
│   └── evidence.py
├── tests/                        # 测试
│   ├── api/
│   ├── cli/
│   ├── integration/
│   ├── unit/
│   ├── fakes/
│   ├── fixtures/
│   └── conftest.py
├── venv/                         # 历史宿主虚拟环境；NF1 后不再保留
├── .env.example
├── .gitignore
├── .dockerignore
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## 4. 基础设施与环境配置

### 4.1 Docker Compose

NF1 主入口文件：`infra/docker/compose.voiceclone.yaml`

| 服务 | 镜像 | 用途 |
|---|---|---|
| `ai-voiceclone` | `ai-voiceclone:cu130` | API/CLI/test/DB/推理训练统一执行容器，唯一对外端口 658 |

关键约定：

- `ai-voiceclone` 通过 volume 把项目内的 `.data/{db,artifacts,models,test-runs}` 挂载到容器内的固定路径。
- 容器内运行库路径为 `/app/.data/db`，避免遮蔽仓库内 `/app/db/migrations`；artifacts/models/test-runs 分别挂载到 `/app/data/artifacts`、`/app/models`、`/app/test-runs`。
- 环境变量 `DB_PATH`、`ARTIFACT_ROOT`、`MODELS_DIR`、`EVIDENCE_ROOT`、`MOCK_ADAPTERS` 在容器内固定，不可通过 `.env` 覆盖容器路径。
- `ai-voiceclone` 服务声明 `runtime: nvidia` 与 GPU 资源预留，需要主机安装 NVIDIA Container Toolkit。
- 只发布宿主端口 `658:658`；SSH、debug、vLLM 或其他辅助端口不属于 `myvoiceclone` 运行边界。

### 4.2 环境变量 `.env.example`

```env
# 数据目录统一放在项目根目录 .data/ 下，容器内固定挂载
DB_PATH=.data/db/myvoiceclone.sqlite
ARTIFACT_ROOT=.data/artifacts
MODELS_DIR=.data/models
EVIDENCE_ROOT=.data/test-runs

# Docker 默认使用真实 adapter；离线开发时可改为 true
MOCK_ADAPTERS=false
LOG_LEVEL=INFO

ENABLE_SECURITY_POLICY=false
ENABLE_VEC1_PROBE=false

HUGGINGFACE_TOKEN=
CUDA_VISIBLE_DEVICES=
```

### 4.3 本地配置 `configs/local.yaml`

```yaml
db_path: ".data/db/myvoiceclone.sqlite"
artifact_root: ".data/artifacts"
models_dir: ".data/models"
evidence_root: ".data/test-runs"
```

配置优先级：**环境变量 > `configs/local.yaml` > 代码默认值**（由 `config.py` 统一解析）。

### 4.4 数据目录隔离策略

项目采用“**运行时数据目录自包含在项目内**”策略，所有大文件统一放在 `.data/`，并通过 `.gitignore` / `.dockerignore` 排除：

| 类型 | 项目内位置 | 容器内固定位置 |
|---|---|---|
| 代码 | `.` | `/app` |
| 数据库 | `.data/db/myvoiceclone.sqlite` | `/app/.data/db/myvoiceclone.sqlite` |
| artifacts | `.data/artifacts` | `/app/data/artifacts` |
| 模型 | `.data/models` | `/app/models` |
| evidence | `.data/test-runs` | `/app/test-runs` |

`.gitignore` 已排除 `.data/`、`db/*.sqlite`、`models/`、所有音频与模型权重文件，避免大文件进入版本控制或 Docker 镜像。

### 4.5 模型/数据/artifact 存放约定

- **Artifact**：统一由 `ArtifactStore.create_artifact()` 写入，按 `artifact_type` 分子目录，ID/文件名使用 `mvc_<uuidhex>`，防止冲突。
- **模型注册表**：训练完成后导出到 `.data/models/registry/<model_name>_final.pth`，同时在 DB `artifacts` 中注册 `model_registry` 类型记录。
- **数据库迁移**：`db/migrations/` 下 001-008 SQL 脚本，由 `storage/migrations.py` 按版本号顺序执行并校验 checksum。

---

## 5. 全部技术栈

### 5.1 Python 与构建

- **Python**：>= 3.10（NF1 后由 `ai-voiceclone` 容器提供，当前容器 Python 为 3.12 系）
- **构建后端**：setuptools + wheel
- **包管理**：pip + `pyproject.toml` extras

### 5.2 核心依赖（按 extras 分组）

| extras | 依赖 |
|---|---|
| （核心） | `pyyaml` |
| `api` | `fastapi`, `uvicorn`, `pydantic`, `python-multipart` |
| `cli` | `typer` |
| `db` | `sqlite-vec` |
| `audio` | `soundfile`, `torchaudio` |
| `preprocess` | `pyannote.audio`, `openai-whisper`, `demucs` |
| `test` | `pytest`, `httpx` |
| `dev` | `ruff`, `mypy` |
| `first-test` | 包含上述 api/cli/db/audio/preprocess/test 全部 |

### 5.3 测试框架

- `pytest` 为主
- `pytest.ini` 定义 markers：unit / api / cli / integration / live / gpu / slow
- 默认只运行 unit/api/cli/integration（`addopts = -m "unit or api or cli or integration"`）
- FastAPI 测试使用 `fastapi.testclient.TestClient`

### 5.4 Docker 基础镜像

- 预处理：`python:3.12-slim` + ffmpeg + libsndfile1
- 训练：默认 `nvidia/cuda:13.0.0-devel-ubuntu24.04`，在 Dockerfile 内安装 PyTorch/Coqui；`nvcr.io/nvidia/pytorch:25.03-py3` 保留为可选 base，但当前网络下拉取慢。

### 5.5 数据库

- **SQLite** 主数据库
- **sqlite-vec** 扩展用于 128 维向量存储与近似搜索
- WAL 模式 + busy_timeout=5000

### 5.6 外部模型与工具

| 用途 | 工具/模型 |
|---|---|
| 音频探针/归一化/切片 | FFmpeg / ffprobe |
| 说话人分割 | PyAnnote `speaker-diarization-3.1` |
| 人声分离/降噪 | Demucs `htdemucs` |
| 语音识别 | OpenAI Whisper `medium` |
| TTS/真实推理 | Coqui XTTS-v2 |
| 歌声/语音转换训练 | So-VITS-SVC、RVC |
| 向量嵌入 | 内部 `AudioEmbedder` + sqlite-vec |

### 5.7 运行环境（本机扫描）

- OS：Ubuntu 24.04.4 LTS (Noble Numbat)
- CPU：ARM aarch64，Cortex-X925 + Cortex-A725，20 核
- GPU：NVIDIA GB10 (Blackwell)，CUDA 13.0，驱动 580.159.03
- RAM：128 GB
- Docker：29.2.1

---

## 6. Verdict

### 6.1 优点

1. **架构清晰**：domain/storage/adapters/pipelines/jobs/api/cli/services 分层明确，并通过 `tests/unit/test_architecture_boundaries.py` 强制依赖规则。
2. **Mock 可运行**：显式设置 `MOCK_ADAPTERS=true` 时无需 GPU、无需真实模型、无需网络即可跑通端到端流程。
3. **可观测性强**：job_events、artifacts、segment_reviews、policy_events、eval_samples 等多表记录完整操作链。
4. **测试覆盖广**：unit/api/cli/integration 四层测试，共 155+ 个用例通过。
5. **治理机制已就位**：release gate、consent ledger、waive 机制、结构化错误 envelope 都已实现。
6. **容器化支持**：preprocess/train 两个 Dockerfile 与 Compose 文件可直接构建运行。
7. **Evidence 机制**：first-test evidence pack 收集器 + 校验器，支持 skipped/retained 状态记录。

### 6.2 已知问题

1. **测试失败 1 个**：`tests/unit/test_first_test_closure_docs.py::test_first_test_closure_head_anchors_match_current_head`
   - 原因：closure 文档里引用的 Git HEAD 还是 `952fbc5`，而当前 HEAD 已变为 `9806d7e`。
   - 影响：仅影响文档锚点一致性检查，不影响功能。
2. **DeprecationWarning**：多处使用 `datetime.utcnow()`，Python 3.12 已提示弃用，建议替换为 `datetime.now(timezone.utc)`。
3. **真实训练未实现**：`SovitsAdapter` / `RvcAdapter` 在 `MOCK_ADAPTERS=false` 时直接抛 `NotImplementedError` 或 `RuntimeError`，first-test 阶段只完成集成骨架。
4. **真实 objective scorer 未接入**：`eval/objective.py` 中的 SQUIM/DNSMOS proxy 处于占位状态。
5. **部分 schema 兼容层尚未收敛**：`source_artifact_id` 与 `parent_artifact_id` 语义存在折叠；`embedding_items` 兼容表仍未移除；`pipeline_runs` 未作为生产 workflow ledger 写入。

### 6.3 TODO / Deferred items

来源：`docs/closure/first-test/deferred-items-ledger.md`

| ID | 事项 | 状态 | 触发条件 |
|---|---|---|---|
| FTD-01 | live capstone 真实执行 | pending-live | `RUN_FIRST_TEST_CAPSTONE=1` + 合法音频 + 模型/cache/token |
| FTD-02 | 非 skipped evidence pack | retained | FTD-01 完成后 |
| FTD-03 | 真实 objective proxy | retained | 选型并安装 DNSMOS/SQUIM 等 |
| FTD-04 | 模型下载/cache/license | retained | owner 允许下载并提供 cache |
| FTD-05 | vec0/embedder 真实维度迁移 | retained | ECAPA/CLAP/SBERT 接入 |
| FTD-06 | 多 worker / queue / SQLite 并发 | retained | 引入 worker pool 或 broker |
| FTD-07 | 全局 API response envelope | retained | 前端/外部 consumer contract freeze |
| FTD-08 | 完整 OTel 平台 | retained | 多服务 trace 需求 |
| FTD-09 | 众包 MOS/P.808 平台 | retained | 发布级外部评审需求 |
| FTD-10 | fake adapter Protocol/ABC 冻结 | retained | adapter interface freeze |
| FTD-11~FTD-27 | 详见 deferred ledger | retained/partial | 见文档 |

### 6.4 测试通过情况

最近运行结果（宿主 venv 迁移前基线；NF1 收口必须以 `docker exec ai-voiceclone python -m pytest -q` 为准）：

```
162 passed, 1 skipped, 2 deselected, 15 warnings
```

- 跳过：1 个 live capstone（未设置 `RUN_FIRST_TEST_CAPSTONE=1`）
- deselected：2 个 live/gpu 测试（默认不包含）
- 警告：主要是 `datetime.utcnow()` 弃用与 `httpx` 版本提示

**结论：默认测试套件通过；NF1 后只采信容器内测试结果。**

### 6.5 是否可运行

- **Mock 模式**：可直接运行。执行 `./scripts/bootstrap_env.sh` 后，用 `docker exec ai-voiceclone python -m myvoiceclone.cli init-db` 和 `docker exec ai-voiceclone python -m myvoiceclone.cli vec-health` 验证。
- **真实模式**：需要额外配置 HuggingFace Token、模型权重、CUDA 环境，当前 first-test 阶段仅部分路径可用（如 XTTS real inference 骨架已实现，但训练与 objective 评估仍为占位）。

### 6.6 主要风险

1. **真实训练缺失**：first-test 之后若要进行真实 So-VITS/RVC 训练，需要新增大量外部训练脚本与模型权重管理。
2. **SQLite 并发瓶颈**：当前为单进程同步 JobRunner，生产级并发需迁移到 PostgreSQL 或加消息队列。
3. **模型/license 合规**：XTTS-v2 使用 Coqui Public Model License，真实使用前需确认授权边界。
4. **安全策略默认关闭**：`ENABLE_SECURITY_POLICY=false`，发布闸在默认配置下不拦截，需要显式启用。
5. **Schema 漂移风险**：007 migration 采用“新增列 + 兼容视图”策略，长期需要一次 breaking migration pass。

---

## 7. 附录#1 - 常用命令

### 7.1 初始化环境

```bash
# 1. 构建并启动 ai-voiceclone 容器
./scripts/bootstrap_env.sh

# 2. 初始化数据库
docker exec ai-voiceclone python -m myvoiceclone.cli init-db

# 3. 验证 sqlite-vec 加载
docker exec ai-voiceclone python -m myvoiceclone.cli vec-health
```

容器内 console script 等价命令为 `myvoiceclone init-db` 与 `myvoiceclone run preprocess-all /app/data/raw/sample.wav`；NF1 后这些命令必须在 `ai-voiceclone` 容器内执行。

### 7.2 运行测试

```bash
# 默认套件（unit + api + cli + integration）
docker exec ai-voiceclone python -m pytest -q

# 全部测试（包含 live/gpu/slow）
docker exec ai-voiceclone python -m pytest -q -m ""

# 仅单元测试
docker exec ai-voiceclone python -m pytest -q -m unit

# 仅 API 测试
docker exec ai-voiceclone python -m pytest -q -m api

# 查看跳过原因
docker exec ai-voiceclone python -m pytest -q -rs
```

### 7.3 启动 API

```bash
# API 由 ai-voiceclone 容器常驻启动，唯一宿主端口为 658
curl http://127.0.0.1:658/health
```

### 7.4 CLI 常用流程

```bash
# 1. 预处理单个音频
docker exec ai-voiceclone python -m myvoiceclone.cli ingest /app/data/raw/audio.wav
# 或端到端预处理
docker exec ai-voiceclone python -m myvoiceclone.cli run preprocess-all /app/data/raw/audio.wav

# 2. 单独运行 diarize
docker exec ai-voiceclone python -m myvoiceclone.cli run diarize <RECORDING_ID>

# 3. 查看待审 segment
docker exec ai-voiceclone python -m myvoiceclone.cli curate list

# 4. 标记 segment 状态
myvoiceclone curate mark <SEGMENT_ID> --status keep --reason "quality OK"

# 5. 创建并冻结数据集
myvoiceclone dataset create my-dataset --filter keep
myvoiceclone dataset freeze my-dataset

# 6. 训练 So-VITS
myvoiceclone train sovits my-dataset --profile long

# 7. 评估模型运行
myvoiceclone eval <MODEL_RUN_ID> --suite default

# 8. 查看报告
myvoiceclone report show <REPORT_ID>

# 9. 审计 recording 全链路
myvoiceclone audit <RECORDING_ID>
```

### 7.5 Docker 操作

```bash
# 0. 准备 .env
cp .env.example .env
# 编辑 .env：填写 HUGGINGFACE_TOKEN，数据路径保持默认 .data/ 即可
mkdir -p .data/{db,artifacts,models,test-runs,raw}

# 1. 构建并运行唯一 ai-voiceclone 容器
docker compose -f infra/docker/compose.voiceclone.yaml build ai-voiceclone
docker compose -f infra/docker/compose.voiceclone.yaml up -d ai-voiceclone

# 2. 需要验证 mock 流程时显式打开 mock
MOCK_ADAPTERS=true docker compose -f infra/docker/compose.voiceclone.yaml up -d ai-voiceclone
docker exec ai-voiceclone python -m myvoiceclone.cli run preprocess-all /app/data/raw/sample.wav

# 3. 真实 XTTS 推理见下一节；默认 MOCK_ADAPTERS=false
```

### 7.6 真实 XTTS 推理实战记录

当前最快可用的真实声音克隆路径是 **Coqui XTTS-v2 reference voice cloning**。它不需要先完成 So-VITS/RVC 训练，只需要一段合法、非静音、干净的人声参考音频和待合成文本。

已验证的本地状态：

- `ai-voiceclone:cu130` 是 NF1 后的专用运行镜像。
- 运行时数据统一在 `.data/`，旧的根目录 `data/`、`models/` 不再使用。
- XTTS-v2 缓存在 `.data/models/coqui/tts/tts_models--multilingual--multi-dataset--xtts_v2/`。
- `model.pth` SHA256：`c7ea20001c6a0a841c77e252d8409f6a74fb423e79b3206a0771ba5989776187`。
- Docker Compose 默认进入 real mode：`MOCK_ADAPTERS=false`。
- 最新验证输出：`.data/artifacts/rendered_audio/art_c0009d4aa051.wav`，元数据为 `adapter_mode=real`、`tool=coqui-tts`、`device=cuda`。

真实推理命令：

```bash
docker compose -f infra/docker/compose.voiceclone.yaml run --rm \
  -e COQUI_TOS_AGREED=1 \
  ai-voiceclone python -m myvoiceclone.cli infer real \
  --text "This is a real XTTS inference test." \
  --reference-artifact-id <REFERENCE_AUDIO_ARTIFACT_ID> \
  --language en
```

当前项目内已经验证过的非静音参考 artifact 是 `art_4bb8dc928a99`，它来自真实 XTTS 输出，仅用于端到端 smoke test。要真正克隆用户声音，应把授权人声音频登记为 `reference_audio`，或先走 ingest/preprocess 生成可用 cleaned artifact，再作为 `--reference-artifact-id`。

常见坑：

| 问题 | 现象 | 处理 |
|---|---|---|
| Coqui TOS 非交互确认 | 容器内报 `EOF when reading a line` | 推理命令加入 `-e COQUI_TOS_AGREED=1` |
| Hugging Face 大文件下载不稳定 | 自动下载 `model.pth` 失败或下载到不完整文件 | 用 `aria2c --continue=true --split=16` 下载签名 URL，并以 SHA256 校验为准 |
| Python 3.12 / aarch64 依赖冲突 | `TTS` 包不可用，Coqui 拉到不兼容依赖 | 使用当前 Dockerfile 固定组合：`coqui-tts==0.27.5`、`torch==2.12.0`、`torchaudio==2.11.0 --no-deps`、`transformers==4.57.3`、`torchcodec==0.14.0` |
| compose 未读取根目录 `.env` | 不显式传 `MOCK_ADAPTERS=false` 时生成 mock artifact | compose 默认值已改为 `${MOCK_ADAPTERS:-false}`；用 `docker compose -f infra/docker/compose.voiceclone.yaml config \| rg MOCK_ADAPTERS` 验证 |
| 静音参考音频 | Coqui 提示 `Max=0.00 min=0.00`，推理能成功但没有克隆意义 | 换成非静音、干净、授权的人声 WAV |

验证最新输出：

```bash
docker exec ai-voiceclone python - <<'PY'
import json, os, sqlite3, wave

conn = sqlite3.connect(".data/db/myvoiceclone.sqlite")
conn.row_factory = sqlite3.Row
row = conn.execute("""
    select id, uri, metadata_json
    from artifacts
    where artifact_type = 'rendered_audio'
    order by created_at desc
    limit 1
""").fetchone()
meta = json.loads(row["metadata_json"])
path = ".data/artifacts/" + row["uri"]
with wave.open(path, "rb") as wav:
    print(row["id"], path)
    print(meta["adapter_mode"], meta["tool"], meta["device"])
    print(wav.getnchannels(), wav.getframerate(), wav.getnframes() / wav.getframerate())
    print(os.path.getsize(path))
PY
```

### 7.7 API 端到端声音克隆流程

API 已补齐上传参考音频、提交推理 job、查询进度、下载最终音频和 SQLite 请求审计。当前后台执行使用 FastAPI `BackgroundTasks`；后续可替换为独立 worker/queue。

ID 合约：

- 新生成的数据库主键、`run_id`、`job_id`、`artifact_id`、`trace_id` 统一使用 `mvc_` + 32 位 UUID hex，例如 `mvc_0123456789abcdef0123456789abcdef`。
- 新代码统一通过 `myvoiceclone.ids.new_id()` 生成 ID；API 审计中非法或缺失的 `x-trace-id` 会被替换为新的 `mvc_` trace。
- `db/migrations/010_uuid_primary_ids.sql` 已把剩余自增数字主键表 `job_events`、`eval_metrics`、`policy_events` 迁移为 `TEXT` UUID 主键默认值。

```bash
# 1. 启动 API
docker exec ai-voiceclone python -m uvicorn myvoiceclone.api.app:create_app --host 0.0.0.0 --port 8000

# 2. 创建 run
RUN_ID=$(curl -s -X POST http://127.0.0.1:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"name":"local-clone","adapter_mode":"real"}' | jq -r .id)

# 3. 上传非静音、授权 WAV 作为 reference_audio
REF_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/runs/$RUN_ID/reference-audio" \
  -F "file=@/path/to/voice.wav;type=audio/wav" | jq -r .id)

# 4. 提交真实 XTTS 推理 job，并让 API 后台启动
JOB_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/runs/$RUN_ID/infer" \
  -H 'content-type: application/json' \
  -d "{\"text\":\"Hello from my cloned local voice.\",\"reference_artifact_id\":\"$REF_ID\",\"language\":\"en\",\"start_immediately\":true}" | jq -r .id)

# 5. 查询 run 聚合状态、job events、artifacts
curl -s "http://127.0.0.1:8000/api/runs/$RUN_ID/status" | jq .

# 6. 下载最终 rendered_audio artifact
ART_ID=$(curl -s "http://127.0.0.1:8000/api/runs/$RUN_ID/status" \
  | jq -r '.artifacts[] | select(.artifact_type=="rendered_audio") | .id' | tail -1)
curl -L "http://127.0.0.1:8000/api/artifacts/$ART_ID/download" -o cloned.wav
```

可用接口：

| 接口 | 用途 |
|---|---|
| `POST /api/runs` | 创建一次克隆 run |
| `GET /api/runs/{run_id}` | 查看 run 元数据 |
| `GET /api/runs/{run_id}/status` | 聚合 jobs/events/artifacts/failures |
| `POST /api/runs/{run_id}/reference-audio` | 上传 WAV 并登记为 `reference_audio` |
| `POST /api/runs/{run_id}/reference-audio/from-artifact` | 将已有 artifact 提升为 `reference_audio` |
| `POST /api/runs/{run_id}/infer` | 创建 `infer_real` job；`start_immediately=true` 时后台执行 |
| `GET /api/jobs/{job_id}` | 查询 job |
| `POST /api/jobs/{job_id}/run?background=true` | 手动后台执行已有 job |
| `GET /api/artifacts/{artifact_id}` | 查询 artifact 元数据 |
| `GET /api/artifacts/{artifact_id}/download` | 下载 artifact 文件 |

接口注册位置：

| 模块 | 注册内容 |
|---|---|
| `src/myvoiceclone/api/app.py` | FastAPI app、错误处理、审计 middleware、runs/jobs/artifacts 路由注册 |
| `src/myvoiceclone/api/routes_runs.py` | run 创建/查询/status、音频上传、reference audio、推理 job |
| `src/myvoiceclone/api/routes_jobs.py` | job 查询与手动执行 |
| `src/myvoiceclone/api/routes_artifacts.py` | artifact 查询与下载 |

错误响应统一包含 `error.code` 和 `error.trace_id`。当前稳定错误码包括：

```text
run_not_found
artifact_not_found
artifact_type_unsupported
reference_audio_invalid
reference_audio_silent
job_not_found
job_execution_failed
inference_model_unavailable
inference_failed
download_not_found
request_validation_error
internal_error
```

每个 API 请求会写入 SQLite `api_request_logs`，字段包括 `trace_id`、`method`、`path`、`status_code`、`error_code`、`run_id`、`job_id`、`artifact_id`、请求/响应摘要和耗时。功能流水线仍通过 `jobs`、`job_events`、`artifacts` 记录执行过程和产物 lineage。

接口测试文档/回归入口：

```bash
docker exec ai-voiceclone python -m pytest tests/api/test_voice_clone_api_flow.py -q
docker exec ai-voiceclone python -m pytest tests/unit/test_ids.py tests/unit/storage/test_schema_drift.py -q
```

### 7.8 Evidence 收集

```bash
# 收集 skipped evidence
RUN_ID=$(docker exec ai-voiceclone python - <<'PY'
from myvoiceclone.ids import new_id
print(new_id())
PY
)
SKIP_REASON="RUN_FIRST_TEST_CAPSTONE=1 is required for live first-test capstone" \
RUN_ID="$RUN_ID" \
./scripts/collect_first_test_evidence.sh

# 校验 evidence pack
docker exec ai-voiceclone python -m myvoiceclone.evidence validate \
  ".data/test-runs/$RUN_ID" \
  --repo-root .

# 真实 capstone（需要合法短音频、模型、cache、token）
RUN_FIRST_TEST_CAPSTONE=1 \
FIRST_TEST_AUDIO_PATH=/path/to/legal_short.wav \
docker exec ai-voiceclone python -m pytest tests/integration/test_first_test_capstone.py -m live -q -rs
```

### 7.9 其他实用命令

```bash
# 下载模型 manifest（不下载真实权重）
./scripts/download_models.sh

# dry-run 任何脚本
./scripts/bootstrap_env.sh --dry-run
./scripts/run_preprocess.sh /path/to/audio.wav --dry-run
./scripts/run_train_sovits.sh my_dataset --dry-run

# 代码检查（dev 依赖已安装）
docker exec ai-voiceclone ruff check src tests
docker exec ai-voiceclone mypy src
```
