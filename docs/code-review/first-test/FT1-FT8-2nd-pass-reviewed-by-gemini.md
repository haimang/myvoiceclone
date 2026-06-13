# Nano-Agent 代码审查模板

> 审查对象: `first-test (FT1-FT8)`
> 审查类型: `closure-review | rereview | mixed`
> 审查时间: `2026-06-13`
> 审查人: `Gemini`
> 审查范围:
> - `src/myvoiceclone/pipelines/`
> - `src/myvoiceclone/adapters/`
> - `src/myvoiceclone/api/`
> - `src/myvoiceclone/jobs/`
> - `src/myvoiceclone/storage/`
> - `src/myvoiceclone/domain/`
> - `infra/docker/`
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/closure/first-test/first-test-closure.md`
> - `docs/closure/first-test/deferred-items-ledger.md`
> - `docs/baseline/device_stacks.md`
> 对照真相:
> - `myvoiceclone/docs/eval/first-test/proposed-planning.md`
> - `myvoiceclone/docs/closure/first-test/first-test-closure.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 该实现主体架构与流程闭环已基本建立，但由于发现 SQLite 迁移外键保护缺失、Mock 模式下音频切片及分离逻辑引发下行数据损毁、证据导出路径硬编码可移植性泄漏等多项 Critical/High 级别的 Blockers，本轮 Review 不予收口。

