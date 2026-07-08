# NF2-NF4 production-ready refactor —— proposed-planning（planning · 站② proposed）by Codex

> **stage**：`proposed`（站②·收窄/重锚）
> **作者**：`Codex`（panel / 跨模型 handoff：`none`）· **时间**：`2026-07-07`
> **本链 scope-fence**：阶段族 `new-refactors` 下 `NF2-NF4 production-ready voiceclone` 链站②。
> **文档性质（自宣告）**：**取代口头 initial 切分**，作 pre-charter-qna 前**唯一精炼工作基线**；本文件冻结零决策（仅 CITE 真相）。
> **上游权威输入**：`NF1 closure / production-ready gap study / HEAD 实测 / 当前容器事实`
> **下游消费者**：[[planning-final]]（站③）+ `NF2-NF4/pre-charter-qna.md`（owner-gate 裁决）+ `docs/plan/new-refactors/NF2-*.md..NF4-*.md`
> **文档状态**：`draft`

---

## 0. TL;DR `[核心]`

- **核心论点**：NF2-NF4 三段切分是合适的最小 DAG：NF2 先固化真实容器与模型依赖，NF3 再补生产级异步 API/control plane，NF4 最后只选择一条真实 voiceclone 路径做端到端闭环。推荐 NF4 优先产品化 `XTTS reference audio + text -> rendered audio -> real eval -> release gate`；不要在 NF4 同时承诺 So-VITS/RVC 训练生产化。
- **本态相对 initial 做了什么（一句话 supersession）**：从“三个阶段补 gap”的口头切分，收窄为 `NF2 image/runtime hardening -> NF3 durable API/worker -> NF4 XTTS-first production path` 的串行主路径，并把 So-VITS/RVC 训练设为 owner override / 后续 NF5 候选（← `T-R-3`, `T-R-8`）。
- **本态新增 reference-checked 真相**：新增 16 条 `T-R`，证实 4 条基础前提，证伪 6 条过度声称，驱动 DAG 串行化和 NF4 路线推荐。

---

## 1. Reference anchors / 输入与依据 `[核心]`

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `NF1-docker-images-closure.md` | `closure` | NF1 已完成容器-only、658 唯一端口、host venv 删除；同时留下 base substrate/auth/real train gap | `docs/closure/new-refactors/NF1-docker-images-closure.md:18`, `docs/closure/new-refactors/NF1-docker-images-closure.md:20`, `docs/closure/new-refactors/NF1-docker-images-closure.md:86` |
| `state-of-productio-ready-gaps.md` | `reference-anchor / gap-study` | production-ready gap 总账、P0/P1 建造建议、start-gate | `docs/eval/new-refactors/state-of-productio-ready-gaps.md:24`, `docs/eval/new-refactors/state-of-productio-ready-gaps.md:145`, `docs/eval/new-refactors/state-of-productio-ready-gaps.md:172`, `docs/eval/new-refactors/state-of-productio-ready-gaps.md:200` |
| Docker runtime | `HEAD` | 当前 `ai-voiceclone` 使用本地 base、只安装 api/db/cli/test、658 暴露、默认 real mode | `infra/docker/Dockerfile.ai-voiceclone:5`, `infra/docker/Dockerfile.ai-voiceclone:15`, `infra/docker/compose.voiceclone.yaml:16`, `infra/docker/compose.voiceclone.yaml:34` |
| Python dependencies | `HEAD` | `preprocess` extra 存在但未进 Dockerfile；模型下载脚本只写 manifest | `pyproject.toml:20`, `pyproject.toml:23`, `scripts/download_models.sh:17`, `scripts/download_models.sh:21` |
| API/job routes | `HEAD` | 当前 API 有 run/job surface，但长任务仍由 sync/BackgroundTasks 执行，状态查询依赖弱关联 | `src/myvoiceclone/api/routes_jobs.py:38`, `src/myvoiceclone/api/routes_runs.py:217`, `src/myvoiceclone/api/routes_runs.py:248`, `src/myvoiceclone/api/routes_runs.py:275` |
| Training adapters | `HEAD` | So-VITS/RVC 非 mock 未实现，训练 pipeline 仍写 fake feature/rendered bytes | `src/myvoiceclone/adapters/training/sovits_adapter.py:27`, `src/myvoiceclone/adapters/training/rvc_adapter.py:22`, `src/myvoiceclone/pipelines/train.py:278`, `src/myvoiceclone/pipelines/train.py:422` |
| Eval/scoring/security | `HEAD` | 真实 scoring/eval 缺失，release policy 默认 disabled，API audit 记录 request/response JSON | `src/myvoiceclone/pipelines/score.py:28`, `src/myvoiceclone/eval/objective.py:71`, `src/myvoiceclone/domain/policies.py:19`, `src/myvoiceclone/api/audit.py:69` |
| Artifact/data schema | `HEAD` | artifact 有 lineage 基础，但写文件再写 DB；jobs/artifacts schema 已有可扩展列 | `src/myvoiceclone/storage/artifact_store.py:43`, `src/myvoiceclone/storage/artifact_store.py:58`, `db/migrations/007_reconcile_to_plan.sql:40`, `db/migrations/007_reconcile_to_plan.sql:78` |

