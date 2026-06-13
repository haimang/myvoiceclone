# myvoiceclone first-build P0-P8 第二轮代码审查

> 审查对象: `myvoiceclone first-build P0-P8`
> 审查类型: `code-review | rereview`
> 审查时间: `2026-06-13`
> 审查人: `Kimi`
> 审查范围:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md` §6/§8/§12/§14/§15
> - `myvoiceclone/docs/code-review/first-build/P0-P8-review-VF-ledger.md` 第一轮修复台账
> - `myvoiceclone/src/myvoiceclone/` 全部源码
> - `myvoiceclone/db/migrations/00{1..7}_*.sql`
> - `myvoiceclone/infra/docker/`
> - `myvoiceclone/tests/`
> 对照真相:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`
> - `myvoiceclone/docs/code-review/first-build/P0-P8-review-VF-ledger.md`
> 文档状态: `reviewed`

---

## 0. 总结结论

- **整体判断**：first-build P0-P8 在第二轮审查节点上是一个**“可运行的 mock 骨架，但尚未成为可承接下一阶段真实训练的坚实基础”**。第一轮修复清除了多处运行时 bug 与架构越界，但修复本身存在“ schema 补列但代码不消费”、“枚举扩充但全工程仍用裸字符串”、“服务层抽出但 CLI 仍直接 import pipeline” 等半修复状态；同时数据库状态机、Docker 数据卷根目录、模型产出链路、API 接口统一性四个基础面仍有显著漂移。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. 第一轮修复中的 V1（schema 对账）、V6（CLI 边界）、V9（AudioProbe DTO）、V14（db_path DRY）、V15（states 枚举消费）并未真正收口，系统仍运行在旧列名/旧路径/裸字符串上，存在回归风险。
  2. Docker 与数据卷尚未落到用户要求的 `/mnt/usb/workspace/myvoiceresearch`；`DB_PATH`/`ARTIFACT_ROOT`/`MODELS_DIR` 三个环境变量在 compose.yaml 中声明但代码完全不消费。
  3. API/CLI 在请求模型、路由路径、错误信封、状态枚举四方面与 final-execution-plan §15 存在系统性漂移，尚未形成统一的契约表面。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `myvoiceclone/docs/eval/first-build/final-execution-plan.md` §6（逐 phase 台账）、§8（测试计划）、§12（文件定位矩阵 / 抽象层）、§14（数据库 schema / 状态机）、§15（接口设计）
  - `myvoiceclone/docs/code-review/first-build/P0-P8-review-VF-ledger.md` 第一轮修复台账与处置回填
- **核查实现**：
  - `src/myvoiceclone/` 全部源码
  - `db/migrations/001_core_schema.sql` ~ `007_reconcile_to_plan.sql`
  - `infra/docker/Dockerfile.preprocess`、`Dockerfile.train`、`compose.yaml`
  - `configs/local.yaml`、`configs/models.yaml`
  - `tests/` 全部测试文件
- **执行过的验证**：
  - `venv/bin/python -m pytest -q` → `92 passed, 1 skipped, 0 failed`
  - `venv/bin/python -m pytest -m api -q` → `14 passed`
  - `venv/bin/python -m pytest -m cli -q` → `4 passed`
  - `venv/bin/python -m pytest tests/unit/storage/ -q` → `12 passed`
  - 应用全部 7 条 migration 到临时 SQLite，导出 schema 与 §14.3 逐项对账
  - `grep -R "from myvoiceclone\.(pipelines|eval|adapters)" src/myvoiceclone/api/*.py` → 0 命中（验证 V5）
  - `grep -R "from myvoiceclone.domain.states" src/` → 0 命中（验证 V15 未消费）
  - `docker compose -f infra/docker/compose.yaml config` 验证 compose 可渲染
- **复用 / 对照的既有审查**：
  - `P0-P8-review-VF-ledger.md` — 仅作为“待验证修复清单”线索，所有 verdict 均基于本轮独立 Read/grep/测试/推理得出。

### 1.1 已确认的正面事实

