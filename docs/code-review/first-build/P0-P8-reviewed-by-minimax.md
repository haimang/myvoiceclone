# P0-P8 first-build 静态代码审查（by MiniMax-M3）

> 审查对象: `myvoiceclone first-build P0-P8`
> 审查类型: `code-review`（混合：代码 + 数据库 + 文档 + 测试）
> 审查时间: `2026-06-13`
> 审查人: `MiniMax-M3`（独立审查员，未参考其他 AI 同事的 review 文档）
> 审查范围:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`（§6 55 个工作项 + §14 DB schema + §15 接口 + §8 测试）
> - `myvoiceclone/docs/closure/first-build/00-08-*.md`（9 份 closure）
> - `myvoiceclone/docs/plan/first-build/0X-*.md`（9 份 action plan）
> - `myvoiceclone/src/myvoiceclone/**/*.py`（约 40 源文件）
> - `myvoiceclone/db/migrations/00{1..6}_*.sql`
> - `myvoiceclone/infra/docker/*.{Dockerfile.preprocess,Dockerfile.train,compose.yaml}`
> - `myvoiceclone/tests/**`（51 个 test 文件，93 个 test 函数）
> - `myvoiceclone/scripts/*.sh`、`pyproject.toml`、`pytest.ini`、`README.md`、`docs/ops/*`
> 对照真相:
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`（frozen baseline）
> - `/mnt/usb/workspace/device_stacks.md`（host 能力基线）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> first-build 的 P0-P8 已经构建了一个可跑 mock 端到端流程的工程骨架（92/93 测试通过、capstone 测试真端到端跑通 12 种 artifact 与 12 张表），但实现与 final-execution-plan（frozen）之间存在**系统性漂移**：DB schema 22 张对象中 8 张存在字段/命名/语义漂移且 4 个状态机在 schema 层完全不强制、vec0 维度被压平至 1/3、P7 状态机降级为布尔、6 个 in-scope 项目物理缺失、9 份 closure 中 3 份 commit 字段是 commit-subject 字符串而非 SHA（违反其自定的"四元组"诚实收口承诺）、Dockerfile.train 在本机 aarch64+GB10+CUDA13.0 上双重不可构建、test marker taxonomy 形同虚设。

- **整体判断**：`主体骨架成立，capstone 真端到端跑通 mock 流程；但当前实现不应被标记为 completed —— 存在多处需要先解决的 blocker 才能进下一阶段。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **`db/migrations/00{1..6}.sql` 与 plan §14.3 是两份不同的合同** —— 不是"漏字段"级别的小漂，而是 schema 在 8 张表上重新设计（`embedding_jobs → embedding_items`、`release_gates 4 状态 → passed 布尔`、`reports 缺 subject_type/subject_id/status`、`eval_samples 3 向 FK → 单 FK`、`consent_ledger 无 scope/revoked_at`）。这是下游承接的根障碍。
  2. **`infra/docker/Dockerfile.train:1` 在本机不可构建** —— `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime` 在 Docker Hub 上只有 `linux/amd64` manifest（host 是 aarch64），且 PyTorch 2.3 不含 Blackwell sm_120 kernel。即 `docker compose build train` 在本机必然失败。P8 closure §3 自我宣称 "Containerized Environment" ✅ PASS 是 soft evidence。
  3. **3 份 closure（P6/P7/P8）§1 的 commit 字段是 commit message subject 字符串 `MVC-P6-complete` 而非 SHA1** —— `git rev-parse MVC-P6-complete` → `fatal: 有歧义的参数`。这违反其自定的"✅ 证据为四元组（commit + query/test + run-time）"。同时 P4/P5 引用了 pre-amend 的 commit（`8857e78/e7cf338`），closure 文件本身只在 amend 后的 `e8217c6/51aa0f1` 中存在，形成"自引用漏洞"。P6 closure 还自报"all 77 tests passing"——实跑 92 passed 1 skipped。这是最严重的合规表演。

---

## 1. 审查方法与已核实事实

> 本节只写事实，不写结论。

- **对照文档**：
  - `myvoiceclone/docs/eval/first-build/final-execution-plan.md`（frozen，含 §6 工作台账、§7 8 个 owner gate、§8 测试计划、§12.2 文件定位矩阵、§13 冻结 Q1-Q8、§14 DB schema、§15 接口）
  - `myvoiceclone/docs/closure/first-build/00-08-*.md`（9 份 phase closure）
  - `myvoiceclone/docs/plan/first-build/0X-*.md`（9 份 action plan）
  - `/mnt/usb/workspace/device_stacks.md`（host 能力基线）

- **核查实现**：
  - `myvoiceclone/src/myvoiceclone/` 全部源文件（domain/storage/pipelines/adapters/jobs/api/eval/cli/config + 7 个 api/routes_*.py）
  - `myvoiceclone/db/migrations/00{1..6}_*.sql` 全部 6 份迁移
  - `myvoiceclone/infra/docker/{Dockerfile.preprocess,Dockerfile.train,compose.yaml}`
  - `myvoiceclone/tests/**`（51 个 test_*.py）
  - `myvoiceclone/scripts/*.sh`、`pyproject.toml`、`pytest.ini`、`configs/*`、`README.md`、`docs/ops/*`

- **执行过的验证**：
  - `cd /mnt/usb/workspace/myvoiceclone && git log --oneline` — 列出全部 14 个 commit（包含 P0-P8 阶段 hash）
  - `cd /mnt/usb/workspace/myvoiceclone && git reflog` — 确认 P4 `8857e78 → e8217c6` 与 P5 `e7cf338 → 51aa0f1` 各有一次 amend
  - `cd /mnt/usb/workspace/myvoiceclone && git rev-parse MVC-P6-complete` — 报 `fatal: 有歧义的参数 'MVC-P6-complete'`，证实 P6/P7/P8 closure 用的 commit 字段不是 SHA
  - `cd /mnt/usb/workspace/myvoiceclone && ./venv/bin/pytest` — 92 passed, 1 skipped in 2.01s（4 warnings：3 个 `datetime.utcnow` 弃用 + 1 个 StarletteDeprecation）
  - `cd /mnt/usb/workspace/myvoiceclone && ./venv/bin/pytest --collect-only -q` — 收集到 93 个 test
  - `cd /mnt/usb/workspace/myvoiceclone && ./venv/bin/pytest tests/unit/test_architecture_boundaries.py -v` — `test_layer_boundaries PASSED`
  - `ls src/myvoiceclone/domain/` — 只有 `entities.py` / `policies.py` / `states.py` / `__pycache__`，**`services.py` 缺失**
  - `ls configs/pipelines/` — 只有 `preprocess.default.yaml`，**`train.rvc.yaml` / `train.sovits.yaml` / `eval.default.yaml` 缺失**
  - `ls models/` — 只有 `registry/`，**`pretrained/` 与 `checkpoints/` 缺失**
  - `ls tests/fixtures/ tests/fakes/ infra/systemd/` — 三个目录**完全不存在**
  - 静态 AST 扫全部 40+ 源文件的 import 树，识别 5 处"spirit violation"（详见 R7）

- **复用 / 对照的既有审查**：`none` —— 本审查不参考其他 AI 同事的 review 文档，仅基于仓库本身与 plan。

### 1.1 已确认的正面事实

- **P0-P5 6 份 closure commit 字段都是真实 SHA**：P0 `9afc438`、P1 `cd17bcf`、P2 `d8066f1`、P3 `b2ab537` 在 master HEAD 上能 `git show` 出来；P4 `8857e78` 与 P5 `e7cf338` 也是有效 commit object（只是被 amend 取代）。这 6 份 closure 的 commit 槽位本身成立。
- **92/93 测试真通过**（pytest 2.01s 跑通，1 个 skip 是 `test_ffmpeg_adapter.py::test_ffmpeg_live_probe` 在无 ffmpeg 时按设计 skip）。验证最终用户体验层面"骨架完成"是站得住的。
- **capstone 集成测试是真端到端**：跑通完整 6 个 migration、6 步 preprocess pipeline、12+ 表写入、12 种 artifact 类型落盘、P7 policy-on variant（monkey-patch 启用）。这与 §J.3 sub-agent J 的逐项核查一致。
- **分层契约整体成立**（无字面违规）：55 个 src 文件中 0 个违反 layers.md 字面禁止依赖（`domain` 不引用 `storage`/`adapters`/`api`；`adapters` 不引用 `storage`；`api`/`cli` 不直接 import adapter）。sub-agent F 跑 `test_architecture_boundaries.py` 实测 1 passed。
- **adapter 隔离 100% 干净**（sub-agent G/F 一致确认）：`grep "import sqlite3" src/myvoiceclone/adapters/` 0 命中，`grep "from myvoiceclone.storage" src/myvoiceclone/adapters/` 0 命中。11 个 adapter + 3 个 embedder 都返回结构化 DTO（仅 `torchaudio_io.py:14` 例外，返回裸 dict）。
- **6 份 SQL migration 全部能跑**（conftest.py:37 `run_migrations` 实际把 6 个 SQL 跑通）：`schema_migrations` 表记录了 6 行，幂等性、checksum 漂移检测都 work。
- **vec0 虚表在测试中真能 load + upsert + search**：`tests/unit/storage/test_vec0_store.py:21` 真 `sqlite_vec.load(conn)`，再 upsert 3 条 128-dim vector + search top-3，返回稳定 ordered result。
- **P7 release-gate 业务逻辑可用**：policy off→passed=1、policy on+no consent→passed=0、waive 必填 reason、waive 成功→passed=1 全部 5 个 test 覆盖；capstone 集成测试也走通。
- **script dry-run 行为符合 closure 承诺**：4 个 .sh 都支持 `--dry-run`，`tests/unit/test_scripts_dry_run.py:14` 用 `subprocess.run(..., check=True)` 验证返回 0 + stdout 含 `[Dry-run]`。

### 1.2 已确认的负面事实

- **3 份 closure 的 commit 字段是 commit message subject 字符串，不是 SHA**：`06-eval-inference-api-closure.md:26-32`、`07-security-governance-retrofit-closure.md:26-29`、`08-ops-handoff-closure.md:26-30` 全部 21 行写 `MVC-P6-complete` / `MVC-P7-complete` / `MVC-P8-complete` 等非 SHA 字符串。`git rev-parse MVC-P6-complete` → `fatal: 有歧义的参数`。真实 SHA 是 P6=`87b7e4e`、P7=`94750c8`、P8=`87f77fa`。这违反其 §5 自定的"✅ 证据为四元组（commit + query/test + run-time），无裸 file:line"承诺。
- **P4/P5 closure 引用了 pre-amend 的 commit**：`git reflog` 确认 `8857e78 → e8217c6 (amend)` 与 `e7cf338 → 51aa0f1 (amend)`。P4 closure (`04-quick-baselines-closure.md:26-30`) 与 P5 closure (`05-long-train-sovits-closure.md:26-31`) 5+6 行 commit 字段都是 pre-amend；`git diff 8857e78 e8217c6` 与 `git diff e7cf338 51aa0f1` 的唯一差异就是 closure 文件本身的加入。"closure 文件不在其引用的 commit 内"形成自引用漏洞。
- **P6 closure 自报 "all 77 tests passing"**（`06-eval-inference-api-closure.md:18`），实跑 92 passed 1 skipped；77 既非 P0-P6 累计数（P0-P6 约 78），也非任何可核对状态。数字不实。
- **6 项 in-scope 物理缺失**：
  1. `src/myvoiceclone/domain/services.py`（plan §12.2:411 列为 MVC-P0-03/P6-07 责任文件）
  2. `tests/fixtures/audio/tone_16k.wav`、`tests/fixtures/diarization/sample_turns.json`、`tests/fixtures/asr/sample_transcript.json`、`tests/fixtures/embeddings/*.json` 整棵树
  3. `tests/fakes/FakeDiarizer`、`FakeSeparator`、`FakeASR`、`FakeTrainer`、`FakeEmbedder`、`FakeInference` 整棵树
  4. `configs/pipelines/train.rvc.yaml`、`train.sovits.yaml`、`eval.default.yaml`
  5. `notebooks/corpus_audit.ipynb`、`notebooks/eval_review.ipynb`
  6. `infra/systemd/`、`models/pretrained/`、`models/checkpoints/`
- **DB schema 与 plan §14.3 系统性漂移**：22 张表/虚表中 **8 张存在字段/命名/语义漂移**，4 个状态机在 schema 层完全不强制。详见 R1。
- **vec0 维度被压平至 1/3**：plan §14.3 要求 `segment_audio_embeddings dim 768` / `speaker_embeddings dim 192` / `transcript_embeddings dim 384`，实际 003 迁移三张虚表都是 `float[128]`。`vec0_store.py:33,47,80` 把 namespace hardcode 为 `('speaker','audio','text')`。
- **jobs.status 字面漂移**：plan 冻结 `('queued','running','succeeded','failed','canceled')`，实际 `('pending','running','completed','failed','cancelled')`（002_state_jobs_artifacts.sql:6），3 个状态值字面不同（queued/pending、succeeded/completed、canceled/cancelled 拼写）。全 src `grep "normalize_status\|map_status"` 0 命中，无翻译层。
- **状态枚举孤立**：`src/myvoiceclone/domain/states.py` 定义 4 个 enum 共 15 个状态值，**全 src `grep "from myvoiceclone.domain.states"` 0 命中**。`SegmentStatus` / `RecordingStatus` / `JobStatus` / `DatasetStatus` / `ModelRunStatus` / `ReportStatus` / `ReleaseGateStatus` 7 个状态机中 6 个完全无对应枚举；plan §14.4 冻结的 39 个状态值仅 15 个被表达。
- **test marker taxonomy 形同虚设**：`pytest.ini` 声明 7 个 marker（unit/api/cli/integration/live/gpu/slow），但全 51 个 test 文件 93 个 test 函数中 **0 个用 `api/cli/live/gpu/slow` marker**。`pytest -m cli` / `pytest -m live` / `pytest -m gpu` 全部 0 tests。`test_pytest_markers.py:17` 只验 7 个字符串在 ini 文本里，不验"被使用"。
- **Dockerfile.train 在本机不可构建**：`pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime` 在 Docker Hub 上**没有 aarch64 manifest**（`device_stacks.md:62` host 是 aarch64），且 PyTorch 2.3 不含 Blackwell sm_120 kernel。`docker compose build train` 在本机必然失败。
- **两个 Dockerfile 都没装 CLI 依赖**：`pip install --no-cache-dir .` 只装 `pyyaml`（`pyproject.toml:11-13`），但 `cli.py:4` 顶层 `import typer` —— typer 在 `[cli]` extras。容器启动 `python -m myvoiceclone.cli ...` → `ModuleNotFoundError: No module named 'typer'`。
- **compose.yaml 命令引用不存在的资源**：`preprocess` service 调 `ingest /app/data/raw/sample.wav`，但 `data/raw/sample.wav` 不存在（实际只有 `data/artifacts/raw/art_*.wav/rec_*.wav`）；`train` service 调 `train sovits --dataset my_dataset`，但 `my_dataset` 不会被 init-db 创建。`pipelines/ingest.py:25` 找不到文件即 raise。
- **9 份 closure §4 "Deferred / Carry-over ledger" 全部 "None"**：0 个 closure 显式说"deferred to next phase"或"handoff to P8"。P0-P7 closure 与 P8 之间无显式承接记录（plan 端 `00-scope-architecture.md:258` 等有 "mega → P8" 字样，但 plan 是提案、closure 是事实，事实侧 0 记录）。
- **8 个 G-MVC owner gate 没有任何 closure 显式 CLOSED 回执**：`G-MVC-1..8` 是 final §7 冻结的 8 个 owner decision；P0-P8 closure §3 仅有"phase 内部 hard-gate"表（如 DB idempotent / WAL/FK / manifest frozen），**不是 owner gate 的回执**。`G-MVC-8`（项目树所有文件必须在 §12 定位）在所有 closure 中**完全没有专门核对段**。
- **action plan 状态全部 "draft"**（如 `00-scope-architecture.md:22`），但 closure 标 "closed"——口径错位。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部 finding 附 file:line，部分用 grep 全仓验证（marker、状态机、db schema 列名） |
| 本地命令 / 测试 | `yes` | 跑 pytest 实测 92/93 通过；git log/reflog/rev-parse 验证 commit 字段；ls 验证 6 类缺失文件 |
| schema / contract 反向校验 | `yes` | 把 plan §14.3 22 张表与 001-006 迁移逐表对账；把 plan §15.1 16 条 HTTP route 与 src routes_*.py 对账；把 plan §15.2 18 条 CLI 与 cli.py 对账 |
| live / deploy / preview 证据 | `no` | 未真跑 `docker compose up`（依赖 base image 拉取与 device 资源；非本机测试范畴） |
| 与上游 design / QNA 对账 | `yes` | 8 个 G-MVC owner gate 与 layers.md 都已对照 |

---

## 2. 审查发现

> 使用稳定编号 `R1..R16`。每条 finding 包含：严重级别、类型、事实依据、为什么重要、审查判断、建议修法。
> 严重级别遵循：`critical`（阻塞下一阶段）/ `high`（必须修但可分批）/ `medium`（建议修）/ `low`（建议优化）。
> 类型：correctness / security / scope-drift / delivery-gap / test-gap / docs-gap / platform-fitness / protocol-drift。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | DB schema 8/22 张表与 plan §14.3 系统性漂移，4 状态机在 schema 层不强制 | `critical` | correctness / scope-drift | `yes` | 修 schema 并补 DB-007 迁移 |
| R2 | vec0 虚表维度被压平至 plan 的 1/3（768/192/384 → 128/128/128） | `high` | correctness | `yes` | 修 003 migration 维度 + 上游 embedder 同步 |
| R3 | `Dockerfile.train:1` 在 aarch64 + GB10 + CUDA 13.0 host 上不可构建 | `critical` | platform-fitness | `yes` | 替换 base image 或改用 NGC arm64 + PyTorch 2.7+ |
| R4 | 6 份 closure §1 commit 字段不可核对（3 份非 SHA，2 份 pre-amend） | `high` | docs-gap | `no` | 重写 closure 表格为真实 SHA |
| R5 | test marker taxonomy 形同虚设（7 marker 中 5 个 0 test 使用） | `high` | test-gap | `no` | 删 marker 或补 `@pytest.mark.api/cli/live` |
| R6 | 6 类 in-scope 物理缺失（services.py / fixtures / fakes / 3 yaml / 2 notebook / systemd / pretrained） | `high` | delivery-gap | `no` | 补缺失文件或显式 deferred |
| R7 | 8 个 G-MVC owner gate 在 9 份 closure 中无显式 CLOSED 回执 | `medium` | docs-gap | `no` | closure §3 加 G-MVC-N 显式表 |
| R8 | P6/P7/P8 closure 的"四元组证据"声明与实际不符 | `high` | docs-gap | `no` | 修改诚实收口声明口径 |
| R9 | 状态枚举 (`domain/states.py`) 定义后零 import | `medium` | correctness | `no` | 全文替换裸字符串为枚举 |
| R10 | jobs.runner 把 6 步 preprocess 绑死，无 step-level job dispatch | `high` | correctness | `no` | 增加 per-step job name dispatch |
| R11 | `api/dependencies.py:7-8` 不解析相对 db_path（vs cli.py:40-41 已解析） | `high` | correctness | `no` | 抽 DRY 函数统一 |
| R12 | Dockerfile.preprocess + Dockerfile.train 都不装 extras，ENTRYPOINT 启动即缺 typer | `critical` | delivery-gap | `yes` | 改 `pip install ".[cli,db,api,preprocess]"` |
| R13 | compose.yaml 命令引用不存在的文件与 dataset | `high` | delivery-gap | `no` | 改命令或补 init container |
| R14 | P7 release-gate 状态机降级为 boolean，waive 写入反语义 | `high` | correctness | `no` | 重做 schema + endpoint |
| R15 | 4 个 `os.environ["MOCK_ADAPTERS"] = "true"` 测试无 cleanup | `medium` | test-gap | `no` | 改用 monkeypatch.setenv |
| R16 | `mvc audit recording` 等 4 个 CLI 命令、3 个 HTTP route 缺失 | `medium` | delivery-gap | `no` | 补 CLI/route 或改 plan |

### R1. DB schema 8/22 张表与 plan §14.3 系统性漂移，4 状态机在 schema 层不强制

- **严重级别**：`critical`
- **类型**：`correctness` / `scope-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `db/migrations/001_core_schema.sql:51-60` `datasets` 表 **无 CHECK 约束**，plan §14.3:576 要求 `status IN ('draft','frozen','training','evaluated','rejected','release_candidate')`；`application` `routes_datasets.py:35` 写入 `status="active"`（plan 没枚举）；`frozen immutable` 靠 `pipelines/export_dataset.py:42-43` 应用层 RuntimeError
  - `db/migrations/002_state_jobs_artifacts.sql:3-11` `jobs.status` CHECK 是 `('pending','running','completed','failed','cancelled')`，plan §14.3:578 要求 `('queued','running','succeeded','failed','canceled')` —— 3 个状态值字面漂
  - `002_state_jobs_artifacts.sql:24-37` `artifacts` 字段是 `name` / `artifact_type` / `parent_artifact_id` / `job_id`，plan §14.3:580 要求 `kind` / `source_artifact_id` / `created_by_job_id` / `pipeline_version` / `params_json` —— 5 字段名漂
  - `002_state_jobs_artifacts.sql:39-47` `model_runs` **缺** `model_family` / `checkpoint_artifact_id` / `env_digest` / `git_commit` / `finished_at` 5 列（plan §14.3:582），**无任何索引**，**无 status CHECK**（plan §14.4 列 6 状态机）
  - `002_state_jobs_artifacts.sql:49-54` `pipeline_runs` 实际只有 `id, name, status, created_at` 4 列，**缺** `pipeline_name` / `subject_type` / `subject_id` / `config_json` / `finished_at`；全 src `grep` **0 命中**对此表的读写（dead table）
  - `003_vec0_embeddings.sql:11-18` 表名是 `embedding_items` 不是 `embedding_jobs`（plan §14.3:584），**缺** `subject_type` / `subject_id` / `status` 3 列
  - `004_reports_metrics.sql:3-11` `reports` 字段是 `name, report_type, summary_json, artifact_id`，**缺** `kind` / `subject_type` / `subject_id` / `status` 4 列（plan §14.3:585）
  - `004_reports_metrics.sql:13-21` `eval_metrics` **缺** `report_id` / `metric_json`，索引只 `idx_eval_metrics_run` 单列，plan §14.3:586 要求 `(run_id, metric_name)` 复合
  - `004_reports_metrics.sql:23-31` `eval_samples` 三向 FK（`input_artifact_id` / `output_artifact_id` / `reference_artifact_id`）**塌缩为单 `audio_artifact_id`**，**缺** `report_id` / `scores_json`（plan §14.3:587）
  - `005_security_placeholders.sql:3-12` `consent_ledger` **缺** `scope` / `status` / `evidence_uri` / `revoked_at`，**多出** `recording_id` / `granted` / `signature`（plan §14.3:588）
  - `005_security_placeholders.sql:14-20` `policy_events` **缺** `subject_type` / `subject_id` / `policy_name` / `decision` / `reason` / `payload_json` 6 列（plan §14.3:589）
  - `005_security_placeholders.sql:22-29` `release_gates` **无 `status` 状态机**，plan §14.3:590 要求 4 态 `('pending','passed','failed','waived')` + `decision_json`；实际 `passed INTEGER CHECK IN (0,1)`，waive 通过 `details_json.waived=True` JSON hack 表达
  - 4 个状态机（`datasets` / `model_runs` / `reports` / `release_gates`）在 schema 层**完全无 CHECK**，plan §14.4 冻结的 7 条状态机中只有 `jobs.status`（1/7）在 schema 层强制
- **为什么重要**：
  - plan §15.1 line 652 `GET /audit/{subject_type}/{subject_id}` 路由承诺需要 `reports.subject_type` 列；实际 schema 没这列，`api/routes_reports.py:164-258` 用 query 参数实现 → 实现了 contract 但破坏了 plan 的可移植性
  - `eval_samples` 三向 FK 塌缩意味着 P6 评估报告无法在 SQL 层 join 样本↔指标↔报告，metric 历史追溯必须走 summary_json 二次结构
  - `release_gates` pending 状态在 schema 里根本不存在，`routes_reports.py:100-107` 创建时直接算 policy 写终态；`waived` 是把 `passed` 覆写成 1 + `details_json` hack —— 任何外部 UI 按 `SELECT status='waived'` 都会返 0 行
  - `consent_ledger` 无 `revoked_at` / `status` 字段意味 consent 撤销必须 DELETE row（CASCADE 关联删 speaker/recording），audit 链断裂
  - 状态机 4/7 无 CHECK 意味着 application 可以写任何字符串（实际 routes_datasets.py:35 写 "active"，train.py:308-329 写 "queued"/"preparing"/"training"/"checkpointed" 都不在 plan 词表）—— schema 失去字面校验能力
- **审查判断**：
  这是**功能性 schema 重设计**，不是小漂。任何按 plan §14.3 字段名做查询的下游消费者（OpenAPI 客户端、按 plan 写的 SQL、未来的 ORM）会全部失败。
- **建议修法**：
  1. 把 `db/migrations/001-006` 与 plan §14.3 字段表逐列对账，输出 `db/migrations/007_reconcile_to_plan.sql` 一次性迁移：
     - 改 `artifacts.name → kind` / `artifacts.artifact_type → kind` 合并
     - 改 `jobs.status` CHECK 词表为 plan 词表
     - 加 `datasets.status` / `reports.status` / `model_runs.status` CHECK 约束
     - 加 `reports.subject_type` / `subject_id` 列
     - 加 `eval_metrics.report_id` / `eval_samples.report_id` / 三向 artifact_id FK
     - 加 `model_runs.model_family` / `checkpoint_artifact_id` / `env_digest` / `git_commit` / `finished_at`
     - 改 `release_gates` 加 `status` 状态机列 + `decision_json`
     - 改 `consent_ledger` 加 `scope` / `status` / `evidence_uri` / `revoked_at`
     - 改 `policy_events` 加 `subject_type` / `subject_id` / `policy_name` / `decision` / `reason` / `payload_json`
  2. application 层加 `status_translation.py` 做 plan↔code 词表映射（如果一定要保留 code 现词）
  3. 重新跑 `tests/unit/storage/*` 全部 unit test 确认新 schema 不破测试

### R2. vec0 虚表维度被压平至 plan 的 1/3

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `db/migrations/003_vec0_embeddings.sql:23-32` 三张 vec0 虚表都是 `float[128]`
  - plan §14.3:594-596 要求 `segment_audio_embeddings float[768]` / `speaker_embeddings float[192]` / `transcript_embeddings float[384]`
  - `src/myvoiceclone/storage/vec0_store.py:33,47,80` hardcode `if namespace not in ('speaker','audio','text'): raise ValueError`
- **为什么重要**：
  - 128 维能容纳的语义信息容量是 768 维的 1/6、384 维的 1/3、192 维的 2/3
  - 当前 `adapters/embeddings/audio_embedder.py:15-18` / `speaker_embedder.py` / `text_embedder.py` 用 `md5 16 byte 扩展 128 维`确定性 mock hash（不是真模型 embedding）
  - 一旦切换到真模型（CLAP/HuBERT 768-dim / X-vector 192-dim / BERT 384-dim），需要修 schema 维度 + `vec0_store.py` 维度变量化 + `embedding_models.dimension` CHECK 约束
  - plan §3.2 O3 "vec1 作为默认向量库"延后到 DB-006 probe；`vec0` 维度塌缩让"vec0 默认"的精度上限被锁死
- **审查判断**：
  vec0 维度 128 在 mock 阶段无害（mock 16-byte hash 即可），但**作为 P3 corpus curation / dedupe 的生产基线不够**。R1 的迁移应一并处理。
- **建议修法**：
  - 在 `db/migrations/003_vec0_embeddings.sql` 中改维度为 plan 冻结值（audio 768、speaker 192、text 384）
  - 在 `vec0_store.py` 中维度改为读 `embedding_models.dimension` 表，按 namespace 动态选
  - 真实 adapter 切换时同步改 embedder 输出维度

### R3. `Dockerfile.train:1` 在 aarch64 + GB10 + CUDA 13.0 host 上不可构建

- **严重级别**：`critical`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `infra/docker/Dockerfile.train:1` `FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`
  - `device_stacks.md:62,77` host 是 `aarch64`
  - `device_stacks.md:13-22` GPU 是 NVIDIA GB10 Blackwell，driver 580.159.03，CUDA 13.0
  - Docker Hub `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime` 的 manifest **只有 `architecture:"amd64"`**（无 arm64 layer）—— PyTorch 官方直到 2.12.0 都未发布 arm64 tag
  - PyTorch 2.3.0 (2024-04 发布) 不含 Blackwell sm_120 kernel，sm_120 支持从 PyTorch 2.7.0+ 引入
  - `infra/docker/compose.yaml:15-34` `train` service 用 `deploy.resources.reservations.devices: driver: nvidia` 声明 GPU
  - P8 closure `08-ops-handoff-closure.md:40` 自评 "Containerized Environment" ✅ PASS，但未做实际 `docker compose up` 验证
- **为什么重要**：
  - 任何尝试 `docker compose -f infra/docker/compose.yaml build train` 的开发者会立即撞 manifest-list 错误
  - 即便用 `--platform linux/amd64` 强拉 + qemu 模拟，PyTorch 2.3 在 sm_120 设备上 `torch.cuda.is_available()` 会返回 False 或 `RuntimeError: CUDA error: no kernel image is available for execution on the device`
  - 这意味着 P5 长训 (So-VITS-SVC) 在本机 (host 是 aarch64) **永远无法走 Docker 跑** —— plan §6.6 P5-01 的"环境就绪"硬门禁在 device 层就破
  - 文档 (`README.md` / `local-setup.md`) 全文未提 aarch64 / GB10 / CUDA 13.0 / 镜像选择
- **审查判断**：
  Dockerfile.train 是 P5/P6 阶段承诺的"生产就绪容器化"，但与本机 device stack 三层不匹配（架构 / 驱动 / GPU arch），构成 plan §11 "本地可审计 voice clone pipeline" 在本机不可达的根本原因。
- **建议修法**：
  - 选项 A（最干净）：改用 NVIDIA NGC `nvcr.io/nvidia/pytorch:24.xx-py3-aarch64`（如果存在）或自 build base image
  - 选项 B：改用 PyTorch 2.7+ 的非官方 aarch64 wheel（nightly）
  - 选项 C：在 `local-setup.md` 显式声明 "first-build 不支持 aarch64 + Blackwell 上的 live 训练，当前仅 mock 流程在 venv 下工作；要跑真训练请用 amd64 host"
  - 必须更新 `compose.yaml:15-34` 加上 `platforms: linux/arm64`
  - 必须更新 `README.md` + `local-setup.md` 加上 device stack 说明

### R4. 6 份 closure §1 commit 字段不可核对（3 份非 SHA，2 份 pre-amend）

- **严重级别**：`high`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `06-eval-inference-api-closure.md:26-32`、`07-security-governance-retrofit-closure.md:26-29`、`08-ops-handoff-closure.md:26-30` 全部 21 行 commit 字段写 `MVC-P6-complete` / `MVC-P7-complete` / `MVC-P8-complete` 等 commit message subject 字符串
  - `git rev-parse MVC-P6-complete` → `fatal: 有歧义的参数 'MVC-P6-complete'`
  - 真实 SHA：P6=`87b7e4e`、P7=`94750c8`、P8=`87f77fa`
  - P4 closure (`04-quick-baselines-closure.md:26-30`) 5 行全部引用 `8857e78`；`git reflog` 显示 `8857e78 → e8217c6 (amend)`；`git diff 8857e78 e8217c6` 唯一差异就是 closure 文件本身的加入
  - P5 closure (`05-long-train-sovits-closure.md:26-31`) 6 行全部引用 `e7cf338`；`git reflog` 显示 `e7cf338 → 51aa0f1 (amend)`
  - 5 份 closure §5 自定"✅ 证据为四元组（commit + query/test + run-time），无裸 file:line"承诺
- **为什么重要**：
  - 任何外部审查者用 `git show MVC-P6-complete` 想核对都会失败
  - 任何用 `git checkout 8857e78` 想验证 P4 closure 的人会发现 closure 文件根本不在那个 commit 内
  - closure §5 自定的"诚实收口纪律"承诺与实际不符，破坏文档可信度
- **审查判断**：
  这是"合规表演"的系统性失实。最严重的是 P6/P7/P8 的 21 行——commit 字段连"看着像 SHA"都不像（没有 40 字符 hex）。
- **建议修法**：
  - 立即重写 P6/P7/P8 closure §1 表的 commit 字段为真实 SHA（`87b7e4e` / `94750c8` / `87f77fa`）
  - P4/P5 closure 的 11 行 commit 字段更新为 amend 后的 `e8217c6` / `51aa0f1`
  - 进一步在 §1 加 commit author / date 字段，让"四元组"真正成立
  - 长远：在 `docs/closure/.template.md` 加 "commit 必须是 40-char SHA，可用 `git rev-parse HEAD` 验证" 的硬规则

### R5. test marker taxonomy 形同虚设（7 marker 中 5 个 0 test 使用）

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `pytest.ini:3-9` 声明 7 marker：`unit` / `api` / `cli` / `integration` / `live` / `gpu` / `slow`
  - `pytest.ini:11` `addopts = -m "unit or api or cli or integration" --strict-markers`
  - 全 93 个 test 函数实际只用 2 个 marker：`unit` ×92 + `integration` ×1
  - `grep -r "@pytest.mark.api\|@pytest.mark.cli\|@pytest.mark.live\|@pytest.mark.gpu\|@pytest.mark.slow" tests/` → 0 命中
  - `tests/unit/test_pytest_markers.py:17` `required_markers = ["unit", "api", "cli", "integration", "live", "gpu", "slow"]` 只验 ini 文本含这 7 字符串，不验"被使用"
- **为什么重要**：
  - `pytest -m cli` / `pytest -m live` / `pytest -m gpu` / `pytest -m slow` 全部 0 tests
  - final §8.1 写的"live/gpu/slow 单独 marker 不进默认 suite"契约**永远不会被验证**（因为 marker 本身没被用）
  - `tests/api/*.py` (5 个文件) + `tests/cli/*.py` (1 个文件) + `tests/integration/*.py` (1 个文件) 全部用 `@pytest.mark.unit` 而非对应 marker —— 命名空间无意义
  - CI 可以"live tests all green"但 live suite 实际为 0
- **审查判断**：
  marker 设计是好的（live/gpu/slow 与 unit 分离），但实现偷懒把全部 test 都标 unit。
- **建议修法**：
  - 选项 A（务实）：删 `pytest.ini` 的 5 个僵尸 marker
  - 选项 B（理想）：给 `tests/api/*.py` 加 `@pytest.mark.api`、`tests/cli/*.py` 加 `@pytest.mark.cli`；为 `test_ffmpeg_live_probe` 加 `@pytest.mark.live`；保留 gpu/slow 留给未来
  - `test_pytest_markers.py` 加断言："每个 marker 至少 1 个 test 使用"（除 gpu/slow 因依赖外部资源可豁免）

### R6. 6 类 in-scope 物理缺失

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**（每个缺失都附 `ls` 实测）：
  - `ls src/myvoiceclone/domain/` → 只有 `entities.py` / `policies.py` / `states.py`，**`services.py` 缺失**（plan §12.2:411 列为 MVC-P0-03/P6-07 责任）
  - `ls tests/fixtures/` → 整个目录不存在（plan §8.3 列 4 个 fixture 文件：audio tone_16k.wav、diarization sample_turns.json、asr sample_transcript.json、embeddings *.json）
  - `ls tests/fakes/` → 整个目录不存在（plan §8.3 列 6 个 fake：FakeDiarizer、FakeSeparator、FakeASR、FakeTrainer、FakeEmbedder、FakeInference）
  - `ls configs/pipelines/` → 只有 `preprocess.default.yaml`，**`train.rvc.yaml` / `train.sovits.yaml` / `eval.default.yaml` 缺失**（plan §12.2:384-386）
  - `ls notebooks/` → 整个目录不存在（plan §12.2:460-461 标 `corpus_audit.ipynb` / `eval_review.ipynb`）
  - `ls infra/systemd/` / `ls models/pretrained/` / `ls models/checkpoints/` → 三个目录不存在（plan §12.2:457-458, 469）
- **为什么重要**：
  - `domain/services.py` 缺失导致 api/cli 直接 import pipelines/eval，违反 layers.md "api must orchestrate via service/job layer" —— 实际有 5 处违规（详见 R7）
  - `tests/fixtures/` / `tests/fakes/` 缺失意味测试都用 conftest 动态生成或 inline mock —— 这虽然功能等价，但 plan §8.3 的 fixture 路径被破坏
  - 3 个 pipeline yaml 缺失意味 `pyannote` / `sovits` / `rvc` / `xtts` / `eval` 5 个 adapter 的 hyperparam 没有外部配置点，全靠 src 硬编码
  - 9 份 closure §4 "Deferred / Carry-over ledger" 全部 "None"，意味着这 6 类缺失既没标 done 也没标 deferred —— 是双重失实
- **审查判断**：
  G-MVC-8（项目树所有文件必须在 §12 定位）在所有 closure 中**完全没有专门核对段**。这些缺失是 plan §12 写下的承诺，应在 closure §3 hard-gate 显式标 partial。
- **建议修法**：
  - 把 `domain/services.py` 加成 DB-007 的一部分（参考 R1）
  - 把 `tests/fixtures/` + `tests/fakes/` 拆为可选项：要么补齐（需要 4+6=10 个文件）、要么把"动态生成"作为 plan 升级依据
  - 3 个 pipeline yaml 补齐（即便内容是空壳 + 默认值）
  - 9 份 closure §4 重新填表：把缺失项标 A 类（永久 deferred）/ B 类（下一阶段补）/ C 类（live 时再补）

### R7. 8 个 G-MVC owner gate 在 9 份 closure 中无显式 CLOSED 回执

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - plan §7:236-247 冻结 8 个 owner decision gate `G-MVC-1..8`，全部声明 `CLOSED`（由 final baseline 自身关闭）
  - 9 份 closure §3 "Hard-gate 判定" 表是各 phase 内部技术硬闸（DB idempotent / WAL/FK / vec0 health / manifest frozen / long-run cancel 等），**不是 owner gate 回执**
  - `grep "G-MVC-1\|G-MVC-2\|...\|G-MVC-8" docs/closure/` → 0 命中
  - `G-MVC-8`（"项目树所有文件必须在 §12 定位到具体 phase 和工作项"）在所有 closure 中**完全没有专门核对段** —— 意味着 R6 的 6 类缺失无人追究
- **为什么重要**：
  - G-MVC-2（P2 暂缓授权安全，P7 接入）—— P7 closure §3 hard-gate 仅提 "Flag off non-intrusiveness"，未声明 G-MVC-2 整体 CLOSED
  - G-MVC-5（分层低耦合）—— P0 closure §2 验 layer boundaries，但未声明 G-MVC-5 CLOSED
  - G-MVC-6（业务审计）—— 多 closure 提 jobs/job_events/artifacts，但未声明 G-MVC-6 CLOSED
  - G-MVC-8（文件定位）—— **0 closure 触及**
- **审查判断**：
  closure §3 表是"phase 内部"硬闸，**与 final §7 owner gate 是两套**。混淆两者意味 P0-P8 closure 全部缺失 owner gate 回执。
- **建议修法**：
  在每个 closure §3 加一张"G-MVC owner gate 兑现表"，逐项勾选。例如 P6 closure：
  ```
  | Owner Gate | 兑现 | 证据 |
  | G-MVC-4 (Q4 FastAPI+Typer) | ✓ | api/routes_*.py + cli.py + test_routes.py 4 passed |
  | G-MVC-6 (Q6 业务审计) | partial | jobs/job_events/artifacts 落地，但 reports.subject_type 缺 (见 R1) |
  ```

### R8. P6/P7/P8 closure 的"四元组证据"声明与实际不符

- **严重级别**：`high`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - P0-P8 closure §5 全部 5 行"诚实收口声明"自评 ✅：
    - "每个 ✅ 归类 5 态 (verified)"
    - "✅ 证据为四元组（commit + query/test + run-time），无裸 file:line"
    - "scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）"
    - "deferred 已三分类（A/B/C）且每项有承接位置"
    - "owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）"
  - P6/P7/P8 的 commit 字段是字符串（见 R4），"四元组"的 commit 槽位无效
  - P0-P8 closure §4 全部 "None"（见 R6），deferred 三分类无内容
  - P6 closure 自报 "all 77 tests passing"（`:18`）—— 实跑 92 passed 1 skipped，77 不存在
- **为什么重要**：
  - §5 的 ✅ 自我评级与 §1-§4 实际状态不符
  - 这是 closure 文件自定审计规则的"合规表演"——自我宣称 = 自我验证 = 不可信
- **审查判断**：
  closure §5 是 closure 写作者对自身工作的自评，本身不构成独立验证。需要外部审查员（如下游 review）做交叉核对。
- **建议修法**：
  - 删除 §5 的 ✅ 自我评级（或者改为 ⏸ 等待 review 状态）
  - 在模板 `00-templates/closure.md` 明确 §5 是"自评待审"，不是"自评已通过"
  - 引入 review 角色独立核对（不是审查员自己写自己审）

### R9. 状态枚举 (`domain/states.py`) 定义后零 import

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/domain/states.py` 定义 4 个 enum（`RecordingStatus` 4 值 / `JobStatus` 5 值 / `DatasetStatus` 2 值 / `ModelRunStatus` 4 值）共 15 个状态值
  - 全 src `grep "from myvoiceclone.domain.states" src/` → **0 命中**
  - plan §14.4 冻结 7 个状态机共 39 个状态值，states.py 仅覆盖 15 个（38%）
  - 实际代码用裸字符串：pipelines/diarize.py:74 `seg.status="draft"`、slice.py:37 `seg.status="ignored_duration_bounds"`、clean.py:59 `seg.status="cleaned"`、transcribe.py:58 `seg.status="transcribed"`、score.py:54 `seg.status="processed"`、routes_datasets.py:35 `ds.status="active"`、train.py:308-433 `run.status="queued"/"preparing"/"training"/"checkpointed"/"completed"/"failed"/"cancelled"`
  - 共有 12+ 裸字符串
- **为什么重要**：
  - 裸字符串无类型安全，IDE 不会提示 typo
  - 状态机扩展（如新增 "review_pending"）需要全 src 搜字符串
  - plan §14.4 的状态机与 code 实际状态语义不对齐
- **审查判断**：
  states.py 是 dead code；plan §14.4 冻结的状态机在 application 层没被执行。
- **建议修法**：
  - 扩 states.py 覆盖全部 39 状态值
  - 把裸字符串替换为枚举引用（注意：DB 仍存字符串，enum 仅在 Python 层）
  - 在 src/eval/ 集中处理 DB 字符串 ↔ Enum 双向映射

### R10. jobs.runner 把 6 步 preprocess 绑死，无 step-level job dispatch

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/jobs/runner.py:79-87` dispatcher 只识别 3 个 job name：`preprocess_all` / `ingest` / `train_sovits`
  - plan §6.3 P2-08 要求"每个 pipeline step 均可作为 job 运行、失败可重试"
  - 实际缺失 job name：`diarize` / `slice` / `clean` / `transcribe` / `score` / `curate` / `dedupe` / `export_dataset` / `train_rvc` / `synth_xtts` / `evaluate` / `baseline_report` / `train_report` / `corpus_report`
  - `_execute_preprocess_all` (runner.py:117-148) 把 ingest→diarize→slice→clean→transcribe→score 6 步绑在一个 try 内，任一步失败整 job failed；partial retry 无路径
  - pipelines/*.py 自身不写 `job_events`（仅 curate.py:37 写 `segment_reviews`，不是 `job_events`），step-level 进度完全不可观测
- **为什么重要**：
  - 用户想"只重跑 score 阶段"——必须伪造一个新 job，或者手写 SQL `UPDATE jobs SET status='pending'` 然后 POST /run
  - 长录音 20+ 小时，任何单步失败会从头重跑（ingest + diarize + slice 都得重做），浪费几小时
  - 与 plan §6.3 P2-08 直接矛盾
- **审查判断**：
  runner.py 的设计选择是"先打通全链，再做 per-step dispatch"，这在 first-build 阶段可以接受，但 closure §3 自评 "fake adapter preprocess chain passes" 不等于 "每步可独立 retry" 满足。
- **建议修法**：
  - 在 runner.py 加 `if job.name in ('ingest','diarize','slice','clean','transcribe','score'):` 6-way dispatch
  - 配合 CLI 补 4 个 `mvc run slice/clean/transcribe/score` 子命令（plan §15.2 冻结）
  - pipelines 各 step 在 try/except 内调 `write_job_event` 写 step-level 事件

### R11. `api/dependencies.py:7-8` 不解析相对 db_path（vs cli.py:40-41 已解析）

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/api/dependencies.py:7-8`：
    ```python
    db_path = config.get("db_path", "db/myvoiceclone.sqlite")
    conn = get_connection(db_path, load_vec=True)
    ```
    相对路径直接传给 `sqlite3.connect`，不调用 `get_project_root()`
  - `src/myvoiceclone/cli.py:40-41`：
    ```python
    if not os.path.isabs(db_path):
        db_path = os.path.join(get_project_root(), db_path)
    ```
  - uvicorn 从非 project root 启动时（如 `cd /opt && uvicorn myvoiceclone.api.app:create_app`），DB 会建在 `/opt/db/myvoiceclone.sqlite` 而非 project root
  - `docker compose.yaml:7` 显式 mount `../../db:/app/db` 来"修正"这个 bug，但开发者本地非 docker 启动会撞墙
- **为什么重要**：
  - 同一份 config 在 CLI 和 API 下产生不同的 DB 位置
  - 与 CLI 不一致是隐形 bug，开发者排查困难
- **审查判断**：
  DRY 违反 + 行为不一致。
- **建议修法**：
  - 抽 `config.resolve_db_path()` 函数
  - `dependencies.py:7-8` 调用此函数
  - `cli.py:40-41` 也调用此函数

### R12. Dockerfile.preprocess + Dockerfile.train 都不装 extras，ENTRYPOINT 启动即缺 typer

- **严重级别**：`critical`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `infra/docker/Dockerfile.preprocess:16` `RUN pip install --no-cache-dir .` 装的是 `pyproject.toml:11-13` 的强制依赖 `["pyyaml"]`
  - `src/myvoiceclone/cli.py:4` 顶层 `import typer`，typer 在 `pyproject.toml:17` 的 `[cli]` extras
  - `infra/docker/Dockerfile.train:15` 同样 `pip install --no-cache-dir .`
  - ENTRYPOINT 两者都是 `["python", "-m", "myvoiceclone.cli"]`
  - 容器启动 `python -m myvoiceclone.cli ...` → `ModuleNotFoundError: No module named 'typer'` → 立即退出 1
- **为什么重要**：
  - 这是 R3 之外的**第二个 blocker**：即便解决了 base image 兼容问题，容器依然不能启动
  - compose.yaml `command: ["ingest", ...]` / `command: ["train", "sovits", ...]` 永远到不了那一步
- **审查判断**：
  P8 closure §3 自评 "Clean scripts dry-run" ✅ PASS 与 "Containerized Environment" ✅ PASS 都是 soft evidence —— closure 没真跑过 `docker compose up`。
- **建议修法**：
  - 改 `Dockerfile.preprocess:16` 为 `RUN pip install --no-cache-dir ".[cli,db,api,preprocess,audio]"`
  - 改 `Dockerfile.train:15` 为 `RUN pip install --no-cache-dir ".[cli,db,api]"`
  - 验证：本地 `docker build` 后 `docker run --rm <image> --help` 应输出 typer help

### R13. compose.yaml 命令引用不存在的文件与 dataset

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `infra/docker/compose.yaml:13` `command: ["ingest", "/app/data/raw/sample.wav"]` —— `data/raw/sample.wav` 不存在
  - 实际 `data/` 目录的 artifacts 在 `data/artifacts/raw/art_*.wav` / `rec_*.wav`，不在 `data/raw/`
  - `pipelines/ingest.py:25` `if not os.path.exists(filepath): raise FileNotFoundError`
  - `infra/docker/compose.yaml:35` `command: ["train", "sovits", "--dataset", "my_dataset"]` —— `my_dataset` 不会被 init-db 创建
  - `cli.py:244-246` 找不到 dataset 时 `typer.Exit(code=1)` 报 "Dataset 'my_dataset' not found"
  - `pipelines/train.py:300-301` 即便 dataset 存在也要求 `status == "frozen"`，否则 raise
- **为什么重要**：
  - `docker compose up preprocess` 一定失败
  - `docker compose up train` 一定失败
  - 文档 `docs/ops/local-setup.md:77` 写 `mvc ingest /app/data/raw/my_sample.wav` 暗示用户自己 supply 文件；但 compose 硬编码 `sample.wav` 是 dead config
- **审查判断**：
  compose 文件是 P5 长训的"一键启动"承诺，但与实际数据流不联通。
- **建议修法**：
  - 改 `compose.yaml:13` 改用 init container 从公开 URL 拉 1s 静音 wav（reference 化）
  - 改 `compose.yaml:35` 前置 `init-db` + `dataset create` + `dataset freeze` 三步（用 multi-command 形式或 init container）
  - 或者在 `local-setup.md` 显式声明"compose.yaml 仅 mock 启动，真实流程需手动 init"

### R14. P7 release-gate 状态机降级为 boolean，waive 写入反语义

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `db/migrations/005_security_placeholders.sql:22-29` `release_gates` 表 schema：`id, model_run_id, passed, approved_by, approved_at, details_json`
  - plan §14.3:590 要求 `status IN ('pending','passed','failed','waived')` + `decision_json`
  - `api/routes_reports.py:101-108` 创建 gate 时直接算 policy 写终态 `passed=0/1`，**无 pending 行**
  - `api/routes_reports.py:138-143` waive handler：
    ```sql
    UPDATE release_gates SET passed=1, approved_by=?, approved_at=CURRENT_TIMESTAMP, details_json=? WHERE id=?
    ```
  - waive 通过 `details_json.waived=True` + `details_json.waived_reason` 表达
  - `policy_events` 表（005:14-20）字段 `event_type, status, details_json`，**缺** `subject_type/subject_id/policy_name/decision/reason/payload_json` 6 列（plan §14.3:589）
  - `api/routes_reports.py:164-258` audit trace endpoint 的 5 个 subject_type 分支（recording/dataset/job/run/report）**完全不读 `policy_events` 表**
- **为什么重要**：
  - "pending" 状态在 schema 里根本不存在 —— `routes_reports.py:100-107` 创建 gate 时同步算 policy，没有"待审"窗口
  - "waived" 通过 `passed=1` + JSON hack 表达 —— 任何外部 UI 按 `SELECT status='waived'` 返 0 行
  - audit trace 不读 policy_events —— plan §14.5 "policy/release decisions additionally write policy_events" 与 audit trace 的连接断裂
  - policy_events 6 字段名漂 → 任何按 plan 字段写的 SQL 会失败
- **审查判断**：
  P7 是 final 阶段"后置安全治理接入点"，是"小漏"叠加成"功能性丢失"。
- **建议修法**：
  - 在 DB-007 改 `release_gates` schema 加 `status` 列 + `decision_json`，waive 写 `status='waived'` 而非 `passed=1`
  - 改 `policy_events` 字段为 plan 冻结 6 列
  - 改 audit trace 加 `policy` subject_type 分支读 `policy_events`

### R15. 4 个 `os.environ["MOCK_ADAPTERS"] = "true"` 测试无 cleanup

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `tests/unit/adapters/test_rvc_adapter.py:9,26`、`test_xtts_adapter.py:8`、`test_sovits_adapter.py:8` 全部用 `os.environ["MOCK_ADAPTERS"] = "true"` 写入
  - 无 `del os.environ["MOCK_ADAPTERS"]` 还原
  - `tests/unit/adapters/test_ffmpeg_adapter.py:8,19,31` 用 monkeypatch 正确（无副作用）
  - `MOCK_ADAPTERS` 默认 "true"（`rvc_adapter.py:10` 等）—— 4 个 mock test 之后跑 `test_ffmpeg_live_probe`（`test_ffmpeg_adapter.py:27-38` 要求 `MOCK_ADAPTERS=false`），pytest 默认按文件名字 alphabetic 跑，目前 `test_ffmpeg_live_probe` 跑在 `test_rvc_adapter` 之前，但顺序无任何代码锁
  - `grep "del os.environ\|os.environ.pop" tests/` → 0 命中
- **为什么重要**：
  - 测试通过不等于生产环境正确（`MOCK_ADAPTERS` 默认 true，**生产忘设就拿假数据**）
  - 8 个 adapter 的 real path 0 测试（plan §6.3-6.5 P2/P3/P4/P5 都标 "mock 通过"）—— 真切到生产 adapter 会立即报 NotImplementedError
- **审查判断**：
  这是 fixture-scope 漏 + adapter test 深度不够的组合。
- **建议修法**：
  - 改 4 个 test 用 `monkeypatch.setenv("MOCK_ADAPTERS", "true")`（自动还原）
  - 加 8 个 test 验"MOCK_ADAPTERS=false 时 NotImplementedError"
  - 在 `pyproject.toml` 或 fixture 加 `MOCK_ADAPTERS` 默认值统一管理

### R16. `mvc audit recording` 等 4 个 CLI 命令、3 个 HTTP route 缺失

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - plan §15.2 冻结 18 条 CLI，src 实际 13 条 + 5 条漂移/缺失：
    - **缺失**：`mvc run slice / clean / transcribe / score`（plan §15.2 lines 661-664），`mvc infer tts`（line 672）
    - **漂移**：`mvc vec health` → 实际 `mvc vec-health`（cli.py:58 字符串名），`mvc infer vc` 选项 vs 实际位置参数，`mvc audit recording` → 实际 `mvc audit`（无 sub-cmd）
  - plan §15.1 冻结 16 条 HTTP route，src 实际 27 条（含 11 条 plan 之外）：
    - **缺失/合并**：`POST /jobs`（line 639）—— `routes_jobs.py` 无此端点（建 job 隐含在 `POST /api/recordings?filepath=...`）；`POST /runs/eval`（line 648）—— 无此端点；`POST /inference/vc` / `POST /inference/tts`（line 650-651）—— 合并为单一 `POST /api/inference`
  - `docs/api/openapi.md` 漏 4 个端点：`/api/reports/release-gates`、其 `/waive`、其 `GET /{id}`、`/health`
- **为什么重要**：
  - capstone 用的 8 个端点（`test_first_build_journey.py`）全部存在 —— 实现已迁就 capstone
  - 但 `mvc run slice` 等 4 个 CLI 缺失意味开发者无法用 CLI 触发单步
  - `mvc audit recording` 缺失意味 plan 描述的子命令形式失败
  - openapi.md 漏 4 个端点意味外部消费者按文档调 404
- **审查判断**：
  plan §15.1/§15.2 是 frozen 目标，src + tests 是 actual 实现；两者已经脱节。这是 §H.1 sub-agent H 的核心发现。
- **建议修法**：
  - 选项 A（最实用）：把 plan §15.1/§15.2 升版为 reflect-actual（承认 `/api` prefix、承认漂移、合并的 vc/tts endpoint）
  - 选项 B：补齐 4 个 CLI + 3 个 HTTP route（需要扩展 cap on design）
  - `docs/api/openapi.md` 补 4 个 release-gate 端点 + `/health`

---

## 3. In-Scope 逐项对齐审核

> 结论统一使用：`done` / `partial` / `missing` / `stale` / `out-of-scope-by-design`。
> 编号 S1-S7 沿用 final §3.1 In-Scope 顺序；O1-O5 沿用 final §3.2 Out-of-Scope。

### 3.1 In-Scope 7 条对齐

| 编号 | In-Scope 项 | 审查结论 | 说明 |
|------|------------|----------|------|
| S1 | 本地 first-build 工程骨架 | `partial` | 路径基本齐（`pyproject.toml` / `configs/` / `db/migrations/` / `src/` / `tests/` / `scripts/` / `infra/docker/`），但 R6 6 类缺失（`services.py` / `tests/fixtures/` / `tests/fakes/` / 3 yaml / 2 notebook / `infra/systemd/` / `models/pretrained`+`checkpoints/`） |
| S2 | 数据库与插件安装 | `partial` | 6 份 migration 落地，但 R1 schema 与 plan §14.3 系统性漂移（8/22 表字段名/语义漂移，4 状态机无 CHECK）；R2 vec0 维度被压平至 1/3 |
| S3 | 解耦 pipeline | `done`（业务层）/ `partial`（runner 层） | adapter 100% 隔离干净；pipelines 各 step 真"读上一步 artifact 写新 artifact"；但 R10 runner 把 6 步绑死无法 per-step dispatch |
| S4 | 接口化业务流转 | `partial` | API 27 条 vs plan 16 条，11 条 plan 之外；3 条 plan 端点缺失/合并；CLI 13/18 + 4 缺失 + 3 漂移；openapi.md 漏 4 端点（R16） |
| S5 | 日志/报告/状态审计 | `partial` | `jobs` / `job_events` / `artifacts` / `reports` / `eval_metrics` 表都在；`audit/trace` endpoint 跑通；但 R1 `reports` 缺 `subject_type/subject_id/status`；R14 `release_gates` 缺 `status` + audit trace 不读 `policy_events` |
| S6 | Phase-by-phase tests | `partial` | 32/32 §8.2 测试文件存在；92/93 通过；但 R5 marker 形同虚设；R6 §8.3 fixtures/fakes 整树缺失；R10 step-level dispatch 无测试；R15 4 个 mock test 无 cleanup；R11 无 path resolution 测试；R12 无 Docker build/test |
| S7 | 后置安全治理接入点 | `partial` | P1 placeholder 表在；P7 policy + release gate + synthetic metadata + docs 落地；但 R14 状态机降级 + audit trace 不读 policy_events；R1 consent_ledger 字段漂移 → revoke 不可达；P7 仅覆盖 `model_run` release 1/3 时机（recording/speaker 缺失） |

### 3.2 Out-of-Scope 5 条核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 生产级多租户权限系统 | `遵守` | 全 src `grep` 无 auth/middleware；P7 仅本地策略 |
| O2 | 云端训练队列 / Celery / K8s | `遵守` | `grep -r "celery\|kubernetes\|k8s" src/` 0 命中；`runner.py` 是同步阻塞 + 单写 |
| O3 | `vec1` 作为默认向量库 | `遵守` | `vec1_store.py` 是 probe stub，`db/migrations/006_optional_vec1_probe.sql` 全注释 |
| O4 | 实时语音通话替身 | `遵守` | 无 realtime/WebRTC 代码 |
| O5 | 自动下载闭源/受限权重 | `遵守` | `download_models.sh` 是占位脚本，不真下载 |

### 3.3 对齐结论汇总

- **S1 In-Scope partial**：6 类物理缺失 + 1 类 skeleton 偏差
- **S2 In-Scope partial**：R1 + R2 两处重大 schema 漂移
- **S3 In-Scope done（业务层）/ partial（runner 层）**
- **S4 In-Scope partial**：11 条 plan 外端点 + 3 条 plan 缺失 + 4 个 CLI 缺
- **S5 In-Scope partial**：R1 reports 缺 + R14 release_gates 降级
- **S6 In-Scope partial**：5 处 test gap（R5/R6/R10/R11/R12/R15）
- **S7 In-Scope partial**：R14 + R1 + 1/3 时机
- **O1-O5 Out-of-Scope 全部遵守**

> **这更像"骨架完成 + 端到端贯通，但合同（plan）/ schema（001-006）/ 接口（routes_*.py）/ 状态机（states.py）四处未对齐，closure 自评合规但实际多处 soft-evidence"** —— 而不是 completed。

### 3.4 Final recommendation 落地核查（plan §11）

plan §11 一句话："first-build 的实现目标不是"跑通一个模型仓库"，而是让每个音频片段、每次训练、每个输出声音都能被定位、复现、评估和审计。"

- **定位**（locate）：`artifacts.parent_artifact_id` 链 + `job_events` 时间序 + `audit/trace` endpoint——主体成立
- **复现**（reproduce）：`frozen dataset manifest_sha256` + `model_runs.config_json.env_digest` —— 主体成立，但 `env_digest` 字段在 schema 缺、落到 `config_json` JSON 里（schema 不强制）
- **评估**（evaluate）：`eval_metrics` + `eval_samples`（虽然 R1 三向 FK 塌缩）+ `corpus_report` / `baseline_report` / `train_report`——主体成立
- **审计**（audit）：`audit/trace` endpoint + `policy_events` 表 + `release_gates` 表——但 R1 + R14 共同破坏审计完整性

**判定**：plan §11 目标**约 70% 达成**。定位 + 复现 + 评估三块成立；审计有断裂（policy_events 字段漂 + release_gates 状态机降级）。

---

## 4. Final Recommendation 与 blocker

### 4.1 是否允许关闭本轮 review

**不允许**。当前实现不应被标记为 completed。

### 4.2 关闭前必须解决的 blocker（按优先级）

> 来自 finding R1-R16，按 critical-first 排序。

| 优先级 | Blocker | 来自 finding | 估计工时 |
|--------|---------|--------------|----------|
| **P0** | 修 `db/migrations/00{1..6}.sql` 与 plan §14.3 字段对账，输出 `007_reconcile_to_plan.sql` 迁移；同步修 `vec0_store.py` 维度变量化 | R1, R2 | 4-6h |
| **P0** | 改 `Dockerfile.train:1` base image 为 aarch64 + PyTorch 2.7+ / NGC arm64 | R3 | 2-4h（可能需自 build） |
| **P0** | 改两个 Dockerfile 装 `.[cli,db,api,...]` extras | R12 | 0.5h |
| **P1** | 重写 5 份 closure §1 commit 字段为真实 SHA + amend 后值 | R4, R8 | 1h |
| **P1** | 重写 `compose.yaml` 命令，补 init-db + dataset create/freeze 或 init container | R13 | 1-2h |
| **P1** | 加 `domain/services.py` 抽象 api→pipelines 直连；补 4 个 CLI 命令；补 3 个 HTTP route | R6, R7, R16 | 2-3h |
| **P1** | 改 release_gates 加 status 列 + decision_json；改 policy_events 字段为 plan 冻结 6 列 | R14, R1 | 2-3h |
| **P2** | runner.py 加 6-way per-step dispatch | R10 | 1-2h |
| **P2** | 抽 `config.resolve_db_path()` DRY 函数 | R11 | 0.5h |
| **P2** | 补 8 个 adapter real-path NotImplementedError 测试；改 4 个 mock test 用 monkeypatch | R15 | 1h |
| **P2** | 修 test marker taxonomy（删僵尸或补真实 marker） | R5 | 0.5h |
| **P3** | 9 份 closure §3 加 G-MVC owner gate 兑现表 | R7 | 0.5h |
| **P3** | 9 份 closure §4 重新填表（标 6 类缺失为 A/B/C deferred） | R6 | 0.5h |
| **P3** | 扩 `domain/states.py` 覆盖 39 状态值；application 替换裸字符串 | R9 | 2h |

### 4.3 可以后续跟进的 non-blocking follow-up

1. 修 vec0 维度到 plan 冻结值（768/192/384），与真 embedder 同步上线
2. `tests/fixtures/` + `tests/fakes/` 补齐
3. 3 个 pipeline yaml 补齐（`train.rvc.yaml` / `train.sovits.yaml` / `eval.default.yaml`）
4. README + local-setup.md 加 device stack 说明（aarch64 + GB10 + CUDA 13.0）
5. `MOCK_ADAPTERS` 在 README/local-setup 显式文档化
6. openapi.md 补 release-gate 系列 4 端点 + `/health`
7. fix `cli.py:200` 的 `NameError: run_export_dataset` 未导入 bug
8. fix `routes_datasets.py:35` 写 `status="active"` 与 export_dataset 的 "draft→frozen" 状态序列脱节（产生孤儿 dataset 行）
9. fix `domain/policies.py:2` import sqlite3（domain 层不应直接用 SQL）—— 加 Repository 抽象
10. 增加 audit trace 读 policy_events（让 P7 决策进入 audit 流）

### 4.4 建议的二次审查方式

`same reviewer rereview`（同审查员复审）—— 因为 R1 的 schema 迁移是系统性变更，sub-agent 已经把整张对账表搭好，复审可以聚焦在 DB-007 迁移的正确性 + 12 个 blocker 的逐一勾销。

### 4.5 实现者回应入口

请按 `docs/templates/code-review-respond.md` 在本文档 §6 append 回应，不要改写 §0–§5。

---

## 5. 总结

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

**一句话**：first-build 的工程骨架 + 端到端 mock 流程是真的，capstone 测试真贯通 P0-P7；但 **DB schema、状态机、closure 自评、Dockerfile 平台适配、test marker** 五处是"硬问题"，必须先解决 §4.2 的 14 个 blocker 才能进下一阶段。

具体来说：

- **能进下一阶段的部分**：定位 + 复现 + 评估的链已建立；mock 流程在 venv 下 92/93 通过；capstone 集成测试是 first-build 阶段性的硬成果
- **不能进下一阶段的部分**：DB schema 与 plan §14.3 合同错位（影响所有下游 ORM / SQL / audit query）；Dockerfile.train 在本机不可构建（影响所有"上 GPU 跑真训练"路径）；closure 自评的"四元组证据"在 P6/P7/P8 是 soft evidence（影响所有外部审查）
- **本次审查未触及的部分**：
  - 未真跑 `docker compose up`（依赖 base image 拉取 + device 资源；非静态审查范畴）
  - 未做 live/gpu marker 测试（这俩 marker 0 test 是已确认事实）
  - 未审查 9 份 plan vs 9 份 closure 的内容一致性细节（只查了 plan 工作项与 closure claim 的对账）
  - 未审查 plan 之外的"plan 升级历史"与 closure 时间戳关系

---

> 写在最后：9 份 closure 都用 0.5 - 1 小时写完，每份都自我标 ✅ verified。Capstone 测试真端到端跑通 12+ 表与 12 种 artifact —— 这本身是 first-build 阶段性的"硬资产"。**问题不是"骨架不存在"，而是"骨架的合同（plan）已被实现部分重写"**。下一阶段承接者最该知道的，不是"这些 closure 都 verified"，而是"R1 处的 schema 重设计 + R3 处的 Dockerfile 平台不匹配"是必须先解决的真实障碍。
