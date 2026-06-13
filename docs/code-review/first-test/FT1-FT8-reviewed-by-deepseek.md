# Nano-Agent 代码审查模板

> 审查对象: `first-test / FT1-FT8 — implementation-complete-awaiting-live-verification`
> 审查类型: `code-review`
> 审查时间: `2026-06-13`
> 审查人: `Deepseek (Copilot CLI)`
> 审查范围:
> - `src/myvoiceclone/` — 全部源代码
> - `tests/` — 全部测试代码
> - `db/migrations/` — 全部数据库迁移
> - `infra/docker/` — Docker 基础设施
> - `docs/plan/first-test/` — FT1-FT8 action-plan
> - `docs/closure/first-test/` — FT1-FT8 closure
> 对照真相:
> - `docs/eval/first-test/proposed-planning.md` — 工作基线
> - `docs/eval/first-test/reference-anchor.md` — 业务锚点
> - `docs/closure/first-test/first-test-closure.md` — 收口声明
> 文档状态: `reviewed`

---

## 0. 总结结论

> 该实现主体成立，数据库、Docker 基础设施、可观测性核心骨架完整且设计合理，但在训练 workflow e2e 执行链条中存在 3 个关键阻断性缺陷：`run_curation` 缺失导致 curate job 必崩；`infer_real` 与 `eval_first_test` job 创建后无法被 runner 执行；评估链路仅存 shell 而无真实执行体。当前不应标记为 `e2e test ready`。

- **整体判断**：`FT1-FT6 代码质量良好，FT7/FT8 文档完备，但 runner 执行调度与 pipeline 实现之间存在 3 个断开点，使 e2e 全流程无法通过 API runner 打通。`
- **结论等级**：`approve-with-followups`
- **是否允许关闭本轮 review**：`no` — 存在 3 个必须修复的 blocker
- **本轮最关键的 1-3 个判断**：
  1. `scope compliance 优秀 — 91/92 工作项 done，无 scope drift，所有关键不变量保持`
  2. `workflow runner 执行调度缺失 infer_real/eval_first_test 分发 + run_curation 不存在 — 导致 API e2e 链路断裂`
  3. `可观测性事件系统设计良好 (job_events + metadata_json)，但缺乏日志基础设施与 stack trace 捕获`

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。
> 明确你看了哪些文件、跑了哪些命令、核对了哪些计划项 / 设计项 / closure claim。

- **对照文档**：
  - `docs/eval/first-test/proposed-planning.md` — FT1-FT8 全量工作项与测试项台账
  - `docs/eval/first-test/reference-anchor.md` — 8 个业务簇与 TR-1..TR-7 技术红线
  - `docs/closure/first-test/first-test-closure.md` — 收口声明、evidence 矩阵、hard-gate 判定
  - `docs/plan/first-test/FT1..FT8-*.md` — 各阶段 action-plan
  - `docs/closure/first-test/FT1..FT8-*-closure.md` — 各阶段 closure
- **核查实现**：
  - `src/myvoiceclone/` — 52 个 Python 源文件，覆盖 CLI / API / pipelines / adapters / storage / eval / domain / jobs / evidence
  - `tests/` — 56 个测试文件，覆盖 unit / api / cli / integration
  - `db/migrations/` — 8 个 SQL 迁移文件
  - `infra/docker/` — 2 个 Dockerfile + 1 个 compose.yaml
- **执行过的验证**：
  - 静态代码审查：逐文件比对 `cli.py`, `config.py`, `runner.py`, `events.py`, `evidence.py`, 全部 pipelines、全部 adapters、全部 API routes、全部 schemas
  - Schema 审查：核对全部 8 个 migration 的表/列/FK/索引定义
  - Docker 审查：核对 compose.yaml volume 挂载与 config.py 路径解析的完全链路
  - Workflow 追踪：从 ingest → diarize → slice → clean → transcribe → score → curate → export → train → infer → evaluate 全链条 contract 分析
  - 命名审计：核对 DB 表名/列名与 domain entities / API schemas / pipeline 变量名之间的语义一致性
- **复用 / 对照的既有审查**：
  - `none` — 本轮为独立审查，未参考任何既有审查报告

### 1.1 已确认的正面事实