---

## 2. 规划真相台账（Planning Truth Register · 站②）★ `[核心]`

### 2.1 继承（截至 initial）

- `T-O-1`：NF1 已冻结 host 不执行 Python，所有执行必须进入 `ai-voiceclone` 容器；658 是唯一外部通讯口。
- `T-O-2`：`MOCK_ADAPTERS=true` 测试通过只能证明集成契约，不证明真实生产能力。
- `T-O-3`：生产准备目标要求容器自包含执行逻辑、可重封 image、全套异步 API 和状态监控。
- `T-O-4`：三段 action-plan 是最小合理切分，但每段必须以 hard-gate 收口，不能把 NF4 训练路线过载。

### 2.2 新增 reference-checked 真相（本态析出）★

| Truth-ID | 类型 | 真相内容（一句话）| 来源（`file:line` / RA-n）| 证实/证伪了哪条暂定前提 | 触发的 AP/DAG 调整 |
|----------|------|--------------------|-----------------------------|--------------------------|---------------------|
| `T-R-1` | `reference-checked` | NF1 容器边界已达成，但 base substrate 和公网 auth 是 carry-over | `docs/closure/new-refactors/NF1-docker-images-closure.md:18`, `docs/closure/new-refactors/NF1-docker-images-closure.md:20` | 证实 `T-O-1`，证伪“NF1 后环境已生产完备” | NF2 必须作为第一段硬前置 |
| `T-R-2` | `HEAD` | 当前 Dockerfile 仍基于本地 `ai-voiceclone-base:cu130` | `infra/docker/Dockerfile.ai-voiceclone:5` | 证伪“镜像可从 repo 独立重建” | NF2 增加 base rebuild / registry anchor |
| `T-R-3` | `HEAD` | 当前 Dockerfile 未安装 `preprocess` extra | `infra/docker/Dockerfile.ai-voiceclone:15`, `pyproject.toml:20` | 证伪“real preprocess 容器内可用” | NF2 必须先安装/验证真实依赖 |
| `T-R-4` | `HEAD` | 模型下载脚本只写 manifest，不下载/校验真实权重 | `scripts/download_models.sh:17`, `scripts/download_models.sh:21` | 证伪“模型 cache 已生产准备” | NF2 加模型 cache/hash/license gate |
| `T-R-5` | `HEAD` | 当前 API 有 job/run surface，但 run/infer 可用 BackgroundTasks | `src/myvoiceclone/api/routes_jobs.py:38`, `src/myvoiceclone/api/routes_runs.py:217` | 证伪“生产异步已完成” | NF3 建 durable worker，禁止长任务依赖 API 进程内任务 |
| `T-R-6` | `HEAD` | run status 依赖 `payload_json LIKE` 和 artifact metadata LIKE | `src/myvoiceclone/api/routes_runs.py:252`, `src/myvoiceclone/api/routes_runs.py:275` | 证伪“状态监控强一致” | NF3 加结构化 run/job/artifact link |
| `T-R-7` | `HEAD` | So-VITS 非 mock 直接 NotImplemented | `src/myvoiceclone/adapters/training/sovits_adapter.py:27` | 证伪“训练可生产执行” | NF4 不默认承诺训练；训练路线需 owner override |
| `T-R-8` | `HEAD` | RVC train/convert 非 mock 不可用 | `src/myvoiceclone/adapters/training/rvc_adapter.py:22`, `src/myvoiceclone/adapters/training/rvc_adapter.py:32` | 证伪“RVC baseline/VC 可生产执行” | NF4 推荐 XTTS-first |
| `T-R-9` | `HEAD` | So-VITS pipeline 仍生成 fake feature/rendered sample | `src/myvoiceclone/pipelines/train.py:278`, `src/myvoiceclone/pipelines/train.py:422` | 证伪“只补 adapter 即可训练生产化” | 训练专项不得塞入 NF4 默认路径 |
| `T-R-10` | `HEAD` | XTTS `synth_to_file` 有真实 Coqui TTS 调用路径 | `src/myvoiceclone/adapters/training/xtts_adapter.py:41`, `src/myvoiceclone/adapters/training/xtts_adapter.py:55` | 证实“可先做一条真实推理路径” | NF4 推荐 XTTS reference inference |
| `T-R-11` | `HEAD` | scoring real mode 直接拒绝，mock 常数不能筛真实数据 | `src/myvoiceclone/pipelines/score.py:28`, `src/myvoiceclone/pipelines/score.py:48` | 证伪“dataset 可生产自动筛选” | NF4 只做推理闭环时可避开训练 dataset gate；真实 eval 仍必做 |
| `T-R-12` | `HEAD` | objective metrics 明确是 mock 且 `quality_gate_eligible=false` | `src/myvoiceclone/eval/objective.py:71`, `src/myvoiceclone/eval/objective.py:79` | 证伪“release gate 有真实质量证据” | NF4 加 real eval contract |
| `T-R-13` | `HEAD` | API 无 auth 中间件，658 对外时风险为 blocker | `src/myvoiceclone/api/app.py:20`, `infra/docker/compose.voiceclone.yaml:16` | 证伪“658 可直接生产暴露” | NF3 将 API token / bind policy 纳入 P0 gate |
| `T-R-14` | `HEAD` | API audit 记录 request/response JSON，缺敏感字段策略 | `src/myvoiceclone/api/audit.py:69`, `src/myvoiceclone/api/audit.py:122` | 证实“审计有基础”，证伪“审计已生产合规” | NF3 加 redact/retention |
| `T-R-15` | `HEAD` | artifact 已有 sha/lineage 字段，但先写文件再写 DB | `src/myvoiceclone/storage/artifact_store.py:43`, `src/myvoiceclone/storage/artifact_store.py:58` | 证实“artifact store 可扩展”，证伪“产物写入已原子” | NF3 加 artifact hardening |
| `T-R-16` | `reference-checked` | gap study 推荐下一周期只选一条真实路径，建议先 XTTS | `docs/eval/new-refactors/state-of-productio-ready-gaps.md:200`, `docs/eval/new-refactors/state-of-productio-ready-gaps.md:202` | 证实 `T-O-4` | NF4 默认路径固定为 XTTS-first，训练进入 owner-gate |

