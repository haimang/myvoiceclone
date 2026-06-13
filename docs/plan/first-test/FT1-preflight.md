# FT1 Preflight Action Plan

> 服务业务簇: `FT1 · 准入收敛与测试入口统一`
> 计划对象: `first-test preflight, command/config/job-entry cleanup`
> 类型: `upgrade`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT1-preflight.md`
> 上游前序 / closure:
> - `docs/eval/first-test/proposed-planning.md`
> 下游交接:
> - `docs/plan/first-test/FT2-schema-observability.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/reference-anchor.md`
> - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT1`, `reference-anchor axis A/E/F/G`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT1 是 first-test 的准入层。它不实现真实模型能力，而是移除会让真实测试 day-1 失败的入口、配置和假成功问题：命令漂移、bootstrap extras、env 键漂移、`preprocess_all` payload、空 manifest、artifact root resolver。

- **服务业务簇**：`Preflight / 环境与入口收敛`
- **计划对象**：CLI/API/config/scripts/dataset freeze readiness
- **本次计划解决的问题**：
  - 文档/脚本命令和真实 entry point 不一致。
  - 完整 preprocess 入口缺一等可用路径。
  - 空 dataset freeze 可误判为成功。
- **本次计划的直接产出**：
  - 可执行的 first-test 本地准入命令。
  - `preprocess_all` CLI/API job creation 合同。
  - empty manifest guard 与 artifact root resolver 测试。
- **本计划不重新讨论的设计结论**：
  - first-test 以本地 SQLite + DB job 为基线（来源：`docs/eval/first-test/reference-anchor.md:189`）。
  - 真实证据必须落 DB/artifact/evidence pack（来源：`docs/eval/first-test/reference-anchor.md:190`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先审计入口与配置，再修 CLI/API/job payload，最后补测试闸。FT1 的原则是让后续 FT2-FT7 不需要绕过公开入口或手工插 DB。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 命令与环境准入 | S | 修 `myvoiceclone` 命令、extras、env 示例 | - |
| Phase 2 | preprocess 入口统一 | M | CLI/API 创建可被 runner 消费的 `preprocess_all` job | Phase 1 |
| Phase 3 | dataset/config 防假成功 | S | empty manifest guard 与 artifact root resolver | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — 命令与环境准入**
   - **核心目标**：first-test 操作者按 docs/scripts 能启动正确 CLI 与 live deps 探针。
   - **为什么先做**：命令层失败会阻断所有真实测试。
2. **Phase 2 — preprocess 入口统一**
   - **核心目标**：公开入口创建 payload 含 `filepath` 或 artifact/path 的 `preprocess_all` job。
   - **为什么放在这里**：后续真实预处理和 API e2e 都依赖这一入口。
3. **Phase 3 — dataset/config 防假成功**
   - **核心目标**：空 manifest 不可 frozen，API runner 尊重 env artifact root。
   - **为什么放在这里**：避免后续 FT3/FT4 基于假数据继续执行。

### 1.4 执行策略说明

- **执行顺序原则**：docs/scripts/config → CLI payload → API job creation → dataset/artifact guard。
- **风险控制原则**：所有入口变更都配 CLI/API unit tests；不引入真实模型依赖。
- **测试推进原则**：短途单元和 TestClient 为主，不跑 live。
- **文档同步原则**：README/ops/scripts 与 `.env.example` 同步。
- **回滚 / 降级原则**：若 API orchestration 未完成，至少保留可用 CLI `preprocess_all` 入口，不再手工插 DB。

### 1.5 本次 action-plan 影响结构图

```text
FT1 Preflight
├── command/config
│   ├── README.md / docs/ops/local-setup.md
│   ├── scripts/bootstrap_env.sh
│   └── .env.example / src/myvoiceclone/config.py
├── preprocess entry
│   ├── src/myvoiceclone/cli.py
│   ├── src/myvoiceclone/api/routes_recordings.py
│   └── src/myvoiceclone/jobs/runner.py
└── fake-zero guard
    ├── src/myvoiceclone/pipelines/export_dataset.py
    └── tests/unit + tests/api
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** 修正 `mvc`/`myvoiceclone` 命令漂移。
- **[S2]** live bootstrap 安装 extras 并提供依赖探针。
- **[S3]** `.env.example` 与 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR/MOCK_ADAPTERS` 对齐。
- **[S4]** 修 CLI/API `preprocess_all` job payload 与 artifact root resolver。
- **[S5]** dataset freeze 空 manifest guard。