- `FT1-FT8 共 92 个工作项+测试项中，91 项 done，1 项 partial（T-FT3.2 live 组件），0 项 missing；所有 4 个 live pending 项均正确 gated 并 skip with reason` — 证据：closed-loop 验证从 proposed-planning 到实际源码/测试的完整 case-by-case 映射
- `数据库 16 张表的设计语义统一、命名一致（全 snake_case），job_events + metadata_json 提供了充足的扩展性承载 e2e 状态流转与事件追踪` — 证据：8 个 migration 文件全量审查，FK 关系链完整（jobs → job_events，artifacts → jobs，segments → recordings，model_runs → datasets）
- `Docker 容器 volume 挂载完全正确：DB (/app/db)、artifacts (/app/data)、models (/app/models) 全部映射到 /mnt/usb/workspace/myvoiceresearch/` — 证据：compose.yaml lines 31-32, 47-50 + config.py lines 37-68 + .env.example lines 2-5 三方验证一致
- `所有 7 个关键不变量全部保持：mock/real 分离、live/gpu/slow gating、禁止 silent mock fallback、artifact 外置 repo、FastAPI Upload→immediate artifact、架构层级边界、skip denominator` — 证据：每个不变量均有至少 1 个自动化测试守卫
- `Evidence pack 导出器生成 8 个结构化 JSON 文件，覆盖 env/db/trace/artifacts/skips，且 validator 拒绝 mock-as-real、空 manifest、repo 大文件` — 证据：`evidence.py:249-314` validator 规则 + `tests/unit/test_first_test_evidence_validator.py` 4 个 rejection 测试

### 1.2 已确认的负面事实

- `jobs/runner.py:347` 尝试 `from myvoiceclone.pipelines.curate import run_curation`，但 `pipelines/curate.py` 仅包含 `update_segment_status` 与 `run_deduplication` 两个函数，不存在 `run_curation` — 任何 curate job 执行时必抛 `ImportError`
- `jobs/runner.py:81-102` 的 job 分发 switch 未包含 `infer_real` 与 `eval_first_test` 两个 job name 的 `elif` 分支，导致 `routes_runs.py:143-164` 创建的两个 job 类型无法被 runner 执行 — 创建后永远卡在 `QUEUED` 状态
- `pipelines/evaluate.py` 仅一行 `return evaluate_objective_metrics(run_id, conn)` 的委托调用，无 DB 写入、无 job 集成、无事件发出；`cli.py:283` 的 `eval` 命令写入硬编码 mock 值 (`0.85`, `0.07`) 而非运行真实评估
- `pipelines/__init__.py` 为空（仅 `# pipelines package`），无 pipeline 注册表、无版本标识、无可发现性机制
- 日志基础设施极其薄弱：整个 `src/myvoiceclone/` 中仅有 4 个 logger 定义，其中 2 个有实际调用；pipelines 与 adapters 全部无日志输出
- `services/__init__.py:28` 定义了 `logger` 但从未调用 — service 层完全不可观测

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 所有发现均附带精确 `file:line` 引用 |
| 本地命令 / 测试 | no | 本轮为纯静态审查，未在本机执行测试（测试已在 closure 阶段由实施者执行并证明 134 passed） |
| schema / contract 反向校验 | yes | 从 DB migration 到 domain entities 到 API schemas 到 pipeline 代码，四方交叉验证命名一致性 |
| live / deploy / preview 证据 | no | live capstone 被正确 gated，审查范围限定为 static implementation review |
| 与上游 design / QNA 对账 | yes | 全量对照 proposed-planning §6.1-6.8 逐项核查 |

---

## 2. 审查发现

> 使用稳定编号：`R1 / R2 / R3 ...`。
> 每条 finding 都应包含：严重级别、类型、事实依据、为什么重要、审查判断、建议修法。
> 只写真正影响 correctness / security / scope / delivery / test evidence 的问题，不写纯样式意见。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `run_curation` 缺失导致 curate job 执行时 ImportError | critical | correctness | yes | 实现 `run_curation` 并注册到 runner dispatch |
| R2 | Runner 不支持 `infer_real` 与 `eval_first_test` job 分发 | critical | delivery-gap | yes | 在 `runner.py:81-102` 增加两个 elif 分支 |
| R3 | 评估链路无真实执行体，CLI eval 写入硬编码 mock 值 | high | delivery-gap | yes | 实现 `_execute_step_evaluate` 并接入真实 eval 引擎 |
| R4 | 日志基础设施严重不足，pipelines/adapters/service 层无日志 | high | platform-fitness | no | 在 pipeline 与 adapter 入口/出口/异常处增加结构化日志 |
| R5 | `services/__init__.py:76` 传递 `model_run_id` 给 `run_train_rvc`，但函数签名不接受该参数 | medium | correctness | no | 统一函数签名，或修复调用方 |
| R6 | `configs` volume 在 compose.yaml 中以 rw 模式挂载，存在运行时污染 repo 风险 | medium | platform-fitness | no | 改为 `:ro` 只读挂载 |
| R7 | Evidence pack 不自动捕获 stdout/stderr，也不捕获 stack trace | medium | test-gap | no | 在 evidence exporter 中增加 subprocess stdout/stderr 采集 |
| R8 | `pipeline_runs` 表无任何代码写入，属于 dead code | low | scope-drift | no | 移除或在 deferred ledger 中明确其 reopen trigger |

