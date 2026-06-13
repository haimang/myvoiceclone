# Nano-Agent 代码审查模板

> 审查对象: `myvoiceclone first-test FT1-FT8 (2nd-pass)`
> 审查类型: `code-review`
> 审查时间: `2026-06-13`
> 审查人: `DeepSeek`
> 审查范围:
> - `src/myvoiceclone/` — 全部源码 (api, domain, jobs, pipelines, eval, adapters, storage, services, config, evidence)
> - `db/migrations/` — 全部 8 个迁移脚本
> - `infra/docker/` — Dockerfile.preprocess, Dockerfile.train, compose.yaml
> - `tests/` — 全部测试文件
> - `docs/closure/first-test/` — FT1-FT8 全部 closure 文档
> - `docs/closure/first-test/deferred-items-ledger.md`
> - `docs/baseline/device_stacks.md`
> - `docs/eval/first-test/proposed-planning.md`
> 对照真相:
> - `docs/eval/first-test/proposed-planning.md` — FT1-FT8 规划基线
> - `docs/eval/first-test/reference-anchor.md` — 8 业务簇、TR 纪律
> - `docs/baseline/device_stacks.md` — 本机 NVIDIA GB10/CUDA 13.0/aarch64 技术状态
> 文档状态: `reviewed`

---

## 0. 总结结论

- **整体判断**：`FT1-FT8 第一轮修复的主体工作成立，代码实现与 closure 声明一致。但本轮审查在两个关键维度上发现核心结构性问题：报错体系几乎不存在（1 个自定义异常 vs 124 个泛型 raise），数据库状态流有 3 个 CRITICAL bug（`eval_reports` 表名错误、`recording` 状态机断连、`VectorStore(Protocol)` 运行时崩溃）。容器化 CUDA 穿透缺少 `runtime: nvidia` 声明导致 `docker compose up` 下 GPU 不可用。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **报错体系是最大结构性债务**：124 个 raise 语句中仅 1 个使用自定义异常（`FFmpegAdapterError`），其余全部为泛型 `ValueError`/`RuntimeError`。零错误码、零报错速查手册、零结构化 API 错误响应，这使系统在真实训练中不可调试。
  2. **3 个 CRITICAL 缺陷阻止 e2e test ready**：`VectorStore(Protocol)` 在 `curate.py:198` 的实例化会触发 `TypeError` 运行时崩溃；`evidence.py` 查询不存在的 `eval_reports` 表导致 trace.json 永不包含报告；`recording` 状态机 ingest 后完全断连。
  3. **容器化 CUDA 穿透少一行关键配置**：`compose.yaml` 缺少 `runtime: nvidia`，导致 `docker compose up` 下 `deploy.resources` 被忽略，GPU 不可穿透到容器。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/eval/first-test/proposed-planning.md` — FT1-FT8 规划，含 30 项工作重分配、82 项测试注入、5 个 owner gate
  - `docs/baseline/device_stacks.md` — GB10 Blackwell (sm_120)、CUDA 13.0、aarch64、Docker 29.2.1
  - `docs/closure/first-test/deferred-items-ledger.md` — FTD-01 ~ FTD-17 deferred 台账
- **核查实现**：
  - `src/myvoiceclone/` — 54 个 Python 源文件，覆盖 api/domain/jobs/pipelines/eval/adapters/storage/services
  - `db/migrations/` — 001 ~ 008 共 8 个 SQL 迁移
  - `infra/docker/` — 2 个 Dockerfile + compose.yaml
  - `tests/` — 53 个测试文件，含 unit/api/cli/integration
- **执行过的验证**：
  - 对全部 6 个审查簇发起独立 sub-agent 并行深度调查
  - 独立阅读全部源码文件（api 路由、domain 实体/状态机、jobs runner/events、pipelines 12 个文件、eval 4 个模块、adapters 10 个文件、storage 5 个文件、config/evidence/services）
  - 交叉对比 closure 文档 vs 代码实现
  - 交叉对比 deferred 台账 vs 代码实际状态
  - 独立验证 `VectorStore(Protocol)` 的实例化可行性
  - 独立验证 `evidence.py` 对 `eval_reports` 的查询目标表是否实际存在
  - 独立核查 `recording` 表的状态流转是否在 pipeline 代码中实际发生
