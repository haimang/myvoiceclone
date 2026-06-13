# FT1-FT8 review verified-findings ledger

> **审查标的** | `myvoiceclone first-test FT1-FT8`
> **审查阶段 / 轮次** | `第 1 轮合并`
> **合并 / 核查人（实现者）** | `Codex`
> **合并日期** | `2026-06-13`
> **文档状态** | `resolved`

**审查来源锚定**：
- `docs/code-review/first-test/FT1-FT8-reviewed-by-deepseek.md` — 8 findings，最高 `critical`
- `docs/code-review/first-test/FT1-FT8-reviewed-by-kimi.md` — 15 findings，最高 `high`

**对照真相**：
- `docs/eval/first-test/proposed-planning.md`
- `docs/eval/first-test/reference-anchor.md`
- `docs/plan/first-test/index.md`
- `docs/closure/first-test/first-test-closure.md`
- `src/myvoiceclone/`, `tests/`, `db/migrations/`, `infra/docker/`

---

## 0. 合并方法与核查纪律

- **合并范围**：2 份独立审查共 23 条 raw findings，合并为 21 条 unified findings。
- **核查纪律**：
  1. reviewer 结论只作线索，所有 `valid*` 均已对当前真实代码 grep/read。
  2. 冲突处以当前实测为准；例如 Kimi 关于 HEAD `31b4a04` 的判断在本仓属实。
  3. 同类问题取多方最严严重级别。
  4. `[true-bug]` 与 `[partial-delivery]` 默认本轮修复；真实 live/model/owner 环境项进入 deferred ledger。

## 1. 一句话裁定 + 合并统计

- **一句话裁定**：2 方第 1 轮 23 条 raw findings 合并为 21 条；其中 12 条本轮修复，7 条有理由 deferred，1 条 acknowledge，1 条 stale-rejected；最关键缺口是 runner 调度断点、Docker/evidence 容器化缺口、closure 锚点失真。
- **合并后统一 finding 数**：21
- **按 verdict**：`valid 13` · `valid-conditional 2` · `valid-owner-gated 3` · `valid(子项 overstated) 2` · `stale-rejected 1`
- **按三类归属**：`[true-bug] 8（V1,V2,V3,V4,V6,V7,V8,V12）` · `[partial-delivery] 4（V5,V9,V13,V15）` · `[true-deferred] 7（V10,V11,V14,V16,V17,V18,V19）` · `n/a 2（V20,V21）`
- **按处置**：`fix 12` · `partial-fix 0` · `defer 7` · `ack 1` · `stale-rejected 1`
- **blocker 数**：0 after planned fixes；pre-fix blockers were V1,V2,V3,V4,V6,V7,V8,V12。
- **净增承重盲区**：peer reviews caught runner dispatch gaps (`infer_real`/`eval_first_test`), Docker container boot gaps, and invalid closure evidence anchors that earlier closure self-review missed.

## 2. 合并映射（reviewer finding → 统一编号）