### R1. `run_curation` 缺失导致 curate job 执行时 ImportError

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `jobs/runner.py:347` — `from myvoiceclone.pipelines.curate import run_curation`
  - `pipelines/curate.py:1-133` — 仅含有 `update_segment_status()` 和 `run_deduplication()` 两个函数，**不存在** `run_curation`
  - `jobs/runner.py:352` — `run_curation(self.conn, self.artifact_store, recording_id, job_id=job.id)` 调用该不存在函数
  - `jobs/runner.py:99-100` — `curate` 类型的 job 被分发到 `_execute_step_curate`，而后者在第 347 行执行该 import
- **为什么重要**：
  - 任何通过 API 或 CLI 创建的 `curate` 类型 job，在执行时必抛 `ImportError: cannot import name 'run_curation'`，导致整个 curation 步骤不可用
  - curation 是 preprocess 链条中"数据清理→训练"的关键桥接步骤，其断裂意味着从 clean/transcribe/score 到 dataset export 之间的状态转换无法通过 job runner 完成
- **审查判断**：
  - 极有可能是实现者在拆分 curation 模块时遗漏了顶层的 `run_curation` 编排函数
  - `curate.py` 中的 `update_segment_status` 和 `run_deduplication` 两个子函数实现质量良好，功能完整。缺失的只是将它们编排成一个可由 runner 调用的顶层函数
- **建议修法**：
  - 在 `pipelines/curate.py` 中新增 `run_curation(conn, artifact_store, recording_id, job_id)` 函数
  - 该函数应：接受 recording_id → 找到所有符合条件的 segments → 执行标记操作 → 可选执行 dedup → 写入 job_event → 返回结果
  - 同时检查 runner._execute_step_curate 的参数传递是否与 pipeline/domain services 层一致

### R2. Runner 不支持 `infer_real` 与 `eval_first_test` job 分发

- **严重级别**：`critical`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `api/routes_runs.py:143-152` — `POST /runs/{id}/infer` 创建 `job_name="infer_real"` 的 Job 并存入 DB
  - `api/routes_runs.py:155-164` — `POST /runs/{id}/eval` 创建 `job_name="eval_first_test"` 的 Job 并存入 DB
  - `jobs/runner.py:81-102` — job 分发 switch 完整列表为：`preprocess_all`, `ingest`, `train_sovits`, `diarize`, `slice`, `clean`, `transcribe`, `score`, `curate` — **不含** `infer_real` 和 `eval_first_test`
  - 分发 switch 的 `else` 分支（line 102）抛出 `ValueError(f"Unsupported job type: {job.name}")`
- **为什么重要**：
  - API 端点创建了合法的 Job 记录，但 runner 无法执行它们 — 任何通过 `POST /jobs/{job_id}/run` 或 `POST /runs/{id}/infer` + `POST /jobs/{job_id}/run` 触发的执行都会失败
  - 这使 FT6（FastAPI e2e surface）中关于 `start_inference` 和 `start_eval` 的 API contract 形同虚设 — 端点是活的，但后端执行路径是死的
  - 直接影响 e2e 流程中的"推理→评估"环节，导致 API 驱动的 capstone 无法完成
- **审查判断**：
  - 这是接口与实现之间的典型漂移：API 层按计划暴露了推理/评估 job 创建口，但 runner 层的 dispatch 未同步更新
  - `pipelines/infer_real.py` 中的 `run_real_inference()` 实现质量良好，可以独立工作（CLI 路径已验证），只需在 runner 中连接