---

## 3. 辨证审核（Δ 裁定上一阶段）+ 调整溯因 ★ 承重段 `[核心]`

- **§3.0 裁定对象（前序清单）**：本链没有正式 `planning-initial` 文档；本文直接裁定用户口头 initial：`NF2-NF4 三个 action-plan 补 production-ready gaps`，并以 `state-of-productio-ready-gaps.md` 作为 reference-anchor。
- **§3.1 Δ 表 + 调整溯因**：

| item-ID | 裁定（KEEP/REFRAME/CLOSED/NEW）| 来源前序 | 重分配 phase | 复用（✅/♻️/🆕）| **驱动真相（Truth-ID）** | 理由 / 新证据 |
|---------|-------------------------------|----------|--------------|------|--------------------------|------|
| `NF2-01` | `KEEP` | 口头 initial | `NF2` | ♻️ | `T-R-1`, `T-R-2` | image/runtime 是所有真实执行的硬前置 |
| `NF2-02` | `REFRAME` | 口头 initial | `NF2` | 🆕 | `T-R-3`, `T-R-4` | NF2 不只是“装依赖”，还要模型 cache/hash/license 和 preflight |
| `NF3-01` | `KEEP` | 口头 initial | `NF3` | ♻️ | `T-R-5`, `T-R-6` | API suite 必须包含 durable worker 与结构化状态，不只是增加 routes |
| `NF3-02` | `NEW` | gap study | `NF3` | 🆕 | `T-R-13`, `T-R-14` | 658 对外通讯要求 auth/audit redaction 进入 P0 |
| `NF3-03` | `NEW` | gap study | `NF3` | 🆕 | `T-R-15` | artifact/data hardening 必须与 API control plane 同期完成 |
| `NF4-01` | `REFRAME` | 口头 initial | `NF4` | ♻️ | `T-R-7`, `T-R-8`, `T-R-9`, `T-R-16` | NF4 默认不做全量训练生产化，只做一条真实闭环 |
| `NF4-02` | `KEEP` | gap study | `NF4` | ♻️ | `T-R-10`, `T-R-12` | XTTS real inference 有实现基础，但 eval/release gate 必须补真实证据 |
| `NF4-03` | `CLOSED` | 口头 initial | `NF5 candidate` | ⏸ | `T-R-7`, `T-R-8`, `T-R-9` | So-VITS/RVC 训练生产化规模过大，需 owner 明确 override 才进入 NF4 |
| `ALL-01` | `NEW` | template discipline | `NF2-NF4` | 🆕 | `T-O-2`, `T-R-16` | 所有 phase DoD 禁止用 mock pytest 作为 production-ready 证据 |

