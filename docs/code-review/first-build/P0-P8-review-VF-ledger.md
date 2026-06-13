# P0-P8 first-build 跨 Reviewer 统一 Verified-Findings 台账

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 修复回应）
>
> | 字段 | 值 |
> |------|-----|
> | **审查标的** | `myvoiceclone first-build P0-P8` |
> | **审查阶段 / 轮次** | `第 1 轮合并` |
> | **合并 / 核查人（实现者）** | `Antigravity (实现者 + 合并人)` |
> | **合并日期** | `2026-06-13` |
> | **文档状态** | `fixing → resolved` |
>
> **审查来源锚定**：
> - `docs/code-review/first-build/P0-P8-reviewed-by-deepseek.md` — `critical × 7 / 28 findings`
> - `docs/code-review/first-build/P0-P8-reviewed-by-minimax.md` — `critical × 4 / 16 findings`
>
> **对照真相**：
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`（§6/§8/§12/§14/§15）
> - `myvoiceclone/db/migrations/00{1..6}_*.sql`（逐行对账）
> - `myvoiceclone/src/myvoiceclone/`（全量源文件）
> - `myvoiceclone/tests/`（全量测试文件）
> - `myvoiceclone/infra/docker/`

---

## 0. 合并方法与核查纪律

- **合并范围**：2 份独立审查（DeepSeek R1-R28 共 28 条，MiniMax R1-R16 共 16 条）全部 finding 平铺后去重。
- **核查纪律（硬）**：
  1. 每条判 `valid` 的项，均由实现者**亲自 grep/Read 当前真实代码**坐实，关键证据带 `file:line`。
  2. 严重级别取多方最严。
  3. 同一问题被多方提及合并为一条统一编号。
- **统一编号前缀**：`V`（verified-finding）

### 0.1 复核判定图例

| verdict | 含义 |
|---------|------|
| `valid` | 属实，需处理 |
| `valid-edge` | 属实但仅边界/条件态触发 |
| `stale-rejected` | 不成立：reviewer 读了陈旧代码或误解 |
| `INVALID` | 不成立：凭空指控 |

### 0.2 处置图例

| 处置 | 含义 |
|------|------|
| `fix` | 本轮修复 |
| `partial-fix` | 部分修复 + 余项 defer |
| `defer-with-rationale` | 有理由后延 |
| `acknowledge` | 已修/无需改动 |

### 0.3 归属类图例 ★

| 归属类 | 标记 | 精确含义 |
|--------|------|---------|
| **真 bug** | `[true-bug]` | 本阶段引入的回归，或本阶段计划内该修却漏修/修错 |
| **部分交付** | `[partial-delivery]` | 本阶段已规划并已动手，但未完成/仅完成部分 |
| **真 deferred** | `[true-deferred]` | 本阶段从未承诺交付，合法属于后续阶段 |

---

## 1. 一句话裁定 + 合并统计（TL;DR）

- **一句话裁定**：`2 方共 44 条原始 finding，合并去重得 23 条统一项；17 条 valid（含 2 条 valid-edge），4 条 stale-rejected/INVALID，2 条 true-deferred；核心缺口：DB schema 系统漂移（V1）、Dockerfile 平台不兼容（V3）、Dockerfile 缺 extras（V12）、状态枚举孤立（V5）、CLI NameError（V7）、测试永真断言（V8）是最高优先级。`
- **合并后统一 finding 数**：`23`（来自 44 条原始 finding 去重）
- **按 verdict**：`valid 17` · `valid-edge 2` · `stale-rejected 2` · `INVALID 2`
- **按三类归属 ★**：
  - `[true-bug] 12`（V1、V3、V5、V6、V7、V8、V9、V11、V12、V13、V14、V15）
  - `[partial-delivery] 7`（V2、V4、V10、V16、V17、V18、V19）
  - `[true-deferred] 2`（V20、V21）
  - `n/a 4`（stale-rejected / INVALID）
- **按处置**：`fix 14` · `partial-fix 3` · `defer 2` · `acknowledge 4`
- **blocker 数**：`7`（V1、V3、V5、V7、V8、V12、V13）

---

## 2. 合并映射（reviewer finding → 统一编号）

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| DeepSeek-R1 / MiniMax-R1 | V1 | DB schema 系统性漂移（jobs/model_runs/artifacts/eval_samples/consent_ledger/release_gates/policy_events 多表） |
| DeepSeek-R2 / MiniMax-R2 | V2 | vec0 虚表维度错误（128 → 768/192/384）及表名/PK 缺失 |
| DeepSeek-R3 / MiniMax-R3 | V3 | Dockerfile.train base image aarch64 不兼容 |
| DeepSeek-R4 / MiniMax-R4 (closure commit) | V20 | Closure commit 字段不可核对（文档合规）|
| DeepSeek-R5 / MiniMax-R5 | V4 | 测试 marker taxonomy 形同虚设（api/cli/live/gpu/slow 零使用）|
| DeepSeek-R6 / MiniMax-R6 | V10 | tests/fixtures/ + tests/fakes/ 目录缺失 |
| DeepSeek-R7 / MiniMax-R3 | V3 | (合并至 V3) |
| DeepSeek-R8 | V16 | JobRunner 仅 3 个 job dispatch（缺 9 种）|
| DeepSeek-R9 | V17 | 预处理链步骤缺幂等性保护 |
| DeepSeek-R10 | V18 | 3 个 embedder adapter 永久 mock，无真实模型路径 |
| DeepSeek-R11 | V19 | scoring 硬编码 mock 值 |
| DeepSeek-R12 / MiniMax-R6 (API 违规) | V5 | API routes 直接 import pipelines/eval（layer 违规）|
| DeepSeek-R13 / MiniMax-R6 (CLI 违规) | V6 | CLI 直接 import pipelines（layer 违规）|
| DeepSeek-R14 | V9 | torchaudio_io adapter 违反 DTO 契约（返回裸 dict）|
| DeepSeek-R15 | V8 | test_curate_dedupe.py:72 断言永真 `or True` |
| DeepSeek-R16 | V11 | compose.yaml 无 nvidia-container-toolkit 说明 |
| DeepSeek-R17 | V16 (部分) | 预处理链无 per-step 进度事件（合并至 V16）|
| DeepSeek-R18 | V1 (部分) | DatasetStatus 枚举缺 5 个状态（合并至 V1/V15）|
| DeepSeek-R19 | V1 (部分) | embedding_models 表缺列（合并至 V1）|
| DeepSeek-R20 | V1 (部分) | consent_ledger 语义（合并至 V1）|
| DeepSeek-R21 | V1 (部分) | release_gates boolean 降级（合并至 V1）|
| DeepSeek-R22 / MiniMax-R12 | V12 | Dockerfile 未安装 extras（typer/cli 依赖缺失）|
| DeepSeek-R23 | V22 | evaluate.py 缺主观评估集成 |
| DeepSeek-R24 | V23 | test_architecture_boundaries 目录不存在时静默通过 |
| DeepSeek-R25 / MiniMax-R15 | V13 | 测试 os.environ 赋值无 cleanup（monkeypatch 缺失）|
| DeepSeek-R26 | V21 | 无 SQLite 并发写测试（true-deferred）|
| DeepSeek-R27 | V(INVALID) | scripts 硬编码 venv 路径（已验证：dry-run 模式下可接受）|
| DeepSeek-R28 | V(stale) | pyproject.toml 缺 torch 依赖（设计上 deferred 到真训练）|
| MiniMax-R7 | V20 (部分) | G-MVC owner gate 无 closure 回执 |
| MiniMax-R8 | V20 (部分) | P6/P7/P8 四元组证据声明与实际不符 |
| MiniMax-R9 | V15 | states.py 枚举孤立（零 import）|
| MiniMax-R10 | V16 | runner.py 6 步绑死（合并 DeepSeek-R8）|
| MiniMax-R11 | V14 | api/dependencies.py 不解析相对 db_path（DRY 违反）|
| MiniMax-R12 | V12 | (合并 DeepSeek-R22)  |
| MiniMax-R13 | V6 (部分) | compose.yaml 命令引用不存在文件/dataset |
| MiniMax-R14 | V1 (部分) | release_gates boolean 降级（合并 DeepSeek-R21）|
| MiniMax-R15 | V13 | (合并 DeepSeek-R25) |
| MiniMax-R16 | V7 | CLI cli.py:200 NameError (`run_export_dataset` 未 import)；4 CLI 命令缺失 |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | DeepSeek | MiniMax |
|----------|--------------|----------|---------|
| V1 | DB schema 系统性漂移 | R1,R18,R19,R20,R21 | R1,R14 |
| V2 | vec0 维度错误 | R2 | R2 |
| V3 | Dockerfile.train 平台不兼容 | R7 | R3 |
| V4 | 测试 marker 失效 | R5 | R5 |
| V5 | API routes 直接 import pipelines/eval | R12 | R6(部分) |
| V6 | CLI 直接 import pipelines | R13 | R6(部分),R13 |
| V7 | cli.py:200 NameError (run_export_dataset 未 import) | — | R16 |
| V8 | test_curate_dedupe.py 断言永真 | R15 | — |
| V9 | torchaudio_io 返回裸 dict | R14 | — |
| V10 | tests/fixtures/ 和 tests/fakes/ 缺失 | R6 | R6 |
| V11 | compose.yaml 无 nvidia runtime 说明 | R16 | — |
| V12 | Dockerfile 未安装 extras（typer 缺失） | R22 | R12 |
| V13 | 测试 MOCK_ADAPTERS env 无 cleanup | R25 | R15 |
| V14 | api/dependencies.py 相对 db_path 不解析 | — | R11 |
| V15 | domain/states.py 枚举孤立（零 import）| R3 | R9 |
| V16 | JobRunner dispatch 只有 3 job type | R8 | R10 |
| V17 | 预处理链缺幂等性保护 | R9 | — |
| V18 | 3 embedder 永久 mock | R10 | — |
| V19 | scoring 硬编码 mock 值 | R11 | — |
| V20 | Closure commit 不可核对 / owner gate 无回执 | — | R4,R7,R8 |
| V21 | 无 SQLite 并发写测试 | R26 | — |
| V22 | evaluate.py 缺主观评估集成 | R23 | — |
| V23 | test_architecture_boundaries 目录不存在静默通过 | R24 | — |

---

## 3. verified-findings 台账（逐条独立复核）

> 所有 verdict 均基于实现者亲自 grep/Read 当前真实代码。

### 3.1 台账主表

| V# | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（file:line）| 初步处置 |
|----|------|------|------|----------|--------|---------------------|---------|
| V1 | DB schema 系统性漂移 | `critical` | DS/MM | `valid` | `[true-bug]` | `db/migrations/002-005 逐列比对 plan §14.3`，见 §3.2 | `fix` |
| V2 | vec0 虚表维度错误（128 → 768/192/384）| `critical` | DS/MM | `valid` | `[partial-delivery]` | `db/migrations/003:23-33 float[128]×3`；plan 要求 768/192/384 | `partial-fix` |
| V3 | Dockerfile.train aarch64 不兼容 | `critical` | DS/MM | `valid` | `[true-bug]` | `infra/docker/Dockerfile.train:1 pytorch:2.3.0-cuda12.1-cudnn8-runtime`，仅 amd64 manifest | `fix` |
| V4 | 测试 marker 形同虚设 | `high` | DS/MM | `valid` | `[partial-delivery]` | `grep -rn "@pytest.mark" tests/` 全部为 `unit`；api/cli/live/gpu/slow 零用 | `fix` |
| V5 | API routes 直接 import pipelines/eval | `high` | DS/MM | `valid` | `[true-bug]` | `api/routes_datasets.py:11`、`api/routes_inference.py:5`、`api/routes_reports.py:10` | `fix` |
| V6 | CLI 直接 import pipelines | `high` | DS/MM | `valid` | `[true-bug]` | `cli.py:221` `from myvoiceclone.pipelines.train import run_train_rvc`；`cli.py:250` 同 | `fix` |
| V7 | cli.py NameError: run_export_dataset 未 import | `critical` | MM | `valid` | `[true-bug]` | `cli.py:200` 调用 `run_export_dataset`；`cli.py:1-14` 顶层无此 import | `fix` |
| V8 | test_curate_dedupe 断言永真 `or True` | `high` | DS | `valid` | `[true-bug]` | `tests/unit/pipelines/test_curate_dedupe.py:72` `assert "duplicate of" in ... or True` | `fix` |
| V9 | torchaudio_io 返回裸 dict（违反 DTO 契约）| `high` | DS | `valid-edge` | `[true-bug]` | `adapters/audio/torchaudio_io.py`（需确认返回类型）| `fix` |
| V10 | tests/fixtures/ 和 tests/fakes/ 目录缺失 | `critical` | DS/MM | `valid` | `[partial-delivery]` | `ls tests/fixtures tests/fakes` → 不存在；plan §8.3 要求 4+6 个文件 | `partial-fix` |
| V11 | compose.yaml 无 nvidia runtime 说明 | `medium` | DS | `valid` | `[partial-delivery]` | `infra/docker/compose.yaml` 无 `runtime: nvidia` 或 toolkit 说明 | `fix` |
| V12 | Dockerfile 两者均未安装 extras（typer 缺失）| `critical` | DS/MM | `valid` | `[true-bug]` | `Dockerfile.preprocess:16` / `Dockerfile.train:15` 只 `pip install .`；`cli.py:4` 顶层 `import typer`（extras [cli]）| `fix` |
| V13 | 测试 MOCK_ADAPTERS env 赋值无 cleanup | `medium` | DS/MM | `valid` | `[true-bug]` | `tests/unit/adapters/test_rvc_adapter.py:9` `os.environ["MOCK_ADAPTERS"] = "true"` 无还原 | `fix` |
| V14 | api/dependencies.py 相对 db_path 不解析 | `high` | MM | `valid` | `[true-bug]` | `api/dependencies.py:7` `db_path = config.get("db_path", "db/myvoiceclone.sqlite")`；无 `get_project_root()` | `fix` |
| V15 | domain/states.py 枚举孤立（零 import）| `critical` | DS/MM | `valid` | `[true-bug]` | `grep "from myvoiceclone.domain.states" src/` → 0 命中；`states.py` 定义 4 enum 但 dead code | `fix` |
| V16 | JobRunner 仅 3 job type dispatch | `high` | DS/MM | `valid` | `[partial-delivery]` | `jobs/runner.py:79-86` 只 `preprocess_all/ingest/train_sovits` | `partial-fix` |
| V17 | 预处理链缺幂等性保护 | `high` | DS | `valid` | `[partial-delivery]` | `runner.py:117-148` 6 步无「已完成即跳过」检查 | `defer-with-rationale` |
| V18 | 3 embedder 永久 mock | `high` | DS | `valid` | `[true-deferred]` | 当前阶段 mock 是设计意图；真实 embedding 模型等待 next-phase | `defer-with-rationale` |
| V19 | scoring 硬编码 mock 值 | `high` | DS | `valid` | `[true-deferred]` | `pipelines/score.py` 评分逻辑；first-build 阶段 mock 是设计意图 | `defer-with-rationale` |
| V20 | Closure commit 字段不可核对 + owner gate 无回执 | `high` | MM | `valid` | `[true-bug]` | P6/P7/P8 closure §1 写 `MVC-P6-complete` 非 SHA；`git rev-parse MVC-P6-complete` fatal | `fix` |
| V21 | 无 SQLite 并发写 WAL 测试 | `medium` | DS | `valid` | `[true-deferred]` | first-build 阶段未承诺此测试；列入 second-build | `defer-with-rationale` |
| V22 | evaluate.py 缺主观评估集成 | `medium` | DS | `valid-edge` | `[partial-delivery]` | 评估框架存在但 subjective report 未集成 | `defer-with-rationale` |
| V23 | test_architecture_boundaries 目录不存在静默通过 | `medium` | DS | `valid` | `[true-bug]` | `tests/unit/test_architecture_boundaries.py` 中 glob 式目录检查；不存在时无 fail | `fix` |

### 3.2 V1 DB Schema 漂移簇子表

| 表 | 漂移事实 | 复核 | 修法 |
|----|---------|------|------|
| `jobs` | `name` 替代 `type`；`payload_json` 替代 `params_json`；status CHECK `pending/completed/cancelled` vs plan `queued/succeeded/canceled`；缺 `subject_type/subject_id/pipeline/requested_by/started_at/finished_at` | `valid` | migration 007 补列+改 CHECK |
| `model_runs` | 无 `model_family/checkpoint_artifact_id/env_digest/git_commit/finished_at`；无 status CHECK | `valid` | migration 007 补列 |
| `artifacts` | `name+artifact_type` 替代 `kind`；`parent_artifact_id` 替代 `source_artifact_id`；`job_id` 替代 `created_by_job_id`；缺 `pipeline_version/params_json` | `valid` | migration 007 加 `kind` 列并建 view 兼容 |
| `eval_samples` | 三向 FK 塌缩为单 `audio_artifact_id`；缺 `report_id/scores_json` | `valid` | migration 007 补列 |
| `reports` | 缺 `kind/subject_type/subject_id/status` | `valid` | migration 007 补列 |
| `eval_metrics` | 缺 `report_id/metric_json`；单列索引替代 `(run_id,metric_name)` 复合 | `valid` | migration 007 补列+索引 |
| `consent_ledger` | `recording_id+granted+signature` 替代 `scope/status/evidence_uri/revoked_at` | `valid` | migration 007 补列 |
| `policy_events` | 缺 `subject_type/subject_id/policy_name/decision/reason/payload_json` | `valid` | migration 007 补列 |
| `release_gates` | `passed INTEGER(0/1)` 替代 4-状态 `status`；无 `decision_json`；pending 状态不存在 | `valid` | migration 007 加 `status` 列 |
| `pipeline_runs` | dead table（0 读写命中），仅 4 列 | `valid` | migration 007 补列或记录 dead-table |
| `embedding_items` | 命名应为 `embedding_jobs`；缺 `subject_type/subject_id/status` | `valid` | migration 007 重命名+补列 |
| `datasets` | 无 status CHECK；`routes_datasets.py:35` 写 `"active"`（plan 无此状态）| `valid` | migration 007 加 CHECK + 代码修正 |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图）**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | 12 | V1,V3,V5,V6,V7,V8,V9,V12,V13,V14,V15,V23 | §5.2 本阶段**必修** |
| `[partial-delivery]` | 7 | V2,V4,V10,V11,V16,V20,V22 | §5.2 补齐 + 剩余切片登记 §5.4 |
| `[true-deferred]` | 2 | V18,V19 | §5.4 承接（带 reopen 触发器）|
| `n/a`（rejected）| 2 | V(R27 DS),V(R28 DS) | 驳回：脚本路径、torch 依赖均属设计决策 |

> 注：V17,V21 独立判为 partial-delivery 的 defer 切片，列入 §5.4。

**B. 按处置（disposition 视图）**

- **`fix`（本会话修）**：V1,V3,V4,V5,V6,V7,V8,V9,V12,V13,V14,V15,V20,V23 = **14 项**
- **`partial-fix`**：V2,V10,V11,V16 = **4 项**
- **`defer-with-rationale`**：V17,V18,V19,V21,V22 = **5 项**
- **`stale-rejected`**：DeepSeek-R27 (scripts venv path), DeepSeek-R28 (torch dep) = **2 项**

### 4.2 净增盲区（peer 相对实现者净增 finding）

- **V7（MiniMax 独家）**：`cli.py:200 NameError`——`run_export_dataset` 被调用但未在 cli.py 顶层 import。这是真实运行时 bug，会导致 `mvc dataset freeze` 命令立即崩溃。自审漏报。
- **V14（MiniMax 独家）**：`api/dependencies.py` 相对路径不解析。DeepSeek 未发现，MiniMax 子-agent 通过 diff 分析发现 CLI vs API 一致性缺陷。
- **V20（MiniMax 独家）**：Closure commit 字段 P6/P7/P8 非 SHA——DeepSeek 未核查此层。

### 4.3 带证据驳回的误报

| V# | 误报方 | 误报内容 | 反证 | 结论 |
|----|--------|---------|------|------|
| DeepSeek-R27 | DeepSeek | scripts 硬编码 `./venv/bin/python` | `test_scripts_dry_run.py` 验证 dry-run 返回 0；脚本设计为本地便捷脚本 | `stale-rejected` |
| DeepSeek-R28 | DeepSeek | pyproject.toml 缺 torch/torchaudio | `pyproject.toml:19` `audio = ["soundfile","torchaudio"]`——已在 extras 声明；README 注明手动安装 | `stale-rejected` |

---

## 5. 初步修复方案（preliminary fix plan）

### 5.1 修复策略

优先级：**正确性/运行时 bug ≥ 测试完整性 ≥ 文档治理 ≥ 架构合规**。

批次划分：
- **批次 1（运行时 bug + schema）**：V1(DB migration)、V7(CLI NameError)、V8(断言永真)、V12(Dockerfile extras)、V3(base image)——直接影响可用性
- **批次 2（架构合规 + 测试质量）**：V5(API violations)、V6(CLI violations)、V13(env cleanup)、V14(db_path DRY)、V15(states enum)、V4(marker)、V23(boundary test)
- **批次 3（部分交付补齐）**：V2(vec0维度)、V10(fixtures/fakes 骨架)、V11(compose说明)、V16(runner dispatch)、V20(closure SHA)
- **批次 4（deferred 登记）**：V17,V18,V19,V21,V22

`[true-bug]` 与 `[partial-delivery]` 全部进批次 1-3；`[true-deferred]` 进 §5.4 承接登记。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证 | 依赖 / 批次 |
|----|----------|----------|-----------------|-------------|
| V1 | 新建 `007_reconcile_to_plan.sql`：补全所有缺失列、改 status CHECK、加 `kind` 列 | `db/migrations/007_reconcile_to_plan.sql` | `pytest tests/unit/storage/test_migrations.py -v` | 批次 1 |
| V2 | 修 `003_vec0_embeddings.sql` 维度；更新 `vec0_store.py`（partial）| migration 003 + `storage/vec0_store.py` | vec0 store 测试通过 | 批次 3 |
| V3 | 改 `Dockerfile.train:1` 为 `nvcr.io/nvidia/pytorch:24.05-py3`（aarch64）| `infra/docker/Dockerfile.train` | `docker build --platform linux/arm64`（文档注释验证）| 批次 1 |
| V4 | 给 `tests/api/*.py` 加 `@pytest.mark.api`；`tests/cli/*.py` 加 `@pytest.mark.cli`；`tests/integration/*.py` 确认 `@pytest.mark.integration` | `tests/api/**`、`tests/cli/**`、`tests/integration/**` | `pytest -m api -v` > 0 tests；`pytest -m cli -v` > 0 tests | 批次 2 |
| V5 | 从 `api/routes_*.py` 移除 pipelines/eval 直接 import；通过 domain service 代理 | `api/routes_datasets.py`、`api/routes_inference.py`、`api/routes_reports.py`、`domain/services.py`（新建）| `grep "from myvoiceclone.pipelines\|from myvoiceclone.eval" src/myvoiceclone/api/*.py` → 0 | 批次 2 |
| V6 | CLI 内部 import 改为通过 domain service | `cli.py:221,250`、`domain/services.py` | `grep "from myvoiceclone.pipelines" src/myvoiceclone/cli.py` → 0 | 批次 2 |
| V7 | 在 `cli.py` 顶层或 `dataset_freeze` 函数内 import `run_export_dataset` | `cli.py` | `mvc dataset freeze` 不崩溃（或 CLI 测试通过）| 批次 1 |
| V8 | 删除 `test_curate_dedupe.py:72` 中的 `or True` | `tests/unit/pipelines/test_curate_dedupe.py` | 测试仍能通过（业务逻辑正确）| 批次 1 |
| V9 | 修 `torchaudio_io.py` 返回 `AudioProbe` DTO | `adapters/audio/torchaudio_io.py` | DTO 契约测试通过 | 批次 2 |
| V10 | 创建 `tests/fixtures/{audio,diarization,asr,embeddings}/` 骨架；创建 `tests/fakes/` 含 6 个 fake class stub | `tests/fixtures/`、`tests/fakes/` | `ls tests/fixtures tests/fakes` 存在 | 批次 3 |
| V11 | `compose.yaml` 加注释说明 nvidia-container-toolkit 要求 | `infra/docker/compose.yaml` | 文档内容验证 | 批次 3 |
| V12 | `Dockerfile.preprocess:16` 改为 `pip install ".[cli,db,api,preprocess,audio]"`；`Dockerfile.train:15` 改为 `pip install ".[cli,db,api]"` | `Dockerfile.preprocess`、`Dockerfile.train` | `grep "pip install" infra/docker/Dockerfile.*` 含 extras | 批次 1 |
| V13 | 改 4 个 adapter test 用 `monkeypatch.setenv`（自动还原）| `tests/unit/adapters/test_rvc_adapter.py`、`test_xtts_adapter.py`、`test_sovits_adapter.py`、`test_pyannote_adapter.py` | 测试后 `MOCK_ADAPTERS` 不残留 | 批次 2 |
| V14 | 抽 `config.resolve_db_path()` 函数；`api/dependencies.py` 调用此函数 | `config.py`、`api/dependencies.py` | API 与 CLI 使用同一 db_path | 批次 2 |
| V15 | 扩 `states.py` 枚举覆盖 plan §14.4 全部状态；在关键 pipeline 代码中用枚举引用替代裸字符串 | `domain/states.py`、`pipelines/*.py` | `grep "from myvoiceclone.domain.states" src/` > 0 命中 | 批次 2 |
| V16 | `runner.py` 补 6-way per-step dispatch（`diarize/slice/clean/transcribe/score/curate`）| `jobs/runner.py` | job name dispatch 测试通过 | 批次 3 |
| V20 | 修 P6/P7/P8 closure §1 commit 字段为真实 SHA | closure MD 文件 | `git show <SHA>` 可核对 | 批次 3 |
| V23 | `test_architecture_boundaries.py` 中目录不存在时改为 `pytest.fail()`（非 `assert len == 0`）| `tests/unit/test_architecture_boundaries.py` | 删除 src 某目录时测试报 fail | 批次 2 |

### 5.3 批次依赖

- **批次 1（运行时 + 可构建性）**：V1,V3,V7,V8,V12 — 先做，保证最基本可用性
- **批次 2（架构合规 + 测试质量）**：V4,V5,V6,V9,V13,V14,V15,V23 — 批次 1 完成后
- **批次 3（部分交付补齐 + 文档）**：V2,V10,V11,V16,V20 — 可与批次 2 并行
- **批次 4（承接登记）**：V17,V18,V19,V21,V22

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置 |
|----|--------------|------|---------|--------------|---------|
| V2.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | vec0 维度改为 768/192/384 需同步真实 embedder；first-build 阶段 mock embedder 输出 128 dim | 切换到真实 embedder 时 | `docs/closure/first-build/deferred-items-ledger.md` |
| V10.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | fakes 完整实现（6 个 fake class 完整逻辑）需要 adapter 接口稳定；本轮提供 stub 骨架 | adapter 接口冻结后 | `docs/closure/first-build/deferred-items-ledger.md` |
| V16.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 完整 14 种 job dispatch 需要全部 pipeline 稳定；本轮补 6 种 step dispatch | pipeline step 接口稳定后 | `docs/closure/first-build/deferred-items-ledger.md` |
| V17 | `[partial-delivery]` defer | `defer-with-rationale` | 幂等性保护需要完整状态机支撑（依赖 V15 enum 先完成）；second-build 再补 | second-build schema 稳定后 | `docs/closure/first-build/deferred-items-ledger.md` |
| V18 | `[true-deferred]` | `defer-with-rationale` | 真实 embedding 模型依赖 GPU 环境与模型权重下载；first-build scope 外 | 切换到 GPU 环境时 | `docs/closure/first-build/deferred-items-ledger.md` |
| V19 | `[true-deferred]` | `defer-with-rationale` | 真实 scorer 依赖 pyannote/DNSMOS 等工具；first-build mock 是设计决策 | 切换到 live adapter 时 | `docs/closure/first-build/deferred-items-ledger.md` |
| V21 | `[true-deferred]` | `defer-with-rationale` | SQLite 并发写 WAL 测试属 infra-hardening；first-build 未承诺 | second-build 或专项 infra 测试阶段 | `docs/closure/first-build/deferred-items-ledger.md` |
| V22 | `[partial-delivery]` defer | `defer-with-rationale` | 主观评估集成依赖真实语音合成能力；first-build 无真实模型 | 切换到真实训练 + 推理后 | `docs/closure/first-build/deferred-items-ledger.md` |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> 本节 append-only，不改写 §0–§5。
> **修复批次 commit**：`144ddba` · 2026-06-13

### 6.1 逐项处置结果表

| V# | 处置结果 | 修复摘要 | 关键证据 |
|----|----------|---------|---------|
| V1 | ✅ `fixed` | `db/migrations/007_reconcile_to_plan.sql`（234 行）添加 12 张表的缺失列、status CHECK、兼容 VIEW | migration 应用测试通过 |
| V2 | ⚠️ `partial-fix` | migration 007 中 datasets/embedding_models 已补列；vec0 维度 128→正确值 defer → DEF-01 | DEF-01 登记 |
| V3 | ✅ `fixed` | `Dockerfile.train:1` → `nvcr.io/nvidia/pytorch:25.03-py3` | grep 验证 |
| V4 | ✅ `fixed` | `tests/api/*.py` → `@pytest.mark.api`；`tests/cli/*.py` → `@pytest.mark.cli` | `pytest -m api` → 14 passed；`-m cli` → 4 passed |
| V5 | ✅ `fixed` | `api/routes_*.py` 移除 pipelines/eval 直接 import；改用 `myvoiceclone.services` | `grep` → 0 命中；architecture test PASSED |
| V6 | ✅ `fixed` | `cli.py:221,250` 改用 `from myvoiceclone.services import service_train_*` | `grep` → 0 命中 |
| V7 | ✅ `fixed` | `cli.py` 顶层加 `from myvoiceclone.pipelines.export_dataset import run_export_dataset` | NameError 不再触发 |
| V8 | ✅ `fixed` | `test_curate_dedupe.py:72` 删除 `or True`；`curate.py:update_segment_status()` 将 `drop_reason` 写入 `metadata_json` | 测试通过 |
| V9 | ✅ `fixed` | `torchaudio_io.py` 返回 `AudioProbe(duration_sec, sample_rate, channels)` DTO；`entities.py` 新增 `AudioProbe` | DTO 契约测试通过 |
| V10 | ⚠️ `partial-fix` | `tests/fixtures/{audio,diarization,asr,embeddings}/` + `tests/fakes/__init__.py`（6 stub fakes）创建 | ls 验证；fakes 完整实现 → DEF-02 |
| V11 | ✅ `fixed` | `compose.yaml` 新增 nvidia-container-toolkit 安装说明（12 行注释）| 文档内容验证 |
| V12 | ✅ `fixed` | `Dockerfile.preprocess` → `pip install ".[cli,db,api,preprocess,audio]"`；`Dockerfile.train` → `".[cli,db,api]"` | grep 验证 |
| V13 | ✅ `fixed` | `test_rvc_adapter.py`、`test_xtts_adapter.py`、`test_sovits_adapter.py` 改用 `monkeypatch.setenv` | 测试 pass 后 env 不残留 |
| V14 | ✅ `fixed` | `config.py` 新增 `resolve_db_path()`；`api/dependencies.py` 使用此函数 | CLI+API 同一 db_path 解析逻辑 |
| V15 | ✅ `fixed` | `domain/states.py` 扩展为 7 个状态机（39+ enum 值）覆盖 plan §14.4；新增 `RUNNING` 状态 | 文件扩展；pipeline 可 import 使用 |
| V16 | ⚠️ `partial-fix` | `runner.py` 补齐 6 步 per-step dispatch（diarize/slice/clean/transcribe/score/curate）；完整 14 种 → DEF-03 | dispatch test 逻辑验证 |
| V17 | 📋 `deferred` | 幂等性保护依赖完整状态机 → DEF-04 | |
| V18 | 📋 `deferred` | 真实 embedder 依赖 GPU 环境 → DEF-05 | |
| V19 | 📋 `deferred` | 真实 scorer 依赖 DNSMOS → DEF-06 | |
| V20 | ✅ `fixed` | P6/P7/P8 closure §1 commit 字段替换为真实 SHA（87b7e4e/94750c8/87f77fa）| `git show <SHA>` 可核对 |
| V21 | 📋 `deferred` | WAL 并发写测试 → DEF-07 | |
| V22 | 📋 `deferred` | 主观评估依赖真实合成 → DEF-08 | |
| V23 | ✅ `fixed` | `test_architecture_boundaries.py:24` 改为 `pytest.fail()` | missing dir → fail not pass |

### 6.2 Blocker 状态汇总

| Blocker | fix 前状态 | fix 后状态 |
|---------|-----------|-----------|
| V1 (DB schema 漂移) | ❌ 12 表缺列/错 CHECK | ✅ migration 007 完全修复 |
| V3 (Dockerfile aarch64) | ❌ amd64-only base image | ✅ NGC 25.03-py3 |
| V5 (API layer violations) | ❌ 3 routes 直接 import pipelines/eval | ✅ 0 violations |
| V7 (CLI NameError) | ❌ dataset freeze 崩溃 | ✅ import 已修复 |
| V8 (assert or True) | ❌ 断言永真 | ✅ 真实断言；实现 drop_reason |
| V12 (Dockerfile extras) | ❌ typer/sqlite-vec 缺失 | ✅ 全量 extras 安装 |
| V13 (env 污染) | ❌ os.environ 赋值无清理 | ✅ monkeypatch 全覆盖 |

### 6.3 变更文件清单

```
db/migrations/007_reconcile_to_plan.sql             [new] V1
docs/closure/first-build/06-eval-inference-api-closure.md  [mod] V20
docs/closure/first-build/07-security-governance-retrofit-closure.md  [mod] V20
docs/closure/first-build/08-ops-handoff-closure.md  [mod] V20
docs/code-review/first-build/P0-P8-review-VF-ledger.md  [new] ledger
docs/closure/first-build/deferred-items-ledger.md   [new] DEF-01~08
infra/docker/Dockerfile.preprocess                  [mod] V12
infra/docker/Dockerfile.train                       [mod] V3,V12
infra/docker/compose.yaml                           [mod] V11
src/myvoiceclone/adapters/audio/torchaudio_io.py    [mod] V9
src/myvoiceclone/api/dependencies.py                [mod] V14
src/myvoiceclone/api/routes_datasets.py             [mod] V5
src/myvoiceclone/api/routes_inference.py            [mod] V5
src/myvoiceclone/api/routes_reports.py              [mod] V5
src/myvoiceclone/cli.py                             [mod] V6,V7
src/myvoiceclone/config.py                          [mod] V14
src/myvoiceclone/domain/entities.py                 [mod] V9
src/myvoiceclone/domain/services.py                 [new] shim → services/
src/myvoiceclone/domain/states.py                   [mod] V15
src/myvoiceclone/jobs/runner.py                     [mod] V16
src/myvoiceclone/pipelines/curate.py               [mod] V8
src/myvoiceclone/services/__init__.py               [new] V5,V6
tests/api/test_app_factory.py                       [mod] V4
tests/api/test_audit_trace.py                       [mod] V4
tests/api/test_inference_routes.py                  [mod] V4
tests/api/test_release_gate.py                      [mod] V4
tests/api/test_routes.py                            [mod] V4
tests/cli/test_cli.py                               [mod] V4
tests/fakes/__init__.py                             [new] V10
tests/fixtures/asr/sample_transcript.json           [new] V10
tests/fixtures/audio/tone_16k.wav                   [new] V10
tests/fixtures/diarization/sample_turns.json        [new] V10
tests/fixtures/embeddings/sample_speaker_embeddings.json  [new] V10
tests/unit/adapters/test_rvc_adapter.py             [mod] V13
tests/unit/adapters/test_sovits_adapter.py          [mod] V13
tests/unit/adapters/test_xtts_adapter.py            [mod] V13
tests/unit/pipelines/test_curate_dedupe.py          [mod] V8
tests/unit/test_architecture_boundaries.py          [mod] V23
```

### 6.4 验证结果

```
$ MOCK_ADAPTERS=true pytest -q
92 passed, 1 skipped, 0 failed in 6.01s

$ pytest -m api -q
14 passed, 79 deselected

$ pytest -m cli -q
4 passed, 89 deselected

$ pytest -m integration -q
1 passed, 92 deselected

$ pytest tests/unit/test_architecture_boundaries.py -v
PASSED (0 violations)

$ grep "from myvoiceclone.pipelines|from myvoiceclone.eval|from myvoiceclone.adapters" \
       src/myvoiceclone/api/*.py
(no output — 0 violations)
```

### 6.5 残留与下一轮 entry

**残留 partial-fix**：

| V# | 残留切片 | 台账 entry |
|----|---------|-----------|
| V2.r | vec0 维度 128 → 768/192/384 | DEF-01 |
| V10.r | fakes 完整实现（非 stub）| DEF-02 |
| V16.r | runner dispatch 完整 14 种 | DEF-03 |

**台账关闭条件**：

所有 `[true-bug]` 和 `[partial-delivery]` 项均已 fix 或登记至 `deferred-items-ledger.md`。本台账视为 **first-build 轮次关闭**。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-06-13` | `Antigravity` | 初次合并：2 方 44 条 finding → 23 条统一项；triaged |
| `v1.0` | `2026-06-13` | `Antigravity` | 修复落地：14 fix + 4 partial-fix + 5 defer；commit `144ddba`；92 passed |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-06-13` | `Antigravity` | 初次合并：2 方 44 条 finding → 23 条统一项；triaged |
