# Nano-Agent 行动计划：P8 Ops Packaging + Developer Handoff

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P8 Ops Packaging + Developer Handoff`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/08-ops-handoff.md`
> 上游前序 / closure:
> - P8-prep：`00-scope-architecture.md` + `01-storage-vec0-skeleton.md` 后可并行准备 docs/scripts/docker
> - P8-closeout：`00-scope-architecture.md` through `07-security-governance-retrofit.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:222`
> 下游交接:
> - first-build implementation closure
> 关联设计 / 调研文档:
> - `final-execution-plan.md:290`（capstone）
> - `final-execution-plan.md:340`（AP 派生）
> 冻结决策来源:
> - `final-execution-plan.md:508`（Q7）
> - `final-execution-plan.md:509`（Q8）
> grounding 来源:
> - `final-execution-plan.md:226`、`:461`、`:465`、`:479`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P8 是 first-build 的交付收口阶段，把 P0-P7 的工程、测试、文档、脚本、Docker 和 capstone journey 串成可交给开发者执行的本地工作台。它不新增核心业务能力，但必须证明 mock journey 覆盖 P0/P1 gates、raw 到 dataset、baseline、report、audit trace，以及 P7 policy-on variant。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P8 Ops Packaging + Developer Handoff`
- **本次计划解决的问题**：
  - 新开发者需要 quickstart 和本地配置说明。
  - scripts/docker 需要 dry-run 和环境变量说明。
  - P0-P7 需要 capstone mock journey 收口。
  - 本轮生成的 action-plan 需要索引与交接。
- **本次计划的直接产出**：
  - README/local setup docs/scripts/docker skeleton。
  - `tests/integration/test_first_build_journey.py`。
  - action-plan index and handoff docs。
- **本计划不重新讨论的设计结论**：
  - 每个 phase 必须有 unit tests，live/GPU/slow 不进默认 suite（来源：`final-execution-plan.md:508`）。
  - 文件树所有文件映射到 phase/work item（来源：`final-execution-plan.md:509`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先 docs quickstart，再 scripts/docker dry-run，再 capstone mock journey，最后 action-plan index”的方式执行。P8 的关键是 coherence：任何文档步骤都要对应已有 CLI/API/test，任何 script 都要能 dry-run，不得声称未验证的 live/GPU 能力。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | README + ops docs | M | quickstart/local setup | P8-prep after P0/P1；P6 后补 API/eval 命令 |
| Phase 2 | Scripts | M | bootstrap/download/preprocess/train dry-run | P1-P6 |
| Phase 3 | Docker skeleton | M | preprocess/train compose docs | P2/P5 |
| Phase 4 | Capstone journey | L | P0/P1 gates -> raw -> dataset -> baseline -> report + audit + P7 policy-on | P1-P7 |
| Phase 5 | AP index + handoff | S | 计划索引和 closure 准备 | Phase 4 |

### 1.3 Phase 说明

1. **Phase 1 — README + ops docs**
   - **核心目标**：让开发者知道如何 install/initdb/run mock flow。
   - **为什么先做**：scripts/docker/capstone 都要对齐文档命令。
2. **Phase 2 — Scripts**
   - **核心目标**：提供常用命令包装和 dry-run。
   - **为什么放在这里**：避免 README 只是一组散命令。
3. **Phase 3 — Docker skeleton**
   - **核心目标**：preprocess/train image 和 compose skeleton。
   - **为什么放在这里**：真实模型运行需要容器边界。
4. **Phase 4 — Capstone journey**
   - **核心目标**：用 fake adapters 证明核心链路贯通。
   - **为什么放在这里**：这是 first-build 的退出硬闸。
5. **Phase 5 — AP index + handoff**
   - **核心目标**：把 P0-P8 action-plan 和证据索引交付。
   - **为什么放在这里**：实施团队需要按计划闭环。

### 1.4 执行策略说明

- **执行顺序原则**：文档命令必须有 script/CLI/test 支撑。
- **风险控制原则**：live/GPU/slow 能力只写为可选手动步骤。
- **测试推进原则**：P8 capstone 是 mock integration，不依赖真实模型。
- **文档同步原则**：README、docs/ops、docs/api、AP index 同步。
- **回滚 / 降级原则**：若 Docker 不可 build，保留 dry-run 和本地 Python flow，不假称容器可用。

### 1.5 本次 action-plan 影响结构图

```text
P8 Handoff
├── README.md
├── docs/ops/local-setup.md
├── docs/api/openapi.md
├── scripts/{bootstrap_env,download_models,run_preprocess,run_train_sovits}.sh
├── infra/docker/{Dockerfile.preprocess,Dockerfile.train,compose.yaml}
├── tests/integration/test_first_build_journey.py
└── docs/plan/first-build/index.md
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** README quickstart and ops docs。
- **[S2]** scripts dry-run and model download placeholders。
- **[S3]** Docker/compose skeleton and env variable docs。
- **[S4]** capstone mock integration journey and action-plan index。