- **复用 / 对照的既有审查**：
  - `docs/code-review/first-test/FT1-FT8-review-VF-ledger.md` — 仅作为 FTD-11~FTD-17 的来源线索，所有验证独立完成

### 1.1 已确认的正面事实

- **R1 修复完整性成立**：12 项 V-fix 声明均在代码中找到对应实现。FTD-11~FTD-17 全部为真实未解决问题，分类正确，没有"假装修复但未修复"的虚假 closure。
- **测试诚实性成立**：progress 134→148 passed 的逻辑一致，所有测试均执行真实代码路径（in-memory SQLite/TestClient），无伪造或同义反复测试。live/slow/gpu 门控纪律保持。
- **数据流主体成立**：ingest→diarize→slice→clean→transcribe→score→curate→freeze→infer→eval→report→release gate 的完整链条骨架存在，artifact lineage 可通过 `parent_artifact_id` 逐跳追溯。
- **mock/real 隔离保持**：`adapter_mode` / `metric_source` 标记贯穿 artifacts, eval_metrics, evidence validator。禁止 mock-as-real 的证据校验器拒绝混入。
- **FT6 API surface 结构合理**：`/api/runs` 的 create→upload→preprocess→infer→eval→status 链路清晰，`RunStatusResponse` 聚合 jobs/events/artifacts/failure_summary。
- **容器化方向正确**：`Dockerfile.train` 使用 `nvcr.io/nvidia/pytorch:25.03-py3`（aarch64 原生），`deploy.resources.reservations.devices` 声明 GPU 需求，数据卷挂载到 repo 外部的 `/mnt/usb/workspace/myvoiceresearch/`。

### 1.2 已确认的负面事实