- 测试套件全绿：`92 passed, 1 skipped, 0 failed`，说明当前 mock 路径可运行。
- 第一轮修复中以下项目确实完成：V3（Dockerfile.train 换用 NGC aarch64 镜像）、V4（pytest marker 补全）、V5（API 不再直接 import pipelines/eval/adapters）、V7（CLI NameError 修复）、V8（断言永真修复）、V11（compose nvidia toolkit 说明）、V12（Dockerfile 安装 extras）、V13（adapter 测试 env cleanup）、V20（closure SHA 可核对）、V23（architecture boundary 测试失败路径正确）。
- `myvoiceclone.services` 服务层已创建，承担了数据集冻结、RVC/SoVITS 训练、XTTS 合成、报告生成等编排职责，为后续真实实现预留了统一入口。
- `config.resolve_db_path()` 已存在，API `dependencies.py` 已调用它，CLI/API 的 DB 路径解析开始收敛。
- `ArtifactStore` 的 artifact 路径布局清晰（`<root>/<type>/<id><ext>`），URI 相对化，便于跨环境迁移。
- SoVITS 训练链路在 mock 层面完整：feature cache → per-epoch checkpoint → eval_metrics → registry model → rendered sample，且支持 resume/cancel。

### 1.2 已确认的负面事实

- `db/migrations/007_reconcile_to_plan.sql` 虽然增加了 plan-canonical 列（`kind`、`source_artifact_id`、`created_by_job_id`、`params_json` 等），但**应用代码与仓库仍使用旧列名**；新增列只是 schema 占位。
- `domain/states.py` 已扩展为 7 个状态机，但**整个 `src/` 无人 import 使用**，所有状态仍用裸字符串写入。
- `cli.py:13` 直接 `from myvoiceclone.pipelines.export_dataset import run_export_dataset`，第一轮 V6 修复未覆盖该点；`test_architecture_boundaries.py` 的 CLI 规则只禁 `adapters` 不禁 `pipelines`，因此测试无法拦截。
- `domain/entities.py` 中 `AudioProbe` 被重复定义两次（3 字段与 4 字段），`torchaudio_io.py` 以 3 参数实例化，会在真实音频路径触发 `TypeError`。
- `infra/docker/compose.yaml` 的数据卷挂载在 `../../db`、`../../data`、`../../models`，全部落在项目仓库内；用户要求的 `/mnt/usb/workspace/myvoiceresearch` 未出现。
- `compose.yaml` 声明的 `DB_PATH`、`ARTIFACT_ROOT`、`MODELS_DIR` 环境变量在代码中无人读取；配置仍以 `configs/local.yaml` 为准。
- vec0 虚表维度仍为 `float[128]`，与 plan 要求的 768/192/384 不符；`embedding_jobs` 表已创建但 `Vec0Store` 仍读写旧表 `embedding_items`。
- 所有训练/embedding 适配器均为 mock，真实模式下抛 `NotImplementedError`；`scripts/download_models.sh` 是空壳。
- API 无统一响应信封；`ReleaseGateResponse` 仍暴露 `passed: int` 而非 plan 的 `status` 枚举；`/audit/trace` 路径与 §15.1 不符；`/api/inference` 把 TTS 语义混在 VC 路径下。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 所有关键结论均带 file:line，见 §2。 |
| 本地命令 / 测试 | `yes` | pytest 全量及 marker 子集、schema 应用、docker compose config 渲染。 |
| schema / contract 反向校验 | `yes` | 将 7 条 migration 应用到临时 DB，dump schema 与 plan §14.3 逐项比对。 |
| live / deploy / preview 证据 | `no` | 未实际构建 Docker 镜像或运行 GPU 训练；仅做静态与 dry-run 分析。 |
| 与上游 design / QnA 对账 | `yes` | 以 final-execution-plan.md §14/§15 为唯一 contract surface。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 第一轮修复 V1/V6/V9/V14/V15 处于“半修复”状态 | `critical` | `correctness` | `yes` | 统一列名/路径/枚举消费 |
| R2 | 数据库状态机未真正落地：CHECK 缺失或放宽，状态值漂移 | `critical` | `correctness` | `yes` | 补 CHECK、统一枚举、淘汰旧别名 |
| R3 | Docker 数据卷未落到 `/mnt/usb/workspace/myvoiceresearch` | `critical` | `platform-fitness` | `yes` | 改写 compose 挂载与配置解析 |
| R4 | DB_PATH/ARTIFACT_ROOT/MODELS_DIR 环境变量声明但无效 | `high` | `correctness` | `no` | 在 config.py 增加 env 覆盖 |
| R5 | vec0 维度/命名空间与 plan 不符且 `embedding_jobs` 表未被使用 | `high` | `protocol-drift` | `no` | 新增 migration + 切 Vec0Store |
| R6 | 训练/embedding 适配器全 mock，模型下载脚本为空壳 | `high` | `delivery-gap` | `no` | 属于 first-build deferred，但需明确 reopen 条件 |
| R7 | `model_runs` plan-canonical 列（env_digest/git_commit/checkpoint_artifact_id/model_family）仅 schema 存在 | `high` | `correctness` | `no` | 改 ModelRunRepository + pipelines |
| R8 | API 无统一响应信封，错误格式与路径不统一 | `high` | `protocol-drift` | `no` | 引入 ApiResponse + 全局异常处理 |
| R9 | API 路由路径与 plan §15.1 多处漂移 | `high` | `protocol-drift` | `no` | 调整 router prefix 与路径 |
| R10 | CLI/API 参数与语义不一致 | `high` | `protocol-drift` | `no` | 统一 service 入口与请求模型 |
| R11 | `pipeline_runs` 死表；`recordings.status` 未跟踪预处理进度 | `medium` | `delivery-gap` | `no` |  wiring pipeline_runs 或移除 |
| R12 | Dockerfile.train 缺 ffmpeg/audio 依赖；Dockerfile.preprocess 缺 demucs/libsndfile1 | `medium` | `platform-fitness` | `no` | 补充系统包与 extras |

