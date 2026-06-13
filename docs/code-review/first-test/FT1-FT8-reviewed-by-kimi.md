# first-test FT1-FT8 代码审查报告

> 审查对象: `myvoiceclone first-test FT1-FT8 实现、测试、Docker、schema、workflow、FastAPI e2e surface`
> 审查类型: `closure-review | code-review | mixed`
> 审查时间: `2026-06-13`
> 审查人: `Kimi`
> 审查范围:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/closure/first-test/first-test-closure.md` 及 FT1-FT8 子 closure
> - `docs/plan/first-test/FT*.md`
> - `src/myvoiceclone/` 实现、`tests/` 测试、`db/migrations/`、`infra/docker/`
> 对照真相:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/closure/first-test/first-test-closure.md`
> - `docs/eval/first-test/final-input-pack.md`
> 文档状态: `reviewed`

---

## 0. 总结结论

- **整体判断**：FT1-FT8 的代码骨架、默认测试、schema/observability contract、FastAPI surface、evidence pack 已落地且默认 suite 全绿，但**当前不是 e2e-test-ready**：容器无法独立初始化数据库、curate 步骤存在 ImportError、真实训练未消费 dataset、live capstone/HTTP 仅为 skip gate，且 closure 文档的 commit 锚点与实际 HEAD 严重不符。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `docs/closure/first-test/*.md` 全部声称证据基于 `working tree @ 4e4ca3b`，但实际 HEAD 为 `31b4a04`，且 `4e4ca3b` 只是模板提交，与 first-test 实现无关——closure 的审计链不可信。
  2. `src/myvoiceclone/jobs/runner.py:347` 引用不存在的 `myvoiceclone.pipelines.curate.run_curation`，导致 curate job 运行时 `ImportError`，直接阻断预处理主链。
  3. `infra/docker/Dockerfile.preprocess` 与 `Dockerfile.train` 均未 COPY/mount `db/migrations`，容器内执行 `mvc init-db` 会失败，first-test 无法在纯容器环境中启动。

---

## 1. 审查方法与已核实事实

### 对照文档
- `docs/eval/first-test/proposed-planning.md` — FT1-FT8 工作项与测试矩阵
- `docs/closure/first-test/first-test-closure.md` 及 `FT1-preflight-closure.md` .. `FT8-closure-deferred-closure.md`
- `docs/plan/first-test/index.md` 及 `FT1-preflight.md` .. `FT8-closure-deferred.md`
- `docs/closure/first-test/deferred-items-ledger.md`
- `docs/eval/first-test/final-input-pack.md`

### 核查实现
- `src/myvoiceclone/cli.py`
- `src/myvoiceclone/config.py`
- `src/myvoiceclone/jobs/runner.py`
- `src/myvoiceclone/jobs/events.py`
- `src/myvoiceclone/pipelines/curate.py`、`export_dataset.py`、`infer_real.py`、`train.py`、`score.py`、`evaluate.py`
- `src/myvoiceclone/adapters/training/xtts_adapter.py`、`rvc_adapter.py`、`sovits_adapter.py`
- `src/myvoiceclone/api/routes_runs.py`、`routes_jobs.py`、`routes_reports.py`、`schemas.py`
- `src/myvoiceclone/evidence.py`
- `src/myvoiceclone/storage/migrations.py`、`repositories.py`、`artifact_store.py`
- `db/migrations/001_core_schema.sql` .. `008_first_test_observability.sql`
- `infra/docker/Dockerfile.preprocess`、`Dockerfile.train`、`compose.yaml`
- `tests/` 下 FT1-FT8 相关单元/集成/API 测试

### 执行过的验证
- `git -C /mnt/usb/workspace/myvoiceclone rev-parse HEAD` → `31b4a04ac7a6f4040ff01a3226a076a3174a9004`
- `git -C /mnt/usb/workspace/myvoiceclone show --stat 4e4ca3b` → 仅 `docs/templates/*.md`，与 first-test 实现无关
- `./venv/bin/python -m pytest -q` → `139 passed, 1 skipped, 2 deselected, 14 warnings`
- `./venv/bin/python -m pytest tests/integration/test_first_test_capstone.py tests/integration/test_first_test_http_smoke.py -m live -q -rs` → `2 skipped, 1 deselected`
- `./venv/bin/python -m myvoiceclone.evidence validate /mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z --repo-root /mnt/usb/workspace/myvoiceclone` → `{"ok": true}`
- `docker buildx build --check -f infra/docker/Dockerfile.preprocess .` → `Check complete, no warnings found`
- `docker buildx build --check -f infra/docker/Dockerfile.train .` → `Check complete, no warnings found`
- `docker compose -f infra/docker/compose.yaml config` → volumes 映射可解析，数据卷指向 `/mnt/usb/workspace/myvoiceresearch/{db,data,models}`