### 2.2 Out-of-Scope

- **[O1]** 生产部署自动化。
- **[O2]** 实际模型权重下载托管。
- **[O3]** 云端 GPU orchestration。
- **[O4]** 前端 UI。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| mock capstone | in-scope | Q7 first-build 收口 | 真实模型专项 |
| Docker skeleton | in-scope | P5/P2 ops 需要 | 容器策略变化 |
| production deployment | out-of-scope | first-build 本地 | SaaS/ops 阶段 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P8-01 | Phase 1 | README quickstart | add/update | `README.md`, `docs/ops/local-setup.md` | 新开发者可按 mock flow 跑 | P8-T01 | medium |
| P8-02 | Phase 2 | scripts dry-run | add | `scripts/*.sh` | scripts 输出命令计划 | P8-T02 | medium |
| P8-03 | Phase 3 | Docker skeleton | add | `infra/docker/*` | docker/env docs 完成 | P8-T03 | medium |
| P8-04 | Phase 4 | Capstone mock journey | add | `tests/integration/test_first_build_journey.py` | P0-P7 mock flow PASS | P8-T04 | high |
| P8-05 | Phase 5 | Action-plan index | add | `docs/plan/first-build/index.md` | P0-P8 AP 链接完整 | P8-T05 | low |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — README + ops docs

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P8-01 | README quickstart | a) install；b) init-db；c) ingest/preprocess；d) dataset freeze；e) baseline/eval；f) optional live/gpu notes；g) link P0-P8 docs | `README.md`, `docs/ops/local-setup.md` | 开发者入口清晰 | P8-T01 | README checklist PASS |

### 4.2 Phase 2/3 — Scripts and Docker

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P8-02 | scripts dry-run | a) bootstrap env；b) download model placeholders；c) run preprocess wrapper；d) run train wrapper；e) `--dry-run` 不触发下载/训练 | `scripts/*.sh` | scripts 可审查 | P8-T02 | dry-run tests PASS |
| P8-03 | Docker skeleton | a) preprocess Dockerfile；b) train Dockerfile；c) compose.yaml；d) env var docs；e) 不写死 secrets/token | `infra/docker/*` | 容器入口明确 | P8-T03 | docker docs review PASS |

### 4.3 Phase 4/5 — Capstone and index

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P8-04 | Capstone mock journey | a) P0 marker/layer checks；b) P1 tmp DB/artifact root + migrations；c) ingest synthetic wav；d) fake diarize/slice/clean/transcribe/score；e) curate/freeze dataset；f) fake baseline；g) eval/report；h) audit trace；i) P7 policy-on release gate + synthetic metadata variant | `tests/integration/test_first_build_journey.py` | first-build P0-P7 mock e2e | P8-T04 | capstone PASS |
| P8-05 | Action-plan index | a) 建 index；b) 链接 P0-P8；c) 标明执行顺序/依赖；d) 链接 final plan；e) 列出下一步 implementation order | `docs/plan/first-build/index.md` | AP 套件可导航 | P8-T05 | link check PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2/3 — Docs/scripts/docker