### R1. 第一轮修复 V1/V6/V9/V14/V15 处于“半修复”状态

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - V1：迁移 `007_reconcile_to_plan.sql` 已增加 `kind`、`source_artifact_id`、`created_by_job_id`、`params_json` 等列，但 `src/myvoiceclone/storage/artifact_store.py:51-54` 仍只写入 `artifact_type`、`parent_artifact_id`、`job_id`；`JobRepository` 仍使用 `payload_json` 与 `error_msg`。
  - V1：`Vec0Store` 仍读写旧表 `embedding_items`（`storage/vec0_store.py:14,25,70,85,94`），而 migration 007 创建的 `embedding_jobs` 无人使用。
  - V6：`cli.py:13` 直接 `from myvoiceclone.pipelines.export_dataset import run_export_dataset`，`dataset_freeze` 直接调用它，未走 `service_export_dataset`。
  - V9：`domain/entities.py:10-15` 与 `:124-129` 两次定义 `AudioProbe`（3 字段 vs 4 字段），后者覆盖前者；`adapters/audio/torchaudio_io.py:31-34` 以 3 参数构造，真实路径会触发 `TypeError`。
  - V14：`config.py:36-48` 新增 `resolve_db_path()`，但 `cli.py:37-43` 与 `:46-50` 仍内联相对路径解析。
  - V15：`domain/states.py` 扩展为 7 个枚举，但 `grep "from myvoiceclone.domain.states" src/` 命中 0 处；`jobs/runner.py`、`cli.py`、`pipelines/*.py`、`routes_*.py` 仍写裸字符串。
- **为什么重要**：这些“半修复”制造了 schema/代码/契约的三重真相：测试通过，但 plan-canonical 列与枚举是死代码；下一次真实训练或 schema 收缩时会突然断裂。
- **审查判断**：第一轮修复在“消除 reviewer 发现的表面症状”上有效，但未完成“让 plan-canonical 契约成为唯一真相”的收口。
- **建议修法**：
  1. 选定唯一命名体系：以 plan §14.3 为准，重写 `ArtifactStore`、`JobRepository`、`ModelRunRepository` 与 entity，删除旧列别名。
  2. CLI `dataset_freeze` 改为 `from myvoiceclone.services import service_export_dataset`。
  3. 删除重复的 `AudioProbe`，统一所有 adapter 使用 4 字段版本（含 `format`）。
  4. `cli.py` 全部 DB/artifact 路径解析调用 `config.resolve_db_path()` / 新增 `resolve_artifact_root()`。
  5. 在所有写 status 的位置改用 `domain.states.*` 枚举，并收紧 migration CHECK。

