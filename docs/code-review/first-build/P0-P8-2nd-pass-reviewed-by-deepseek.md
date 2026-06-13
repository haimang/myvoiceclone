# P0-P8 first-build 第 2 轮代码审查报告

> **文档性质**：`2nd-pass code review`（首次修复落实后的独立复核）
>
> | 字段 | 值 |
> |------|-----|
> | **审查标的** | `myvoiceclone first-build P0-P8`（第 1 轮修复后） |
> | **审查人** | `DeepSeek`（独立，非参考其他 reviewer 报告） |
> | **审查日期** | `2026-06-13` |
> | **审查轮次** | `第 2 轮` |
> | **文档状态** | `reviewed` |
>
> **审查输入（唯一）**：
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`（§6/§8/§12/§14/§15）
> - `myvoiceclone/docs/code-review/first-build/P0-P8-review-VF-ledger.md`（§1-§6，含 V1-V23 修复台账）
> - `myvoiceclone/` 全量 HEAD 源文件（db/migrations/*.sql、src/**/*.py、tests/**/*.py、infra/docker/**、configs/**、pyproject.toml、pytest.ini）
>
> **审查策略**：独立 reasoning，不引用 DeepSeek-R1-R28、MiniMax-R1-R16 或其他 reviewer 的分析结论。一切判断仅基于 HEAD 代码 vs final-execution-plan 的逐行对账。

---

## 0. 审查方法论

1. **第 1 轮修复复核**：逐条对照 VF-ledger §6.1 的 23 项修复声明，在 HEAD 源码中坐实。
2. **全新发现**：扫描第 1 轮 reviewer 未覆盖的盲区——实体与 DB 迁移后的字段漂移、入口点可运行性、数据隔离合规、运行时正确性。
3. **分层交叉分析**：DB schema ↔ entities ↔ repositories ↔ API schemas ↔ routes ↔ CLI 之间做 4 层对齐。

> **纪律**：所有 finding 带 `file:line` 证据。不使用"可能"、"或许"等模糊词——每个问题要么有确切代码行坐实，要么不做记录。

---

## 1. TL;DR 一句话裁定

> **第 1 轮修复完成度约 70%。但第 1 轮修复本身引入了 3 个新 regression（AudioProbe 重复定义→TypeError、entry_point 不存在→CLI 不可用、fakes 引用不存在 entity 类型→test import 失败），且修复范围未覆盖实体层与 API 层的同步更新——系统性的 Schema↔Entity↔Schema 三层漂移构成了 12 条必须修复的 critical finding。**

关键数字：

| 类别 | 数量 |
|------|------|
| **critical** | 13 |
| **high** | 8 |
| **medium** | 6 |
| **low** | 2 |
| **合计** | **29** |

---

## 2. 第 1 轮修复复核 （18 项 fix 声明逐一坐实）

### 2.1 复核判定图例

| verdict | 含义 |
|---------|------|
| ✅ `fix-confirmed` | 修复落地，代码正确 |
| ⚠️ `fix-partial` | 修复方向正确但不完整 |
| ❌ `fix-incomplete` | 修复声明与代码事实不符 |
| 🔴 `fix-introduced-bug` | 修复引入了新回归 |

### 2.2 逐项复核表

| V# | 声明处置 | 复核结果 | 证据与说明 |
|----|----------|----------|-----------|
| V1 | `✅ fixed` | ⚠️ `fix-partial` | migration 007 添加了 12 表缺失列。但 (a) `jobs_v2:42` 用了 `GENERATED ALWAYS AS (name) VIRTUAL`——SQLite 不支持 VIRTUAL 生成列语法，migration 会报错；(b) 添加了双名 `type`/`name` 和 `params_json`/`payload_json`，产生命名双轨；(c) 修复后 entities.py/repositories.py/API schemas.py 均未同步更新。详见 §3.1 V24 |
| V2 | `⚠️ partial-fix` | ⚠️ `fix-partial` | vec0 维度 128 未改为 768/192/384。plan §14.3 明确要求三维度。vec0_store.py 未对维度做任何校验。ledger 正确标记为 defer |
| V3 | `✅ fixed` | ✅ `fix-confirmed` | `Dockerfile.train:6` 已改为 `nvcr.io/nvidia/pytorch:25.03-py3`。注：NGC 25.03 支持 aarch64 + Blackwell sm_120 |
| V4 | `✅ fixed` | ⚠️ `fix-partial` | `tests/api/test_routes.py:13` 有 `@pytest.mark.api`，`tests/cli/test_cli.py:9` 有 `@pytest.mark.cli`。但 `live`/`gpu`/`slow` 三个 marker 零使用——plan §8.1 要求这些 marker 存在但可空。中等缺陷 |
| V5 | `✅ fixed` | ✅ `fix-confirmed` | `grep "from myvoiceclone.pipelines\|from myvoiceclone.eval" api/*.py` → 0 命中。API 层违规已清零 |
| V6 | `✅ fixed` | ❌ `fix-incomplete` | **cli.py:13 仍有 `from myvoiceclone.pipelines.export_dataset import run_export_dataset`**！此 import 在 ledger 修复范围外——V6 只处理了 cli.py:221,250（train 命令），未处理第 13 行的顶层 import。详见 §3.5 V31 |
| V7 | `✅ fixed` | ✅ `fix-confirmed` | `cli.py:13` 已添加 `from myvoiceclone.pipelines.export_dataset import run_export_dataset`。此 import 本身与 V6 的架构原则冲突，但就 V7（NameError 修复）而言是正确的 |
| V8 | `✅ fixed` | ✅ `fix-confirmed` | `test_curate_dedupe.py:72` 已删除 `or True`。`curate.py:34` 将 `drop_reason` 写入 `metadata_json` |
| V9 | `✅ fixed` | 🔴 `fix-introduced-bug` | **entities.py 第 10 行定义 `AudioProbe(duration_sec, sample_rate, channels)`，第 125 行**重复**定义了 `AudioProbe(duration_sec, sample_rate, channels, format)`。后者覆盖前者。`torchaudio_io.py:31-35` 调用 `AudioProbe(duration_sec=..., sample_rate=..., channels=...)`——只用 3 个参数，但存活的类需要 4 个（缺失 `format`）。**运行时 TypeError**。详见 §3.2 V25 |
| V10 | `⚠️ partial-fix` | ⚠️ `fix-partial` | `tests/fakes/__init__.py` 存在，含 6 个 fake class。但 fakes 导入了 `TranscriptResult`、`EmbeddingResult`、`AudioConvertResult`——这些类型**在 entities.py 中不存在**（grep 确认 0 命中）。`tests/fakes/__init__.py` 自身 import 会失败。详见 §3.8 V28 |
| V11 | `✅ fixed` | ✅ `fix-confirmed` | `compose.yaml:1-13` 有 nvidia-container-toolkit 安装说明 |
| V12 | `✅ fixed` | ✅ `fix-confirmed` | Dockerfile.preprocess:17 → `".[cli,db,api,preprocess,audio]"`；Dockerfile.train:21 → `".[cli,db,api]"` |
| V13 | `✅ fixed` | ✅ `fix-confirmed` | `grep "os.environ\[.MOCK_ADAPTERS" tests/` → 仅出现在注释中。所有 adapter test 使用 `monkeypatch.setenv` |
| V14 | `✅ fixed` | ⚠️ `fix-partial` | `api/dependencies.py:13` 调用了 `config.resolve_db_path()`。但 `cli.py:37-43` 和 `cli.py:49-51` 仍用**自己的**路径解析逻辑（手动调用 `get_project_root()`），未使用 `resolve_db_path()`。DRY 违反 |
| V15 | `✅ fixed` | ❌ `fix-incomplete` | `domain/states.py` 扩展到了 7 个 enum（39+ 值）。但 **`grep "from myvoiceclone.domain.states" src/` → 0 命中**！零 import、零使用。runner.py 仍用裸字符串 `"running"`/`"completed"`/`"failed"`。详见 §3.3 V26 |
| V16 | `⚠️ partial-fix` | ✅ `fix-confirmed` | `runner.py:87-98` 已补齐 6 步 per-step dispatch |
| V17 | `📋 deferred` | — `deferred` | 幂等性保护未实现，符合 defer 策略 |
| V18 | `📋 deferred` | — `deferred` | 3 embedder mock，符合 first-build 策略 |
| V19 | `📋 deferred` | — `deferred` | scoring mock，符合 first-build 策略 |
| V20 | `✅ fixed` | — `not-verified` | Closure commit SHA 替换——文档级修复，不阻塞代码运行 |
| V21 | `📋 deferred` | — `deferred` | WAL 并发测试延后 |
| V22 | `📋 deferred` | — `deferred` | 主观评估延后 |
| V23 | `✅ fixed` | ✅ `fix-confirmed` | `test_architecture_boundaries.py:27` 改为 `pytest.fail()` |

### 2.3 复核小结

- **14 项 fix 声明中**：
  - 6 项完全确认（V3, V5, V7, V8, V11, V12, V13, V16, V23）
  - 4 项部分完成（V1, V2, V4, V14）
  - 2 项实质未完成（V6, V15）
  - 1 项引入了新 bug（V9 → AudioProbe 重复定义 TypeError）
  - 1 项无法验证（V20）

---

## 3. 第 2 轮新发现

### 3.1 【Critical】V24 — jobs_v2 migration 语法错误 + 实体/Schema/Repo 三层漂移

**位置**：`db/migrations/007_reconcile_to_plan.sql:42`

```sql
type TEXT GENERATED ALWAYS AS (name) VIRTUAL,
```

**问题**：SQLite **不支持** `GENERATED ALWAYS AS` 语法（这是 PostgreSQL/MySQL 语法）。SQLite 3.31+ 支持 `GENERATED ALWAYS AS (...) STORED`，但 `VIRTUAL` 关键字仅限特定用法。执行 migration 007 会在该行抛出 syntax error，导致所有后续 DDL 被跳过（SQLite `executescript` 遇错即停）。

**连带影响**：migration 007 是第 1 轮修复的核心交付物。如果 migration 失败，V1 的全部修复（12 张表的列补齐、status CHECK、embedding_items 重命名）将实质上**全部未生效**。

**修复**：删除 `type` 列（已有 `name` 即可），或改为 SQLite 兼容的 computed column 语法 `TEXT AS (name)`。

---

同时，migration 007 添加了以下列到各表，但**实体层、repository 层、API schema 层均未同步更新**：

| 表 | 007 新增列 | entities.py 是否有 | repositories.py 是否读写 | API schemas.py 是否有 |
|----|-----------|-------------------|----------------------|---------------------|
| `jobs` | `type`, `subject_type`, `subject_id`, `pipeline`, `requested_by`, `started_at`, `finished_at` | ❌ 全无 | ❌ `JobRepository.save()` 用 `name` 写 `name`；不写新列 | ❌ `JobResponse` 无这些字段 |
| `artifacts` | `kind`, `source_artifact_id`, `created_by_job_id`, `pipeline_version`, `params_json` | ❌ 仍用 `artifact_type`/`parent_artifact_id`/`job_id` | ❌ `ArtifactStore.create_artifact()` 用旧列名 | ❌ 无 ArtifactResponse schema |
| `model_runs` | `model_family`, `checkpoint_artifact_id`, `env_digest`, `git_commit`, `finished_at` | ❌ `ModelRun` 仅 7 字段 | ❌ `ModelRunRepository.save()` 用旧表结构 INSERT | ❌ `ModelRunResponse` 无这些字段 |
| `reports` | `kind`, `subject_type`, `subject_id`, `status` | ❌ 用 `report_type` | ❌ `ReportRepository.save()` 用 `report_type` | ❌ `ReportResponse` 用 `report_type` |
| `eval_samples` | `input_artifact_id`, `output_artifact_id`, `reference_artifact_id`, `report_id`, `scores_json` | ❌ 无对应 entity | ❌ `evaluate_objective_metrics()` 用旧 `audio_artifact_id` | ❌ 无 eval_sample schema |
| `consent_ledger` | `scope`, `status`, `evidence_uri`, `revoked_at` | ❌ 无对应 entity | ❌ `policies.py:66` 仍查 `granted` 列，不用 `status` | ❌ 无 schema |
| `policy_events` | `subject_type`, `subject_id`, `policy_name`, `decision`, `reason`, `payload_json` | ❌ 无对应 entity | ❌ `policies.py:80,95` 用旧 `details_json`，不写新列 | ❌ 无 schema |
| `release_gates` | `status`, `decision_json` | ❌ 无对应 entity | ❌ `routes_reports.py:107` INSERT 用 `passed` 不用 `status` | ❌ `ReleaseGateResponse` 用 `passed: int` 不用 `status` |

**严重性**：critical。这构成了**三层系统漂移**——DB 层（migration 007）已"修复"，但 Python 代码层完全未跟进。所有写 DB 的代码路径使用的是旧列名/旧结构，007 添加的新列永远不会被填充。

---

### 3.2 【Critical】V25 — AudioProbe 重复定义 + torchaudio_io 调用签名不匹配

**位置**：
- `domain/entities.py:10` — `class AudioProbe(duration_sec, sample_rate, channels)`（3 参数）
- `domain/entities.py:125` — `class AudioProbe(duration_sec, sample_rate, channels, format)`（4 参数，覆盖前者）
- `adapters/audio/torchaudio_io.py:31-35` — `return AudioProbe(duration_sec=..., sample_rate=..., channels=...)`（3 参数调用）

**问题**：
1. 第 125 行的定义带有 `format: str` 字段且无默认值。V9 fix 在第 10 行新增了 3 字段版 AudioProbe，但忘记删除第 125 行的旧定义。
2. `torchaudio_io.py:31-35` 调用 3 参数版，但第 125 行覆盖后只存在 4 参数版 → **运行时 TypeError: __init__() missing 1 required positional argument: 'format'**。
3. `adapters/audio/ffmpeg.py` 的 `FFmpegAdapter.probe()` 返回类型未知——如果也返回 AudioProbe，同样会触发此 bug。

**严重性**：critical。这是一个纯运行时 bug，在 torchaudio_io.py 被实际调用时即刻崩溃。torchaudio_io 被 dto_contract test 测试时也会触发。

**修复**：删除第 10-16 行或第 124-129 行的重复定义，统一为一个 `AudioProbe`（含 `format` 或给 `format` 默认值 `""`）。

---

### 3.3 【Critical】V26 — domain/states.py 枚举零使用（V15 修复实质无效）

**位置**：`domain/states.py` 定义了 7 个 enum（RecordingStatus, SegmentStatus, JobStatus, DatasetStatus, ModelRunStatus, ReportStatus, ReleaseGateStatus），但：

```bash
$ grep "from myvoiceclone.domain.states" src/ → 0 命中
```

**零 import、零使用**。以下关键位置仍在用裸字符串：

| 文件 | 行 | 当前写法 | 应用 enum |
|------|-----|---------|----------|
| `jobs/runner.py` | 73 | `job.status = "running"` | `JobStatus.RUNNING` |
| `jobs/runner.py` | 102 | `job.status = "completed"` | `JobStatus.COMPLETED` (or `SUCCEEDED`) |
| `jobs/runner.py` | 117 | `job.status = "failed"` | `JobStatus.FAILED` |
| `jobs/runner.py` | 109 | `job.status = "cancelled"` | `JobStatus.CANCELLED` |
| `jobs/queue.py` | 18 | `status="pending"` | `JobStatus.PENDING` |
| `cli.py` | 170 | `Dataset(..., status="active")` | `DatasetStatus.ACTIVE` |
| `cli.py` | 275-276 | `INSERT eval_metrics` 无状态引用 | — |
| `pipelines/ingest.py` | 99 | `status="processed"` | `RecordingStatus.PROCESSED` |
| `pipelines/train.py` | 42 | `status="running"` | `ModelRunStatus.RUNNING` |
| `pipelines/train.py` | 102 | `run.status = "completed"` | `ModelRunStatus.COMPLETED` |
| `pipelines/train.py` | 319 | `run.status = "preparing"` | `ModelRunStatus.PREPARING` |
| `pipelines/train.py` | 329 | `run.status = "training"` | `ModelRunStatus.TRAINING` |
| `pipelines/train.py` | 375 | `run.status = "checkpointed"` | `ModelRunStatus.CHECKPOINTED` |
| `pipelines/score.py` | 52 | `seg.status = "needs_review"` | `SegmentStatus.NEEDS_REVIEW` |
| `pipelines/score.py` | 54 | `seg.status = "processed"` | `SegmentStatus.PROCESSED` |
| `pipelines/curate.py` | 17 | `status in ("keep", "drop", ...)` | `SegmentStatus.KEEP`, etc. |

**严重性**：critical。39 个 enum 值的定义是纯粹的 dead code。Enum 存在的价值是在编译/类型检查时捕获拼写错误，但全项目用裸字符串消解了这层保护。这使 V15 的修复形同虚设。

---

### 3.4 【Critical】V27 — pyproject.toml CLI entry_point 指向不存在函数

**位置**：
- `pyproject.toml:28`：`myvoiceclone = "myvoiceclone.cli:main"`
- `cli.py`：无 `main` 函数。最后一行是 `if __name__ == "__main__": app()`。

**问题**：`pip install -e .` 会在 `PATH` 中创建 `myvoiceclone` 命令，指向 `myvoiceclone.cli:main`。但此符号不存在 → `AttributeError: module 'myvoiceclone.cli' has no attribute 'main'`。

**正确写法**：`myvoiceclone = "myvoiceclone.cli:app"`（Typer 的 `app` 对象直接 callable）。

**严重性**：critical。CLI 入口点完全不可用。

---

### 3.5 【Critical】V28 — tests/fakes/__init__.py 引用不存在 entity 类型

**位置**：`tests/fakes/__init__.py:17-20`

```python
from myvoiceclone.domain.entities import (
    AudioProbe, DiarizationTurn, SeparationResult, TranscriptResult,
    TrainResult, EmbeddingResult, SynthResult, AudioConvertResult,
)
```

**问题**：`TranscriptResult`、`EmbeddingResult`、`AudioConvertResult` 在 `entities.py` 中**不存在**（grep 确认 0 命中）。`SeparationResult` 存在于 entities.py:143（仅 `cleaned_path` 字段）。fakes 中 `FakeASR.transcribe()` 返回 `TranscriptResult(...)` 带 4 个字段（text, language, segments）——这个类型在整个项目中从未定义。

**严重性**：critical。`from tests.fakes import ...` 会在 import 时抛出 `ImportError`。所有依赖 fakes 的测试（包括 capstone journey）将直接跳过或失败。

---

### 3.6 【Critical】V29 — 数据隔离完全缺失：/mnt/usb/workspace/myvoiceresearch 不存在

**位置**：
- `/mnt/usb/workspace/myvoiceresearch/` — **目录不存在**
- `compose.yaml:29-31,45-48` — 数据 volume 映射到 `../../db`、`../../data`、`../../models`（即 `/mnt/usb/workspace/myvoiceclone/db`、`/mnt/usb/workspace/myvoiceclone/data`、`/mnt/usb/workspace/myvoiceclone/models`）

**问题**：用户需求明确要求"数据 volume 存放在 mnt/usb/workspace/myvoiceresearch 内，避免大数据暴露在宿主机的硬盘上"。当前设计将 db、models、data 全部放在项目仓库子目录下。对于 GB 级 checkpoint 和 20+ 小时音频数据，这会迅速填满宿主机硬盘。

**严重性**：critical。大数据策略完全未实现。需要在 compose.yaml 中将 volumes 改为外部 USB 挂载路径，并在 `configs/local.yaml` 中配置对应的 artifact_root/models_dir。

---

### 3.7 【Critical】V30 — Dockerfile.preprocess 缺少 demucs 依赖

**位置**：
- `pyproject.toml:20`：`preprocess = ["pyannote.audio", "openai-whisper"]`
- `Dockerfile.preprocess:17`：`pip install ".[cli,db,api,preprocess,audio]"`
- `adapters/separation/demucs_adapter.py` — import demucs

**问题**：preprocess extras 中**没有 demucs**。Dockerfile.preprocess 安装了 `.[preprocess]` 但不会获得 demucs。当 `runner.py:153` 调用 `run_clean()` → `DemucsAdapter()` 时，`import demucs` 失败 → `ImportError`。

**严重性**：critical。preprocess 容器在 clean 步骤会崩溃。

**修复**：在 `pyproject.toml` 中 `preprocess` extras 增加 `"demucs"`，或单独添加一个 `separation` extras 并在 Dockerfile 中安装。

---

### 3.8 【Critical】V31 — CLI 直接 import pipelines 违反架构（V5/V6 修复未完成）

**位置**：`cli.py:13`

```python
from myvoiceclone.pipelines.export_dataset import run_export_dataset
```

**问题**：ledger §6.1 声明 V5 和 V6 "全部修复"——API routes 不再直接 import pipelines，CLI 中 train 命令改为 service。但 `cli.py:13` 的**顶层** import 仍然直接引用 pipelines。这违反了 plan §12.3 的架构规则："CLI 只依赖 domain services 和 jobs"。

值得注意的是，`test_architecture_boundaries.py:41` 中 cli 层的 forbidden_rules 只禁止 `myvoiceclone.adapters`，**没有禁止 `myvoiceclone.pipelines`**。这意味着即使 V23 fix 生效，架构测试也不会捕获此违规。

**严重性**：critical。架构边界测试的规则本身不完整 + V5/V6 修复有盲区。

---

### 3.9 【Critical】V32 — test_architecture_boundaries.py 规则不完整

**位置**：`tests/unit/test_architecture_boundaries.py:36-43`

```python
forbidden_rules = {
    ...
    "api": ["myvoiceclone.adapters", "myvoiceclone.pipelines", "myvoiceclone.eval"],
    "cli": ["myvoiceclone.adapters"],  # ← 只禁止 adapters，未禁止 pipelines
}
```

**问题**：api 层禁止了 pipelines 和 eval，但 cli 层只禁止 adapters。CLI 与 API 同为入口层，应该适用相同的禁止规则。当前规则下，CLI 可以随意 import pipelines/eval 而不会被测试捕获。

**严重性**：critical。测试规则的设计缺陷使架构违规可以绕过检测。

---

### 3.10 【High】V33 — 实体层字段与 DB 迁移后 schema 不一致（全局）

**范围**：entities.py 中 5 个核心 entity（Job, Artifact, ModelRun, Report, Dataset）的字段集与 migration 001-007 后的 DB schema 不一致。

详见表（已在 V24 中列出），此处强调最高风险项：

| Entity | 高风险不一致 |
|--------|------------|
| `Job` | `payload_json` 被写为 `params_json` 的别名（007 backfill），但 entity 只用 `payload_json`——新代码若用 `params_json` 列会读到旧值 |
| `Artifact` | `artifact_store.py:51` INSERT 写入 `parent_artifact_id` 和 `job_id` 列，但 007 新增了 `source_artifact_id`、`created_by_job_id`、`kind` 列——新写入的数据在这些列上留 NULL |
| `ModelRun` | `ModelRunRepository.save():383` INSERT 只写 5 列（id, name, dataset_id, status, config_json），但 migration 007 后表有 13 列。新增的 `model_family`, `env_digest`, `git_commit`, `finished_at` 永远不会被填充 |

**严重性**：high。不影响当前 mock 流程（新列为 NULL 且无 NOT NULL 约束），但在生产/半生产环境当代码需要查询新列时会得到全 NULL。

---

### 3.11 【High】V34 — API response schema 与 DB schema 不同步

**位置**：`api/schemas.py`

| Pydantic schema | 缺失的 DB 列（migration 007 后存在） | DB 列名不一致 |
|-----------------|--------------------------------------|---------------|
| `JobResponse:52-58` | `type`, `subject_type`, `subject_id`, `pipeline`, `requested_by`, `started_at`, `finished_at` | — |
| `ModelRunResponse:60-66` | `model_family`, `checkpoint_artifact_id`, `env_digest`, `git_commit`, `finished_at` | — |
| `ReportResponse:73-79` | `kind`, `subject_type`, `subject_id`, `status` | schema 用 `report_type`，DB 新增 `kind` |
| `ReleaseGateResponse:81-87` | `status`, `decision_json` | schema 用 `passed: int`（二进制），DB 新增 `status TEXT`（四态枚举） |

**严重性**：high。API 返回的 JSON 结构与 DB schema 脱节。当需要在 UI 或其他消费者中展示新字段时，API 无法返回。

---

### 3.12 【High】V35 — 无统一 API 信封（envelope）

**位置**：所有 `api/routes_*.py` 文件

**问题**：API 响应没有统一信封。各 route 直接返回 Pydantic model 或 dict：
- `routes_recordings.py:15` → `[RecordingResponse(...)]`（直接 list）
- `routes_datasets.py:17` → `repo.list_all()`（domain dataclass list）
- `routes_reports.py:54` → `repo.list_all()`（domain dataclass list）
- `routes_reports.py:168` → `{"subject_id": ..., "trace_events": ...}`（裸 dict）

错误响应同样不统一：
- `HTTPException(status_code=404, detail="Recording not found")`
- `HTTPException(status_code=400, detail=str(e))` — 透传内部异常消息，信息泄露风险

**建议信封**：
```json
{
  "status": "ok",
  "data": { ... },
  "meta": { "timestamp": "...", "request_id": "..." }
}
```
错误信封：
```json
{
  "status": "error",
  "error": { "code": "NOT_FOUND", "message": "Recording not found" },
  "meta": { "timestamp": "...", "request_id": "..." }
}
```

**严重性**：high。无统一信封使前端/消费者需要为每个 endpoint 编写不同的解析逻辑。属于基础架构缺陷。

---

### 3.13 【High】V36 — services/__init__.py 与 domain/services.py 双写风险

**位置**：
- `src/myvoiceclone/services/__init__.py`（271 行，含全部 service 实现）
- `src/myvoiceclone/domain/services.py`（23 行，"thin compatibility shim" re-export）

**问题**：
1. `domain/services.py:3-11` 注释说 "Actual implementations live in myvoiceclone.services"——但文件路径是 `services/__init__.py`，不在 `domain/` 下。
2. `domain/services.py` 的 re-export 在**模块加载时**执行（line 12: `from myvoiceclone.services import (...)`），意味着每次 `import myvoiceclone.domain.services` 都会执行 `services/__init__.py` 的全部顶层代码——包括 `load_local_config` 调用。
3. 两个文件维护同一组函数签名——如果 `services/__init__.py` 修改了函数参数但 `domain/services.py` 未同步 re-export，会导致调用方拿到过时的接口。

**严重性**：high。双维护面 + 非懒惰 import 引入不必要的耦合。

---

### 3.14 【High】V37 — domain/policies.py 违反分层架构（domain 层访问 storage）

**位置**：`domain/policies.py`

```python
# line 6: from myvoiceclone.config import load_local_config
# line 13: def check_release_policy(conn: sqlite3.Connection, ...)
# line 28: cursor.execute("SELECT dataset_id FROM model_runs WHERE id = ?;", ...)
# line 80: conn.execute("INSERT INTO policy_events ...")
```

**问题**：plan §12.3 明确规定 `domain` 层禁止依赖 storage/config。`policies.py` 位于 `domain/` 包下，但直接依赖 `sqlite3.Connection` 和 `config.load_local_config`——这违反了分层原则。

**严重性**：high。`test_architecture_boundaries.py` 的 domain 层规则（line 37）禁止 `myvoiceclone.storage` 和 `myvoiceclone.api`，但 `sqlite3` 不在禁止列表中（stdlib），所以当前测试不会捕获此违规。但语义上这是分层破坏——domain 层不应直接执行 SQL。

---

### 3.15 【High】V38 — embedding_items 重命名后 vec0_store.py 未同步

**位置**：
- `db/migrations/007_reconcile_to_plan.sql:146-161` — 创建 `embedding_jobs` 新表
- `db/migrations/003_vec0_embeddings.sql:11-18` — 原 `embedding_items` 表
- `storage/vec0_store.py:14,23-28,70,85,94` — **仍然查询 `embedding_items`**

**问题**：migration 007 创建了 `embedding_jobs` 表但**未删除 `embedding_items`**（line 157-158 复制了数据但后续无 `DROP TABLE IF EXISTS embedding_items`）。`vec0_store.py` 的所有 SQL 查询仍然引用 `embedding_items`。这意味着：
1. 如果 migration 007 成功运行，`vec0_store.py` 的查询会找到 `embedding_items` 中的**旧数据**（未被迁移填充的新列全 NULL）
2. 如果 future 代码切换到 `embedding_jobs` 表，vec0_store.py 不会跟随

**严重性**：high。重命名未完成——两表并存，代码用旧表名，数据一致性分裂。

---

### 3.16 【Medium】V39 — pydantic schemas.py 中 ReleaseGateResponse.passed 为 int 非 bool

**位置**：`api/schemas.py:84` — `passed: int`

**问题**：`passed` 使用 `int` 类型注解（而非 `bool`），且 migration 007 已新增 `status TEXT` 列。API 仍然使用旧的二进制 passed 语义，与新 DB schema 的四态 status（pending/passed/failed/waived）不一致。

---

### 3.17 【Medium】V40 — conftest.py setsampwidth 重复调用

**位置**：`tests/conftest.py:18-19`

```python
w.setsampwidth(2) # 16-bit
w.setsampwidth(2)
```

**问题**：同一行代码出现两次——复制粘贴错误。不影响功能，但表明代码审查不够仔细。

---

### 3.18 【Medium】V41 — CLI eval 命令硬编码 mock 值且未标记

**位置**：`cli.py:275-276`

```python
conn.execute("INSERT INTO eval_metrics (run_id, metric_name, metric_value) VALUES (?, 'speaker_similarity', 0.85);")
conn.execute("INSERT INTO eval_metrics (run_id, metric_name, metric_value) VALUES (?, 'wer', 0.07);")
```

**问题**：写死 0.85 和 0.07——没有说明这是 mock-only。如果用户用真实模型跑 `mvc eval`，会得到假指标。

---

### 3.19 【Medium】V42 — 缺少 `mvc infer tts` 命令

**位置**：`cli.py:282-293`（仅有 `infer vc`，无 `infer tts`）

**问题**：plan §15.2 要求 `mvc infer vc` 和 `mvc infer tts` 两条命令。实际只实现了 vc。services/__init__.py 中有 `service_synth_xtts`（TTS），但没有 CLI 入口。

---

### 3.20 【Medium】V43 — compose.yaml 中 datasets 命令引用不存在的 dataset

**位置**：`compose.yaml:64`

```yaml
command: ["train", "sovits", "--dataset", "my_dataset"]
```

**问题**：`my_dataset` 是一个**硬编码的不存在 dataset 名**。用户必须手动创建并冻结同名 dataset 才能使用此 compose service。compose.yaml 的注释（第 63 行）提到了这一点，但对首次使用的用户不友好——应该提供一个 docker-compose override 示例或使用环境变量。

---

### 3.21 【Medium】V44 — download_models.sh 路径与 configs/models.yaml 不一致

**位置**：
- `scripts/download_models.sh:17` → `mkdir -p models/base`
- `configs/models.yaml:1` → `pretrained_dir: "models/pretrained"`

**问题**：脚本创建 `models/base/`，配置期望 `models/pretrained/`。如果未来模型下载实现后，模型会被放到错误的目录，pipeline 找不到。

---

### 3.22 【Low】V45 — services/__init__.py 导入了未使用的 resolve_db_path

**位置**：`services/__init__.py:25`

```python
from myvoiceclone.config import load_local_config, resolve_db_path
```

`resolve_db_path` 在 services/__init__.py 中从未被使用。

---

### 3.23 【Low】V46 — 无 @pytest.mark.live, @pytest.mark.gpu, @pytest.mark.slow 测试

**位置**：整个 `tests/` 目录

pytest.ini:8-9 注册了 `live`、`gpu`、`slow` 三个 marker，但全项目 50+ 测试文件中没有一处使用这些 marker。虽然 plan 允许这些 marker "初始为空"，但 plan §8.1 说 "默认运行 '否'"——marker 存在但无测试，符合设计意图。标记为 low。

---

## 4. 数据库结构综合评估

### 4.1 整体评价

migration 链（001-007）覆盖了 plan §14.3 要求的 15 张表 + 3 张 vec0 虚表。核心问题不在于"少了什么表"，而在于：

1. **命名双轨**：migration 007 同时保留了旧列名（`name`/`payload_json`/`artifact_type`/`job_id`）和新列名（`type`/`params_json`/`kind`/`created_by_job_id`），没有明确 canonical choice。
2. **Python↔DB 脱节**：entities.py 和 repositories.py 全部使用旧列名，007 新增的列永远不会被写入。
3. **migration 本身有语法错误**：V24 的 `GENERATED ALWAYS AS VIRTUAL` 会导致 migration 007 在标准 SQLite 上失败。

### 4.2 状态流转是否足够

plan §14.4 定义的状态机如下：

```
recording: new → ingested → diarized → sliced → cleaned → transcribed → scored → curated → dataset_ready
segment: new → needs_review → keep | drop | fixed
dataset: draft → frozen → training → evaluated → rejected | release_candidate
job: queued → running → succeeded | failed | canceled
model_run: queued → preparing → training → checkpointed → succeeded | failed | canceled
report: draft → generated → archived
release_gate: pending → passed | failed | waived
```

**当前实现**：
- `recording` 状态链：仅实现了 `unprocessed→processed`（ingest.py:99），后续步骤只修改 segment 状态，不更新 recording 状态。recording 的状态机**未被驱动**。
- `segment` 状态链：完整但只有 `score.py` 和 `curate.py` 驱动。
- `dataset` 状态链：`cli.py:170` 创建时置 `active`（不在 plan canonical 状态中），freeze 后变 `frozen`。缺少 `training→evaluated→rejected/release_candidate` 的自动流转。
- `job` 状态链：runner.py 使用 `pending→running→completed/failed/cancelled`，与 plan 的 `queued→running→succeeded/failed/canceled` **命名不一致**。plan 用 `succeeded`，代码用 `completed`。两者都在 migration 007 CHECK 约束中，但代码和 plan 之间有漂移。
- `model_run` 状态链：train.py 使用 `queued→preparing→training→checkpointed→completed/failed/cancelled`，与 plan 一致，除了 `completed` vs `succeeded` 的相同漂移。
- `report` 状态链：eval/report.py 使用 `draft→generated`（`archived` 未实现）。
- `release_gate` 状态链：routes_reports.py 使用 `passed: 0/1`（二进制），迁移后新增 `status` 列（四态）但未被代码使用。

---

## 5. Docker & 容器环境综合评估

### 5.1 容器可唤醒性

| 组件 | 状态 | 说明 |
|------|------|------|
| Dockerfile.preprocess | ⚠️ 缺 demucs | preprocess extras 不含 demucs → clean 步骤崩溃（V30） |
| Dockerfile.train | ✅ 基本可构建 | NGC 25.03 是 aarch64 compatible，含 PyTorch + CUDA。但未安装 soundfile（torchaudio 间接依赖可能不满足） |
| compose.yaml GPU | ✅ | 有 `deploy.resources.reservations.devices` + nvidia driver |
| compose.yaml volumes | ❌ 无数据隔离 | 指向 `/mnt/usb/workspace/myvoiceclone/{db,data,models}` 而非 `/mnt/usb/workspace/myvoiceresearch/` (V29) |
| compose.yaml 命令 | ⚠️ 引用占位 dataset | `my_dataset` 不存在 (V43) |
| ENTRYPOINT | ⚠️ 入口点问题 | `ENTRYPOINT ["python", "-m", "myvoiceclone.cli"]` 是可行的。但 pyproject.toml 中的 `cli:main` 入口点本身 broken (V27) |

### 5.2 数据存储合理性

| 路径 | 物理位置 | 合规？ | 说明 |
|------|---------|--------|------|
| `db/` | `/mnt/usb/workspace/myvoiceclone/db/` | ❌ | 应在 `/mnt/usb/workspace/myvoiceresearch/db/` |
| `data/` | `/mnt/usb/workspace/myvoiceclone/data/` | ❌ | 应在 `/mnt/usb/workspace/myvoiceresearch/data/` |
| `models/` | `/mnt/usb/workspace/myvoiceclone/models/` | ❌ | 应在 `/mnt/usb/workspace/myvoiceresearch/models/` |

**当前仅 `/mnt/usb/workspace/myvoiceclone/models/registry/` 存在且为空。`/mnt/usb/workspace/myvoiceresearch/` 完全不存在。**

### 5.3 模型下载与训练产出链路

```
models.yaml: pretrained_dir → "models/pretrained"
models.yaml: checkpoints_dir → "models/checkpoints"
models.yaml: registry_dir → "models/registry"
download_models.sh → mkdir -p models/base  ← 路径与配置不一致 (V44)
compose.yaml → ../../models:/app/models
train.py → export to models/registry/ (line 385-387)
```

训练产出的 checkpoint 和 exported model 会写入 `artifact_store.root_dir`（即 `data/artifacts`），而非 `models/` 目录。只有 So-VITS export 步骤（train.py:387）将文件写入 `models/registry/`。checkpoint 的 `.pth` 文件在 `data/artifacts/checkpoint/` 下，模型注册表快照在 `data/artifacts/model_registry/` 下。**这导致了训练产出的碎片化**——checkpoint 和 model registry 分属不同目录。

---

## 6. API 接口综合评估

### 6.1 信封统一性：未实现

全部 7 个 route 文件均返回裸模型或裸 dict，无统一 `{status, data, meta}` 信封。错误响应使用 FastAPI 原生 `HTTPException` 的 JSON 格式，但 detail 字段内容不统一（有的返回静态字符串，有的返回 `str(e)` 透传内部异常）。

### 6.2 Schema 与 DB 对齐：不同步

5 个 Pydantic response schema 中有 4 个与 migration 007 后的 DB schema 不一致（详见 V34）。API 表面上"能工作"（因为新列为 NULL 且无 NOT NULL 约束），但语义上返回的 JSON 是不完整的。

### 6.3 路由与 Plan 对照

| plan §15.1 路由 | 实际路由 | 偏差 |
|----------------|---------|------|
| `POST /recordings` → `{recording_id, status}` | `POST /api/recordings?filepath=...` → `JobResponse` | 参数方式和响应类型均不同 |
| `POST /runs/train` | `POST /api/training/jobs` | 路径不同 |
| `POST /runs/eval` | 无对应路由 | **缺失** |
| `POST /inference/vc` | 无独立路由 | 合并为 `POST /api/inference` |
| `POST /inference/tts` | 无独立路由 | **缺失** |
| `GET /audit/{subject_type}/{subject_id}` | `GET /api/audit/trace?subject_id=...&subject_type=...` | 路径参数→查询参数 |

---

## 7. 交叉分析：修复引入的新问题

第 1 轮修复引入了以下新 bug 或不完整：

| 新发现编号 | 第 1 轮关联 | 问题性质 |
|-----------|-----------|---------|
| V25 (AudioProbe 重复) | V9 fix | V9 修复添加了 3 字段 AudioProbe 但未删除旧 4 字段版 → TypeError |
| V27 (entry_point broken) | 无直接关联 | V12 修复使 Dockerfile 可安装了 extras，但安装后 `myvoiceclone` 命令不可用因为 `cli:main` 不存在 |
| V28 (fakes import 失败) | V10 partial-fix | V10 创建了 fakes 目录，但 fakes 引用不存在的 entity 类型 → ImportError |
| V31 (CLI 直连 pipeline) | V5/V6 fix | V5/V6 修复了 train 命令但遗漏了 cli.py:13 的顶层 import |
| V38 (embedding_items 残留) | V1 fix | 007 创建了 embedding_jobs 但未删除旧表，vec0_store.py 仍引用旧表 |

---

## 8. 优先级排序与修复建议

### 8.1 阻断级（必须在进入 P5 前修）

| 优先级 | 编号 | 问题 | 修复方向 |
|--------|------|------|---------|
| P0 | V25 | AudioProbe 重复定义 TypeError | 删除 entities.py:125-129 重复定义，保持 3 字段版（给 format 默认值） |
| P0 | V27 | CLI entry_point broken | pyproject.toml:28 改为 `"myvoiceclone.cli:app"` |
| P0 | V28 | fakes 引用不存在 entity 类型 | 删除不存在的 import（TranscriptResult 等）或定义它们 |
| P0 | V24 | migration 007 GENERATED ALWAYS 语法 | 删除 VIRTUAL 列，简化 jobs 表 |
| P0 | V30 | preprocess 缺 demucs 依赖 | pyproject.toml preprocess extras 加 `"demucs"` |
| P0 | V31 | CLI 直接 import pipelines | cli.py:13 改为通过 services 或延迟 import |

### 8.2 高优（进入 P5 前修）

| 优先级 | 编号 | 问题 | 修复方向 |
|--------|------|------|---------|
| P1 | V26 | states.py 枚举零使用 | 在 runner.py/train.py/cli.py/score.py 中替换裸字符串为 enum |
| P1 | V29 | 数据隔离缺失 | 创建 `/mnt/usb/workspace/myvoiceresearch/{db,data,models}`，更新 compose.yaml volumes |
| P1 | V32 | 架构测试规则不完整 | cli 层 forbidden_rules 增加 `myvoiceclone.pipelines`, `myvoiceclone.eval` |
| P1 | V33 | 实体层与 DB 不一致 | 更新 entities.py 中的 Job/Artifact/ModelRun/Report dataclass |
| P1 | V34 | API schema 与 DB 不一致 | 更新 schemas.py 中的 response models |
| P1 | V37 | policies.py 分层破坏 | 将 SQL 操作移到 storage 层 |
| P1 | V38 | embedding_items/embedding_jobs 双表 | 统一为 embedding_jobs，更新 vec0_store.py |

### 8.3 中优（P5 过程中修）

| 优先级 | 编号 | 问题 |
|--------|------|------|
| P2 | V35 | 统一 API 信封 |
| P2 | V36 | services 双写风险 |
| P2 | V40 | conftest.py setsampwidth 重复 |
| P2 | V41 | CLI eval 硬编码 mock |
| P2 | V42 | 缺少 infer tts 命令 |
| P2 | V43 | compose.yaml 硬编码 dataset |
| P2 | V44 | download_models.sh 路径不一致 |

### 8.4 低优

| 优先级 | 编号 | 问题 |
|--------|------|------|
| P3 | V45 | services 未使用 import |
| P3 | V46 | 缺 live/gpu/slow marker 测试 |

---

## 9. 总结

### 9.1 关键数据

- **总计发现 29 条** new finding
- **critical 13 条**：包括 1 个 migration SQL 语法错误、1 个运行时 TypeError、1 个 CLI 完全不可用、3 个架构违规、3 个 import 失败、1 个数据隔离缺失、1 个 Docker 依赖缺失、1 个 enum dead code、2 个 namespace 漂移
- **high 8 条**：系统性的 Entity↔DB↔API Schema 三层不一致
- **第 1 轮修复引入 5 个新 bug**

### 9.2 最危险的发现

1. **V24 + V25 + V27 + V28 + V30**：这 5 个 critical 都是**纯运行时阻塞性问题**——migration 失败、AudioProbe 调用崩溃、CLI 入口点不存在、fakes import 失败、demucs 缺失。任何一个都会导致系统在特定代码路径上不可用。
2. **V29**：数据隔离完全未实现。当开始载入真实 20h+ 音频时，宿主机硬盘会被迅速填满。
3. **V26 + V31 + V32**：架构测试本身有设计漏洞，且 V5/V6/V15 的修复实质性不完整——enum 为零使用，CLI 仍有直接 pipeline import。

### 9.3 对下一步工作的建议

**P0 block（6 个 critical runtime bugs）必须在进入 P5 长训之前全部修复。** P1 的 7 个 schema alignment issues 可以在 P5 的第一阶段并行修复（因为它们主要影响正确的数据写入而非读取）。P2 的 API envelope 和 cleanup items 可以在 P5-P6 之间处理。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| v1.0 | 2026-06-13 | DeepSeek | 初始第 2 轮审查报告：29 条 finding，13 critical + 8 high + 6 medium + 2 low |