### 复用 / 对照的既有审查
- 无。本轮审查完全基于子代理的并行代码碰撞与本人的独立复核，未采信其他同事（Kimi/Deepseek/GPT）的现有报告。

### 1.1 已确认的正面事实

- 默认 pytest suite 全绿（`139 passed, 1 skipped, 2 deselected`），FT1-FT8 对应测试基本覆盖 closure 声称的边界。
- schema migration `001-008` 在空 DB 上顺序执行成功，核心表、FK、索引、`job_events.metadata_json`、`artifacts.kind/source_artifact_id/created_by_job_id` 等 first-test 所需字段已落地。
- `evidence.py` 实现了完整的 evidence pack（`manifest.json`、`env.json`、`commands.json`、`db_summary.json`、`artifact_manifest.json`、`trace.json`、`skips.json`、`README.md`），validator 能拒绝 skip-without-reason、empty pack、mock-as-real、repo 内大音频。
- FastAPI `POST /api/runs/{run_id}/audio` 立即把 bytes 写入 artifact 目录并落 DB，不依赖 `UploadFile` 临时对象；`start preprocess/infer/eval` 仅创建 DB job 并返回 job id，不直接执行长任务，符合 proposed-planning TR-4。
- `pytest.ini` 正确排除 `live/gpu/slow` marker，evidence pack 的 `skip_denominator` 记录了 skipped 原因。
- mock/real 在 artifact metadata 与 eval metric metadata 中有明确 `adapter_mode`/`metric_source` 标记，未发现 silent mock fallback。

### 1.2 已确认的负面事实

- 全部 closure 文档使用 `working tree @ 4e4ca3b` 作为证据锚点，与实际 HEAD `31b4a04` 不一致；`4e4ca3b` 本身不包含任何 first-test 实现代码。
- `src/myvoiceclone/jobs/runner.py:347` 的 curate 步骤引用未定义的 `run_curation`，会导致 `ImportError`。
- Dockerfile 未 COPY/mount `db/migrations`，容器内无法完成数据库初始化。
- 仓库根目录缺少 `.dockerignore`，Docker build context 会卷入 `venv/`、`data/`、`.git/`、`db/`、`models/` 等目录。
- `Dockerfile.train` 在 NGC PyTorch 镜像中重复安装 `torchaudio`，存在破坏预装 CUDA 约束的风险。
- `tests/integration/test_first_test_capstone.py:53-58` 在设置 `RUN_FIRST_TEST_CAPSTONE=1` 后仍因 "owner-provided model/cache/token configuration" skip，没有真实 capstone 执行体。
- `tests/integration/test_first_test_http_smoke.py:6-8` 仅有 env gate，没有真实 uvicorn HTTP socket 测试。
- `src/myvoiceclone/pipelines/train.py` 的 SoVITS/RVC 真实训练未实现，使用 fake bytes；`run_real_inference` 仅接 XTTS，未按 `model_id` engine 类型路由。
- DB schema 与 `docs/eval/first-build/final-execution-plan.md` §14.3 存在多处命名/索引/约束漂移（`job_events.level`、`jobs.error`、`release_gates.report_id/decided_at` 等）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 所有关键发现均标注 `file:line`，closure/proposed-planning 中对应条目已逐条核对 |
| 本地命令 / 测试 | yes | 已运行全量 pytest、live marker 测试、evidence validate、docker buildx --check、docker compose config |
| schema / contract 反向校验 | yes | 已检查 migrations SQL、临时 DB PRAGMA、schema drift 测试、API contract fixture |
| live / deploy / preview 证据 | yes | 检查了 skipped evidence pack 目录与 validator；未执行真实模型 live capstone（环境不支持） |
| 与上游 design / QnA 对账 | yes | 逐条对照 proposed-planning FT1.1-FT8.4 与 closure 声称 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | closure commit 锚点与实际 HEAD 不符 | high | docs-gap | yes | 修正所有 closure 为真实 HEAD，补充 `git rev-parse HEAD` 证据 |
| R2 | Docker 镜像缺少 `db/migrations` 导致容器内 init-db 失败 | high | platform-fitness | yes | Dockerfile COPY `db/migrations` 或 compose mount；推荐两者都做 |
| R3 | curate job 引用未定义的 `run_curation` | high | correctness | yes | 实现 `run_curation` 或从 runner 移除该 step |
| R4 | Dockerfile.train 在 NGC 镜像上重复安装 torchaudio 可能破坏 CUDA | high | platform-fitness | yes | 使用 NGC pip constraint 或拆分 audio extra，避免覆盖预装 torch |
| R5 | 缺少 `.dockerignore`，build context 可能卷入大文件 | high | security | yes | 新增 `.dockerignore` 排除 `venv/`, `data/`, `db/*.sqlite`, `models/`, 音频/模型文件 |
| R6 | evidence 导出目录未挂载到容器 | medium | platform-fitness | yes | compose 增加 `/mnt/usb/workspace/myvoiceresearch/test-runs` 挂载 |
| R7 | FT7 live capstone 只有 skip gate，无真实执行体 | high | test-gap | yes | 实现最小真实链路或明确 deferred 并补充 owner 交付 checklist |
| R8 | FT6 live HTTP 测试只有 env gate | medium | test-gap | no | 实现 uvicorn + httpx 真实 HTTP smoke |
| R9 | 真实训练未消费 dataset manifest，使用 fake bytes | high | scope-drift | no | 训练 adapter 真实读取 frozen manifest 并按 SoVITS/RVC 目录结构准备数据 |
| R10 | real inference 仅支持 XTTS，未按 model_id 路由 | medium | correctness | no | 根据 engine 类型路由或 schema 限制 model_id |
| R11 | score/objective 存在硬编码 mock 值且未自动接入 smoke | medium | test-gap | no | 自动调用 smoke evaluator，mock 值显式标记 `metric_source=mock` |
| R12 | DB schema 与 final-execution-plan 存在命名/索引/约束漂移 | medium | protocol-drift | no | 通过 migration alias 或新增 migration 补齐 plan canonical 列/索引/CHECK |
| R13 | API response contract snapshot 过浅 | low | test-gap | no | 升级为完整 JSON snapshot，覆盖 upload/start/status/report/trace |
| R14 | runner/API 异常时未自动收集 evidence pack | medium | platform-fitness | no | 在 runner except/finally 或全局异常处理器中调用 `collect_evidence_pack` |
| R15 | action-plan 中部分测试文件名与实际路径不一致 | low | docs-gap | no | 更新 FT1/FT2 action plan 测试台账 |