- **本态核心转向（一句话）**：三阶段从“补全部缺口”收窄为“先让容器真实可运行，再让 API 可恢复控制，最后只闭合 XTTS-first 真实路径”（← `T-R-3`, `T-R-5`, `T-R-16`）。

---

## 4. 范围与非范围（In/Out-Scope · sized 仍 gated）`[核心]`

- **In-Scope [S1]**：NF2 生产镜像、自包含依赖、模型 cache/preflight、base 可重建/可拉取（受 `T-R-2`, `T-R-3`, `T-R-4`）。
- **In-Scope [S2]**：NF3 durable worker、job control API、status/progress contract、structured run/job/artifact linkage、API auth/audit redaction、artifact/data hardening（受 `T-R-5`, `T-R-6`, `T-R-13`, `T-R-15`）。
- **In-Scope [S3]**：NF4 推荐路径：XTTS reference inference 的真实 API e2e、真实 smoke/ASR/speaker eval、release gate 不接受 mock metric（受 `T-R-10`, `T-R-12`, `T-R-16`）。
- **Out-of-Scope / 延后 [O1]**：So-VITS 真实长训；重评条件：owner 在 `G-NF4-1` 明确选择训练优先，并接受 NF4 范围膨胀。
- **Out-of-Scope / 延后 [O2]**：RVC 真实训练/转换；重评条件：owner 选择 RVC-only 作为首条生产路径。
- **Out-of-Scope / 延后 [O3]**：公网多租户治理、计费、UI、强水印算法；重评条件：658 对不可信网络开放或出现多用户需求。
- **Out-of-Scope / 延后 [O4]**：把所有模型权重强行封进镜像；是否封入由 `G-NF2-2` owner gate 决定。

---

## 5. 跨阶段贯穿主题（threaded themes）`[核心]`

- **技术路线红线**：`MOCK_ADAPTERS=true` 不得作为 NF2-NF4 production DoD；长任务不得由 FastAPI `BackgroundTasks` 承载；NF4 默认只做一条真实路径；任何 release gate 不得接受 `metric_source=mock`。
- **治理冻结面**：658 若对非本机开放，NF3 必须先完成 API token / bind policy / audit redaction；release gate 默认不能在 security disabled 且无真实 metric 时标 production passed。
- **migration inventory**：NF3 预计新增 `012_job_worker_control.sql`、`013_run_artifact_links.sql`、`014_artifact_lifecycle.sql`、`015_api_auth_audit_redaction.sql`；NF4 预计新增 `016_real_eval_metrics.sql`（编号为 proposed，最终以 action-plan 冻结为准）。
- **image inventory**：NF2 预计拆分 `Dockerfile.ai-voiceclone-base-cu130`、`Dockerfile.ai-voiceclone`、可选 `Dockerfile.ai-voiceclone-test`；是否推 registry 由 owner-gate 决定。
- **evidence inventory**：每个 phase 必须输出容器内 real-mode evidence，不接受 host Python，不接受裸 `pytest -q` 作为唯一证据。

---

## 6. DAG（关键路径 + 并行窗）+ DAG 调整溯因 `[核心]`

```text
NF1 closure
  |
  v
NF2.P1 base/image reproducibility
  -> NF2.P2 dependency + model cache + preflight
  -> NF2.P3 real-mode container smoke
  -> NF2 hard-gate: image can be rebuilt, real preflight is explicit
  |
  v
NF3.P1 DB/job control schema
  -> NF3.P2 durable worker + lease/heartbeat
  -> NF3.P3 API suite: create/start/cancel/retry/resume/status/download/archive
  -> NF3.P4 auth/audit redaction + artifact lifecycle
  -> NF3 hard-gate: API-only control survives service restart
  |
  v
NF4.P0 owner route decision
  -> recommended NF4.P1 XTTS reference inference orchestration
  -> NF4.P2 real eval metrics + release gate
  -> NF4.P3 production e2e evidence pack
  -> NF4 hard-gate: MOCK_ADAPTERS=false API-only e2e pass

Parallel windows:
  - NF2.P1 base image work can run in parallel with NF2.P2 dependency pin research.
  - NF3 API schemas can draft in parallel with DB migration design, but implementation waits for schema freeze.
  - NF4 eval metric implementation can spike after NF2 preflight passes, but e2e waits for NF3 worker/API.
```