| 来源 finding | 合并到 | 合并后问题 |
|--------------|--------|------------|
| DeepSeek-R1 / Kimi-R3 | V1 | `run_curation` missing, curate job ImportError |
| DeepSeek-R2 | V2 | runner does not dispatch `infer_real` / `eval_first_test` |
| DeepSeek-R3 / Kimi-R11 | V3 | eval orchestration/CLI still writes mock values and does not run smoke/objective path |
| Kimi-R1 | V4 | closure evidence anchor uses stale `4e4ca3b` instead of current HEAD |
| Kimi-R2 | V5 | Docker images cannot access `db/migrations` for `init-db` |
| Kimi-R4 | V6 | train Dockerfile installs unconstrained `torchaudio` on NGC image |
| Kimi-R5 | V7 | missing `.dockerignore`, build context can include local data/models/venv |
| Kimi-R6 | V8 | evidence output root not mounted in compose |
| DeepSeek-R6 | V9 | compose mounts configs read-write |
| Kimi-R7 | V10 | FT7 live capstone has only gated/deferred execution |
| Kimi-R8 | V11 | FT6 live HTTP test only gates, no real socket body |
| DeepSeek-R5 | V12 | `service_train_rvc` passes args unsupported by `run_train_rvc` |
| Kimi-R10 | V13 | real inference accepts arbitrary `model_id` but only supports XTTS |
| Kimi-R9 | V14 | real training does not consume dataset manifest; fake bytes remain |
| Kimi-R13 | V15 | API contract fixture is too shallow |
| DeepSeek-R7 / Kimi-R14 | V16 | evidence pack does not automatically capture stdout/stderr/stack traces |
| DeepSeek-R4 | V17 | logging coverage is thin outside runner/storage |
| Kimi-R12 | V18 | DB schema differs from first-build final-execution-plan canonical names |
| DeepSeek-R8 | V19 | `pipeline_runs` remains unwired |
| Kimi-R15 | V20 | some action-plan test filenames are stale |
| Kimi S43 | V21 | FT7 pre-capstone gate checks closure files, not test results |

## 3. verified-findings 台账

| V# | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据 | 初步处置 |
|----|------|------|------|----------|--------|----------|----------|
| V1 | `run_curation` missing | critical | DeepSeek/Kimi | valid | `[true-bug]` | `src/myvoiceclone/jobs/runner.py` imports `run_curation`; `src/myvoiceclone/pipelines/curate.py` lacks it | fix |
| V2 | runner lacks `infer_real`/`eval_first_test` dispatch | critical | DeepSeek | valid | `[true-bug]` | `routes_runs.py` creates both job names; `JobRunner.run()` does not dispatch them | fix |
| V3 | eval orchestration/CLI mock values | high | DeepSeek/Kimi | valid | `[true-bug]` | `pipelines/evaluate.py` only calls objective; `cli.py eval` inserts `0.85/0.07` | fix |
| V4 | closure evidence anchor stale | high | Kimi | valid | `[true-bug]` | `git rev-parse HEAD` = `31b4a04`; closures cite `working tree @ 4e4ca3b` | fix |
| V5 | Docker images lack migrations | high | Kimi | valid | `[partial-delivery]` | Dockerfiles copy only `pyproject.toml` and `src/`; `init-db` reads `db/migrations` | fix |
| V6 | train image torchaudio risk | high | Kimi | valid-conditional | `[true-bug]` | `Dockerfile.train` installs `.[cli,db,api,audio]`; `audio` includes unconstrained `torchaudio` | fix |
| V7 | missing `.dockerignore` | high | Kimi | valid | `[true-bug]` | repository root has no `.dockerignore` | fix |
| V8 | evidence root not mounted | medium | Kimi | valid | `[true-bug]` | `evidence.py` defaults `/mnt/.../test-runs`; compose does not mount it | fix |
| V9 | configs mounted rw | medium | DeepSeek | valid | `[partial-delivery]` | compose uses `../../configs:/app/configs` | fix |
| V10 | live capstone body deferred | high | Kimi | valid-owner-gated | `[true-deferred]` | `test_first_test_capstone.py` skips after gate without owner model/cache/token | defer-with-rationale |
| V11 | live HTTP body missing | medium | Kimi | valid-owner-gated | `[true-deferred]` | `test_first_test_http_smoke.py` only gates on `RUN_LIVE_HTTP` | defer-with-rationale |
| V12 | `service_train_rvc` signature mismatch | medium | DeepSeek | valid | `[true-bug]` | service passes `model_name`, `model_run_id`; `run_train_rvc` lacks `model_run_id` | fix |
| V13 | arbitrary `model_id` accepted for XTTS-only implementation | medium | Kimi | valid | `[partial-delivery]` | `infer_real.py` always creates `XttsAdapter(model_id=request.model_id)` | fix |
| V14 | fake training bytes / no real manifest training | high | Kimi | valid-owner-gated | `[true-deferred]` | `train.py` still uses fake rendered/checkpoint content for mock training path | defer-with-rationale |
| V15 | API response contract too shallow | low | Kimi | valid | `[partial-delivery]` | `first_test_run_create.json` checks key names only | fix |
| V16 | evidence stdout/stderr/stack trace capture absent | medium | DeepSeek/Kimi | valid | `[true-deferred]` | `evidence.py` writes commands but no output files; runner failure writes DB event only | defer-with-rationale |
| V17 | logging coverage thin | high | DeepSeek | valid | `[true-deferred]` | most pipeline/adapter modules have no logger calls | defer-with-rationale |
| V18 | schema canonical drift vs first-build plan | medium | Kimi | valid(子项 overstated) | `[true-deferred]` | current FT2 schema drift tests intentionally accept JSON/metadata downgrade | defer-with-rationale |
| V19 | `pipeline_runs` unwired | low | DeepSeek | valid | `[true-deferred]` | migrations define `pipeline_runs`; `rg pipeline_runs src` has no production writes | defer-with-rationale |
| V20 | action-plan test filename drift | low | Kimi | valid(子项 overstated) | `n/a` | functional tests exist; some AP examples stale | acknowledge/fix docs opportunistically |
| V21 | FT7 gate checks closure presence only | low | Kimi | stale-rejected | `n/a` | gate is intentionally docs existence check; actual test status lives in evidence pack/default pytest | stale-rejected |

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | 8 | V1,V2,V3,V4,V6,V7,V8,V12 | 本轮修复 |
| `[partial-delivery]` | 4 | V5,V9,V13,V15 | 本轮补齐 |
| `[true-deferred]` | 7 | V10,V11,V14,V16,V17,V18,V19 | 登记承接 |
| `n/a` | 2 | V20,V21 | ack / rejected |