### R1. closure commit 锚点与实际 HEAD 不符

- **严重级别**：high
- **类型**：docs-gap
- **是否 blocker**：yes
- **事实依据**：
  - `docs/closure/first-test/first-test-closure.md:28-35` 及所有子 closure 表头均声称证据为 `working tree @ 4e4ca3b`。
  - 实际 `git rev-parse HEAD` = `31b4a04ac7a6f4040ff01a3226a076a3174a9004`。
  - `git show --stat 4e4ca3b` 显示该提交仅新增 `docs/templates/*.md`，与 first-test 实现无关；`git diff 4e4ca3b..HEAD --stat` 显示 FT1-FT8 全部代码/测试/文档均在此后提交。
- **为什么重要**：closure 的核心纪律要求“证据为四元组（commit + query/test + run-time）”。错误的 commit 锚点导致所有 closure 的审计链失效，无法从文档追溯到真实实现提交。
- **审查判断**：closure evidence 不可信；implementation 本身存在且默认测试通过，但文档严重失实。
- **建议修法**：
  1. 将所有 closure 文件中的 `working tree @ 4e4ca3b` 改为 `HEAD @ 31b4a04`（或本轮实际最终提交 hash）。
  2. 在 closure 中补充 `git rev-parse HEAD` 与 `git status --short` 的原始输出作为证据附件。

### R2. Docker 镜像缺少 `db/migrations` 导致容器内 init-db 失败

- **严重级别**：high
- **类型**：platform-fitness
- **是否 blocker**：yes
- **事实依据**：
  - `infra/docker/Dockerfile.preprocess:13-14` 与 `Dockerfile.train:18-19` 仅 `COPY pyproject.toml ./` 与 `COPY src/ ./src/`。
  - `src/myvoiceclone/cli.py:40-48` 的 `init-db` 需要读取 `db/migrations` 目录，该目录既未 COPY 进镜像，也未在 `infra/docker/compose.yaml` 中挂载。
- **为什么重要**：first-test 的任何容器化运行都依赖可初始化的数据库；无法 `init-db` 意味着无法通过纯容器完成 FT1 准入。
- **审查判断**：Docker 容器无法独立唤醒 first-test。
- **建议修法**：
  1. 在两个 Dockerfile 中增加 `COPY db/migrations ./db/migrations`。
  2. 在 `compose.yaml` 两个服务下增加 bind mount `./db/migrations:/app/db/migrations`，便于开发时热更新。

### R3. curate job 引用未定义的 `run_curation`