- **报错体系近于不存在**：整个项目仅 1 个自定义异常类（`FFmpegAdapterError`）。124 个 raise 语句中 52 个 `ValueError`、22 个 `RuntimeError`、28 个 `HTTPException`。零错误码、零报错速查手册、零结构化 API 错误响应 schema。
- **`curate.py:198` 存在运行时崩溃点**：`VectorStore(conn)` 尝试实例化一个 `Protocol`（Python 抽象接口），在 `dedupe=True` 时会触发 `TypeError`。
- **`evidence.py:86,146-147` 存在数据丢失 bug**：查询名为 `eval_reports` 但实际表名为 `reports`，导致 trace.json 永远不包含报告数据。
- **`recording` 状态机完全断连**：`RecordingStatus` 定义了 11 个状态，但 ingest 后仅设置 `PROCESSED`，后续 diarize/slice/clean/transcribe/score/curate 从不更新 recording 状态。
- **`compose.yaml` 缺少 `runtime: nvidia`**：`docker compose up` 下 `deploy.resources` 被忽略，训练容器无 GPU 访问。
- **`score.py` 无 artifact 产出**：所有分数硬编码（mock），不创建 artifact，使评分活动在 artifact lineage 中完全不可见。
- **`pipeline_runs` 表完全死亡**：迁移 002 创建、007 扩展，但生产代码零引用。
- **`recordings` 和 `segments` 表无 CHECK 约束**：7 个状态机中 3 个在 DB 层面零约束。
- **`model_runs` 无 FK 到 `jobs`**：无法用单条 SQL 查询"哪个 job 产生了这个 model_run"。
- **`version` 在所有 adapter 的 `metadata()` 中为 `None`**：实际安装版本未被解析。
- **`device` 在所有 adapter 的 `metadata()` 中为静态 `"cuda-or-cpu"`**：实际运行时设备未被写入 artifact metadata（仅 XTTS `synth_to_file` 例外）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 所有发现附 file:line 引用，独立阅读全部源文件 |
| 本地命令 / 测试 | no | 本轮为静态审查，未执行本地 pytest |
| schema / contract 反向校验 | yes | DB migrations vs domain states 交叉对比；API schemas vs 实际响应结构对比 |
| live / deploy / preview 证据 | no | first-test 仅有 skipped evidence；未执行 live capstone |
| 与上游 design / QNA 对账 | yes | proposed-planning.md FT1-FT8 逐项对照 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `curate.py:198` 实例化 Protocol `VectorStore` 导致 Runtime TypeError | critical | correctness | yes | 改用 `NullVectorStore()` 或具体实现 |
| R2 | `evidence.py:86,146` 查询不存在的 `eval_reports` 表 → trace.json 永不包含报告 | critical | correctness | yes | 将 `eval_reports` 改为 `reports` |
| R3 | `recording` 状态机 ingest 后完全断连 — 9 个状态永不写入 | critical | correctness | yes | pipeline 各步骤追加 `recording.status` 更新 |
| R4 | 报错体系几乎不存在 — 124 raise 中仅 1 个自定义异常 | critical | delivery-gap | yes | 建立 `VoiceCloneError` 层级 + 错误码 + 报错速查手册 |
| R5 | `compose.yaml` 缺少 `runtime: nvidia` — GPU 在 `docker compose up` 下不可用 | high | platform-fitness | yes | train 服务添加 `runtime: nvidia` |
| R6 | 报错持久化仅存 `str(e)` 无 traceback — 崩溃后无法离线诊断 | high | delivery-gap | yes | `job.error_msg` 存储 `traceback.format_exc()` |
| R7 | API 零结构化错误响应 — 全部 `HTTPException(status, str)` | high | delivery-gap | no | 创建 `ErrorResponse` Pydantic schema |
| R8 | 无错误码/报错速查手册 — 操作员面对 "Dataset not found" 无法诊断 | high | docs-gap | no | 创建 `docs/error-catalog.md` |
| R9 | 无统一 errors 表 — 查"最近 24h 所有错误"需要 UNION 3 个表 | high | delivery-gap | no | 创建 `errors` 迁移表 |
| R10 | `score.py` 全 mock 无 artifact — 评分在 lineage 中不可见 | medium | correctness | no | `score.py` 产出评分 artifact |
| R11 | `release gate` 空 eval_metrics 时 pass — 评估未执行不应通过 | medium | correctness | no | `quality_pass` 需要 ≥1 个非 mock 指标 |
| R12 | `slice.py` 缺少 `ffmpeg_adapter.metadata()` — 违反 metadata contract | medium | correctness | no | 补全 metadata |
| R13 | `recording` 无 `updated_at` 列 — 状态变化时间不可查 | medium | schema-drift | no | migration 添加 `updated_at` |
| R14 | adapter `metadata()` 中 `version` 全部为 `None` — 证据包不可复现 | medium | test-gap | no | 使用 `importlib.metadata.version()` |
| R15 | `source_artifact_id` 永远等于 `parent_artifact_id` — 语义折叠 | medium | correctness | no | 区分"直接来源"与"原始来源" |
| R16 | `pipeline_runs` 表死亡 — 迁移中定义但代码零引用 | low | scope-drift | no | 移除或正式实现 |
| R17 | adapter `device` 静态 `"cuda-or-cpu"` — 实际 device 未写入 artifact | low | test-gap | no | 运行时解析实际 device |
| R18 | `migration 007` 后 `embedding_items` 未 DROP — 遗留死表 | low | schema-drift | no | 添加 DROP TABLE embedding_items |
| R19 | API 零 pagination — 所有列表端点返回全量无界数据 | high | delivery-gap | no | 添加 `limit`/`offset` 参数 |
| R20 | `RunStatusResponse` 嵌套字段为裸 `List[Dict]` — 无类型安全 | medium | correctness | no | 替换为 typed sub-model |
| R21 | API 仅 1/36 端点有 frozen contract snapshot | medium | docs-gap | no | 扩展所有 11 个 response schema 的 contract fixtures |
| R22 | API 错误 HTTP code 不一致 — 同类型错误用 400/422/500 | medium | protocol-drift | no | 统一 400 用于 validation，500 用于 server error |
| R23 | `GET /api/runs` 列表端点缺失 — 无法枚举所有 run | medium | delivery-gap | no | 添加 run 列表端点 |
| R24 | Report/gate ID 由调用方提供 — 无 prefix 约束，可能碰撞 | low | correctness | no | 服务端自动生成 `report_`/`gate_` ID |
| R25 | `create_gate_report` 与 `get_audit_trace` 缺少 `response_model` | low | protocol-drift | no | 添加 `GateReportResponse` / `AuditTraceResponse` schema |