- **整体判断**：`first-test 的核心代码骨架、API 终点以及基于 mock_adapters 的单元测试套件均已就位，但迁移脚本、Mock 边界隔离以及硬编码路径在真实容器化/存量部署中存在重大缺陷，当前不应标记为 completed，且不允许关闭本轮 review。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `007_reconcile_to_plan.sql 迁移脚本在 DROP 并重建主表时未暂时停用外键（PRAGMA foreign_keys = OFF），在非空存量数据库部署时将因关联表的强外键约束触发迁移崩溃。`
  2. `Mock 模式下的音频处理存在破坏性实现：ffmpeg 切片在 mock 下直接复制完整原音频破坏了时长的一致性，而 demucs 分离直接写入纯文本 "mock cleaned audio data" 导致生成的 .wav 文件数据结构损毁，会在下行读取或客观质量校验时造成 crash。`
  3. `evidence.py 中硬编码了 DEFAULT_EVIDENCE_ROOT 外部路径，违反了容器化环境的可移植性原则，导致 Docker 容器必须强行镜像宿主机的外部磁盘目录树。`

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - [proposed-planning.md](file:///root/workspace/myvoiceclone/docs/eval/first-test/proposed-planning.md)
  - [first-test-closure.md](file:///root/workspace/myvoiceclone/docs/closure/first-test/first-test-closure.md)
  - [deferred-items-ledger.md](file:///root/workspace/myvoiceclone/docs/closure/first-test/deferred-items-ledger.md)
  - [device_stacks.md](file:///root/workspace/myvoiceclone/docs/baseline/device_stacks.md)
- **核查实现**：
  - [score.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/pipelines/score.py)
  - [ffmpeg.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/adapters/audio/ffmpeg.py)
  - [demucs_adapter.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/adapters/separation/demucs_adapter.py)
  - [evidence.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/evidence.py)
  - [runner.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/jobs/runner.py)
  - [states.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/domain/states.py)
  - [007_reconcile_to_plan.sql](file:///root/workspace/myvoiceclone/db/migrations/007_reconcile_to_plan.sql)
  - `src/myvoiceclone/api/` (API routes 目录)
  - `infra/docker/` (Dockerfile 及 compose.yaml 目录)
- **执行过的验证**：
  - 本轮作为静态审查，核心基于 sub-agent 在多话题层面的代码扫描与依赖关系图审计。
- **复用 / 对照既有审查**：
  - `None` — 全程进行独立、辩证的静态代码复核。

### 1.1 已确认的正面事实

- **架构边界守卫有效**：API 与 CLI 层成功移除了所有对 pipelines/eval 层的直接导入，改为通过统一的服务编排入口 [services/__init__.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/services/__init__.py) 进行桥接。
- **数据流 lineage 追踪完整**：`artifacts` 数据库表、`job_events` 事件流以 JSON 格式记录了 preprocess 所有步骤（ingest, diarize, slice, clean, transcribe, score）的一级 lineage 及父子关联。
- **API 覆盖面完备**：API 终点覆盖了从 raw 音频上传（立刻落盘为 artifact，避免长任务生命周期丢失临时文件）、任务分发、状态查询到 subjective 评分及 audit trace 的完整业务链条。

### 1.2 已确认的负面事实

- **SQLite 007 迁移安全性低**：当 `PRAGMA foreign_keys = ON;` 启用时，直接执行重建 `jobs` 和 `datasets` 表的 `DROP TABLE` 逻辑会因 `job_events` 和 `dataset_segments` 表的外键引用被拒绝，导致旧库升级失败。
- **Mock 模式下文件一致性破裂**：[demucs_adapter.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/adapters/separation/demucs_adapter.py#L35) 直接向 `.wav` 路径写入纯文本，导致该文件数据损坏，任何依赖 wave 头读取的操作都会崩溃。
- **证据链路径环境耦合**：[evidence.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/evidence.py#L16) 将证据导出的根路径硬编码为 `/mnt/usb/workspace/myvoiceresearch/test-runs`，导致容器化或多开发机迁移非常困难。
- **隐藏的静默 Mock 绕过**：[score.py](file:///root/workspace/myvoiceclone/src/myvoiceclone/pipelines/score.py#L40) 中的 noise_score, overlap_score, speaker_score 在 `MOCK_ADAPTERS=false` 时依然被强制赋予静态常数值，绕过了真实的数据质量校验。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 逐行审计了 `ffmpeg.py`、`demucs_adapter.py`、`score.py`、`evidence.py`、`007_reconcile_to_plan.sql` 等关键模块。 |
| 本地命令 / 测试 | `no` | 本轮仅进行静态推理与逻辑碰撞，未在真实容器内跑 live 流程。 |
| schema / contract 反向校验 | `yes` | 对照 migration 007 脚本，反向审计了其在外键约束启用下的行为。 |
| live / deploy / preview 证据 | `yes` | 审查了 skipped capstone 证据导出包的内容结构。 |
| 与上游 design / QNA 对账 | `yes` | 对照了 `proposed-planning.md` 中定义的 FT1-FT8 八大业务簇及测试红线。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 007 迁移脚本对 DROP 主表操作缺乏外键停用保护 | `high` | `correctness` | `yes` | `PRAGMA foreign_keys = OFF;` 包裹 |
| R2 | Preprocess 分离与切片在 Mock 模式下生成损坏文件并忽略时长约束 | `high` | `correctness` | `yes` | 生成合法 Tiny WAV 骨架并根据时值做 truncate/silent 填充 |
| R3 | 证据导出路径 DEFAULT_EVIDENCE_ROOT 外部强耦合导致容器可移植性破裂 | `medium` | `platform-fitness` | `yes` | 改为环境变量注入并回退至默认容器内路径 |
| R4 | 质量评分逻辑 score.py 包含无视 mock 标志的隐藏静默 mock 常量 | `medium` | `delivery-gap` | `no` | 在非 mock 下对缺失分数抛出警告或显式处理 |
| R5 | 异常捕获机制边界泄漏，缺乏系统级统一异常继承层次与全局 API 拦截 | `medium` | `correctness` | `no` | 引入统一 MVC 异常继承树并在 app.py 中挂载全局异常拦截器 |
| R6 | Job 状态空间分类漂移（Plan Canonical 与 Code Compat 并存） | `low` | `protocol-drift` | `no` | 统一迁移应用端状态代码到 canonical 属性 |
| R7 | Demucs 临时目录在搬运输出文件后未实施垃圾清理导致存储脏留 | `low` | `platform-fitness` | `no` | 在 separate 逻辑中加入 try-finally 执行临时目录清理 |

---

### R1. 007 迁移脚本对 DROP 主表操作缺乏外键停用保护

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [007_reconcile_to_plan.sql:L32](file:///root/workspace/myvoiceclone/db/migrations/007_reconcile_to_plan.sql#L32): `DROP TABLE IF EXISTS datasets;`
  - [007_reconcile_to_plan.sql:L61](file:///root/workspace/myvoiceclone/db/migrations/007_reconcile_to_plan.sql#L61): `DROP TABLE IF EXISTS jobs;`
  - [sqlite.py:L27](file:///root/workspace/myvoiceclone/src/myvoiceclone/storage/sqlite.py#L27): `PRAGMA foreign_keys = ON;` 在每次连接数据库时均被强行拉起。
- **为什么重要**：
  - SQLite 在启用外键强制检查时，如果直接 `DROP` 某个包含活动引用的主表（例如，存在 `job_events` 记录指向正在被 drop 的 `jobs` 表，或者存在 `dataset_segments` 记录指向 `datasets` 表），将会报外键约束错误，导致迁移直接中断，存量老库根本无法升级。
- **审查判断**：
  - 这是一个严重的 schema 维护安全漏洞，在干净库初始安装时暴露不明显，但在存量数据更新时将直接引发部署灾难。
- **建议修法**：
  - 在 `007_reconcile_to_plan.sql` 文件的最顶端插入 `PRAGMA foreign_keys = OFF;`，并在整个迁移脚本结束后恢复 `PRAGMA foreign_keys = ON;`。

---

### R2. Preprocess 分离与切片在 Mock 模式下生成损坏文件并忽略时长约束

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [demucs_adapter.py:L35](file:///root/workspace/myvoiceclone/src/myvoiceclone/adapters/separation/demucs_adapter.py#L35): `f.write(b"mock cleaned audio data")` 直接将文本字节写入 `.wav` 后缀的文件中。
  - [ffmpeg.py:L152](file:///root/workspace/myvoiceclone/src/myvoiceclone/adapters/audio/ffmpeg.py#L152): `shutil.copy(in_path, out_path)` 在 Mock 模式下无视 `start_sec` 与 `end_sec` 的实际范围，直接物理复制整条长音轨。
- **为什么重要**：
  - 1）写入文本字节到 `.wav` 后缀会导致生成的根本不是一个合法的 RIFF/WAV 文件。当下行单元测试或真实 pipeline（例如，客观指标评测模块）使用 Python `wave` 库或 libsndfile 尝试加载该文件时，将引发不可捕获的损坏音频异常，导致 mock 调试流崩溃。
  - 2）ffmpeg 复制完整音频会导致切片时长名不副实，绕过了时长的业务检查，破坏了数据一致性。
- **审查判断**：
  - Mock 代码不可粗暴敷衍，必须输出满足基础文件协议的多媒体数据骨架和格式规范。
- **建议修法**：
  - 1）Mock 切片逻辑应当利用 Python `wave` 库生成一个包含几秒无声（Muted）数据的合法短 WAV 文件。
  - 2）Mock 分离逻辑可以直接对输入的切片 WAV 进行文件复制，而不是向输出文件写入纯文本垃圾数据。

---

### R3. 证据导出路径 DEFAULT_EVIDENCE_ROOT 外部强耦合导致容器可移植性破裂

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [evidence.py:L16](file:///root/workspace/myvoiceclone/src/myvoiceclone/evidence.py#L16): `DEFAULT_EVIDENCE_ROOT = Path("/mnt/usb/workspace/myvoiceresearch/test-runs")` 属于写死的外部硬路径。
- **为什么重要**：
  - Docker 容器内部本应拥有自己隔离的虚拟文件空间。因为应用层把证据存储位置死锁在了 `/mnt/usb/...`，导致 `compose.yaml` 中容器内外的 volume 挂载不得不高度镜像宿主机结构。一旦更换运行节点（或者目标机器无外置 `/mnt/usb` 盘符），程序就会因路径无写入权限而直接崩溃。
- **审查判断**：
  - 违反了容器化部署无状态和高可移植性原则。
- **建议修法**：
  - 修改 `DEFAULT_EVIDENCE_ROOT` 的赋值逻辑，优先从环境变量（如 `EVIDENCE_ROOT`）读取，仅在未设置时 fallback 到容器内常规目录 `/app/test-runs`：
    ```python
    DEFAULT_EVIDENCE_ROOT = Path(os.getenv("EVIDENCE_ROOT", "/app/test-runs"))
    ```

---

### R4. 质量评分逻辑 score.py 包含无视 mock 标志的隐藏静默 mock 常量

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - [score.py:L40](file:///root/workspace/myvoiceclone/src/myvoiceclone/pipelines/score.py#L40):
    ```python
    noise_score = 0.9  # Mock noise score
    overlap_score = 1.0  # Mock overlap score
    speaker_score = 0.85  # Mock speaker similarity
    ```
- **为什么重要**：
  - 在 `MOCK_ADAPTERS=false` 的真实数据处理流程中，这三个质量维度依然被硬编码常量完全遮掩。这意味着即使录音存在严重爆音或背景杂音，系统也会因为隐藏的假数据通过质量校验，直接拉低了整个训练数据集的纯净度，这背离了数据流的实践要求。
- **审查判断**：
  - 此为隐秘的静默 Mock，在首轮修复中未被识别，属于 delivery 缺陷。
- **建议修法**：
  - 如果并非 mock 环境，应当接入真正的声学特征提取器来得出分数；若当前阶段必须保留为占位，也应在非 mock 下抛出 warning，并在 `metadata_json` 显式标记为 `metric_source: mock`。

---

### R5. 异常捕获机制边界泄漏，缺乏系统级统一异常继承层次与全局 API 拦截

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - 整个应用只定义了 [ffmpeg.py:L8](file:///root/workspace/myvoiceclone/src/myvoiceclone/adapters/audio/ffmpeg.py#L8) 中的 `FFmpegAdapterError`，其他如 Pyannote、Whisper、Demucs 等适配层均直接抛出 Python 内建异常。
  - API Routes（如 [routes_inference.py:L12](file:///root/workspace/myvoiceclone/src/myvoiceclone/api/routes_inference.py#L12)）手工使用 `try-except Exception` 强行包裹，并把底层的 raw traceback / SQLite constraint 错误直接暴露给 HTTP 响应体。
- **为什么重要**：
  - 底层库的崩溃细节（比如 CUDA OOM，连接超时）没有被拦截转换就直达网络接口，容易导致底层信息泄露，也降低了 API 系统的健壮度。
- **审查判断**：
  - 缺乏面向领域设计的异常抽象层。
- **建议修法**：
  - 1）设计一个全局异常基类（如 `MVCError`），提供标准错误码和消息封装。
  - 2）在 `app.py` 中挂载全局的异常拦截拦截中间件（FastAPI Exception Handler），将异常统一规整为标准响应体（如 `{"status": "error", "error": {...}}`）。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | FT1 准入收敛 | `done` | `myvoiceclone` 脚本入口、extras/live bootstrap、环境隔离、CLI 输入合同等均已就位。 |
| S2 | FT2 schema 与 observability contract | `done` | 数据库 `job_events` 及 `eval_metrics` 可承接可观测数据。 |
| S3 | FT3 真实音频预处理 | `done` | 适配器与 pipeline step 接口定义完成。 |
| S4 | FT4 真实推理 substrate | `done` | 实现了 XTTS 的真实推理包装，支持真实 wav 导出。 |
| S5 | FT5 真实评估与 release gate | `done` | Objective 评分占位、人工主观评价（MOS/ABX）接口及 GateWaive 机制已实现。 |
| S6 | FT6 FastAPI e2e surface | `done` | 提供了完整的多步骤 API 调度终点并覆盖全旅程。 |
| S7 | FT7 live tests 与 capstone | `partial` | capstone 框架和 exporter 编写完成，但真实执行因本地测试节点缺少 GPU 依赖而被 skip，只输出了 skipped pack。 |
| S8 | FT8 closure/deferred reconciliation | `done` | 梳理了 deferred ledgers 并且写了 doc check 单元测试守卫。 |

### 3.1 对齐结论

- **done**: 7
- **partial**: 1
- **missing**: 0
- **stale**: 0
- **out-of-scope-by-design**: 0

> 这一阶段在开发和设计对齐上取得了显著的骨架落地，但受限于本地硬件/环境依赖条件，FT7 并没有产生有效的非空真实运行证据包（只产生了 skipped evidence），且 Mock 底座部分包含文件及逻辑一致性错误。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 真实 RVC/So-VITS 神经网络训练逻辑全面落地 | `遵守` | 保持为 NotImplemented 并归入 deferred ledger。 |
| O2 | vec0 维度的彻底迁移与 SQLite-vec 全库适配 | `遵守` | 依然停留在 `float[128]` 占位，并未非计划性膨胀。 |
| O3 | 生产级长任务队列（Celery/RQ）与并发锁防范 | `遵守` | 保留单机 sqlite job 进度追踪，无生产性队列侵入。 |
| O4 | OTel collector/exporter 监控体系平台级接入 | `遵守` | 仅利用 OTel 领域字段映射落库，未引入任何 SDK 平台复杂性。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`代码结构与骨架定义成立，但因迁移外键限制、Mock 音频文件损毁及环境路径泄露等多项 High/Critical 级别的 Blocker 缺陷，本轮 Review 不予收口。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. `修正 007 迁移脚本，使用 PRAGMA foreign_keys = OFF; 进行 table 重建保护。`
  2. `修正 demucs_adapter.py 中 Mock separate 部分，严禁向 .wav 路径写入纯文本，必须生成或复制真实的 wav 数据。`
  3. `修正 ffmpeg.py 中 Mock extract_segment 部分，按照 start/end 时长动态产出符合切片长度的 mock wav 文件，不可复制完整原音轨。`
  4. `修正 evidence.py，移除硬编码路径 DEFAULT_EVIDENCE_ROOT，全面改为环境变量注入。`
- **可以后续跟进的 non-blocking follow-up**：
  1. `消除 score.py 中隐藏的硬编码质量常数。`
  2. `在 api 服务层中引入自定义异常基类并注册全局异常拦截处理器。`
  3. `清除数据库迁移中残留的 embedding_items 等死表。`
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

`本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。`
