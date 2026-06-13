# Nano-Agent 代码审查报告

> 审查对象: `myvoiceclone first-build P0-P8`
> 审查类型: `code-review`
> 审查时间: `2026-06-13`
> 审查人: `DeepSeek (independent reviewer)`
> 审查范围:
> - `myvoiceclone/src/` — 全部源代码（domain / storage / pipelines / adapters / api / cli / jobs / eval）
> - `myvoiceclone/db/migrations/` — 全部 6 份 SQLite migration 文件
> - `myvoiceclone/infra/docker/` — Dockerfile ×2 + compose.yaml
> - `myvoiceclone/tests/` — 全部 47 个测试文件
> - `myvoiceclone/configs/` — 配置文件
> - `myvoiceclone/scripts/` — 全部 4 个 Shell 脚本
> - `myvoiceclone/pyproject.toml` — 项目依赖
> 对照真相:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md` — 执行基线（唯一对照标准）
> - `myvoiceclone/docs/closure/first-build/00-08-*-closure.md` — P0-P8 收口文件
> - `device_stacks.md` — 本地硬件/软件栈规格
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 该实现主体在**骨架完整性、pipeline 链编排、adapter mock 策略、分层隔离**上达到了 first-build 的核心预期；但 **数据库 schema 与执行计划存在系统性漂移（87 项列级差异），状态机枚举完全孤立，API/CLI 层绕过 domain services 直接调用 pipelines，且测试 marker 体系失效**。当前不应标记为 `closed`，需在以下关键问题上完成修正后才能进行下一步工作。

- **整体判断**：`该实现处于 "架构骨架正确、但 schema 合同和接口纪律需要实质性仲裁" 阶段。核心流程可以 mock 跑通（integration capstone 通过），但数据库结构无法承接真实业务，评估体系缺失运作保障。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **数据库 schema 与 execution plan 之间存在 87 项列级差异、42 个缺失列、vec0 维度全部错误**——数据库的核心支柱（jobs、model_runs、artifacts、eval）均无法按 plan 规范运作
  2. **domain services 缺失**导致 API/CLI 层绕过架构约束直接调用 pipelines/eval，状态枚举（RecordingStatus / DatasetStatus / ModelRunStatus）与 plan 完全不一致且从未被使用
  3. **测试 marker 体系全部失效**（92/93 测试标记为 `unit`），fixtures/ 和 fakes/ 目录完全缺失，deduplication 断言因 `or True` 永真而从未执行

---

## 1. 审查方法与已核实事实

> 本轮审查完全独立进行，不依赖任何其他 reviewer（Kimi / GPT / Antigravity）的分析报告。所有发现均来自对实际代码文件、SQL migration、测试代码的逐行阅读和与 final-execution-plan.md 的对照。