### 6.1 DAG 调整溯因（Module② · 相对 initial DAG 改了什么 ← 哪条真相）

| DAG 变更 | 相对 initial | **驱动真相（Truth-ID）** | 说明 |
|----------|--------------|--------------------------|------|
| NF2 前置为硬 gate | 原可与 API 并行 → 现为 NF3/NF4 前置 | `T-R-2`, `T-R-3`, `T-R-4` | 真实依赖和模型 cache 不清，API/执行测试会继续落入 mock |
| NF3 放在 NF4 前 | 原可能先做真实执行 → 现先补 durable API | `T-R-5`, `T-R-6` | 生产目标要求只通过 658 API 控制全链，不能靠容器手工命令 |
| NF4 默认选 XTTS-first | 原可能同时补 XTTS/RVC/So-VITS → 现只做一条闭环 | `T-R-7`, `T-R-8`, `T-R-9`, `T-R-10`, `T-R-16` | 训练路线缺口过大，XTTS 有真实实现基础 |
| Security/auth 提前到 NF3 | 原可能后置 → 现与 API control plane 同期 | `T-R-13`, `T-R-14` | 658 是唯一外部通讯口，生产 API 必须先有最小认证与审计策略 |
| Artifact lifecycle 并入 NF3 | 原可能属于数据后续优化 → 现纳入 API suite | `T-R-15` | DELETE/archive/download/status 都依赖 artifact lifecycle |

---

## 7. 逐 phase 工作台账 —— 重分配 + verdict 绑定 + 拆解 `[核心]`

### 7.1 `NF2 — production runtime / image readiness`

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚(`file:line`) + ⛔避坑 + TR | 复用 | 规模 | 受约束真相 |
|------|--------|----------------------------------------------------------|------|------|------------|
| `NF2-01a` | 固化可重建 cu130 base | 参考 NF1 known gap；✅ 现有 `ai-voiceclone-base:cu130` 可作为事实 substrate；HEAD `infra/docker/Dockerfile.ai-voiceclone:5`；⛔ 不再只依赖宿主历史 tag | ♻️ | L | `T-R-1`, `T-R-2` |
| `NF2-01b` | 生产/test 镜像分层 | HEAD 当前复制 docs/tests 到 runtime `infra/docker/Dockerfile.ai-voiceclone:17`；⛔ 不把 test tooling 作为 production runtime 必需 | 🆕 | M | `T-R-2` |
| `NF2-02a` | 安装真实 audio/preprocess 依赖 | HEAD 当前只装 `.[cli,db,api,test]`；preprocess extra 在 `pyproject.toml:20`；⛔ 不用 mock import pass 代替 real preflight | ♻️ | M | `T-R-3` |
| `NF2-02b` | 依赖版本 pin / lock | HEAD extras 未 pin `pyproject.toml:16`; ⛔ 不允许每次 rebuild 拉到不同模型栈 | 🆕 | M | `T-R-3`, `T-R-4` |
| `NF2-03a` | 模型 cache/download manifest + hash + license | HEAD download script 只写 manifest `scripts/download_models.sh:21`; ⛔ 不把运行时隐式联网下载当 production | ♻️ | L | `T-R-4` |
| `NF2-03b` | runtime preflight CLI/API | 参考 gap §8 start-gate；HEAD adapters 已有 preflight 方法；⛔ preflight 不能只返回 import 成功，要报告 model/token/cache/device | ♻️ | M | `T-R-3`, `T-R-4`, `T-R-10` |
| `NF2-04a` | real-mode container smoke | NF1 已有 health/CUDA evidence `docs/closure/new-refactors/NF1-docker-images-closure.md:51`; ⛔ smoke 必须 `MOCK_ADAPTERS=false` | ♻️ | M | `T-O-2`, `T-R-3` |
| `NF2-05a` | 文档降噪与能力标注 | README 仍声称 RVC/So-VITS `README.md:24`; ⛔ 不得把未实现训练写成可用 | ♻️ | S | `T-R-7`, `T-R-8` |