- **严重级别**：high
- **类型**：correctness
- **是否 blocker**：yes
- **事实依据**：
  - `src/myvoiceclone/jobs/runner.py:347` 定义 `_execute_step_curate` 并执行 `from myvoiceclone.pipelines.curate import run_curation`。
  - `src/myvoiceclone/pipelines/curate.py` 中不存在 `run_curation` 函数（仅有 `run_deduplication` 与 `update_segment_status`）。
- **为什么重要**：proposed-planning FT3/FT5 要求 curation/dedup 是预处理与 release gate 的前置；该步骤若运行时 `ImportError`，会阻断从预处理到 dataset freeze 的主链。
- **审查判断**：预处理 workflow 存在实际断点。
- **建议修法**：
  - 方案 A：在 `curate.py` 中实现 `run_curation(conn, artifact_store, recording_id, ...)`，内部调用 `run_deduplication` 与 `update_segment_status`。
  - 方案 B：若 first-test 暂不需要 curate step，从 `runner.py` 中移除该 step，并在 action-plan 中明确 deferred。

### R4. Dockerfile.train 在 NGC 镜像上重复安装 torchaudio 可能破坏 CUDA

- **严重级别**：high
- **类型**：platform-fitness
- **是否 blocker**：yes
- **事实依据**：
  - `infra/docker/Dockerfile.train:23` 执行 `pip install --no-cache-dir ".[cli,db,api,audio]"`。
  - `pyproject.toml:20` 的 `[project.optional-dependencies] audio = ["soundfile", "torchaudio"]` 未加版本约束。
  - NGC PyTorch 25.03 镜像已预装 torch/torchaudio/cuDNN/CUDA，并配有 `/etc/pip/constraint.txt`；无约束安装 `torchaudio` 可能触发版本升级/降级，破坏 CUDA 环境。
- **为什么重要**：训练容器若 CUDA 环境被破坏，真实训练与 GPU live capstone 均无法运行。
- **审查判断**：训练容器存在潜在运行时风险。
- **建议修法**：
  - 方案 A：在 Dockerfile.train 中单独安装 `soundfile`，不再安装 `torchaudio`（依赖 NGC 预装）。
  - 方案 B：使用 NGC pip constraint：`PIP_CONSTRAINT=/etc/pip/constraint.txt pip install --no-cache-dir ".[cli,db,api,audio]"`。
  - 方案 C：拆出 `audio` extra，训练镜像仅安装 `soundfile`，并验证 `torchaudio` 已随 NGC 预装。

### R5. 缺少 `.dockerignore`，build context 可能卷入大文件

- **严重级别**：high
- **类型**：security / platform-fitness
- **是否 blocker**：yes
- **事实依据**：
  - 仓库根目录不存在 `.dockerignore`。
  - `du -sh data db models venv .git` 显示 `venv 56M`、`data 7.6M`、`.git 4.5M`、`models 20K`。
- **为什么重要**：用户若将真实音频/模型权重放入仓库默认目录，`docker build` 会把这些大文件打包进构建上下文，违反“大数据不得暴露在宿主机的硬盘/repo”原则，也会拖慢 build/push。
- **审查判断**：构建上下文存在数据暴露与性能风险。
- **建议修法**：新增 `.dockerignore`，至少排除：
  ```gitignore
  .git/
  venv/
  .venv/
  __pycache__/
  .pytest_cache/
  data/
  db/*.sqlite
  db/*.db
  models/
  *.wav *.mp3 *.flac *.m4a *.ogg *.opus
  *.pth *.pt *.ckpt *.onnx
  ```
  注意保留 `db/migrations/` 不要被 `db/` 全目录排除。

### R6. evidence 导出目录未挂载到容器

- **严重级别**：medium
- **类型**：platform-fitness
- **是否 blocker**：yes（针对 first-test evidence 流程）
- **事实依据**：
  - `src/myvoiceclone/evidence.py:16` 默认输出根目录为 `/mnt/usb/workspace/myvoiceresearch/test-runs`。
  - `infra/docker/compose.yaml` 的 `preprocess`/`train` 服务仅挂载 `db`、`data`、`models` 卷，未挂载 `test-runs`。
- **为什么重要**：若在容器内调用 evidence 收集，结果会写入容器可写层，容器退出即丢失，FT7 evidence pack 无法持久化。
- **审查判断**：容器化证据流程不完整。
- **建议修法**：在两个服务中增加 `- /mnt/usb/workspace/myvoiceresearch/test-runs:/mnt/usb/workspace/myvoiceresearch/test-runs`，或新增环境变量 `EVIDENCE_ROOT=/app/data/test-runs` 并挂载对应路径。

### R7. FT7 live capstone 只有 skip gate，无真实执行体