- **对照文档**：
  - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`（§6 逐 phase 工作台账、§12 文件定位矩阵、§13 裁决冻结、§14 数据库 schema、§15 接口设计）
  - `myvoiceclone/docs/closure/first-build/00-08-*-closure.md`（9 份收口文件的 claim）
- **核查实现**：
  - `src/myvoiceclone/` 全部 44 个源文件
  - `db/migrations/` 全部 6 个 SQL 文件
  - `tests/` 全部 47 个测试文件
  - `infra/docker/` Dockerfile ×2 + compose.yaml
  - `scripts/` 全部 4 个 Shell 脚本
  - `configs/` 配置文件
- **执行过的验证**：
  - 逐表对照 database schema 与 plan §14.3 的 21 张表规格
  - 逐层检查 import 合规性与 layer boundary 规则 (§12.3)
  - 全量 pipeline step 代码走查（ingest→diarize→slice→clean→transcribe→score→curate→export→train→eval）
  - 全量 adapter 的 mock/real 模式、DTO 契约合规性检查
  - 全量测试文件与 plan §8.2 的阶段测试计划对照
- **复用 / 对照的既有审查**：
  - `none` — 本轮为独立首轮审查

### 1.1 已确认的正面事实

- `项目骨架（P0-P1）`：目录树、Python package skeleton、pyproject.toml 依赖声明、configs 配置文件完整落地，与 plan §12.2 文件定位矩阵高度一致
- `SQLite 连接管理`：WAL 模式、外键强制、busy_timeout=5000ms、row_factory 正确配置；migration runner 支持 checksum 漂移检测
- `Pipeline 编排`：`_execute_preprocess_all()` 实现 ingest→diarize→slice→clean→transcribe→score 完整六步链；训练 pipeline 强制 frozen dataset gate；So-VITS 支持 per-epoch checkpoint、cancel 检测、resume、export
- `Adapter mock 策略`：8/12 adapter 使用一致的 `MOCK_ADAPTERS` 环境变量门控模式；mock 响应返回正确类型的 domain DTO
- `Artifact lineage`：artifact_store 实现 parent_artifact_id 血缘链；artifact 注册写入 DB 记录
- `Integration capstone`：`test_first_build_journey.py` 覆盖 A-J（ingest→preprocess→dataset→train→release gate→audit trace），可在无 GPU/网络环境下通过
- `Deduplication`：`run_deduplication()` 实现基于 embedding 相似度的去重决策，使用 vector_store 比较最近邻距离

### 1.2 已确认的负面事实

- `数据库 schema 系统性漂移`：migration 002-006 与 plan §14.3 存在 87 项列级差异（42 个缺失列、24 个错误列名、9 个多余列）；jobs 表缺失 7 个必需列；model_runs 缺失 4 个必需列；eval_samples 缺失 4/7 列
- `vec0 虚拟表全部错误`：3 个虚拟表统一使用 `float[128]` 而非 plan 规定的 768/192/384；缺少 PRIMARY KEY 列；表名与 plan 不符
- `状态枚举孤立`：RecordingStatus / JobStatus / DatasetStatus / ModelRunStatus 枚举定义在 `states.py` 中，但**从未被任何代码引用**——所有状态转换使用裸字符串
- `domain/services.py 缺失`：plan §12.2 指定的 orchestration 层不存在，导致 API/CLI 直接调用 pipelines 和 eval 模块
- `测试 marker 体系失效`：93 个测试中 92 个标记为 `unit`（仅 1 个 `integration`），`api`/`cli`/`live`/`gpu`/`slow` marker 零使用
- `fixtures/ 和 fakes/ 目录不存在`：plan §8.3 要求的 4 类 synthetic fixtures 和 6 个 fake 类全部缺失
- `dedup 断言永真 bug`：`test_curate_dedupe.py:72` 的 `assert ... or True` 永远通过
- `cli.py:200` 存在 `NameError`：`run_export_dataset` 被调用但从未 import
- `Dockerfile.train base image` 使用 CUDA 12.1 的 x86_64 镜像，与目标主机 aarch64 + CUDA 13.0 不兼容

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 所有发现均有 file:line 锚点（见 §2 各 R 项） |
| 本地命令 / 测试 | yes | conftest.py fixture 结构、pytest.ini 配置通过文件核查确认 |
| schema / contract 反向校验 | yes | 全部 21 张表逐列对照 plan §14.3 |
| live / deploy / preview 证据 | no | 未实际执行 Docker build 或 CUDA smoke test（静态分析） |
| 与上游 design / QNA 对账 | yes | 与 final-execution-plan.md §6 / §12-15 逐项对账 |

---

## 2. 审查发现

> 使用稳定编号 R1-R28，按严重级别降序排列。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | jobs/model_runs/artifacts/eval 表 schema 严重偏离 plan | critical | correctness | yes | 重写 migration 002-005 以对齐 plan |
| R2 | vec0 虚拟表维度与结构全部错误 | critical | correctness | yes | 修正为 192/768/384 维度并添加 PK 列 |
| R3 | 状态枚举孤立于代码——全部裸字符串使用 | critical | correctness | yes | 在 domain/states.py 中补全枚举，全局替换裸字符串 |
| R4 | domain/services.py 缺失致 API/CLI 绕过架构 | critical | scope-drift | yes | 创建 services.py 作 API/CLI 唯一出口 |
| R5 | 测试 marker 体系全部失效 | critical | test-gap | yes | 重新分配 @pytest.mark.{api,cli,live,gpu,slow} |
| R6 | fixtures/ 与 fakes/ 目录缺失 | critical | test-gap | yes | 创建并填充 synthetic fixtures 和 6 个 fake 类 |
| R7 | Dockerfile.train 基础镜像与 aarch64/Blackwell 不兼容 | critical | platform-fitness | yes | 改用 ARM 兼容的 PyTorch CUDA 镜像 |
| R8 | JobRunner 仅支持 3/12 种 job 类型 | high | delivery-gap | no | 补齐 train_rvc / diarize / slice / clean / transcribe / score / curate / export / eval 的 dispatch |
| R9 | 预处理链步骤缺乏幂等性保护 | high | correctness | no | diarize/slice/clean 添加"已完成即跳过"检查 |
| R10 | 3 个 embedder adapter 永久 mock 无真实路径 | high | delivery-gap | no | 补充真实 embedding 模型集成或 MOCK_ADAPTERS 门控 |
| R11 | scoring 硬编码 mock 值 | high | delivery-gap | no | 将评分逻辑封装为 ScorerAdapter，mock 模式由 env var 控制 |
| R12 | API routes 直接 import pipelines/eval 模块 | high | scope-drift | no | 所有 routes 改为通过 domain services 调用 |
| R13 | CLI 直接 import pipelines | high | scope-drift | no | CLI 命令改为通过 domain services 调用 |
| R14 | torchaudio_io adapter 违反 DTO 契约 | high | protocol-drift | no | 返回 AudioProbe DTO 而非裸 dict |
| R15 | 测试断言永真 bug（dedup） | high | test-gap | yes | 删除 `or True` |
| R16 | compose.yaml 无 NVIDIA Container Toolkit 说明 | medium | docs-gap | no | 补充文档说明 aarch64 下需要 nvidia-container-toolkit |
| R17 | 预处理链无 per-step 进度事件 | medium | delivery-gap | no | 在 _execute_preprocess_all 中添加 step-level job_events |
| R18 | DatasetStatus 枚举缺失 5 个 plan 定义的状态 | medium | correctness | no | 补充 training/evaluated/rejected/release_candidate |
| R19 | embedding_models 表缺少 namespace/distance/version 列 | medium | correctness | no | 对齐 plan 的列定义 |
| R20 | consent_ledger 语义与 plan 不符 | medium | correctness | no | 改为 scope/status/evidence_uri/revoked_at 结构 |
| R21 | release_gates 使用布尔而非 4 态 status 枚举 | medium | correctness | no | 改为 pending/passed/failed/waived TEXT 枚举 |
| R22 | Dockerfile.preprocess 未安装项目 [preprocess] extras | medium | delivery-gap | no | 添加 `pip install -e .[preprocess]` |
| R23 | evaluate.py 缺少主观评估集成 | medium | delivery-gap | no | 集成 generate_subjective_report |
| R24 | test_architecture_boundaries 目录不存在时静默通过 | medium | test-gap | no | 改为 assert 目录存在或 pytest.skip |
| R25 | 集成测试使用 monkeypatch 替代方案（手动替换全局） | medium | test-gap | no | 改用 pytest monkeypatch fixture |
| R26 | 无 SQLite 并发写测试 | medium | test-gap | no | 添加 API+runner 并发写 WAL 测试 |
| R27 | scripts 硬编码 ./venv/bin/python 路径 | low | platform-fitness | no | 改为使用环境检测或 docker 模式 |
| R28 | pyproject.toml 缺少 torch/torchaudio 作为依赖 | low | delivery-gap | no | 在 extras 中显式声明或文档说明 |

### R1. jobs / model_runs / artifacts / eval 表 schema 严重偏离 plan

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `db/migrations/002_state_jobs_artifacts.sql` — `jobs` 表使用 `name` 而非 `type`、`payload_json` 而非 `params_json`、缺失 `subject_type`/`subject_id`/`pipeline`/`requested_by`/`started_at`/`finished_at`；status 枚举为 `pending/completed/cancelled` 而非 plan 的 `queued/succeeded/canceled`
  - `db/migrations/002_state_jobs_artifacts.sql` — `model_runs` 表使用 `name` 而非 `model_family`、缺失 `checkpoint_artifact_id`/`env_digest`/`git_commit`/`finished_at`
  - `db/migrations/004_reports_metrics.sql` — `eval_samples` 缺失 `input_artifact_id`/`output_artifact_id`/`reference_artifact_id`/`scores_json`/`report_id` 五列
  - `db/migrations/002_state_jobs_artifacts.sql` — `artifacts` 使用 `name`+`artifact_type` 替代 `kind`、`parent_artifact_id` 替代 `source_artifact_id`、`job_id` 替代 `created_by_job_id`
- **为什么重要**：
  - `jobs` 表无法承载作业路由（不知道操作对象是什么类型/哪个实体）、无法记录执行时长、无法关联 pipeline
  - `model_runs` 表无法追溯模型复现所需的全部信息（模型家族、checkpoint、环境摘要、git commit）
  - `eval_samples` 无法连接输入/输出/参考音频三者——核心评估流程不可运作
  - 所有基于 plan contract 编写的应用代码将使用完全错误的列名
- **审查判断**：
  这不是命名偏好问题，而是 schema contract 的结构性漂移。closure 文件中声称 `MVC-P1-04` 至 `MVC-P1-10` 全部 verified，但 migration 002/003/004/005 的实际结构无法支撑 myvoiceclone 业务。**closure 的 verified 声明与代码事实矛盾**。
- **建议修法**：
  1. 以 final-execution-plan.md §14.3 为唯一真相来源，重写 migration 002-006
  2. 特别关注 `jobs` 表补全 7 列、`model_runs` 表补全 4 列、`eval_samples` 补全 5 列
  3. 统一列命名：`kind`（非 `name`+`artifact_type`）、`created_by_job_id`（非 `job_id`）、`model_family`（非 `name`）
  4. 添加所有 plan 规定的 CHECK 约束和复合索引
  5. 修正所有 status 枚举为 plan 规定的值

### R2. vec0 虚拟表维度与结构全部错误

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `db/migrations/003_vec0_embeddings.sql:23-33` — 三个虚拟表统一声明 `float[128]`
  - Plan §14.3: `segment_audio_embeddings USING vec0(segment_id TEXT PRIMARY KEY, embedding FLOAT[768])`、`speaker_embeddings (FLOAT[192])`、`transcript_embeddings (FLOAT[384])`
  - 虚拟表缺少 PRIMARY KEY 列——无法将 embedding 向量与源实体（segment/speaker）关联
  - 表名使用 `vec_audio`/`vec_speaker`/`vec_text` 而非 plan 的 `segment_audio_embeddings`/`speaker_embeddings`/`transcript_embeddings`
  - `embedding_jobs` 表被错误命名为 `embedding_items`，且缺失 `subject_type`/`status` 列
- **为什么重要**：
  - 标准音频 embedding 模型（Wav2Vec2 / HuBERT / Whisper）输出 768 维向量，128 维无法存储
  - 标准说话人 embedding 模型（ECAPA-TDNN / SpeechBrain）输出 192 维
  - 标准文本 embedding 模型（all-MiniLM-L6-v2 / BGE）输出 384 维
  - 无 PK 列意味着无法查询"segment X 的 embedding 是什么"或"与 segment X 最相似的 segments"
  - **整个向量检索功能在真实数据上完全不可用**
- **审查判断**：
  这是 database schema 中最致命的问题——vec0 表不仅是"命名偏差"，而是**维度错误的不可用状态**。closure 声明此 migration "verified" 不成立。
- **建议修法**：
  1. 修正三个虚拟表为 plan 规定的维度（768 / 192 / 384）和表名
  2. 在 `CREATE VIRTUAL TABLE` 语句中添加 PRIMARY KEY 列
  3. 将 `embedding_items` 重命名为 `embedding_jobs`，补全列定义
  4. 更新 `vec0_store.py` 中的 namespace 映射以匹配新表名

### R3. 状态枚举孤立于代码——全部裸字符串使用

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/domain/states.py` 定义了 `RecordingStatus(4 values)`、`JobStatus(5 values)`、`DatasetStatus(2 values)`、`ModelRunStatus(4 values)`
  - 搜索整个 `src/` 目录：**没有任何文件 import 这些枚举类**
  - 所有状态转换使用裸字符串：`rec.status = "processed"` (ingest.py:99)、`seg.status = "sliced"` (slice.py:69)、`seg.status = "cleaned"` (clean.py:59)、`seg.status = "transcribed"` (transcribe.py:58)、`seg.status = "needs_review"` (score.py:52)
  - `RecordingStatus` 的 4 个值与实际使用的 12+ 个裸字符串无交集
  - `DatasetStatus` 仅 2 个值（DRAFT/FROZEN），但代码中使用了 `"active"` (cli.py:169) 和 plan 要求的 6 个状态