### 7.2 `NF3 — production async API / job control plane`

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚(`file:line`) + ⛔避坑 + TR | 复用 | 规模 | 受约束真相 |
|------|--------|----------------------------------------------------------|------|------|------------|
| `NF3-01a` | job worker schema：lease/heartbeat/progress/attempts | Existing jobs schema has extensible fields `db/migrations/007_reconcile_to_plan.sql:40`; ⛔ 不把 `pending/completed` 旧状态继续扩散 | ♻️ | M | `T-R-5`, `T-R-6` |
| `NF3-01b` | 独立 worker 进程 | 当前 API route 直接 `JobRunner.run` `src/myvoiceclone/api/routes_jobs.py:56`; ⛔ 长任务不得由 request path 执行 | 🆕 | L | `T-R-5` |
| `NF3-01c` | cancel/retry/resume semantics | runner 仅在训练循环读取消状态 `src/myvoiceclone/pipelines/train.py:360`; ⛔ cancel API 不能只写状态不被 worker 观察 | 🆕 | L | `T-R-5` |
| `NF3-02a` | API suite 补全 jobs/runs/artifacts/datasets/models/reports CRUD | 当前 schemas 支持响应但 API 动词偏 GET/POST `src/myvoiceclone/api/schemas.py:52`; ⛔ DELETE 必须走 archive/tombstone 策略 | ♻️ | L | `T-R-6`, `T-R-15` |
| `NF3-02b` | 统一 voiceclone orchestration endpoint | 现有 preprocess/infer/eval 分散 `src/myvoiceclone/api/routes_runs.py:194`, `src/myvoiceclone/api/routes_runs.py:217`, `src/myvoiceclone/api/routes_runs.py:236`; ⛔ 不让调用方手工拼状态机 | 🆕 | M | `T-R-6`, `T-R-16` |
| `NF3-03a` | 结构化 run/job/artifact links | 当前 status 使用 payload LIKE `src/myvoiceclone/api/routes_runs.py:252` 和 metadata LIKE `src/myvoiceclone/api/routes_runs.py:275`; ⛔ 不再用 JSON LIKE 作为权威关联 | 🆕 | M | `T-R-6`, `T-R-15` |
| `NF3-04a` | API auth/token + bind policy | 658 暴露在 compose `infra/docker/compose.voiceclone.yaml:16`; app 无 auth middleware `src/myvoiceclone/api/app.py:20`; ⛔ 不可信网络不可裸奔 | 🆕 | M | `T-R-13` |
| `NF3-04b` | API audit redaction/retention | audit 记录 request/response JSON `src/myvoiceclone/api/audit.py:69`; ⛔ 不落明文 token/大音频/敏感路径 | ♻️ | M | `T-R-14` |
| `NF3-05a` | artifact atomic write + archive/delete | artifact 先写文件再 DB `src/myvoiceclone/storage/artifact_store.py:43`, `src/myvoiceclone/storage/artifact_store.py:58`; ⛔ 删除不能破坏 lineage | 🆕 | M | `T-R-15` |
| `NF3-06a` | restart resilience test harness | NF1 有 restart smoke 仅 health `docs/closure/new-refactors/NF1-docker-images-closure.md:63`; ⛔ 需要 job 中途 restart 后可恢复 | 🆕 | M | `T-R-5` |

### 7.3 `NF4 — real voiceclone execution path / quality gate`

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚(`file:line`) + ⛔避坑 + TR | 复用 | 规模 | 受约束真相 |
|------|--------|----------------------------------------------------------|------|------|------------|
| `NF4-00a` | owner route decision freeze | gap study 建议先选一条路径 `docs/eval/new-refactors/state-of-productio-ready-gaps.md:202`; ⛔ 未拍板不得同时做三条路线 | 🆕 | S | `T-R-16` |
| `NF4-01a` | XTTS real inference job 化 | XTTS real file path 已存在 `src/myvoiceclone/adapters/training/xtts_adapter.py:41`; `/api/inference/real` 当前同步 `src/myvoiceclone/api/routes_inference.py:26`; ⛔ 生产路径必须走 NF3 worker | ♻️ | M | `T-R-10`, `T-R-5` |
| `NF4-01b` | Reference audio validation + artifact provenance | API schemas 有 reference fields `src/myvoiceclone/api/schemas.py:93`; artifact metadata 有 tool/model/cache/license fields `src/myvoiceclone/storage/artifact_store.py:47`; ⛔ 不允许输出 artifact 缺 input refs/model/device/license | ♻️ | M | `T-R-10`, `T-R-15` |
| `NF4-02a` | Real eval contract：smoke + reverse ASR + speaker similarity | objective 当前 mock `src/myvoiceclone/eval/objective.py:71`; embeddings 当前 mock `src/myvoiceclone/adapters/embeddings/speaker_embedder.py:9`; ⛔ release 不接受 `metric_source=mock` | 🆕 | L | `T-R-12`, `T-R-11` |
| `NF4-02b` | Release gate 改为真实 metric eligible | policy layer 检查 mock metric `src/myvoiceclone/domain/policies.py:122`; ⛔ `quality_gate_eligible=false` 不能 passed | ♻️ | M | `T-R-12` |
| `NF4-03a` | API-only e2e：create run -> upload reference -> start -> monitor -> download -> eval -> gate | 现有 run status surface `src/myvoiceclone/api/routes_runs.py:248`; ⛔ 不允许 docker exec 手工补链路 | ♻️ | L | `T-R-6`, `T-R-10`, `T-R-16` |
| `NF4-04a` | Evidence pack and docs | NF1 evidence pattern exists `docs/closure/new-refactors/NF1-docker-images-closure.md:47`; ⛔ evidence 必须是 `MOCK_ADAPTERS=false` | ♻️ | M | `T-O-2`, `T-R-16` |
| `NF4-X1` | So-VITS/RVC training override path | So-VITS/RVC 非 mock未实现 `src/myvoiceclone/adapters/training/sovits_adapter.py:27`, `src/myvoiceclone/adapters/training/rvc_adapter.py:22`; ⛔ 只有 owner 在 `G-NF4-1` 选择训练优先时激活 | ⏸ | XL | `T-R-7`, `T-R-8`, `T-R-9` |