- **严重级别**：high
- **类型**：test-gap
- **是否 blocker**：yes
- **事实依据**：
  - `tests/integration/test_first_test_capstone.py:30-58` 在设置 `RUN_FIRST_TEST_CAPSTONE=1` 与合法 `FIRST_TEST_AUDIO_PATH` 后，仍在 `pytest.skip("... owner-provided model/cache/token configuration ...")` 退出。
  - 没有实现 proposed-planning FT7.3 / T-FT7.3 要求的“真实音频 → preprocess → real inference → eval → release → trace”链路。
- **为什么重要**：first-test 的核心目标是“真实 e2e 闭环”。当前只能证明“缺依赖时 skip”，不能证明“提供依赖后能跑通”。
- **审查判断**：真实 capstone 执行体缺失。
- **建议修法**：
  1. 若资源允许，实现一条最小真实链路（CPU/短音频），让 `RUN_FIRST_TEST_CAPSTONE=1` 时真正跑通并生成非 skipped evidence。
  2. 若暂不能执行真实模型，将 FT7.3 明确 deferred 到 `live-verification` 阶段，并在 `deferred-items-ledger.md` 中补充 owner 交付 checklist（模型/cache/token/license/合法音频样本）。

### R8. FT6 live HTTP 测试只有 env gate

- **严重级别**：medium
- **类型**：test-gap
- **是否 blocker**：no
- **事实依据**：
  - `tests/integration/test_first_test_http_smoke.py:6-8` 仅检查 `RUN_LIVE_HTTP=1` 环境变量，否则 skip；没有 uvicorn 启动、upload→start→poll→report 的真实 socket 测试。
- **为什么重要**：TestClient 路径不能替代真实 HTTP socket/端口/序列化路径；缺少 live HTTP 证据意味着 FastAPI e2e 的 runtime surface 未经验证。
- **审查判断**：与 proposed-planning T-FT6.7 存在差距。
- **建议修法**：实现最小 uvicorn + httpx 直播 spike；或明确降级为 deferred 并记录触发条件。

### R9. 真实训练未消费 dataset manifest，使用 fake bytes

- **严重级别**：high
- **类型**：scope-drift
- **是否 blocker**：no（first-test 可选不实现真实训练，但需诚实标记）
- **事实依据**：
  - `src/myvoiceclone/pipelines/train.py:269` 的 `run_prepare_features` 返回 `b"fake_hubert_content..."`。
  - `src/myvoiceclone/pipelines/train.py:415` 的最终 rendered sample 为 `b"fake_sovits_rendered_audio_wav_data"`。
  - `src/myvoiceclone/pipelines/train.py:288-438` 未读取 dataset manifest 中的音频路径作为训练输入。
- **为什么重要**：proposed-planning 的 O1 允许 first-test 不实现全部真实训练，但若代码中存在 fake bytes 冒充训练输出，必须有清晰的 `adapter_mode=mock` 标记，否则 release gate 可能误判为真实结果。
- **审查判断**：训练阶段的真实链路未闭环。
- **建议修法**：
  - 若真实训练 out-of-scope，确保所有 fake bytes 路径显式标记 `adapter_mode=mock` 并阻止 `release gate quality pass`。
  - 若进入真实训练，实现 `prepare()` 将 frozen manifest 音频按 SoVITS/RVC 目录结构展开并真实消费。

### R10. real inference 仅支持 XTTS，未按 model_id 路由

- **严重级别**：medium
- **类型**：correctness
- **是否 blocker**：no
- **事实依据**：
  - `src/myvoiceclone/pipelines/infer_real.py:45` 对任意 `model_id` 都实例化 `XttsAdapter`。
  - `src/myvoiceclone/api/schemas.py` 的 inference request 未限制 `model_id` 必须为 XTTS。
- **为什么重要**：调用方传入 RVC/SoVITS `model_id` 时，行为与请求不符，违反 proposed-planning FT4.1 的 substrate contract。
- **审查判断**：推理 substrate contract 未完全收敛。
- **建议修法**：根据 `model_id` engine 类型路由到对应 adapter，或在 schema 层限制 `model_id` 仅支持已实现的 substrate 并返回 400。

### R11. score/objective 存在硬编码 mock 值且未自动接入 smoke

- **严重级别**：medium
- **类型**：test-gap
- **是否 blocker**：no
- **事实依据**：
  - `src/myvoiceclone/pipelines/score.py:39-42` 硬编码 `noise_score=0.9`、`overlap_score=1.0`、`speaker_score=0.85`。
  - `src/myvoiceclone/eval/objective.py:66-77` 写死 mock 指标（`speaker_similarity=0.84` 等）。
  - `src/myvoiceclone/pipelines/evaluate.py` 的 `run_evaluation` 只调用 objective，未调用 `eval/smoke.py`。