### R2. 数据库状态机未真正落地

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `recordings.status` 无 CHECK 约束（`001_core_schema.sql:25`），`pipelines/ingest.py:99` 直接写 `"processed"`，从未进入 plan §14.4 的 `new → ingested → ... → dataset_ready` 链。
  - `segments.status` 无 CHECK 约束，代码写入 `draft`、`sliced`、`cleaned`、`transcribed`、`processed`、`needs_review`、`keep`、`drop`、`duplicate`、`curated` 等，plan §14.4 仅定义 `new → needs_review → keep | drop | fixed`。
  - `datasets.status` CHECK 包含 plan 未定义的 `'active'`（`007_reconcile_to_plan.sql:20-22`），因为 `routes_datasets.py:36` 与 `cli.py:170` 创建数据集时写 `"active"`。
  - `jobs.status` CHECK 是 plan canonical（queued/running/succeeded/failed/canceled）与代码旧值（pending/completed/cancelled）的并集（`007_reconcile_to_plan.sql:43-44`）。
  - `reports.status` 列有默认值但无 CHECK，且代码未更新该列，状态实际存于 `summary_json`。
- **为什么重要**：状态机是审计、幂等重试、UI 进度、P7 release gate 的前提。CHECK 放宽等于没有状态机。
- **审查判断**：schema 提供了“可写任意字符串”的宽容环境，业务流未与 plan 对齐。
- **建议修法**：
  1. 为 `recordings.status`、`segments.status`、`reports.kind`/`report_type`、`datasets.status` 增加 CHECK。
  2. 淘汰 `jobs`/`model_runs` 中的旧别名，统一为 plan canonical。
  3. 将代码中所有状态字符串替换为 `domain.states` 枚举值，从源头消除漂移。

### R3. Docker 数据卷未落到 `/mnt/usb/workspace/myvoiceresearch`

- **严重级别**：`critical`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `infra/docker/compose.yaml:29-31` 挂载 `../../db:/app/db`、`../../data:/app/data`、`../../configs:/app/configs`。
  - `compose.yaml:45-48` 挂载 `../../db:/app/db`、`../../data:/app/data`、`../../models:/app/models`。
  - 这些相对路径解析到 `/mnt/usb/workspace/myvoiceclone/{db,data,models}`，即项目仓库内部。
  - 用户明确要求：具体数据 volume 应存放在 `/mnt/usb/workspace/myvoiceresearch`，避免大数据暴露在宿主机硬盘上。
- **为什么重要**：20+ 小时录音、feature cache、checkpoint、模型注册表都是大文件；若放在项目仓库内，会污染 git 工作区并可能撑满系统盘。
- **审查判断**：当前布局不满足用户给定的硬约束。
- **建议修法**：
  1. 创建 `/mnt/usb/workspace/myvoiceresearch/{db,data,models}`。
  2. 将 compose 卷改为绝对路径挂载到该目录；`configs` 可保留为只读项目内挂载。
  3. 在 `config.py` 增加 `resolve_artifact_root()` 与 `resolve_models_dir()`，优先读取环境变量，再回退到 `configs/local.yaml`。
  4. 将 migration 文件从 `db/` 移出数据卷（例如镜像内 `resources/migrations`），避免外部卷缺失 migrations 导致 `init-db` 失败。

### R4. DB_PATH/ARTIFACT_ROOT/MODELS_DIR 环境变量声明但无效

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `compose.yaml:32-35,49-53` 声明上述环境变量。
  - `config.py` 的 `resolve_db_path()` 仅读取 `configs/local.yaml`，不看 `DB_PATH`。
  - `services/__init__.py:35-38`、 `cli.py:93,117,199`、 `api/routes_jobs.py:34` 直接取 `config.get("artifact_root", "data/artifacts")`。
  - `grep -R "MODELS_DIR" src/` 无命中。