---

### R1. `curate.py:198` — 实例化 Protocol `VectorStore` 导致 Runtime TypeError

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/storage/vector_store.py:3` — `class VectorStore(Protocol):` 定义为一个纯抽象接口 Protocol
  - `src/myvoiceclone/pipelines/curate.py:192-198` — 当 `dedupe=True` 时执行 `VectorStore(conn)`
  - Python Protocol 不可实例化：`TypeError: Protocols cannot be instantiated`
- **为什么重要**：
  - 这是一个确定的运行时崩溃点。任何触发 `dedupe=True` 的 curate 流程（无论是 CLI 还是 API）都会在此处崩溃。
  - 当前测试可能因为 `dedupe` 默认为 `False`（`curate.py:140`）而未触发，但一旦启用 dedup，系统立即失败。
  - 正确的做法是传入 `NullVectorStore()` 或 `Vec0Store` 等具体实现。
- **审查判断**：
  - 此 bug 类似类型使用错误，应属编码疏忽。`curate.py:8` 正确 import 了 `VectorStore`（Protocol），但 `curate.py:193` 又重复 import 一次，并在 198 行直接实例化。
- **建议修法**：
  - 将 `curate.py:198` 改为使用具体实现 `from myvoiceclone.storage.vec0_store import Vec0Store; VectorStore = Vec0Store(conn, namespace="audio")` 或在无 vec 可用时使用 `NullVectorStore()`。

---

### R2. `evidence.py:86,146-147` — 查询不存在的 `eval_reports` 表导致 trace.json 数据丢失

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/evidence.py:86` — `"eval_reports"` 列示于表清单
  - `src/myvoiceclone/evidence.py:146` — `_table_exists(conn, "eval_reports")` 永远返回 `False`
  - `db/migrations/004_reports_metrics.sql:3` — 实际建表名为 `reports`
  - `src/myvoiceclone/evidence.py:147` — `SELECT * FROM eval_reports` 永不执行，因为表不存在
- **为什么重要**：
  - trace.json 是 evidence pack 的核心组件。缺失 reports 数据意味着离线调试者永远看不到评估报告的历史记录。
  - 这是一个表名拼写错误，属于简单但影响面大的 bug。
- **审查判断**：
  - 八成为编码时的命名不一致。迁移中使用 `reports`，evidence.py 中误用 `eval_reports`。
- **建议修法**：
  - 将 `evidence.py:86,146,147` 中所有 `eval_reports` 改为 `reports`。

---