- **为什么重要**：proposed-planning FT5 要求 smoke metrics 与 objective proxy 分层，且 smoke 应作为自动门控；当前自动评估链路缺失 smoke 层。
- **审查判断**：评估层未按规划有机整合。
- **建议修法**：
  1. 在 `run_evaluation` 中串联 `smoke → objective → subjective`。
  2. 在 `run_real_inference` 与 `run_train_*` 输出后自动调用 `evaluate_wav_smoke`，结果写入 `eval_metrics.metric_json`。
  3. 硬编码 mock 值必须显式标记 `metric_source=mock`（当前部分已做，但 `score.py` 未标记）。

### R12. DB schema 与 final-execution-plan 存在命名/索引/约束漂移

- **严重级别**：medium
- **类型**：protocol-drift
- **是否 blocker**：no
- **事实依据**：
  - `db/migrations/002_state_jobs_artifacts.sql:13-22` 的 `job_events` 使用 `status_from/status_to/message/metadata_json`，而 plan 期望 `level`、`message`、`payload_json`。
  - `db/migrations/007_reconcile_to_plan.sql:43` 的 `jobs` 使用 `error_msg`，plan 期望 `error`。
  - `db/migrations/007_reconcile_to_plan.sql:216-226` 的 `release_gates` 缺少 plan 期望的 `report_id` 与 `decided_at`（当前为 `approved_at`）。
  - `db/migrations/007_reconcile_to_plan.sql:76-89` 的 `artifacts` 索引为 `idx_artifacts_created_by_job` + `idx_artifacts_kind`，plan 期望复合索引 `(created_by_job_id, kind)`。
- **为什么重要**：first-test 先用 JSON 降级承载 metadata 是允许的，但与 plan 的 canonical schema 不一致会增加后续 reconciliation 成本。
- **审查判断**：功能可用，但 schema 尚未严格对齐长期基线。
- **建议修法**：
  - 通过 `GENERATED ALWAYS AS` 别名在 migration 中兼容 plan 列名。
  - 补齐 `release_gates.report_id`、`decided_at`、复合索引、CHECK 约束。
  - 收紧 `jobs.status` / `model_runs.status` CHECK 到 plan canonical 值。

### R13. API response contract snapshot 过浅

- **严重级别**：low
- **类型**：test-gap
- **是否 blocker**：no
- **事实依据**：
  - `tests/api/contracts/first_test_run_create.json:1-4` 仅校验 `required_keys` 与 `links` 存在，未覆盖字段类型、枚举值、完整 JSON 结构。
- **为什么重要**：proposed-planning T-FT6.6 要求 response schema snapshot，breaking change 需显式更新 contract fixture；当前 contract 无法防止字段漂移。
- **审查判断**：contract 测试形态有，但校验力度不足。
- **建议修法**：把 contract 升级为完整 snapshot（排除动态值如 `id`、`created_at`），或引入 `pytest-snapshot`/`inline-snapshot` 管理。

### R14. runner/API 异常时未自动收集 evidence pack

- **严重级别**：medium
- **类型**：platform-fitness
- **是否 blocker**：no
- **事实依据**：
  - `src/myvoiceclone/jobs/runner.py:69-140` 在失败时把 error 写入 `job_events`，但不会自动调用 `collect_evidence_pack()`。
  - API 层异常也没有全局证据收集。
- **为什么重要**：proposed-planning FT7.2 要求 evidence pack 供 debug；错误现场若只依赖 DB，排查者需要额外导出，不符合“标准可观测数据文件”要求。
- **审查判断**：可观测性文件输出需补强。
- **建议修法**：在 `JobRunner.run()` 的 `except/finally` 或 FastAPI 全局异常处理器中调用 `collect_evidence_pack(skip_reason=...)`，确保错误现场自动落盘。

### R15. action-plan 中部分测试文件名与实际路径不一致

- **严重级别**：low
- **类型**：docs-gap
- **是否 blocker**：no
- **事实依据**：
  - `docs/plan/first-test/FT1-preflight.md` 列出 `tests/cli/test_preprocess_entry.py`、`tests/api/test_preprocess_jobs.py`、`tests/api/test_job_artifact_root.py`。
  - 实际测试分别位于 `tests/cli/test_cli.py`、`tests/api/test_routes.py`、`tests/api/test_first_test_preflight.py`。