- **为什么重要**：compose 中的环境变量是运维人员最自然的配置方式；声明却不消费会造成“改 env 不生效”的困惑。
- **审查判断**：配置入口不统一，存在多处硬编码。
- **建议修法**：在 `config.py` 提供统一的 env-aware 解析函数，并替换所有直接读取 local.yaml 的调用点。

### R5. vec0 维度/命名空间与 plan 不符且 `embedding_jobs` 表未被使用

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `db/migrations/003_vec0_embeddings.sql:23-33` 定义 `vec_speaker`、`vec_audio`、`vec_text` 均为 `float[128]`。
  - plan §14.3 要求 `segment_audio_embeddings FLOAT[768]`、`speaker_embeddings FLOAT[192]`、`transcript_embeddings FLOAT[384]`。
  - `Vec0Store` 仍对 `embedding_items` 表做 rowid 映射（`storage/vec0_store.py:14,25,70,85,94`），而 migration 007 创建的 `embedding_jobs` 无人使用。
- **为什么重要**：真实 speaker/audio/text embedder 接入时会因维度不匹配直接失败；同时两张 metadata 表并存会导致数据分裂。
- **审查判断**：属于 first-build deferred（DEF-01/05），但 schema 当前状态无法直接承接真实向量。
- **建议修法**：新增 migration `008_fix_vec0_dimensions.sql`：删除旧 vec 表，按 plan 维度重建；修改 `Vec0Store` 指向 `embedding_jobs`。

### R6. 训练/embedding 适配器全 mock，模型下载脚本为空壳

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `adapters/training/rvc_adapter.py:22`、`sovits_adapter.py:27`、`xtts_adapter.py:18` 在 `MOCK_ADAPTERS != true` 时抛 `NotImplementedError`。
  - `adapters/embeddings/*.py` 返回 MD5 派生的 128 维 mock 向量。
  - `scripts/download_models.sh:16-19` 仅 `mkdir -p models/base` 并打印占位信息，不下载任何权重。
- **为什么重要**：first-build 明确 deferred 真实模型实现，但当前代码没有为“切换真实模型”预留稳定路径（如权重路径、cache 校验、subprocess 命令模板）。
- **审查判断**：符合 first-build scope，但需确保 reopen 条件清晰，并在下次迭代时优先补齐 `download_models.sh` 与 adapter 命令模板。
- **建议修法**：在 deferred-items-ledger 中标记 reopen 触发器；下一轮先实现 `scripts/download_models.sh` 的 URL/checksum 列表与 adapter 的 subprocess 调用骨架。

### R7. `model_runs` plan-canonical 列仅 schema 存在

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - migration 007 已为 `model_runs` 增加 `model_family`、`checkpoint_artifact_id`、`env_digest`、`git_commit`、`finished_at`。
  - `storage/repositories.py:380-390` 的 `ModelRunRepository.save` 仍只写入 `id, name, dataset_id, status, config_json`。
  - `pipelines/train.py` 将 `env_digest`、最后 checkpoint 等数据塞进 `config_json`（`train.py:376,421`），顶层列始终为空。
- **为什么重要**：可复现性、模型注册、实验对比都依赖这些独立列；放在 JSON 里无法索引，也违反 plan 契约。
- **审查判断**：半修复状态与 V1 同类。
- **建议修法**：更新 `ModelRunRepository.save` 写入全部 canonical 列；更新 RVC/SoVITS pipeline 填充这些列。

### R8. API 无统一响应信封，错误格式与路径不统一

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - 所有 route 直接返回 Pydantic 模型或裸 dict，无 `{data, error, meta}` 包装（`routes_recordings.py`、`routes_segments.py`、…、`routes_reports.py:258-262`）。
  - `app.py` 无全局异常处理器。
  - 错误详情格式不统一：有 `"Recording not found"`、`f"Database integrity error: {e}"`、`str(e)` 等。