### 4.2 净增承重盲区

- `V2`：earlier self-review only validated API job creation, not runner executability.
- `V4`：earlier closure used stale base commit language; peer review correctly flagged audit-chain weakness.
- `V5/V7/V8`：container boot and build-context hygiene were not part of the final self-review command set.

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证 | 结论 |
|----|--------|----------|------|------|
| V21 | Kimi | FT7 pre-capstone gate should prove tests passed | FT7 evidence records pytest results; gate's declared scope is closure presence before live marker execution | stale-rejected |

## 5. 初步修复方案

### 5.1 修复策略

先修直接阻断 runner/API/CLI/Docker 的 `[true-bug]` 与 `[partial-delivery]`，再补 contract/doc 锚点。真实 live capstone、real training、full logging/OTel/schema canonical migration 等需要 owner 环境或更大设计面的事项，只登记到 first-test deferred ledger，保持 close type 不被抬高。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证 | gate |
|----|----------|----------|------------------|------|
| V1 | add `run_curation` orchestration and runner test | `curate.py`, `test_runner.py` | curate job test | no |
| V2 | add runner dispatch for `infer_real` and `eval_first_test` | `runner.py`, tests | runner tests | no |
| V3 | route CLI eval through evaluation pipeline and add smoke metric when possible | `evaluate.py`, `cli.py`, tests | CLI/eval tests | no |
| V4 | replace stale closure anchor and add current HEAD note | `docs/closure/first-test/*.md` | docs-check / rg | no |
| V5 | copy migrations into images and/or mount dev migrations | Dockerfiles/compose/tests | docker config text tests | no |
| V6 | avoid unconstrained torchaudio install in train image | Dockerfile.train | docker text test | no |
| V7 | add `.dockerignore` | `.dockerignore`, tests | dockerignore test | no |
| V8 | mount evidence root in compose | compose/tests | compose text test | no |
| V9 | mount configs read-only | compose/tests | compose text test | no |
| V12 | align `run_train_rvc` signature | `train.py`, tests | service signature test | no |
| V13 | reject unsupported non-XTTS model ids | `infer_real.py`, schemas/API tests | inference validation tests | no |
| V15 | strengthen contract fixture to normalized snapshot | contract/test | snapshot test | no |