- **建议修法**：
  - 在 `runner.py:81-102` 的 job dispatch switch 中增加：
    ```python
    elif job.name == "infer_real":
        self._execute_infer_real(job)
    elif job.name == "eval_first_test":
        self._execute_eval(job)
    ```
  - 实现 `_execute_infer_real(self, job)` → 解析 job.payload → 调用 `run_real_inference()` → 写入 step events
  - 实现 `_execute_eval(self, job)` → 解析 run_id → 调用评估引擎 → 写入 eval_metrics + step events

### R3. 评估链路无真实执行体，CLI eval 写入硬编码 mock 值

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `pipelines/evaluate.py:7-12` — 仅一行 `evaluate_objective_metrics(run_id, conn)` 委托调用，无 job 集成、无事件发出、无 DB 写入
  - `cli.py:279-300` — `eval` CLI 命令直接写入两行硬编码的 `eval_metrics`：`overall_score=0.85, noise_penalty=0.07`（lines 283-296），完全不调用任何评估引擎
  - `eval/objective.py` 与 `eval/smoke.py` 中的评估函数（`evaluate_wav_smoke`, `evaluate_objective_proxy`）实现质量良好但因 runner 不调度 `eval_first_test` job（见 R2）而无法被 API 调用
- **为什么重要**：
  - proposed-planning FT5 要求"真实评估与 release gate 分层"，但当前 CLI eval 路径返回的是硬编码的 mock 值，无法用于任何质量判断
  - 评估是 e2e 训练→推理→评估闭环的最终验证环节，缺失真实评估意味着整个 first-test 的核心价值主张（"真实推理+真实评估闭环"）没有实现
- **审查判断**：
  - 评估模块的底层组件（smoke evaluator, objective proxy, subjective report）代码质量良好，问题在于缺乏编排层将它们串入 runner 和 CLI
  - CLI 写入硬编码值是一个明确的"mock-as-real"违规 — 即使 mock_adapter mode 下也不应返回不反映真实计算的数值
- **建议修法**：
  - 将 `eval/smoke.py` 的 `evaluate_wav_smoke` 与 `eval/objective.py` 的 `evaluate_objective_proxy` 组合成一个 `run_evaluation(run_id, conn)` 编排函数
  - 修改 CLI `eval` 命令调用该编排函数，而非写入硬编码 `INSERT`
  - 结合 R2 的修复，使 runner 能通过 `_execute_eval` 调度该编排函数

### R4. 日志基础设施严重不足，pipelines/adapters/service 层无日志

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - 全项目共 5 个 logger 定义：`storage/sqlite.py:6`, `storage/migrations.py:7`, `jobs/runner.py:27`, `services/__init__.py:28`, `adapters/audio/torchaudio_io.py:4`
  - 仅有 3 个 logger 有实际调用（sqlite, migrations, runner）；`services/__init__.py` 的 logger 从未被调用
  - 以下关键模块零日志输出：`pipelines/ingest.py`, `clean.py`, `transcribe.py`, `train.py`, `slice.py`, `score.py`, `curate.py`, `diarize.py`, `infer_real.py`；`adapters/ffmpeg.py`, `demucs_adapter.py`, `whisper_adapter.py`, `pyannote_adapter.py`, `xtts_adapter.py`, `sovits_adapter.py`, `rvc_adapter.py`
  - 无结构化日志格式（纯 f-string），无 correlation ID，无 request tracing
- **为什么重要**：
  - 当 e2e 流程在容器中执行失败时，debug 只能依赖 `str(e)` 异常消息与 DB 中的 `metadata_json["error"]`，无法通过日志时间线还原调用链
  - 缺乏日志使可观测性从"主动诊断"降级为"被动推断" — 审查者可确认事件已记录，但无法确认事件之间的因果链
- **审查判断**：
  - `job_events` + `metadata_json` 提供了优秀的结构化事件存储，但缺乏运行时日志作为补充
  - 不要求在 first-test 阶段引入 OTel/ELK 等平台化方案（proposed-planning §3.2 O4 明确延后），但至少应在 pipeline/adapters 的关键节点（入口/出口/异常/耗时）增加 Python logging
- **建议修法**：
  - 在每个 pipeline 文件头部增加 `logger = logging.getLogger(__name__)`
  - 在 pipeline 函数入口加 `logger.info("开始 %s, recording_id=%s", step_name, recording_id)`
  - 在 pipeline 函数出口加 `logger.info("完成 %s, duration=%.1fs", step_name, elapsed)`
  - 在 try/except 的 except 分支加 `logger.exception("步骤失败: %s", step_name)` 以同时输出 stack trace
  - 在 `api/app.py` 增加一个 FastAPI middleware 记录 request method/path/status/duration