---

## 8. Owner decision gates —— 精炼 OPEN `[核心]`

| 编号 | 决策点 | 影响 | 依新 sizing 精炼的建议 | 状态 |
|------|--------|------|------------------------|------|
| `G-NF2-1` | `ai-voiceclone-base:cu130` 是推私有 registry，还是 repo 内纯 Dockerfile 重建？ | 决定 NF2 工作量和可复现边界 | 推荐：短期推私有 registry + repo 记录 digest；中期补纯 Dockerfile rebuild | `OPEN` |
| `G-NF2-2` | 模型权重封入 image，还是 `.data/models` bind mount？ | 决定镜像大小、构建时间、离线能力 | 推荐：默认 bind mount `.data/models`，镜像只含下载/校验逻辑；关键小模型可选 bake-in | `OPEN` |
| `G-NF2-3` | 是否允许构建期联网下载 gated 模型？ | 影响 PyAnnote/Coqui 可重建性 | 推荐：不在 Docker build 下载 gated 模型；运行前 `model-cache prepare` 显式拉取并记录 hash/license | `OPEN` |
| `G-NF3-1` | 658 是否面向不可信网络？ | 决定 auth 是否必须 P0 | 推荐：按不可信网络处理，NF3 必须有 API token；本地可通过 env 显式关闭 | `OPEN` |
| `G-NF3-2` | SQLite 是否继续作为 production DB？ | 决定 worker lease/locking 复杂度 | 推荐：当前阶段保留 SQLite，但加入 WAL、busy_timeout、lease、backup/export；不要引入新 DB | `OPEN` |
| `G-NF3-3` | artifact 删除语义是 hard delete 还是 archive/tombstone？ | 影响 lineage 和审计 | 推荐：默认 archive/tombstone，物理清理由 maintenance job 执行 | `OPEN` |
| `G-NF4-1` | NF4 第一条真实路径选 XTTS、RVC、还是 So-VITS？ | 决定 NF4 是否可按期收口 | 推荐：选 XTTS reference inference；RVC/So-VITS 训练进入 NF5 | `OPEN` |
| `G-NF4-2` | NF4 最小真实验收样本集由谁提供？ | 决定质量指标可信度 | 推荐：owner 提供 3-5 段授权 reference audio + 3 条固定文本 + 1 条拒绝样本 | `OPEN` |
| `G-NF4-3` | release gate 是否允许人工 waive production quality？ | 决定治理强度 | 推荐：NF4 production gate 不允许质量 waive，只允许记录人工备注；安全/授权 waive 另行审批 | `OPEN` |

**推荐方案汇总**：

1. `G-NF4-1` 选择 **XTTS-first**。
2. NF2 使用 `.data/models` bind mount + 显式 `model-cache prepare/verify`，不要构建期下载 gated 模型。
3. NF3 保留 SQLite，但必须实现 worker lease/heartbeat/retry/cancel 和 API token。
4. So-VITS/RVC 真实训练独立进入 NF5，除非 owner 接受 NF4 规模从 L 提升到 XL 并推迟收口。

---

## 9. 测试计划（+ DoD）`[核心]`

- **A 短途**：
  - NF2：Dockerfile/compose contract、dependency import/preflight、model manifest/hash parser、no host venv regression。
  - NF3：API schema tests、job state transition unit、auth middleware、audit redaction、artifact archive semantics。
  - NF4：XTTS request validation、artifact metadata contract、metric eligibility contract。