### 5.4 承接登记

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置 |
|----|--------------|------|----------|----------------|----------|
| V10 | `[true-deferred]` | defer-with-rationale | owner live audio/model/cache/token required | `RUN_FIRST_TEST_CAPSTONE=1` real env exists | `docs/closure/first-test/deferred-items-ledger.md` |
| V11 | `[true-deferred]` | defer-with-rationale | live HTTP socket body is not required for default suite and needs live env policy | owner requests socket-level live proof | `docs/closure/first-test/deferred-items-ledger.md` |
| V14 | `[true-deferred]` | defer-with-rationale | real training is out of first-test scope | real SoVITS/RVC training becomes target | `docs/closure/first-test/deferred-items-ledger.md` |
| V16 | `[true-deferred]` | defer-with-rationale | automatic stdout/stderr/stack capture needs execution harness redesign | non-skipped capstone run debugging requirement | `docs/closure/first-test/deferred-items-ledger.md` |
| V17 | `[true-deferred]` | defer-with-rationale | full structured logging is platform hardening | live debugging/ops readiness phase | `docs/closure/first-test/deferred-items-ledger.md` |
| V18 | `[true-deferred]` | defer-with-rationale | canonical migration aliases are not required by first-test JSON metadata contract | schema contract freeze / second-build migration | `docs/closure/first-test/deferred-items-ledger.md` |
| V19 | `[true-deferred]` | defer-with-rationale | `pipeline_runs` intentionally not hard dependency in FT2.7 | audit/resume UI requires workflow ledger | `docs/closure/first-test/deferred-items-ledger.md` |

---

## 6. 处置执行回填（fixes 落地后）

### 6.1 对本轮审查的回应

> 执行者: `Codex`
> 执行时间: `2026-06-13 09:39 UTC`
> 回应范围: `V1-V21`
> 对应审查文件: `docs/code-review/first-test/FT1-FT8-reviewed-by-deepseek.md`, `docs/code-review/first-test/FT1-FT8-reviewed-by-kimi.md`

- **总体回应**：本轮 verified 的 runner/Docker/contract/closure 锚点问题已修复；live/model/platform 级事项已登记 deferred，不提升 first-test close type。
- **本轮修改策略**：先修执行链与容器启动阻断，再补合同/文档审计，最后跑默认全量回归、live skip、evidence validate 与 diff check。
- **实现者自评状态**：`ready-for-rereview`

### 6.2 逐项处置结果表