### 2.2 Out-of-Scope

- **[O1]** 真实 PyAnnote/Demucs/Whisper 执行，交 FT3。
- **[O2]** 真实推理 adapter，交 FT4。
- **[O3]** 全局 API envelope，交 FT6 contract 处理。
- **[O4]** schema drift 全面测试，交 FT2。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `preprocess_all` CLI/API job creation | in-scope | 真实预处理不能依赖手工插 DB | FT6 需要更完整 e2e run surface |
| live adapter dependency checks | defer | FT1 只做 bootstrap/probe | FT3 live smoke 开始 |
| full API response envelope | out-of-scope | breaking API contract | FT6 final contract 需要 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| FT1-P1-01 | Phase 1 | 命令与文档入口统一 | update | `pyproject.toml`, `README.md`, `docs/ops/local-setup.md`, `src/myvoiceclone/cli.py:17` | 文档命令与 console script 一致 | FT1-T01 | low |
| FT1-P1-02 | Phase 1 | live bootstrap extras | update | `scripts/bootstrap_env.sh`, `pyproject.toml` | bootstrap 安装 first-test 所需 extras | FT1-T02 | low |
| FT1-P1-03 | Phase 1 | env 示例对齐 | update | `.env.example`, `src/myvoiceclone/config.py:42-68` | env vars 与 runtime resolver 一致 | FT1-T03 | low |
| FT1-P2-01 | Phase 2 | CLI preprocess payload 修复 | update | `src/myvoiceclone/cli.py:92-110`, `src/myvoiceclone/jobs/runner.py:132-136` | CLI 创建 runner 可消费的 job | FT1-T04 | medium |
| FT1-P2-02 | Phase 2 | API preprocess job creation | add/update | `src/myvoiceclone/api/routes_recordings.py:26-38`, `src/myvoiceclone/api/schemas.py:52-67` | API 可创建 pending preprocess job | FT1-T05 | medium |
| FT1-P3-01 | Phase 3 | empty manifest guard | update | `src/myvoiceclone/pipelines/export_dataset.py:46-64`, `src/myvoiceclone/pipelines/export_dataset.py:126-147` | 空 manifest 不可 frozen success | FT1-T06 | low |
| FT1-P3-02 | Phase 3 | API artifact root resolver | update | `src/myvoiceclone/api/routes_jobs.py:33-35`, `src/myvoiceclone/config.py:55-60` | API runner 尊重 `ARTIFACT_ROOT` | FT1-T07 | low |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT1.1` | FT1-P1-01 | `T-FT1.1` | FT1-T01 |
| `FT1.2` | FT1-P1-02 | `T-FT1.2` | FT1-T02 |
| `FT1.3` | FT1-P1-03 / FT1-P3-02 | `T-FT1.3` | FT1-T03 / FT1-T07 |
| `FT1.4` | FT1-P2-01 | `T-FT1.4` | FT1-T04 |
| `FT1.5` | FT1-P2-02 | `T-FT1.5` | FT1-T05 |
| `FT1.6` | FT1-P3-01 | `T-FT1.6` | FT1-T06 |
| `FT1.7` | FT1-P1-01..FT1-P3-02 | `T-FT1.7` | FT1-T01..FT1-T07 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 命令与环境准入

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| FT1-P1-01 | 命令与文档入口统一 | 扫描 README/ops/scripts 中旧命令；统一为 `myvoiceclone` 或补 alias；保留 help smoke。 | `src/myvoiceclone/cli.py:17`, `README.md`, `docs/ops/local-setup.md` | 用户按文档能启动 CLI | FT1-T01 | 无命令漂移 |
| FT1-P1-02 | live bootstrap extras | 把 bootstrap 安装改为 first-test extras；加入 ffmpeg/ffprobe/demucs/whisper/pyannote 探针说明。 | `scripts/bootstrap_env.sh`, `pyproject.toml` | 安装环境可满足 live smoke 前置 | FT1-T02 | dry-run/string probe 通过 |
| FT1-P1-03 | env 示例对齐 | `.env.example` 使用 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR/MOCK_ADAPTERS`；与 resolver 一致。 | `.env.example`, `src/myvoiceclone/config.py:42-68` | config 不再读错键 | FT1-T03 | env unit test 通过 |