- **为什么重要**：客户端无法写出统一的错误处理与分页逻辑。
- **审查判断**：API 功能可用，但契约表面未达 plan §15 的统一性要求。
- **建议修法**：引入 `ApiResponse[T]` 基类与全局 `HTTPException`/通用异常 handler；所有 route 通过 helper 包装返回。

### R9. API 路由路径与 plan §15.1 多处漂移

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - plan 要求 `POST /runs/train`，实现为 `POST /api/training/jobs`（`routes_training.py`）。
  - plan 要求 `GET /runs/{id}`，实现为 `GET /api/training/runs/{id}`。
  - plan 要求 `POST /inference/vc` 与 `POST /inference/tts`，实现只有 `POST /api/inference`（TTS 语义）。
  - plan 要求 `GET /audit/{subject_type}/{subject_id}`，实现为 `GET /api/audit/trace?subject_type=...&subject_id=...`。
  - `routes_reports.py` 未设置 prefix，路径内联 `/reports/...` 与 `/audit/...`，风格与其他 router 不一致。
- **为什么重要**：路径漂移会导致前端/CLI/文档三方不同步。
- **审查判断**：需要在下一轮统一 router prefix。
- **建议修法**：按 plan §15.1 调整 router prefix 与路径；将 audit 路由拆到 `routes_audit.py`。

### R10. CLI/API 参数与语义不一致

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `mvc infer vc --model MODEL_ID --input PATH --out PATH` 是 VC 语义；`POST /api/inference` 却是 TTS 语义（`speaker_id`, `text`）。
  - `mvc train rvc/sovits --dataset NAME --profile ...` 按数据集名称解析；API `POST /api/training/jobs` 按 `dataset_id` 且 hardcode `train_sovits`。
  - `mvc eval RUN_ID` 无 API 对应；`POST /api/reports/baseline`、`/reports/train` 等无 CLI 对应。
- **为什么重要**：同一业务在不同入口行为不同，增加维护成本与测试矩阵。
- **审查判断**：CLI 与 API 尚未共享统一的请求模型。
- **建议修法**：所有 CLI 命令与 API route 调用同一 service，并共享 Pydantic request schema；补齐缺失的对称入口。

### R11. `pipeline_runs` 死表；`recordings.status` 未跟踪预处理进度

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `pipeline_runs` 在 migration 002/007 中创建并扩展列，但 `grep -R "pipeline_runs" src/` 命中 0 处。
  - `recordings.status` 在 ingest 后即写 `processed`，后续 diarize/slice/clean/transcribe/score 只更新 segments。
- **为什么重要**：跨步骤工作流追踪与 recording 级进度展示依赖这两者。
- **审查判断**：不影响当前 mock 测试，但影响下一阶段的 audit UI 与 pipeline orchestration。
- **建议修法**：在 `service_preprocess_all` 与 `JobRunner` 中创建 `pipeline_runs` 记录并关联 job；或从 schema 中移除该表并在文档中说明。

### R12. Dockerfile.train 缺 ffmpeg/audio 依赖；Dockerfile.preprocess 缺 demucs/libsndfile1

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `Dockerfile.train:9-11` 只 apt 安装 `git`，未安装 `ffmpeg` 与 `libsndfile1`。
  - `Dockerfile.train:21` 安装 `".[cli,db,api]"`，缺少 `[audio]`（soundfile/torchaudio）。
  - `Dockerfile.preprocess:4-7` 安装 `ffmpeg`、`git`，未安装 `libsndfile1`；`pyproject.toml:20` 的 `[preprocess]` 缺少 `demucs`。