| V# | 处理结果 | 处理方式 | 修改文件 | 独立复核状态 |
|----|----------|----------|----------|--------------|
| V1 | fixed | 新增 `run_curation`，runner curate job 可执行并有测试覆盖 | `src/myvoiceclone/pipelines/curate.py`, `src/myvoiceclone/jobs/runner.py`, `tests/unit/jobs/test_runner.py` | independently-verified |
| V2 | fixed | runner 增加 `infer_real` 与 `eval_first_test` dispatch | `src/myvoiceclone/jobs/runner.py`, `tests/unit/jobs/test_runner.py` | independently-verified |
| V3 | fixed | CLI eval 改走 service/evaluation pipeline；first-test artifact eval 生成 report 并运行 smoke | `src/myvoiceclone/cli.py`, `src/myvoiceclone/services/__init__.py`, `src/myvoiceclone/pipelines/evaluate.py`, `tests/cli/test_cli.py`, `tests/unit/jobs/test_runner.py` | independently-verified |
| V4 | fixed | closure 证据锚点改为当前 `uncommitted working tree on HEAD 31b4a04`，刷新 evidence pack | `docs/closure/first-test/*.md`, evidence pack | independently-verified |
| V5 | fixed | Dockerfile copy `db/migrations`，compose 开发挂载保留外部数据路径 | `infra/docker/Dockerfile.preprocess`, `infra/docker/Dockerfile.train`, `tests/unit/test_docker_first_test_contract.py` | independently-verified |
| V6 | fixed | 训练镜像不再安装 `audio` extra，避免 unconstrained `torchaudio` 覆盖 NGC 预装 | `infra/docker/Dockerfile.train`, `tests/unit/test_docker_first_test_contract.py` | independently-verified |
| V7 | fixed | 新增 `.dockerignore` 排除 venv/data/models/audio/checkpoint 等，显式保留 migrations | `.dockerignore`, `tests/unit/test_docker_first_test_contract.py` | independently-verified |
| V8 | fixed | compose 挂载 `/mnt/usb/workspace/myvoiceresearch/test-runs` | `infra/docker/compose.yaml`, `tests/unit/test_docker_first_test_contract.py` | independently-verified |
| V9 | fixed | compose `configs` mount 改为只读 | `infra/docker/compose.yaml`, `tests/unit/test_docker_first_test_contract.py` | independently-verified |
| V10 | deferred-with-rationale | live capstone 真实执行仍需 owner 音频/model/cache/token/license；ledger 已承接 | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V11 | deferred-with-rationale | live HTTP socket body 保留为 live-verification 触发项 | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V12 | fixed | `run_train_rvc` 接受 `model_run_id`，与 service 调用对齐 | `src/myvoiceclone/pipelines/train.py` | independently-verified |
| V13 | fixed | `validate_inference_request` 拒绝非 XTTS model_id，API/CLI 继续只支持已实现 substrate | `src/myvoiceclone/pipelines/infer_real.py`, `tests/unit/pipelines/test_real_inference_wrapper.py` | independently-verified |
| V14 | deferred-with-rationale | 真实训练消费 manifest 仍属 post-first-test training phase | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V15 | fixed | create-run contract fixture 升级为 normalized full JSON snapshot | `tests/api/contracts/first_test_run_create.json`, `tests/api/test_first_test_runs.py` | independently-verified |
| V16 | deferred-with-rationale | 自动 stdout/stderr/stack trace evidence 捕获需要执行 harness hardening | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V17 | deferred-with-rationale | pipeline/adapter 全量结构化日志属 observability-hardening | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V18 | deferred-with-rationale | canonical schema aliases/migrations deferred 到 schema-hardening | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V19 | deferred-with-rationale | `pipeline_runs` production workflow ledger deferred 到 UI/resume/multi-job timeline 需求 | `docs/closure/first-test/deferred-items-ledger.md` | deferred-by-owner/charter |
| V20 | fixed | FT1 action-plan stale test paths updated to actual tests | `docs/plan/first-test/FT1-preflight.md` | independently-verified |
| V21 | stale-rejected | FT7 pre-capstone closure gate scope was docs existence; test status is captured in evidence/default pytest | no code change | stale-rejected-by-code |

### 6.3 Blocker / Follow-up 状态汇总

| 分类 | 数量 | 编号 | 说明 |
|------|------|------|------|
| 已完全修复 | 12 | V1,V2,V3,V4,V5,V6,V7,V8,V9,V12,V13,V15,V20 | runner, Docker, contract, docs anchor/path issues fixed |
| 部分修复，需二审 | 0 | - | - |
| 有理由 deferred | 7 | V10,V11,V14,V16,V17,V18,V19 | 已追加到 first-test deferred ledger |
| 拒绝 / stale-rejected | 1 | V21 | reviewer expectation exceeded declared gate scope |
| acknowledge（无需改） | 0 | - | - |
| 仍 blocked | 0 | - | - |

### 6.4 变更文件清单