### R3. `recording` 状态机 ingest 后完全断连

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/domain/states.py:19-32` — `RecordingStatus` 定义了 11 个状态
  - `src/myvoiceclone/pipelines/ingest.py:109` — 唯一设置 `recording.status = RecordingStatus.PROCESSED`
  - `src/myvoiceclone/pipelines/diarize.py` — 未更新 `recording.status`
  - `src/myvoiceclone/pipelines/slice.py` — 未更新
  - `src/myvoiceclone/pipelines/clean.py` — 未更新
  - `src/myvoiceclone/pipelines/transcribe.py` — 未更新
  - `src/myvoiceclone/pipelines/score.py` — 未更新
  - `src/myvoiceclone/pipelines/curate.py` — 未更新
- **为什么重要**：
  - 无法从 DB 单条查询得知 recording 的预处理进度。操作员必须 JOIN segments 才能推断。
  - `RecordingStatus.DIARIZED/SLICED/CLEANED/TRANSCRIBED/SCORED/CURATED/ARCHIVED` 全部是死代码。
- **审查判断**：
  - 状态机定义完整，但代码从未驱动。这使 `recording` 成为 pipeline 中的"孤儿"。
- **建议修法**：
  - 每个 pipeline 步骤结束时追加 `recording.status = RecordingStatus.XXX` 更新，如 `diarize.py` 结尾设 `DIARIZED`。

---

### R4. 报错体系几乎不存在

- **严重级别**：`critical`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - 全项目仅 1 个自定义异常：`adapters/audio/ffmpeg.py:8` `FFmpegAdapterError`
  - 统计：`ValueError` 52 处、`RuntimeError` 22 处、`HTTPException` 28 处、`FileNotFoundError` 8 处、`NotImplementedError` 3+ 处
  - 零错误码、零 `errors.py` 模块、零报错速查手册
  - API 全部使用 `HTTPException(status_code=N, detail="bare string")`，无结构化响应
  - `runner.py:132` 仅存储 `str(e)`，无 traceback
- **为什么重要**：
  - 真实训练中（尤其是长程 SoVITS/RVC）必然产生大量异常。当前体系下无法对异常进行分类、统计、速查、自动修复建议。
  - 前端消费者无法解析 API 错误（无 `code` 字段，无法区分 "NOT_FOUND" 与 "INTERNAL_ERROR"）。
- **审查判断**：
  - 这是 first-test 最根本的架构缺失。报错不是"锦上添花"而是"可运维性的基础"。没有结构化错误体系就无法 claim "e2e test ready"。
- **建议修法**：
  1. 创建 `src/myvoiceclone/errors.py`，建立 `VoiceCloneError` → `AdapterError/ PipelineError/ StorageError/ ValidationError/ ResourceNotFoundError` 层级。
  2. 在 `api/schemas.py` 中创建 `ErrorResponse(BaseModel)` schema。
  3. 创建 `docs/error-catalog.md` 报错速查手册。
  4. 在 `runner.py` 中将 `error_msg = str(e)` 改为 `error_msg = traceback.format_exc()`。

---

### R5. `compose.yaml` 缺少 `runtime: nvidia` — GPU 在 `docker compose up` 下不可用

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `infra/docker/compose.yaml:58-65` — `deploy.resources.reservations.devices` 仅在 `docker stack deploy` (Swarm) 下生效
  - `docker compose up` 下需要 `runtime: nvidia` 或配置 nvidia 为 Docker 默认 runtime
  - 当前 compose.yaml 无 `runtime: nvidia` 声明
  - `tests/unit/test_docker_first_test_contract.py` 未测试 GPU runtime 配置
- **为什么重要**：
  - 按当前 compose.yaml 执行 `docker compose up train` 会得到一个无 GPU 的 PyTorch 容器。
  - 容器内 `torch.cuda.is_available()` 返回 `False`，所有训练静默回退 CPU。
- **审查判断**：
  - 容器化设计方向正确（NGC image + GPU reservation + nvidia-container-toolkit 文档记载），但少了一行关键配置。
- **建议修法**：
  - 在 compose.yaml 的 `train` 服务下添加 `runtime: nvidia` 行，或文档化要求用户配置 `/etc/docker/daemon.json` 的 `"default-runtime": "nvidia"`。

---

### R6. 报错持久化仅存 `str(e)` 无 traceback

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/jobs/runner.py:132` — `job.error_msg = str(e)`
  - `src/myvoiceclone/jobs/runner.py:227` — `write_step_event(..., error=str(exc))`
  - `src/myvoiceclone/pipelines/train.py:450` — `run.config_json["error_msg"] = str(e)`
  - 无任何地方使用 `traceback.format_exc()` 或 `traceback.format_exception()`