### R5. `service_train_rvc` 传递 `model_run_id` 给不接受该参数的 `run_train_rvc`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `services/__init__.py:76-83` — `service_train_rvc` 调用 `run_train_rvc(conn, artifact_store, dataset_id, config, model_run_id=model_run_id)`
  - `pipelines/train.py:14-22` — `run_train_rvc` 函数签名：`def run_train_rvc(conn, artifact_store: ArtifactStore, dataset_id: str, config: dict) -> ModelRun:` — 不接受 `model_run_id` 参数
- **为什么重要**：
  - 当以非默认值传递 `model_run_id` 时，调用会因 unexpected keyword argument 而抛出 `TypeError`
  - 目前代码中 `model_run_id` 的默认值路径可能未触发此错误，但这是一个潜在的运行时炸弹
- **审查判断**：
  - 参数签名漂移 — 可能是功能迭代中一端更新而另一端遗漏
- **建议修法**：
  - 核查 `run_train_rvc` 是否应该接受 `model_run_id` 参数（若应，则更新函数签名；若不应，则更新 `service_train_rvc` 调用方）

### R6. `configs` volume 在 compose.yaml 中以 rw 模式挂载

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `infra/docker/compose.yaml:33` — `../../configs:/app/configs`（无 `:ro` 后缀）
  - `infra/docker/compose.yaml:49` — 同上
  - `config.py` 将 configs 视为只读数据源，但 compose 挂载不强制此约束
- **为什么重要**：
  - 若运行时代码或错误地向 `/app/configs` 写入，会污染宿主机 repo checkout 中的 config 目录
  - 低概率事件，但风险明确可消除
- **审查判断**：
  - 防御性加固，无功能影响
- **建议修法**：
  - 将两处挂载改为 `../../configs:/app/configs:ro`

### R7. Evidence pack 不自动捕获 stdout/stderr 与 stack trace

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `evidence.py:167-247` — `collect_evidence_pack()` 导出 8 个文件但无一包含 subprocess stdout/stderr
  - 所有异常捕获均使用 `str(e)` 而非 `traceback.format_exc()`，stack trace 不进入任何持久化存储
  - `commands.json` 需要调用方手动传入命令列表，无法自动收集
- **为什么重要**：
  - 当 capstone 失败时，证据包能告诉你"哪个 step 失败、error message 是什么"，但不能告诉你"subprocess 的完整 stdout/stderr 输出"或"Python 的完整 stack trace"
  - 这使得远程 debug（不看终端只看证据包）的能力受限
- **审查判断**：
  - Evidence pack 在环境复现方面的完整性（env.json + db_summary + artifact_manifest）已足够优秀，缺失的是运行时输出的采集
  - 在 first-test 阶段这不是最高优先级，但建议在 live capstone 执行前补齐
- **建议修法**：
  - 在 `evidence.py` 中增加可选的 `stdout_stderr.json` 采集（从 job_events.metadata_json 中提取或从 pipeline 输出中捕获）
  - 修改异常处理通用模式：`error = f"{exc}\n{traceback.format_exc()}"` 以保留完整调用栈

### R8. `pipeline_runs` 表无任何代码写入