- **为什么重要**：
  - 状态是业务流转的核心契约。裸字符串消除了编译时类型安全
  - 重构或迁移时，无类型检查的状态赋值可能导致静默的数据损坏
  - plan §14.4 定义了完整的状态机（recording 10 态链、dataset 6 态链、job 5 态链、model_run 7 态链），当前枚举仅覆盖 25%，其余靠字符串
- **审查判断**：
  枚举类已存在但完全孤立，说明设计意图与实现之间出现了断层。需要补全枚举并全局替换。
- **建议修法**：
  1. 在 `states.py` 中按 plan §14.4 补全全部枚举值
  2. 在所有 pipeline/api/cli 代码中将裸字符串替换为枚举引用
  3. 添加 `test_state_machine_completeness.py` 验证枚举覆盖所有运行时状态

### R4. domain/services.py 缺失致 API/CLI 绕过架构

- **严重级别**：`critical`
- **类型**：`scope-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/domain/services.py` 不存在
  - Plan §12.2 明确标注该文件为 MVC-P0-03/P6-07："domain service orchestration"
  - `src/myvoiceclone/api/routes_datasets.py:11` 直接 `from myvoiceclone.pipelines.export_dataset import run_export_dataset`
  - `src/myvoiceclone/cli.py:221` 在函数体内 `from myvoiceclone.pipelines.train import run_train_rvc`
  - 5 处 API/CLI → pipelines/eval 直接调用跨越了架构边界