- **为什么重要**：
  - 真实训练崩溃后，如果只有 `str(e)`（如 "CUDA error: out of memory"），无法定位是哪个 epoch、哪行代码、哪个 tensor 导致。
  - 离线调试完全依赖于能复现，而长程训练复现成本极高。
- **建议修法**：
  - 所有 `str(e)` 错误存储改为 `traceback.format_exc()`，同时保留 `str(e)` 作为短摘要。

---

### R7. API 零结构化错误响应

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/api/schemas.py` 包含 0 个错误相关 Pydantic 模型
  - 全部 API 路由使用 `HTTPException(status_code=N, detail="bare string")`
- **建议修法**：
  - 创建 `ErrorResponse` 与 `ErrorDetail` Pydantic schema，使用 FastAPI 的 `exception_handler` 统一拦截。

---

### R8~R9. 无错误码/报错速查手册 + 无统一 errors 表

- **严重级别**：`high`
- **类型**：`docs-gap` / `delivery-gap`
- **是否 blocker**：`no`
- **建议修法**：创建 `docs/error-catalog.md` + 创建 `errors` 迁移表统一持久化。

---

### R10. `score.py` 全 mock 无 artifact

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/pipelines/score.py:38-42` — 所有分数硬编码
  - score.py 不调用 `artifact_store.create_artifact`，直接 mutate segment 字段
- **建议修法**：使 score 步骤可选地调用真实 scorer，并产出评分 artifact。

---