### 4.2 Phase 2 — preprocess 入口统一

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| FT1-P2-01 | CLI preprocess payload 修复 | a) 增加接受 filepath 的 CLI preprocess 命令；b) 修 `run diarize` 不再用 `recording_id` 创建 `preprocess_all`；c) payload 缺 `filepath` 时错误清晰。 | `src/myvoiceclone/cli.py:92-110`, `src/myvoiceclone/jobs/runner.py:132-136` | CLI job 能被 runner 执行 | FT1-T04 | payload contract 通过 |
| FT1-P2-02 | API preprocess job creation | a) 添加 request schema；b) 创建 `preprocess_all` pending job；c) 返回 `JobResponse`；d) 不立即假执行。 | `src/myvoiceclone/api/routes_recordings.py:26-38`, `src/myvoiceclone/api/schemas.py:52-67` | TestClient 可创建 preprocess job | FT1-T05 | API creation test 通过 |

### 4.3 Phase 3 — dataset/config 防假成功

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| FT1-P3-01 | empty manifest guard | 在 rows/manifest_rows 为空时抛明确错误；不得写 manifest artifact 或 frozen status。 | `src/myvoiceclone/pipelines/export_dataset.py:46-64`, `src/myvoiceclone/pipelines/export_dataset.py:126-147` | 空 dataset 不会假成功 | FT1-T06 | fake-zero test 通过 |
| FT1-P3-02 | API artifact root resolver | `routes_jobs` 使用 `resolve_artifact_root()`，不直接读取 local config fallback。 | `src/myvoiceclone/api/routes_jobs.py:33-35`, `src/myvoiceclone/config.py:55-60` | API artifact 落 env root | FT1-T07 | artifact root drift test 通过 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 命令与环境准入

- **Phase 目标**：让 first-test 操作者可以按 docs/scripts 准确启动环境。
- **本 Phase 对应编号**：FT1-P1-01 / FT1-P1-02 / FT1-P1-03
- **新增文件**：无
- **修改文件**：`README.md`, `docs/ops/local-setup.md`, `.env.example`, `scripts/bootstrap_env.sh`
- **具体功能预期**：
  1. 所有用户可见命令以 `myvoiceclone` 为主。
  2. bootstrap 使用 extras 安装，不只 `pip install -e .`。
  3. `.env.example` 只暴露 runtime 真实读取的键。
  4. live 依赖探针失败时文档要求 stop/skip，不假绿。
- **对应测试台账项**：FT1-T01 / FT1-T02 / FT1-T03
- **收口标准**：命令、env、bootstrap drift test 全通过。
- **风险提醒**：若保留 alias，必须确保不会掩盖 `myvoiceclone` 主入口。

### 5.2 Phase 2 — preprocess 入口统一

- **Phase 目标**：公开入口能创建 runner 可执行的 `preprocess_all` job。
- **对应编号**：FT1-P2-01 / FT1-P2-02
- **新增 / 修改文件**：`src/myvoiceclone/cli.py:92-110`, `src/myvoiceclone/api/routes_recordings.py:26-38`, `src/myvoiceclone/api/schemas.py:52-67`
- **具体功能预期**：
  1. CLI 支持 filepath 或 artifact/path 的完整 preprocess。
  2. `preprocess_all` payload 与 `JobRunner._execute_preprocess_all()` 一致。
  3. API creation endpoint 不要求手工插 DB。
  4. 缺少 filepath/artifact 时返回明确错误。
  5. 入口只创建/触发 job，不假造完成状态。
- **测试台账项**：FT1-T04 / FT1-T05
- **收口标准**：CLI/API payload contract 通过。
- **风险提醒**：不要在 FT1 扩成完整 FT6 e2e run API。

### 5.3 Phase 3 — dataset/config 防假成功

- **Phase 目标**：防止空 dataset 和 artifact root 漂移污染后续阶段。
- **对应编号**：FT1-P3-01 / FT1-P3-02
- **修改文件**：`src/myvoiceclone/pipelines/export_dataset.py:46-147`, `src/myvoiceclone/api/routes_jobs.py:33-35`
- **具体功能预期**：
  1. empty rows 抛异常。
  2. 不写空 manifest artifact。
  3. dataset 不进入 frozen 状态。
  4. API runner 使用 env-aware artifact root。