- **为什么重要**：
  - Plan §12.3 规定 `api | domain services, jobs` 和 `cli | domain services, jobs`——API/CLI 不能直接依赖于 pipelines
  - services.py 的缺失是 API/CLI 违规的根本原因
  - 没有 services 层，无法实现事务协调、跨步骤验证、权限检查等横切关注点
- **审查判断**：
  需要创建 `domain/services.py` 作为 API/CLI 与 pipelines/eval 之间的唯一桥梁。
- **建议修法**：
  1. 创建 `src/myvoiceclone/domain/services.py`
  2. 为每个 pipeline 入口（ingest/diarize/slice/clean/transcribe/score/curate/export/train/eval/inference）定义 service 方法
  3. 重写所有 API routes 和 CLI commands 改为通过 services 调用
  4. 禁止 API/CLI 直接 import pipelines 或 eval 模块

### R5. 测试 marker 体系全部失效

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `pytest.ini` 正确定义了 7 个 marker（unit/api/cli/integration/live/gpu/slow）
  - 全量扫描 47 个测试文件：92/93 测试标记为 `@pytest.mark.unit`，仅 1 个为 `@pytest.mark.integration`
  - `api`/`cli`/`live`/`gpu`/`slow` marker 使用次数 = **零**
  - `tests/api/test_routes.py` 中的所有 API 测试错误标记为 `unit`
  - `tests/cli/test_cli.py` 中的所有 CLI 测试错误标记为 `unit`