- **产品代码**：`src/myvoiceclone/jobs/runner.py`, `src/myvoiceclone/pipelines/curate.py`, `src/myvoiceclone/pipelines/evaluate.py`, `src/myvoiceclone/pipelines/infer_real.py`, `src/myvoiceclone/pipelines/train.py`, `src/myvoiceclone/services/__init__.py`, `src/myvoiceclone/cli.py`
- **Docker/ops**：`.dockerignore`, `infra/docker/Dockerfile.preprocess`, `infra/docker/Dockerfile.train`, `infra/docker/compose.yaml`
- **测试**：`tests/unit/jobs/test_runner.py`, `tests/unit/pipelines/test_real_inference_wrapper.py`, `tests/cli/test_cli.py`, `tests/unit/test_docker_first_test_contract.py`, `tests/api/test_first_test_runs.py`, `tests/api/contracts/first_test_run_create.json`
- **docs**：`docs/closure/first-test/*.md`, `docs/closure/first-test/deferred-items-ledger.md`, `docs/plan/first-test/FT1-preflight.md`, `docs/code-review/first-test/FT1-FT8-review-VF-ledger.md`

### 6.5 验证结果

| 验证项 | 命令 / 证据 | 结果 | 覆盖的 V# |
|--------|-------------|------|-----------|
| targeted review fixes | `./venv/bin/python -m pytest tests/unit/jobs/test_runner.py tests/unit/pipelines/test_real_inference_wrapper.py tests/cli/test_cli.py tests/unit/test_docker_first_test_contract.py tests/api/test_first_test_runs.py tests/unit/test_first_test_closure_docs.py -q` | `29 passed, 1 warning` | V1,V2,V3,V4,V5,V6,V7,V8,V9,V13,V15,V20 |
| architecture/schema/api/eval regression | `./venv/bin/python -m pytest tests/unit/test_architecture_boundaries.py tests/unit/test_project_config.py tests/unit/test_scripts_dry_run.py tests/unit/storage/test_schema_drift.py tests/unit/eval/test_objective.py tests/unit/eval/test_smoke_metrics.py tests/api/test_inference_routes.py tests/api/test_routes.py tests/api/test_audit_trace.py tests/api/test_release_gate.py -q` | `35 passed, 3 warnings` | V2,V3,V12,V13,V15 |
| default full suite | `./venv/bin/python -m pytest -q` | `148 passed, 1 skipped, 2 deselected, 14 warnings` | all fixed/default-gated findings |
| live gated checks | `./venv/bin/python -m pytest tests/integration/test_first_test_http_smoke.py tests/integration/test_first_test_capstone.py -m live -q -rs` | `2 skipped, 1 deselected` with explicit reasons | V10,V11 |
| evidence validate | `./venv/bin/python -m myvoiceclone.evidence validate /mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z --repo-root .` | `ok=true` | V4,V10,V16 |
| syntax / diff hygiene | `./venv/bin/python -m compileall -q src tests`; `git diff --check` | pass | all code/doc edits |

```text
pytest default summary:
148 passed, 1 skipped, 2 deselected, 14 warnings
```

### 6.6 未解决事项与承接

| 编号 | 状态 | 不在本轮完成的原因 | 承接位置 |
|------|------|--------------------|----------|
| V10 | deferred | owner live audio/model/cache/token/license required | `docs/closure/first-test/deferred-items-ledger.md#3-review-r1-追加承接项2026-06-13` |
| V11 | deferred | live socket proof remains live-verification scope | same |
| V14 | deferred | real training was out of first-test scope | same |
| V16 | deferred | automatic output/trace capture needs harness hardening | same |
| V17 | deferred | full structured logging is observability-hardening | same |
| V18 | deferred | canonical schema alignment requires migration/schema freeze | same |
| V19 | deferred | `pipeline_runs` production ledger needs UI/resume/workflow target | same |

### 6.7 Ready-for-rereview gate

- **是否请求二次审查**：`yes`
- **请求复核的范围**：`all findings`
- **实现者认为可以关闭的前提**：
  1. 二审确认 V1/V2/V3 runner/eval execution gaps 已关闭。
  2. 二审确认 V5-V9 Docker/evidence container hardening 已关闭。
  3. 二审接受 V10/V11/V14/V16/V17/V18/V19 的 deferred classification 与 triggers。