- **测试台账项**：FT1-T06 / FT1-T07
- **收口标准**：fake-zero 和 artifact-root drift test 通过。
- **风险提醒**：已有测试若依赖空 freeze 成功，需要改为显式 fixture 数据。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Owner-gate non-blocking for AP drafting | 当前用户消息 + proposed planning | 不等待 owner-gate 制作 AP，但不把 gate 当已关闭 evidence | final 前按 evidence 复核 |
| `TR-1..TR-7` | `docs/eval/first-test/reference-anchor.md:187-195` | 本地 DB job、evidence、no mock fallback、大文件外置 | 回 reference-anchor |
| `FT1` proposed baseline | `docs/eval/first-test/proposed-planning.md:144-168` | 定义本 AP 工作项和测试项 | 回 proposed planning |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT1-1 | `src/myvoiceclone/cli.py:17` | CLI app entry | FT1-P1-01 | ✅ 复用 | 主命令入口 |
| A-FT1-2 | `src/myvoiceclone/cli.py:92-110` | current run diarize/helper | FT1-P2-01 | ♻️ 重 substrate | payload mismatch 落点 |
| A-FT1-3 | `src/myvoiceclone/jobs/runner.py:132-136` | preprocess_all payload contract | FT1-P2-01 | ✅ 复用 | runner 要求 filepath |
| A-FT1-4 | `src/myvoiceclone/api/routes_recordings.py:26-38` | current ingest job API | FT1-P2-02 | ♻️ 重 substrate | 扩展 preprocess job creation |
| A-FT1-5 | `src/myvoiceclone/pipelines/export_dataset.py:46-64` | segment query | FT1-P3-01 | ✅ 复用 | empty rows guard |
| A-FT1-6 | `src/myvoiceclone/api/routes_jobs.py:33-35` | artifact root config | FT1-P3-02 | ♻️ 重 substrate | 应改 resolve_artifact_root |
| A-FT1-7 | `src/myvoiceclone/config.py:42-68` | env resolvers | FT1-P1-03 / FT1-P3-02 | ✅ 复用 | canonical env |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 |
|----|--------------|--------|
| ⛔1 | 继续让真实 preprocess 依赖手工插 DB | `state-analysis` 已确认 API/CLI 入口不足 |
| ⛔2 | 空 manifest 仍 frozen success | 会污染 FT4/FT5 成功语义 |
| ⛔3 | API runner 绕开 env resolver | artifact 会落错 root，破坏 evidence pack |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-test/reference-anchor.md`。

---

## 9. 执行工作日志

- `2026-06-13 08:26 UTC` — [代码制作] 完成 FT1-P1/P2/P3：统一 README/ops 命令为 `myvoiceclone`；新增 `first-test` extra 与 bootstrap dependency probe；`.env.example` 对齐 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR/MOCK_ADAPTERS`；新增 CLI `run preprocess-all`，并让 `run diarize` 只创建单步 diarize job；新增 `POST /api/recordings/preprocess`；`routes_jobs` 改用 `resolve_artifact_root()`；dataset freeze 拒绝空 manifest。
- `2026-06-13 08:26 UTC` — [代码审查，测试与文档回填] 新增/扩展 FT1 测试覆盖 CLI payload、API preprocess job、runtime env resolvers、bootstrap dry-run、README command drift、empty manifest guard、API artifact root env resolver；执行 `./venv/bin/python -m pytest tests/cli/test_cli.py tests/api/test_routes.py tests/api/test_first_test_preflight.py tests/unit/test_project_config.py tests/unit/test_scripts_dry_run.py tests/unit/pipelines/test_export_dataset.py tests/unit/test_first_test_command_docs.py -q`，结果 `25 passed, 3 warnings`；执行 `./venv/bin/python -m pytest tests/unit/test_architecture_boundaries.py -q`，结果 `1 passed`。
- **安全 / 信任边界类工作项的威胁模型锚**：真实音频路径与 artifact root 是本 AP 信任边界。威胁是 path/env drift 导致读写非预期位置或 repo 内落大文件；锚定 `docs/eval/first-test/reference-anchor.md:189-195` 与 `src/myvoiceclone/config.py:42-68`。

---

## 8. 测试台账