- **严重级别**：`low`
- **类型**：`scope-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `db/migrations/002_state_jobs_artifacts.sql:34-44` — 创建 `pipeline_runs` 表
  - `db/migrations/007_reconcile_to_plan.sql:26-32` — 增加列
  - 全项目 grep `pipeline_runs` 无 INSERT/UPDATE 调用 — 该表在代码中仅存在于 migration 与 schema inventory 测试中
- **为什么重要**：
  - 死代码增加 schema 理解负担，且在 schema drift inventory 测试中作为"期望存在"的表存在
  - proposed-planning §6.2 FT2.7 明确将其标为"只做兼容评估，不默认成为硬依赖" — 但当前连评估都不存在（无写入即无数据可评估）
- **审查判断**：
  - 符合 proposed-planning 的 deferred 边界，但应明确其触发条件
- **建议修法**：
  - 在 deferred-items-ledger 中为 `pipeline_runs` 增加条目：触发条件为"需要跨多 job 的 pipeline 级别元数据追踪"
  - 或从 migration 中移除该表，推迟到实际需要时再创建

---

## 3. In-Scope 逐项对齐审核

> 对照 proposed-planning (§6.1-6.8) 的全量工作项与测试项，逐一核查实现。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | `FT1.1..FT1.7` 准入收敛（命令统一、env、CLI/API preprocess、empty guard、artifact root） | `done` | 7 个工作项 + 7 个测试项全部有对应实现与测试，无 gap |
| S2 | `FT2.1..FT2.7` Schema/observability contract（schema inventory、job_events、adapter metadata、failure summary、trace、mock/real 分离、pipeline_runs 边界） | `done` | schema drift inventory 覆盖全量表/列/FK；job_events 含 step/status/duration/error/artifact_ids/adapter_mode；trace API 完整 |
| S3 | `FT3.1..FT3.6` 真实预处理（FFmpeg、PyAnnote、Demucs、Whisper、dataset freeze、reference selector） | `done` | 全部 adapter 实现完整，preflight 模式正确处理 skip；T-FT3.2 的 live 组件正确 gated |
| S4 | `FT4.1..FT4.6` 真实推理（inference contract、XTTS wrapper、model manifest、no mock fallback、artifact metadata、CLI smoke） | `done` | inference contract 校验完整，XTTS adapter 正确拒绝 mock fallback，model manifest 记录 license/provenance |
| S5 | `FT5.1..FT5.6` 真实评估（三层指标、smoke evaluator、objective proxy、subjective、release gate、eval report） | `done` | 三层指标代码存在且测试覆盖；**但评估的 runner 调度与 CLI 集成存在 R2+R3 缺陷** |
| S6 | `FT6.1..FT6.7` FastAPI e2e surface（run/create/upload/start/status/trace/report contract） | `done` | API surface 完整，TestClient 覆盖良好，response contract snapshot 机制存在；**但 start_infer/start_eval 创建的 job 无法被 runner 执行 (R2)** |
| S7 | `FT7.1..FT7.5` Live capstone（marker policy、evidence exporter、API capstone、pre-capstone gate、evidence validator） | `done` | marker gating 正确，evidence pack 8 文件完整，validator 拒绝 mock/empty/large；T-FT7.3 capstone 正确 gated |
| S8 | `FT8.1..FT8.4` Closure/deferred（first-build 核对、closure ledger、deferred boundary、final input pack） | `done` | closure 文档完整，deferred 条目有 trigger 与 target phase，final input pack 索引全部 artifact |
| S9 | `FT1 测试项 T-FT1.1..T-FT1.7` | `done` | CLI help、bootstrap probe、env config、payload contract、API preprocess、empty guard、artifact root — 全部有测试 |
| S10 | `FT2 测试项 T-FT2.1..T-FT2.7` | `done` | migration order、WAL、job_events metadata、failure summary、trace、mock/real isolation、schema snapshot — 全部有测试 |
| S11 | `FT3 测试项 T-FT3.1..T-FT3.6` | `done` — 1 partial | unit 测试全部存在；T-FT3.2 的 live 组件正确 gated with skip reason |
| S12 | `FT4 测试项 T-FT4.1..T-FT4.6` | `done` — 1 pending | unit 测试全部存在；T-FT4.5 live real inference 正确 gated |
| S13 | `FT5 测试项 T-FT5.1..T-FT5.6` | `done` | smoke metrics、proxy unavailable、MOS validation、eval DB、release gate、eval API — 全部有测试 |
| S14 | `FT6 测试项 T-FT6.1..T-FT6.7` | `done` — 1 pending | TestClient 覆盖完整；T-FT6.7 live HTTP 正确 gated |
| S15 | `FT7 测试项 T-FT7.1..T-FT7.5` | `done` — 1 pending | marker、evidence exporter、pre-capstone gate、evidence validator — 全部有测试；T-FT7.3 capstone 正确 gated |
| S16 | `FT8 测试项 T-FT8.1..T-FT8.3` | `done` | closure docs existence、deferred triggers、final input pack — 全部有测试 |
| S17 | 跨阶段不变量（mock/real、gating、no-fallback、artifact 外置、upload→artifact、arch boundary、skip denominator） | `done` | 全部 7 个不变量均有自动化测试守卫 + evidence validator 硬校验 |
| S18 | DAG 序列 FT1→FT8 执行顺序 | `done` | closure 文件存在且按顺序创建；FT8 docs/check 测试验证了文件完整性 |

### 3.1 对齐结论

- **done**: `91`
- **partial**: `1` (T-FT3.2 live 组件，正确 gated)
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `4` (所有 live pending 项，正确 gated)

> 核心判断：scope compliance 层面，FT1-FT8 的实现忠实地覆盖了 proposed-planning 的全部工作项与测试项，无 scope drift，无不变量破坏。但 scope compliance 的"done"不自动等于"e2e test ready" — R1/R2/R3 三个缺陷使 API 驱动的 e2e 执行不可行。

---

## 4. Out-of-Scope 核查

> 本节用于检查实现是否越界，也用于确认 reviewer 是否把已冻结的 deferred 项误判为 blocker。

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 同时实现 RVC/SoVITS/XTTS 全部真实训练（O1） | `遵守` | 仅 XTTS 有真实推理 wrapper，SoVITS/RVC 训练在 mock mode 运行 — 符合"先追求一条真实推理闭环"的范围 |
| O2 | 完整 ECAPA/CLAP/SBERT embedding 平台（O2） | `遵守` | vec0_store 仅存接口定义，embedding 模块在 mock mode 返回随机向量，无真实 embedding pipeline |
| O3 | 生产级任务队列与分布式 worker（O3） | `遵守` | FastAPI 仅 trigger DB job，无 BackgroundTasks 承载长任务 — 符合"第一版只触发 DB job 与可查询状态" |
| O4 | 完整 OTel 平台化接入（O4） | `遵守` | 仅借 OTel vocabulary（step/status/duration/error 字段），无 OTLP 导出 — 符合"本阶段只借 OTel vocabulary" |
| O5 | 众包平台 MOS 流程（O5） | `遵守` | subjective eval 仅提供本地表单字段（MOS 1-5, ABX 0-1, reviewer, comment），无 P.808 集成 |
| O6 | `pipeline_runs` 表升级为硬依赖 | `遵守` | 表存在但无代码写入 — 保持 FT2.7 的"兼容评估"状态 |
| O7 | Live capstone 真实执行 | `误报风险` | FT7 capstone 正确 gated with skip reason，closure 诚实地标为 `pending-live` — 不应被判为 defect |
| O8 | 非 skipped evidence pack | `误报风险` | deferred-items-ledger 正确记录了 FTD-01/FTD-02，有明确的 trigger 与 target |

> 审查确认：所有 out-of-scope 项均被遵守，无越界实现。R1/R2/R3 三个缺陷属于 in-scope 交付 gap，不属于 deferred 项被误判为 blocker。

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`FT1-FT8 代码实现质量良好，scope compliance 达 91/92 done（0 missing），数据库 schema 设计规范且有充足的扩展性，Docker 容器配置正确且数据存储隔离完整到位，evidence pack 系统提供了完善的离线证据导出与校验能力。但 workflow 执行调度（runner）与 pipeline 实现之间存在 3 个关键断开点（R1/R2/R3），使 e2e 全流程无法通过 API runner 打通。当前状态不是 e2e test ready，需修复 R1/R2/R3 后方可进入 live capstone。`

- **是否允许关闭本轮 review**：`no`

- **关闭前必须完成的 blocker**：
  1. **R1** — 实现 `run_curation` 函数在 `pipelines/curate.py` 中，确保 curate job 可执行
  2. **R2** — 在 `runner.py` 增加 `infer_real` 与 `eval_first_test` 的 dispatch 分支，实现对应的 `_execute_*` 方法
  3. **R3** — 实现 `_execute_eval` 编排函数，接入 `eval/` 模块的真实评估引擎；修复 CLI eval 不再写入硬编码 mock 值

- **可以后续跟进的 non-blocking follow-up**：
  1. **R4** — 在 pipelines/adapters/service 层增加结构化日志（入口/出口/异常/耗时）
  2. **R5** — 修复 `service_train_rvc` 与 `run_train_rvc` 之间的参数签名不一致
  3. **R6** — compose.yaml 中 configs 挂载改为 `:ro` 只读
  4. **R7** — evidence pack 增加 stdout/stderr 与 stack trace 采集
  5. **R8** — 清理 `pipeline_runs` 死表或为其明确 reopen trigger

- **建议的二次审查方式**：`same reviewer rereview`

- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

---

## 6. 实现者回应

> *(待实现者填写)*