- **B spike**：
  - NF2：pyannote/whisper/demucs/TTS real preflight in container with `MOCK_ADAPTERS=false`。
  - NF3：worker crash/restart lease recovery spike。
  - NF4：reverse ASR + speaker similarity metric spike on owner sample。
- **D mega**：
  - NF3：API-only long job restart resilience: start job, kill/restart API/worker, verify status resumes.
  - NF4：`MOCK_ADAPTERS=false` API-only e2e: create run, upload reference, start inference, poll status, download rendered audio, run real eval, release gate.

**DoD（每 phase 收口判据雏形）**：

- `NF2 DoD`：
  - `docker compose -f infra/docker/compose.voiceclone.yaml build ai-voiceclone` 从冻结 base/digest 可重复构建。
  - `docker exec ai-voiceclone python -m myvoiceclone.cli preflight --real` 或等价 API 返回 XTTS/Whisper/Demucs/PyAnnote/FFmpeg/Torch/CUDA/model-cache 明确状态。
  - `MOCK_ADAPTERS=false` 下不出现 silent mock fallback。
  - 文档明确哪些能力 real-ready、blocked、deferred。
- `NF3 DoD`：
  - 外部只通过 658 API 可以 create/start/cancel/retry/resume/status/download/archive。
  - worker 与 API 分离，服务重启后 job lease 可恢复或失败可解释。
  - `/api/runs/{id}/status` 不依赖 `metadata_json LIKE` 作为权威关联。
  - API token/audit redaction 测试通过。
- `NF4 DoD`：
  - owner 选定路径在 `MOCK_ADAPTERS=false` 下 API-only 完成。
  - 输出 artifact 有 model/version/device/cache/license/input refs。
  - real eval metrics 写入 `eval_metrics/eval_samples/reports`，`metric_source != mock` 且 `quality_gate_eligible=true`。
  - release gate 基于真实 metric 判定，closure evidence 包含命令、HTTP trace、artifact ids、下载文件、指标报告。

---

## 10. 风险登记 `[核心]`

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| cu130 依赖组合冲突 | TTS/pyannote/whisper/demucs 与 torch 2.12/cu130 不兼容 | NF2 构建反复失败 | NF2 先做 dependency matrix spike，必要时固定两层镜像 |
| Gated model access 不可自动化 | PyAnnote/Coqui 权限或 token 不可用 | real preprocess/eval 阻塞 | 模型 cache prepare 显式失败并给 owner-gate；NF4 XTTS 可先不依赖 PyAnnote |
| SQLite worker 锁竞争 | 长任务频繁写 progress/events | job 状态错乱或 API 卡顿 | WAL、busy_timeout、短事务、lease 表、写入节流 |
| API surface 膨胀 | NF3 一次性补全所有 CRUD | 延误 NF4 | 优先 jobs/runs/artifacts 必需面；低频资源管理可 P1 |
| NF4 被训练路线拖垮 | owner 要求 So-VITS/RVC 同时生产化 | NF4 范围变 XL 且不可预测 | 默认 XTTS-first；训练路线需要 owner 明确 override |
| 质量指标不可信 | speaker similarity/ASR 模型不稳定 | release gate 误判 | 指标标注 model/version/source；先做 threshold calibration spike |
| 认证影响本地易用性 | API token 强制后脚本/测试失败 | 开发效率下降 | 本地 env 可显式 disable，但 production compose 默认 enable |
| Artifact 删除破坏审计 | hard delete 被用于清理空间 | lineage/report 下载失效 | archive/tombstone 默认，GC 单独维护 |

---

## 11. 后继解锁 `[核心]`

- **解锁的下游价值**：
  - NF2 解锁“真实依赖和模型环境可重复重封”。
  - NF3 解锁“只通过 658 API 驱动全链路，并可恢复/取消/重试/审计”。
  - NF4 解锁“一条真实 voiceclone production path 的 API-only 交付证据”。
  - NF4 完成后可自然派生 NF5：So-VITS/RVC 真实训练专项。
- **下游**：→ [[planning-final]]（站③，将 critique 本文并冻结派生 action-plan）；→ `docs/plan/new-refactors/NF2-*.md`, `NF3-*.md`, `NF4-*.md`。

---

## 12. 交叉引用与修订历史 `[可选]`

- **交叉引用**：
  - 上游：`docs/closure/new-refactors/NF1-docker-images-closure.md`
  - 上游：`docs/eval/new-refactors/state-of-productio-ready-gaps.md`
  - 下游：`docs/plan/new-refactors/NF2-*.md`, `NF3-*.md`, `NF4-*.md`

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-07-07 | Codex | 初稿（Δ 裁定 + 重锚 + 真相台账 T-R + DAG + owner gates）|