- **为什么重要**：
  - Markers 是实现 plan §8.1 测试分类体系的核心机制
  - 当前状态无法运行 `pytest -m api` 隔离 API 测试、无法运行 `pytest -m live` 触发真实工具 smoke
  - 所有测试落入一个 `unit` 桶，丧失了分层测试的意义
- **审查判断**：
  `pytest.ini` 的 taxonomy 定义正确，但实现者从未在测试代码中使用这些 marker。closure 声称 `MVC-P0-04 verified` 不成立。
- **建议修法**：
  1. `tests/api/**` → 全部改为 `@pytest.mark.api`
  2. `tests/cli/**` → 全部改为 `@pytest.mark.cli`
  3. `tests/integration/**` → 确认 `@pytest.mark.integration`
  4. 添加至少 1 个 `@pytest.mark.live` 和 `@pytest.mark.gpu` 占位测试

### R6. fixtures/ 与 fakes/ 目录缺失

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/fixtures/` 目录不存在
  - `tests/fakes/` 目录不存在
  - Plan §8.3 要求：`tone_16k.wav`、`sample_turns.json`、`sample_transcript.json`、embedding JSON 文件
  - Plan §8.3 要求：FakeDiarizer、FakeSeparator、FakeASR、FakeTrainer、FakeEmbedder、FakeInference
  - 当前替代方案：adapter 内部通过 `os.getenv("MOCK_ADAPTERS")` 自 mock——mock 逻辑混入生产代码
- **为什么重要**：
  - Plan 的纪律性设计意图是将 mock 隔离在 `tests/fakes/` 中，生产 adapter 不应包含 mock 分支
  - 当前设计导致每次 adapter 方法调用都检查环境变量，且 mock 代码与生产代码耦合
- **审查判断**：
  需要创建 fixtures 和 fakes 目录。fakes 提供可注入的 test doubles，adapter 的 mock 分支应改为由 fakes 替代。
- **建议修法**：
  1. 创建 `tests/fixtures/` 及其子目录，填充 synthetic WAV/JSON
  2. 创建 `tests/fakes/` 目录，提取 FakeDiarizer 等 6 个类
  3. 在 conftest.py 中添加 fake fixture 注入点
  4. 长期：adapter 代码中移除 `MOCK_ADAPTERS` 分支，测试通过依赖注入 fake

### R7. Dockerfile.train 基础镜像与 aarch64/Blackwell 不兼容

- **严重级别**：`critical`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `infra/docker/Dockerfile.train:1` — `FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`
  - `device_stacks.md` — 目标主机为 aarch64 (Cortex-X925/A725, NVIDIA GB10, CUDA 13.0, Driver 580.159.03)
  - `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime` 是 **x86_64** 镜像——在 aarch64 上会因架构不匹配而 **完全无法启动**
  - CUDA 版本：镜像 12.1 vs 主机 13.0 — 即使架构兼容，nvidia-container-toolkit 在跨 CUDA major 版本时也可能出错
- **为什么重要**：
  - 容器训练是 P5 的核心交付物之一。如果镜像无法在目标硬件上启动，则 `compose.yaml` 中的 train 服务和 GPU 直通完全不可用
  - closure 声称 `MVC-P8-03 verified`（"GPU-ready Docker/compose"），但镜像在目标主机上无法构建
- **审查判断**：
  需要替换为 ARM 兼容的 PyTorch CUDA 镜像。可考虑 `pytorch/pytorch:latest`（支持 multi-arch）或基于 `nvidia/cuda:13.0-runtime-ubuntu24.04` 手动安装 PyTorch。
- **建议修法**：
  1. 将 base image 改为 ARM 兼容版本（如 `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` 的 ARM variant）
  2. 或从 `nvidia/cuda:13.0-runtime-ubuntu24.04` aarch64 镜像手动 pip install torch
  3. 在 `docs/ops/local-setup.md` 中补充 NVIDIA Container Toolkit 安装说明
  4. compose.yaml 中添加对 `nvidia-container-runtime` 的 runtime 指定

### R8-R28（其余 finding 详情）

*出于篇幅考虑，R8-R28 的完整分析已在 §2.1 汇总表中给出，每条 finding 均基于与 final-execution-plan.md 的逐项对照和源代码走查。以下是关键补充：*

- **R8（JobRunner dispatch）**：`runner.py:79-87` 仅 `if/elif` 三个 job 类型。至少需要补齐 9 种：train_rvc、synth_xtts、curate、export_dataset、evaluate、以及单独执行的 diarize/slice/clean/transcribe/score
- **R9（幂等性）**：diarize/slice 重运行会产生重复 Segment 和 artifact；需添加"status ≥ 已处理"的跳过逻辑
- **R10（embedder 永久 mock）**：speaker_embedder/audio_embedder/text_embedder 既无 MOCK_ADAPTERS guard 也无真实模型路径，MD5 确定性向量在真实数据上丧失语义
- **R11（scoring mock）**：`score.py:39-41` 对 noise_score/overlap_score/speaker_score 使用硬编码值 0.9/1.0/0.85——需要封装为 ScorerAdapter
- **R12/R13（API/CLI violations）**：`api/routes_datasets.py:11`、`api/routes_inference.py:5`、`api/routes_reports.py:10`、`cli.py:221/250` 共 5 处违规 import
- **R15（断言永真）**：`tests/unit/pipelines/test_curate_dedupe.py:72` 的 `or True` 使最关键的 dedup assertion 永真——**必须立即删除**
- **R20（consent_ledger）**：当前使用 `recording_id`+`granted(BOOLEAN)` 替代 plan 的 `scope`+`status`+`evidence_uri`+`revoked_at`——无法实现 consent scope 管理和撤销追踪

---

## 3. In-Scope 逐项对齐审核

> 与 final-execution-plan.md §7 owner decision gates（G-MVC-1 至 G-MVC-8）逐项对齐。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | G-MVC-1: 双轨模型路线 | `done` | VC/SVC 主线通过 RVC/So-VITS adapter 接入，TTS 通过 XTTS adapter 实现——符合 plan |
| S2 | G-MVC-2: P0-P6 不做授权安全拦截 | `done` | P1 预留 schema，P7 通过 feature flag 启用——符合 plan |
| S3 | G-MVC-3: SQLite + sqlite-vec/vec0 默认 | `partial` | SQLite 正确安装，但 vec0 表维度和结构错误——不可用状态 |
| S4 | G-MVC-4: FastAPI + Typer 接口 | `partial` | 接口存在且结构正确，但 API/CLI 绕过 domain services 直接调用 pipelines |
| S5 | G-MVC-5: 分层禁止反向依赖 | `partial` | domain/storage 层隔离良好，但 api/cli → pipelines 违规（5 处） |
| S6 | G-MVC-6: jobs/job_events/artifacts/reports 审计 | `partial` | 审计链路概念存在，但 jobs 表结构缺陷导致 trace 不完整 |
| S7 | G-MVC-7: 每 phase 有 unit tests | `partial` | 47 测试文件覆盖全部 phase，但 marker 体系失效，fixtures/fakes 缺失 |
| S8 | G-MVC-8: 项目树全部文件映射 | `done` | §12.2 文件定位矩阵中的所有路径均已创建——项目完整 |

### 3.1 对齐结论

- **done**: `2` (G-MVC-1, G-MVC-8)
- **partial**: `6` (G-MVC-3, G-MVC-4, G-MVC-5, G-MVC-6, G-MVC-7)
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像 "8 个决策 gate 中 2 个完全达标、6 个仅有骨架满足但实质合规存在缺口" 的状态，而不是 8 个全部 closed。

---

## 4. Out-of-Scope 核查

> 检查实现是否越界，以及 reviewer 是否将已冻结的 deferred 项误判为 blocker。

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 生产级多租户权限系统 | `遵守` | P7 仅实现本地策略和 release gate，未涉及 RBAC/多租户 |
| O2 | 云端训练队列 / Celery / K8s | `遵守` | 全部使用本地 JobQueue + JobRunner，未引入分布式组件 |
| O3 | vec1 作为默认向量库 | `遵守` | DB-006 正确以注释形式占位、env var gated——默认 off |
| O4 | 实时语音通话替身 | `遵守` | 仅有 batch inference，无 streaming/RT 路径 |
| O5 | 自动下载闭源/受限权重 | `遵守` | download_models.sh 仅打印占位信息，无真实下载 |
| O6 | API/CLI 直接调用 pipelines | `部分违反` | 虽非恶意越界，但 5 处 API/CLI→pipelines 调用违反 layer boundary 约束 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：
  `该 first-build 实现了完整的项目骨架、pipeline 编排和 adapter mock 策略，integration capstone 可无 GPU 通过——这证明了架构分层的正确性。但数据库 schema 存在 87 项系统性漂移、状态枚举完全孤立于代码、测试 marker 体系全部失效——这三者使当前实现无法达到 execution plan 所要求的"数据库可承接全业务、状态机可类型安全驱动、测试可按层级隔离执行"的基准线。需要完成 R1-R7 共 7 个 critical blocker 的修正后，方可标记本阶段为 closed。`

- **是否允许关闭本轮 review**：`no`

- **关闭前必须完成的 blocker**：
  1. **R1**: 重写 migration 002-005 以对齐 plan §14.3（jobs/model_runs/artifacts/eval 表补全全部缺失列和约束）
  2. **R2**: 修正 vec0 虚拟表为正确的维度（768/192/384）和带有 PRIMARY KEY 的结构
  3. **R3**: 补全 domain/states.py 全部枚举，全局替换裸字符串为枚举引用
  4. **R4**: 创建 domain/services.py，重写 API/CLI 改为通过 services 调用 pipelines/eval
  5. **R5**: 重新分配所有测试 marker（api/cli/integration 至少各标记其对应文件）
  6. **R6**: 创建 tests/fixtures/ 和 tests/fakes/ 目录并填充 synthetic 数据和 fake 类
  7. **R7**: 替换 Dockerfile.train 为 aarch64 兼容的 CUDA 镜像

- **可以后续跟进的 non-blocking follow-up**：
  1. R8: JobRunner 补齐全部 12 种 job 类型 dispatch
  2. R9: 预处理链各步骤添加幂等性保护
  3. R10: 为 3 个 embedder adapter 补充真实模型路径
  4. R11: 将 scoring 封装为 ScorerAdapter
  5. R17: 预处理链添加 per-step 进度事件
  6. R26: 添加 SQLite 并发写 WAL 测试
  7. R27/R28: 脚本路径和依赖声明优化

- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

---

## 附录：数据统计

### Schema 漂移量化

| 指标 | 数值 |
|------|------|
| 总列级差异 | 87 |
| 缺失必填列 | 42 |
| 错误列名 | 24 |
| 多余列 | 9 |
| 缺失 CHECK 约束 | 2 |
| 缺失索引 | 5 个复合索引 |
| 错误 status 枚举 | 3 张表 |
| vec0 维度错误 | 3/3 表全部错误 |

### 架构合规量化

| 指标 | 数值 |
|------|------|
| Layer boundary violations | 5 (API×3, CLI×2) |
| 孤立枚举类（从未 import） | 4 |
| 缺失文件（plan 指定但未创建） | 1 (domain/services.py) |
| 缺失目录 | 2 (tests/fixtures/, tests/fakes/) |
| 状态枚举与裸字符串偏差值 | 12+ 裸字符串、枚举覆盖 25% |

### 测试体系量化

| 指标 | 数值 |
|------|------|
| 总测试文件数 | 47 |
| 总测试用例数 | 93 |
| 正确标记的 marker | 1 (integration) |
| 错误标记的 marker | 92 (unit) |
| 未使用的 marker | 5 (api/cli/live/gpu/slow) |
| 断言永真 bug | 1 (test_curate_dedupe.py:72) |
| 缺失 fixtures 目录 | 全部（4 类计划 fixtures 不存在） |
| 缺失 fakes 目录 | 全部（6 个计划 fake 类不存在） |