- **为什么重要**：action plan 是执行基线，文件名不一致会造成审计困惑。
- **审查判断**：功能已覆盖，文档过时。
- **建议修法**：更新 FT1/FT2 action plan 的测试台账，使其与实际文件路径一致。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / closure claim | 审查结论 | 说明 |
|------|------------------------|----------|------|
| S1 | FT1.1 统一命令与文档入口 | done | `myvoiceclone --help` 测试通过；README 使用 `myvoiceclone` |
| S2 | FT1.2 live bootstrap 安装 extras / 依赖探针 | done | `test_scripts_dry_run.py` 通过；脚本包含 `[first-test]` 与 ffmpeg/ffprobe 探针 |
| S3 | FT1.3 `.env.example` 与 config 对齐 | done | `DB_PATH/ARTIFACT_ROOT/MODELS_DIR/MOCK_ADAPTERS` 解析一致 |
| S4 | FT1.4 CLI preprocess payload 修复 | done | `test_cli.py::test_cli_preprocess_all_payload` 通过 |
| S5 | FT1.5 API 创建 preprocess job 最小入口 | done | `test_routes.py::test_create_preprocess_job` 通过 |
| S6 | FT1.6 empty manifest guard | done | `test_export_dataset.py::test_export_dataset_refuses_empty_manifest` 通过 |
| S7 | FT1.7 API artifact root resolver | done | `test_first_test_preflight.py::test_run_job_uses_env_artifact_root` 通过 |
| S8 | FT2.1 schema drift inventory | done | `test_schema_drift.py::test_first_test_schema_inventory` 通过 |
| S9 | FT2.2 SQLite pragma 边界 | done | `test_sqlite_connection.py` 通过 |
| S10 | FT2.3 step-level `job_events` contract | done | `test_runner.py` 通过；migration 008 新增 `metadata_json` |
| S11 | FT2.4 adapter metadata contract | done | `test_artifact_observability.py` 通过 |
| S12 | FT2.5 segment failure summary 上卷 | done | `test_runner.py::test_job_runner_success_preprocess` 覆盖 |
| S13 | FT2.6 audit trace completeness | done | `test_audit_trace.py` 通过 |
| S14 | FT2.7 mock/real evidence separation | done | `test_objective.py` 与 evidence validator 拒绝 mock-as-real |
| S15 | FT3.1 FFmpeg probe/normalize contract | done | `test_ffmpeg_adapter.py` 通过 |
| S16 | FT3.2 PyAnnote preflight / skip reason | done | `test_pyannote_adapter.py` 通过；无 token 时 skip |
| S17 | FT3.3 Demucs optional path / caveat | done | `test_demucs_adapter.py` 通过 |
| S18 | FT3.4 Whisper ASR contract | done | `test_whisper_adapter.py` 通过 |
| S19 | FT3.5 dataset create/freeze 使用真实预处理产物 | partial | unit/integration 通过，但缺少 proposed T-FT3.5 的 integration smoke |
| S20 | FT3.6 reference artifact selector contract | done | `test_reference_select.py` 通过 |
| S21 | FT4.1 推理 input/output contract | done | `test_real_inference_wrapper.py` 通过 |
| S22 | FT4.2 no mock fallback | done | `test_xtts_adapter.py::test_xtts_real_mode_no_mock_fallback` 通过 |
| S23 | FT4.3 真实 adapter wrapper | done | `test_real_inference_wrapper.py` 通过 |
| S24 | FT4.4 model manifest/cache/license | done | `test_xtts_adapter.py::test_xtts_model_manifest_records_license` 通过 |
| S25 | FT4.5 推理输出 artifact metadata | done | `test_real_inference_wrapper.py` 通过 |
| S26 | FT4.6 CLI / live real inference smoke | partial | CLI smoke 通过；live/slow real inference integration test 缺失 |
| S27 | FT5.1 metric taxonomy | done | `test_objective.py` / `test_smoke_metrics.py` 通过 |
| S28 | FT5.2 smoke evaluator | done | `test_smoke_metrics.py` 通过 |
| S29 | FT5.3 objective proxy unavailable 语义 | done | `test_objective.py::test_objective_proxy_unavailable_is_explicit` 通过 |
| S30 | FT5.4 subjective MOS/ABX intake | done | `test_subjective.py` / `test_routes.py::test_subjective_report_endpoint` 通过 |
| S31 | FT5.5 release gate 分层 | done | `test_release_gate.py::test_release_gate_blocks_mock_metrics` 通过 |
| S32 | FT5.6 eval report 关联 artifact/metric source/adapter mode | done | `test_audit_trace.py` / `test_routes.py` 通过 |
| S33 | FT6.1 first-test run API contract | done | `test_first_test_runs.py::test_create_run_contract_snapshot` 通过 |
| S34 | FT6.2 upload 立即写 artifact | done | `test_first_test_runs.py::test_upload_audio_immediately_writes_artifact` 通过 |
| S35 | FT6.3 start preprocess/infer/eval 创建 DB job | done | `test_first_test_runs.py::test_start_jobs_reference_artifact_ids` 通过 |
| S36 | FT6.4 status API 聚合 events/artifacts/failure | done | `test_first_test_runs.py::test_run_status_aggregates_events_artifacts_and_failures` 通过 |
| S37 | FT6.5 report/release/trace 查询 API | done | `test_audit_trace.py` 通过 |
| S38 | FT6.6 response contract fixture | partial | contract fixture 存在但校验过浅 |
| S39 | FT6.7 live HTTP spike | partial | 只有 env gate，无真实 HTTP 调用 |
| S40 | FT7.1 live/slow/gpu marker policy / denominator | done | `test_pytest_markers.py` 通过；`pytest.ini` 默认排除 live/gpu/slow |
| S41 | FT7.2 evidence exporter | done | `test_first_test_evidence_validator.py` 通过；外部 evidence pack 存在 |
| S42 | FT7.3 API capstone live chain | missing | 只有 skip gate，无真实 e2e 执行体 |
| S43 | FT7.4 FT1-FT6 required test gate | partial | 仅检查 closure 文件存在，未验证测试通过状态 |
| S44 | FT7.5 evidence validator | done | `test_first_test_evidence_validator.py` 覆盖 skip/empty/mock-as-real/large repo audio |
| S45 | FT8.1 first-build deferred reconciliation | done | `docs/closure/first-build/deferred-items-ledger.md` 包含 reconciliation snapshot |
| S46 | FT8.2 first-test closure ledger | done | `first-test-closure.md` 存在，close type 与 FT7 skipped evidence 一致 |
| S47 | FT8.3 retained deferred 边界说明 | done | `deferred-items-ledger.md` FTD-01..FTD-10 均有触发器与目标阶段 |
| S48 | FT8.4 proposed→final input pack | done | `final-input-pack.md` 存在且引用文件均存在 |