### R11. Release gate 空 eval_metrics 时 pass

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/domain/policies.py:127` — `quality_pass = policy_result["passed"] and (not has_mock_metric or has_quality_metric)`
  - 当 `metric_jsons` 为空时，`has_mock_metric=False` 且 `has_quality_metric=False`，`quality_pass=True`（依赖 consent）
- **建议修法**：添加条件 `and len(metric_jsons) > 0`。

---

### R12~R18. 中等/低优先级发现

| 编号 | 问题 | 位置 |
|------|------|------|
| R12 | `slice.py:61-66` 缺少 `ffmpeg_adapter.metadata()` | `pipelines/slice.py` |
| R13 | `recording` 表缺少 `updated_at` 列 | `001_core_schema.sql` |
| R14 | adapter `metadata()` 中 `version` 全为 `None` | 全部 adapter 文件 |
| R15 | `source_artifact_id` = `parent_artifact_id` 语义折叠 | `artifact_store.py:69` |
| R16 | `pipeline_runs` 表死亡 | `002_state_jobs_artifacts.sql:49-54` |
| R17 | `device` 静态 `"cuda-or-cpu"` — 未运行时解析 | 全部 adapter `metadata()` |
| R18 | `embedding_items` 迁移后未 DROP | `007_reconcile_to_plan.sql:157` |

---

## 3. In-Scope 逐项对齐审核

> 对照 `proposed-planning.md` §6 的 FT1-FT8 工作项与测试注入。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | FT1.1 统一命令入口 | `done` | CLI 接口完整，typer 多层子命令 |
| S2 | FT1.6 empty dataset guard | `done` | `export_dataset.py:65-69,139-140` 双重守卫 |
| S3 | FT2.2 step-level job_events contract | `partial` | preprocess_all 有 step 事件，但独立 step jobs 无 |
| S4 | FT2.3 adapter metadata contract | `partial` | 5/7 adapter 有 `metadata()`，version/device 均未解析 |
| S5 | FT2.6 mock/real evidence separation | `done` | adapter_mode/metric_source 贯穿 artifacts/eval/evidence |
| S6 | FT3.5 dataset freeze non-empty manifest | `done` | 含 lineage、checksum、split leak detection |
| S7 | FT4.4 禁止 mock fallback | `done` | XTTS real mode 下明确 raise 而非静默回退 |
| S8 | FT5.1 三层指标 | `partial` | smoke 实现、proxy 为 unavailable placeholder、manual MOS 可用 |
| S9 | FT5.5 release gate 分层 | `partial` | smoke/quality/manual 分层存在，但空 eval 时 quality pass (R11) |
| S10 | FT6.1 create run / upload / start | `done` | `/api/runs` 完整 surface |
| S11 | FT6.2 upload 后立即落 artifact | `done` | `upload_audio` 读 content → `create_artifact` |
| S12 | FT6.4 status API | `done` | `RunStatusResponse` 聚合 jobs/events/artifacts/failure_summary |
| S13 | FT6.5 artifacts/eval/report/release/trace | `partial` | reports/trace 表名错误 (R2)；curate 无 API endpoint |
| S14 | FT7.1 live/slow/gpu marker policy | `done` | pytest.ini 默认排除，skip with reason |
| S15 | FT7.2 evidence exporter | `partial` | 结构完整但 `eval_reports` 表名错误 (R2) |
| S16 | FT8 closure/deferred reconciliation | `done` | closure 文档 + deferred ledger 结构完整 |

### 3.1 对齐结论

- **done**: `8`
- **partial**: `8`
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> **总结**：这更像"核心骨架完成，但 metadata contract 不完整 + 2 个 CRITICAL bug + 报错体系完全缺失 + API 缺少 pagination/envelope"，而不是 `implementation-complete-awaiting-live-verification`。当前状态应按 `awaiting-fixes-before-live` 重新分类。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | RVC/SoVITS/XTTS 全部真实训练 (O1) | `遵守` | 仍为 mock/fake bytes，未越界 |
| O2 | 真实 embedding 平台 (O2, FTD-05) | `遵守` | Vec1Store gated behind ENABLE_VEC1_PROBE |
| O3 | 生产级任务队列 (O3, FTD-06) | `遵守` | 单进程 JobRunner，无 broker |
| O4 | 完整 OTel (O4, FTD-08) | `遵守` | 仅借 OTel vocabulary，落 DB events |
| O5 | 众包 MOS 平台 (O5, FTD-09) | `遵守` | 仅本地 MOS/ABX 表单 |
| O6 | `pipeline_runs` 表 (FTD-16) | `遵守` | 已 deferred，但建议删表以减少 schema 噪音 |
| O7 | API envelope freeze (FTD-07) | `遵守` | 未冻结全局 envelope，仅 FT6 contract |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`FT1-FT8 第一轮修复的主体工作成立，但当前不应标记为 e2e-test-ready。存在 4 个 CRITICAL blocker（R1-R4）和 2 个 HIGH blocker（R5-R6），全部集中在报错体系缺失、数据正确性 bug、容器化 GPU 访问、录制状态机断连四个方面。API 层缺乏 pagination/response envelope/结构化错误响应，且仅有 1/36 个端点有 contract snapshot。建议第二轮修复聚焦这 6 个 blocker 后再重新评估。`

- **是否允许关闭本轮 review**：`no`

- **关闭前必须完成的 blocker**：
  1. **R1**: 修复 `curate.py:198` `VectorStore(conn)` → 改用 `NullVectorStore()` 或具体实现
  2. **R2**: 修复 `evidence.py` 中 `eval_reports` → `reports` 的表名错误
  3. **R3**: 在 `diarize/slice/clean/transcribe/score/curate` 各步末尾追加 `recording.status` 更新
  4. **R4**: 建立 `VoiceCloneError` 异常层级 + `ErrorResponse` API schema + `docs/error-catalog.md` 报错速查手册
  5. **R5**: `compose.yaml` train 服务添加 `runtime: nvidia`
  6. **R6**: 所有 `str(e)` 错误存储改为 `traceback.format_exc()`

- **可以后续跟进的 non-blocking follow-up**：
  1. **R7-R9**: API 结构化错误响应、错误码、统一 errors 表
  2. **R10**: `score.py` 产出评分 artifact
  3. **R11**: release gate 空 eval 时不应 pass
  4. **R12-R25**: metadata contract 补全、version/device 运行时解析、死表清理、API pagination、contract snapshot 扩展、错误码统一

- **建议的二次审查方式**：`same reviewer rereview` — 6 个 blocker 修复后由同一审查人复核
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> **本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。**