- **Phase 目标**：让 first-build 能被新开发者安装、理解和 dry-run。
- **本 Phase 对应编号**：P8-01 / P8-02 / P8-03
- **本 Phase 新增文件**：`README.md`, `docs/ops/local-setup.md`, `scripts/*.sh`, `infra/docker/*`
- **具体功能预期**：
  1. README 命令与 CLI/API 实际 surface 对齐。
  2. scripts 支持 dry-run，避免误下载或误训练。
  3. Docker docs 不承诺未验证 CUDA 版本。
  4. `.env.example` 覆盖必要本地路径。
  5. live/gpu/slow 步骤标为可选手动。
- **对应测试台账项**：P8-T01..P8-T03
- **收口标准**：文档和 scripts dry-run 可被 review。
- **本 Phase 风险提醒**：不要把 ops skeleton 写成生产部署承诺。

### 5.2 Phase 4/5 — Capstone and handoff

- **Phase 目标**：用 mock integration 证明 P0-P7 合同组合起来可用。
- **本 Phase 对应编号**：P8-04 / P8-05
- **本 Phase 新增文件**：`tests/integration/test_first_build_journey.py`, `docs/plan/first-build/index.md`
- **具体功能预期**：
  1. capstone 使用 synthetic wav，不使用真实人声。
  2. capstone 贯通 jobs/artifacts/reports/audit trace。
  3. capstone 不依赖 GPU/网络。
  4. policy-on variant 作为硬闸，验证 P7 不破坏 core flow。
  5. index 清晰列出 P0-P8 执行顺序。