- **为什么重要**：真实音频路径会在容器内直接失败。
- **审查判断**：当前 mock 路径不触发，但容器未为真实训练做好准备。
- **建议修法**：在 Dockerfile.train 增加 `ffmpeg`、`libsndfile1` 与 `".[cli,db,api,audio]"`；在 Dockerfile.preprocess 增加 `libsndfile1` 并在 `pyproject.toml` `[preprocess]` 增加 `demucs`。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | P0 scope/layer freeze | `done` | `docs/architecture/layers.md` 存在，分层原则在代码中基本落实（API 不再直接 import adapters/pipelines）。 |
| S2 | P1 SQLite + vec0 骨架 | `partial` | 连接管理、迁移机制、vec0 扩展加载完成；但 vec0 维度/命名空间漂移，`embedding_jobs` 未使用。 |
| S3 | P2 预处理 pipeline | `partial` | 6 步流程与 job runner 已存在；幂等性保护、真实 adapter、状态机推进未实现。 |
| S4 | P3 语料整理与 dataset freeze | `partial` | manifest checksum、split leak 检测存在；review queue 通过 segment_reviews 实现；但 `datasets.status` 使用 `active` 非 plan 值。 |
| S5 | P4 quick baselines | `partial` | RVC/XTTS adapter 为 mock，可生成 model_run 与 sample；baseline eval pack/report 骨架存在。 |
| S6 | P5 SoVITS 长训 | `partial` | mock 链路完整（feature cache → checkpoint → registry → sample），resume/cancel 支持；但真实 adapter 未实现，provenance 列未填充。 |
| S7 | P6 API/CLI/eval | `partial` | FastAPI/Typer 入口存在；路由路径、信封、错误处理、CLI/API 一致性均未与 plan §15 对齐。 |
| S8 | P7 安全治理接入点 | `done` | consent_ledger/policy_events/release_gates placeholder schema 存在；P7 前不启用，符合 scope。 |
| S9 | P8 Docker/ops/handoff | `partial` | Dockerfile 与 compose 存在；但数据卷未落到 `/mnt/usb/workspace/myvoiceresearch`，环境变量无效，README 缺少 Docker 流程。 |
| S10 | 测试 taxonomy | `done` | marker 已补全，unit/api/cli/integration 测试运行正常。 |

### 3.1 对齐结论

- **done**: `4`
- **partial**: `6`
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像“mock 骨架与测试已跑通，但契约表面、状态机、数据卷根目录、provenance 列尚未收口”，而不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 生产级多租户权限 | `遵守` | P0-P6 未实现；P7 占位 schema 存在。 |
| O2 | 云端训练队列 / Celery / K8s | `遵守` | 本地 `JobRunner` 先行。 |
| O3 | `vec1` 默认向量库 | `遵守` | `vec1_store.py` 为 probe，默认不启用。 |
| O4 | 实时语音通话替身 | `遵守` | 仅实现 batch inference。 |
| O5 | 自动下载闭源/受限权重 | `遵守` | `download_models.sh` 为占位，不把 token 写死。 |
| O6 | 真实 embedding/scoring 模型 | `遵守` | 作为 DEF-05/06 deferred，但 reopen 条件需更清晰。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. 统一 schema 真相：要么删除 migration 007 中未使用的 canonical 列并承认当前旧列名是 first-build 事实标准；要么将代码全部迁到 plan-canonical 列名并删除旧列。当前“双轨并存”不可接受。
  2. 将 Docker 数据卷根目录改为 `/mnt/usb/workspace/myvoiceresearch`，并确保 `DB_PATH`/`ARTIFACT_ROOT`/`MODELS_DIR` 环境变量被代码实际消费。
  3. 在 `domain/states.py` 枚举被真正消费之前，为所有 status 列补充 CHECK 约束，使其与 plan §14.4 一致。
- **可以后续跟进的 non-blocking follow-up**：
  1. 引入统一 API 响应信封与全局异常处理。
  2. 对齐 API 路由路径与 plan §15.1。
  3. 补齐 CLI/API 对称入口（eval、inference/vc、reports create）。
  4. 修复 `AudioProbe` 重复定义与 `torchaudio_io` 参数不一致。
  5. 规划 `vec0` 维度修复 migration（DEF-01）与真实 adapter 接入（DEF-05/06）的耦合顺序。
  6. 将 migrations 从数据卷中剥离，避免外部卷缺失导致 `init-db` 失败。
- **建议的二次审查方式**：`same reviewer rereview`（由本轮 reviewer 复核 blocker 修复即可）。
- **实现者回应入口**：请按 `docs/templates/code-review-respond.md` 在本文档 §6 append 回应，不要改写 §0–§5。

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

---

## 6. 实现者回应区（append-only）

（待实现者按模板回填）