### 3.1 对齐结论

- **done**: 38
- **partial**: 6
- **missing**: 1
- **stale**: 0
- **out-of-scope-by-design**: 0

> 这更像“**实现骨架与默认测试已完成，但容器化唤醒、真实训练/推理链路、live capstone 仍未收口**”，而不是 proposed-planning 所要求的 e2e-test-ready 状态。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 同时实现 RVC/SoVITS/XTTS 全部真实训练 | 遵守 | first-test 仅要求一条真实推理闭环；RVC/SoVITS 真实训练已诚实 deferred |
| O2 | 完整 ECAPA/CLAP/SBERT embedding 平台与 vec0 全维度迁移 | 遵守 | vec0 128-d mock boundary 已记录为 deferred |
| O3 | 生产级任务队列与分布式 worker | 遵守 | FastAPI 仅创建 DB job，未引入队列 |
| O4 | 完整 OTel 平台化接入 | 遵守 | 仅借 OTel vocabulary，落 DB events/trace JSON |
| O5 | 众包平台 MOS 流程 | 遵守 | 仅本地 MOS/ABX 表单 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**：修正所有 closure 文档的 commit 锚点为真实 HEAD `31b4a04`，并补充 `git rev-parse HEAD` / `git status --short` 原始输出。
  2. **R2**：Dockerfile 与 compose 必须让容器内可访问 `db/migrations`，使 `mvc init-db` 在容器内可用。
  3. **R3**：修复 `runner.py:347` 的 curate step ImportError（实现 `run_curation` 或从 runner 移除）。
  4. **R4**：修复 `Dockerfile.train` 中 torchaudio 与 NGC 预装 CUDA 的冲突风险。
  5. **R5**：新增 `.dockerignore`，防止大数据被打包进 build context。
  6. **R6**：compose 中挂载 evidence 输出目录 `/mnt/usb/workspace/myvoiceresearch/test-runs`。
  7. **R7**：明确 FT7 live capstone 状态——要么实现最小真实执行体，要么正式 deferred 并补充 owner 交付 checklist。
- **可以后续跟进的 non-blocking follow-up**：
  1. **R8**：实现 `RUN_LIVE_HTTP=1` 下的真实 uvicorn HTTP smoke。
  2. **R9/R10**：训练真实消费 dataset manifest、real inference 按 engine 路由。
  3. **R11**：评估链路串联 smoke → objective → subjective，并自动调用 smoke gate。
  4. **R12**：逐步用 migration alias/新增 migration 对齐 final-execution-plan canonical schema。
  5. **R13**：升级 API response contract 为完整 JSON snapshot。
  6. **R14**：runner/API 异常时自动落盘 evidence pack。
  7. **R15**：更新 action-plan 测试台账与实际文件路径一致。
- **建议的二次审查方式**：`independent reviewer rereview`
- **实现者回应入口**：请按 `docs/templates/code-review-respond.md` 在本文档 §6 append 回应，不要改写 §0–§5。

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码与 closure 文档。