### 8.1 测试清单

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据 |
|---------|--------|------|----|------|------|-----------|
| FT1-T01 | CLI/doc command drift | 短途 | unit/cli | 🔱 fork `tests/cli/test_cli.py` | FT1-P1-01 → 命令一致 | commit + pytest + run-time |
| FT1-T02 | bootstrap extras probe | 短途 | unit/script | 🔱 fork `tests/unit/test_scripts_dry_run.py` | FT1-P1-02 → extras 安装 | commit + pytest + run-time |
| FT1-T03 | env resolver drift | 短途 | unit/config | 🔱 fork `tests/unit/test_project_config.py` | FT1-P1-03 → env 对齐 | commit + pytest + run-time |
| FT1-T04 | CLI preprocess payload | 短途 | unit/cli/jobs | 🆕 新增 `tests/cli/test_cli.py::test_cli_preprocess_all_payload` | FT1-P2-01 → payload 可消费 | commit + pytest + run-time |
| FT1-T05 | API preprocess job creation | 短途 | api/TestClient | 🆕 新增 `tests/api/test_routes.py::test_create_preprocess_job` | FT1-P2-02 → pending job | commit + pytest + run-time |
| FT1-T06 | empty manifest guard | 短途 | unit/pipeline | 🔱 fork `tests/unit/pipelines/test_export_dataset.py` | FT1-P3-01 → no fake-zero | commit + pytest + run-time |
| FT1-T07 | artifact root resolver | 短途 | api/unit | 🆕 新增 `tests/api/test_first_test_preflight.py::test_run_job_uses_env_artifact_root` | FT1-P3-02 → env root | commit + pytest + run-time |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/cli/test_cli.py` | 🔱 fork | 加命令 drift 断言 | 已存在 |
| `tests/unit/test_scripts_dry_run.py` | 🔱 fork | 加 extras 字符串/探针断言 | 已存在 |
| `tests/unit/pipelines/test_export_dataset.py` | 🔱 fork | 加 empty rows failure | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest tests/cli tests/unit tests/api -q` | unit/api/cli | 每次 FT1 变更 |

### 8.4 测试缺口

- 不覆盖真实 PyAnnote/Demucs/Whisper 执行 → FT3。
- 不覆盖完整 API e2e run → FT6/FT7。

### 8.5 测试保真

- PASS 必带四元组；任何 live dependency 不在 FT1 假跑。
- path/env 安全边界必须验证 artifact 不落 repo 默认错误路径。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| CLI API 范围膨胀 | FT1 可能被扩大成完整 e2e API | medium | 只做 preprocess job creation |
| 旧测试依赖空 manifest | guard 会改变行为 | medium | 改 fixture，明确非空数据 |
| env path 写错 | 影响 evidence 外置 | medium | env resolver test |

### 9.2 约束与前提

- **技术前提**：不引入真实模型依赖。
- **运行时前提**：本地 SQLite 与 artifact root 可写。
- **组织协作前提**：owner-gate 不阻塞 AP 制作；执行关闭仍以 evidence 为准。
- **上线 / 合并前提**：FT1 测试全部通过。

### 9.3 文档同步要求

- `README.md`
- `docs/ops/local-setup.md`
- `.env.example`
- `docs/eval/first-test/proposed-planning.md` 如发现范围偏差需回注。

### 9.4 完成后的预期状态

1. first-test 操作者可按文档启动环境与 CLI。
2. CLI/API 均可创建可执行 preprocess job。
3. 空 dataset 不会 frozen success。
4. API job runner 使用正确 artifact root。

---

## 10. 收口

### 10.1 收口硬闸

1. CLI/config/script drift tests 全 PASS（FT1-T01..FT1-T03）。
2. preprocess CLI/API payload tests 全 PASS（FT1-T04..FT1-T05）。
3. fake-zero/artifact-root tests 全 PASS（FT1-T06..FT1-T07）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| 命令/env/bootstrap 对齐 | FT1-P1-01..03 | FT1-T01..03 | commit + pytest + run-time | 未观察 |
| preprocess 入口可用 | FT1-P2-01..02 | FT1-T04..05 | commit + pytest + run-time | 未观察 |
| no fake-zero / env artifact root | FT1-P3-01..02 | FT1-T06..07 | commit + pytest + run-time | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | FT1-P1..P3 全部收口 |
| 测试 | §8 测试台账全 PASS |
| 文档 | README/ops/env 更新 |
| 风险收敛 | 不再需要手工插 DB 跑 preprocess |
| 可交付性 | 可进入 FT2 与 FT3 |

### 10.4 NOT-成功识别

任一入口仍需手工 DB 操作、empty manifest 仍成功、artifact root 不尊重 env，均不得标 `executed`。