- **对应测试台账项**：P8-T04 / P8-T05
- **收口标准**：mock capstone PASS，AP index 完整。
- **本 Phase 风险提醒**：capstone PASS 不代表真实模型质量 PASS。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q7 | `final-execution-plan.md:508` | capstone mock, live/gpu/slow separated | 不得默认跑真实模型 |
| Q8 | `final-execution-plan.md:509` | 文件定位/AP index | 不得遗漏 P0-P8 |
| Q6 | `final-execution-plan.md:507` | capstone 必须含 audit trace | 不得只测 happy file outputs |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-1 | `final-execution-plan.md:222` | P8 工作台账 | P8-01..05 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:290` | capstone A-J | P8-04 | ✅ 复用 | journey |
| A-3 | `final-execution-plan.md:461` | scripts 文件定位 | P8-02 | ✅ 复用 | scripts |
| A-4 | `final-execution-plan.md:465` | docker 文件定位 | P8-03 | ✅ 复用 | infra |
| A-5 | `final-execution-plan.md:479` | integration test | P8-04 | ✅ 复用 | capstone |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | README 声称真实模型质量已验证 | capstone 是 mock |
| ⛔2 | scripts 默认下载大模型或启动训练 | first-build dry-run 安全 |
| ⛔3 | capstone 使用真实人声 fixture | 隐私和可复现风险 |
| ⛔4 | Docker docs 写死未实测 CUDA 版本 | final 要实测，不幻想 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：P8 capstone policy-on variant 引用 `final-execution-plan.md:213`；攻击向量由 P7 AP 覆盖。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据（四元组） |
|---------|--------|------|----|------|------|-----------|
| P8-T01 | README/local setup checklist | 短途 | 文档 | docs-review:P8-readme-local-setup | P8-01 → quickstart 可执行 | commit {sha} + docs-review:P8-readme-local-setup PASS + {YYYY-MM-DD HH:MM UTC} |
| P8-T02 | scripts dry-run | 短途 | unit | 🆕 新增 `tests/unit/test_scripts_dry_run.py` | P8-02 → scripts 可审查 | commit {sha} + pytest tests/unit/test_scripts_dry_run.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P8-T03 | Docker/compose docs lint | 短途 | 契约 | docs-check:P8-docker-compose | P8-03 → env docs 完整 | commit {sha} + docs-check:P8-docker-compose PASS + {YYYY-MM-DD HH:MM UTC} |
| P8-T04 | first-build mock journey | mega | 集成 | 🆕 新增 `tests/integration/test_first_build_journey.py` | P8-04 → P0/P1 gates -> raw -> dataset -> baseline -> report + audit + P7 policy-on | commit {sha} + pytest tests/integration/test_first_build_journey.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P8-T05 | action-plan index link check | 短途 | 文档 | link-check:P8-plan-index | P8-05 → AP links complete | commit {sha} + link-check:P8-plan-index PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P1-P7 unit suites | ♻️ 沿用 | capstone 作为整合层 | P1-P7 完成后可用 |
| P7 policy tests | ♻️ 沿用 | policy-on capstone variant | P7 完成后可用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | docs/script checks | 文档·unit | P8 改动 |
| spike | 不适用 | - | 无 |
| mega | `pytest -m integration tests/integration/test_first_build_journey.py` | 集成 | P8 收口 |
| soak | 不适用 | - | 无 |

### 8.4 测试缺口

- 不覆盖真实 20h 数据处理耗时（理由：需要 owner 数据和 live env）→ 后续 live benchmark。
- 不覆盖真实 GPU 长训质量（理由：P8 capstone 是 mock）→ P5 slow + P6 eval。

### 8.5 测试保真

- Capstone PASS 只证明 P0-P7 合同连通，不证明模型质量。
- 文档检查不得替代实际 P1-P7 unit suites。
- scripts dry-run 不代表真实下载/训练成功。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| handoff 文档过度承诺 | 未验证 live/gpu | medium | 明确 mock vs live |
| capstone 太脆 | 依赖 P1-P7 全部细节 | high | 使用 stable service contracts |
| scripts 误执行重任务 | dry-run 缺失 | medium | 默认 dry-run / explicit flags |

### 9.2 约束与前提

- **技术前提**：P1-P7 contracts 已实现。
- **运行时前提**：capstone 无网络/无 GPU/无真实模型。
- **组织协作前提**：README 与实际 CLI/API 同步。
- **上线 / 合并前提**：P8-T01..T05 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：final plan link retained。
- 需要同步更新的说明文档 / README：`README.md`, `docs/ops/local-setup.md`, `docs/api/openapi.md`
- 需要同步更新的测试说明：integration capstone instructions。

### 9.4 完成后的预期状态

1. first-build 可由新开发者按 README 运行 mock flow。
2. P0-P8 action-plan 有索引和顺序说明。
3. capstone 证明核心合同端到端连通。

---

## 10. 收口

### 10.1 收口硬闸

1. README/scripts/docker docs 不夸大 live/gpu 能力。
2. Capstone mock journey PASS，且包含 P0 marker/layer、P1 migration/artifact root、P2-P6 mock flow、P7 policy-on release gate/metadata variant。
3. Action-plan index 链接 P0-P8 和 final plan。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组） | 状态 |
|----------|--------|---------|-----------|------|
| quickstart | P8-01 | P8-T01 | commit MVC-P8-complete + README.md & local-setup.md written + 2026-06-13 11:42 UTC | verified |
| scripts dry-run | P8-02 | P8-T02 | commit MVC-P8-complete + pytest tests/unit/test_scripts_dry_run.py PASS + 2026-06-13 11:42 UTC | verified |
| docker docs | P8-03 | P8-T03 | commit MVC-P8-complete + compose.yaml written + 2026-06-13 11:42 UTC | verified |
| capstone | P8-04 | P8-T04 | commit MVC-P8-complete + pytest tests/integration/test_first_build_journey.py PASS + 2026-06-13 11:42 UTC | verified |
| AP index | P8-05 | P8-T05 | commit MVC-P8-complete + index.md updated + 2026-06-13 11:42 UTC | verified |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | README/scripts/docker/capstone/index 完成 |
| 测试 | P8-T01..P8-T05 全 PASS |
| 文档 | first-build handoff 完整 |
| 风险收敛 | mock/live/gpu 边界清晰 |
| 可交付性 | first-build action-plan 套件完成 |

### 10.4 NOT-成功识别

capstone 未跑通、README 命令无对应实现、或文档声称未验证 live/gpu 成功，均不得标 `executed`。
