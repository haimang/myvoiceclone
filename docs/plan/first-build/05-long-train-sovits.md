# Nano-Agent 行动计划：P5 Long-run So-VITS-SVC Track

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P5 Long-run So-VITS-SVC Track`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/05-long-train-sovits.md`
> 上游前序 / closure:
> - `03-corpus-dataset-freeze.md`
> - `04-quick-baselines.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:190`
> 下游交接:
> - `06-eval-inference-api.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:190`（P5 工作台账）
> 冻结决策来源:
> - `final-execution-plan.md:502`（Q1）
> - `final-execution-plan.md:507`（Q6）
> grounding 来源:
> - `final-execution-plan.md:194`、`:385`、`:438`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P5 将 P3 的 frozen dataset 和 P4 的 long-train gate 接入 So-VITS-SVC 长训轨。它的目标是把长时间训练封装在 adapter/job/run/report 合同内，而不是让业务层绑定某个训练仓库的内部结构。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P5 Long-run So-VITS-SVC Track`
- **本次计划解决的问题**：
  - 长训需要可 resume/cancel/checkpoint。
  - So-VITS-SVC 环境和命令需要 adapter 封装。
  - feature cache、checkpoint、model registry、report 需要血缘。
- **本次计划的直接产出**：
  - `sovits_adapter.py`, `Dockerfile.train`, `train.sovits.yaml`
  - feature cache contract, long job resume semantics
  - long-train report and model registry rows
- **本计划不重新讨论的设计结论**：
  - So-VITS-SVC 是 VC/SVC 长训候选，经 adapter 接入（来源：`final-execution-plan.md:502`）。
  - 长训必须记录 jobs/model_runs/artifacts/reports（来源：`final-execution-plan.md:507`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先环境与命令封装，再 feature cache，再长任务状态，再 registry/report”的方式。默认 unit suite 使用 fake So-VITS adapter，不启动真实训练；真实 CUDA/长训只作为 `gpu`/`slow` marker。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Train environment | M | Dockerfile.train 与 env digest | P4 gate |
| Phase 2 | So-VITS adapter | L | prepare/train/resume/export command contract | Phase 1 |
| Phase 3 | Feature cache | M | content units/F0/spec artifacts | Phase 2 |
| Phase 4 | Long job + registry | L | checkpoint/resume/cancel/model registry | Phase 3 |
| Phase 5 | Long-train report | M | loss/checkpoint/sample/failure report | Phase 4 |

### 1.3 Phase 说明

1. **Phase 1 — Train environment**
   - **核心目标**：记录 Docker/build/env digest，不幻想环境。
   - **为什么先做**：长训失败常来自环境。
2. **Phase 2 — So-VITS adapter**
   - **核心目标**：统一 prepare/train/resume/export 合同。
   - **为什么放在这里**：业务层不能直连训练仓库。
3. **Phase 3 — Feature cache**
   - **核心目标**：缓存 HuBERT/content units、F0、spec 等派生产物。
   - **为什么放在这里**：resume 和复现实验依赖 cache。
4. **Phase 4 — Long job + registry**
   - **核心目标**：checkpoint、resume、cancel、model_runs 血缘。
   - **为什么放在这里**：24h+ 训练必须可控。
5. **Phase 5 — Long-train report**
   - **核心目标**：训练结果和失败原因可审计。
   - **为什么放在这里**：P6 评估需要完整 run evidence。

### 1.4 执行策略说明

- **执行顺序原则**：P4 gate true 后启动 P5 live；unit fake 可先实现。
- **风险控制原则**：真实训练前必须有 small rehearsal。
- **测试推进原则**：unit fake -> gpu smoke -> slow rehearsal。
- **文档同步原则**：训练配置与 Docker/env digest 写入 report。
- **回滚 / 降级原则**：OOM/环境失败保留 failed run 和 artifacts，不删除 checkpoint。

### 1.5 本次 action-plan 影响结构图

```text
P5 Long Train
├── configs/pipelines/train.sovits.yaml
├── infra/docker/Dockerfile.train
├── src/myvoiceclone/adapters/training/sovits_adapter.py
├── src/myvoiceclone/pipelines/train.py
├── src/myvoiceclone/jobs/runner.py
├── models/checkpoints, models/registry
└── tests/unit/{adapters,jobs,eval}
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** Docker train environment plan and env digest capture。
- **[S2]** So-VITS-SVC adapter contract。
- **[S3]** feature cache artifact lineage。
- **[S4]** long job checkpoint/resume/cancel and model registry/report。

### 2.2 Out-of-Scope

- **[O1]** 真实 24h+ 训练作为默认 CI。
- **[O2]** 模型质量主观发布判断，交给 P6/P7。
- **[O3]** RVC/TTS baseline，已由 P4 处理。
- **[O4]** API/CLI routes，交给 P6。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| fake So-VITS adapter | in-scope | unit contract | live/gpu 启动 |
| actual long train | defer | slow/gpu marker | P4 gate true |
| env digest | in-scope | 可复现长训 | 无 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P5-01 | Phase 1 | Dockerfile.train + env digest | add | `infra/docker/Dockerfile.train`, `configs/models.yaml` | build plan 和 env digest 记录 | P5-T01 | high |
| P5-02 | Phase 2 | So-VITS adapter | add | `adapters/training/sovits_adapter.py` | fake command/artifact contract | P5-T02 | high |
| P5-03 | Phase 3 | Feature cache | add | `pipelines/train.py`, `data/artifacts/jobs/` | cache 可命中可失效 | P5-T03 | medium |
| P5-04 | Phase 4 | Long job resume/cancel | update | `jobs/runner.py` | resume 后 lineage 不断链 | P5-T04 | high |
| P5-05 | Phase 4 | Model registry | add/update | `models/registry/`, `model_runs` | run 可复现 | P5-T05 | medium |
| P5-06 | Phase 5 | Long-train report | add | `eval/report.py`, `data/artifacts/reports/` | report 链接 checkpoints/artifacts | P5-T06 | medium |

---

## 4. Phase 业务表格

### 4.1 Phase 1/2 — Environment + adapter

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P5-01 | Dockerfile.train + env digest | a) 写训练镜像依赖占位；b) 不写死 CUDA 幻想版本；c) env digest 捕获 python/torch/cuda/git/config；d) digest 入 model_run/report | `infra/docker/Dockerfile.train` | 环境可追溯 | P5-T01 | digest fixture PASS |
| P5-02 | So-VITS adapter | a) `prepare(dataset)`；b) `train(run)`；c) `resume(checkpoint)`；d) `export(checkpoint)`；e) 统一 TrainResult；f) 外部命令失败映射为 run failed | `sovits_adapter.py` | 训练仓库被隔离 | P5-T02 | fake adapter PASS |

### 4.2 Phase 3/4 — Feature cache + long job

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P5-03 | Feature cache | a) 为 manifest 生成 feature cache key；b) content/F0/spec 作为 artifacts；c) cache hit 时复用；d) config/hash 变化时失效 | `pipelines/train.py` | feature 可复现 | P5-T03 | cache hit/miss PASS |
| P5-04 | Long job resume/cancel | a) model_run 按 `queued -> preparing -> training -> checkpointed -> succeeded/failed/canceled` 迁移；b) checkpoint event；c) runner 周期性检查 cancel flag；d) resume 使用同 model_run lineage；e) failed 保留 checkpoint；f) timeout/OOM 写 reason | `jobs/runner.py` | 长训可控 | P5-T04 | resume/cancel PASS |
| P5-05 | Model registry | a) registry 记录 manifest id/config/checkpoint/eval score；b) snapshots 写 `models/registry/`；c) DB 与 file snapshot 对齐 | `models/registry/`, `model_runs` | 实验可复现 | P5-T05 | registry query PASS |

### 4.3 Phase 5 — Report

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P5-06 | Long-train report | a) 汇总 env/config/dataset/checkpoints；b) loss 曲线 artifact 占位；c) rendered samples linkage；d) failed reason；e) report row 按 `draft -> generated` 写状态事件 | `eval/report.py` | P6 可评估 | P5-T06 | report fixture PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2 — Environment + adapter

- **Phase 目标**：将 So-VITS-SVC 作为可替换 adapter，而不是业务核心。
- **本 Phase 对应编号**：P5-01 / P5-02
- **本 Phase 新增文件**：`Dockerfile.train`, `sovits_adapter.py`, `configs/pipelines/train.sovits.yaml`
- **具体功能预期**：
  1. adapter 只暴露标准 prepare/train/resume/export。
  2. 环境 digest 每次 run 固定记录。
  3. command construction 可 unit test。
  4. 真实训练失败不会让 run 状态悬空。
  5. 外部仓 commit/path 只在 config/report 中出现。
- **对应测试台账项**：P5-T01 / P5-T02
- **收口标准**：fake train path 生成 checkpoint artifact。
- **本 Phase 风险提醒**：真实 CUDA 兼容性只由 gpu smoke 证明，不由文档保证。

### 5.2 Phase 3/4/5 — Long run control

- **Phase 目标**：长训可恢复、可取消、可审计、可报告。
- **本 Phase 对应编号**：P5-03..P5-06
- **本 Phase 新增 / 修改文件**：`pipelines/train.py`, `jobs/runner.py`, `models/registry/`, `eval/report.py`
- **具体功能预期**：
  1. cache key 包含 manifest hash 和 config hash。
  2. checkpoint 每次写 artifact。
  3. resume 不新建无关 run lineage。
  4. cancel 后状态为 canceled，不误标 failed。
  5. report 能解释 succeeded/failed/canceled 三类结果。
- **对应测试台账项**：P5-T03..P5-T06
- **收口标准**：long train fake journey 产生 registry 和 report。
- **本 Phase 风险提醒**：不要把长期训练日志只留在 stdout。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q1 | `final-execution-plan.md:502` | So-VITS-SVC adapter 主线候选 | 换 adapter 不改 domain |
| Q6 | `final-execution-plan.md:507` | run/artifact/report 必填 | 不得裸跑训练脚本 |
| Q7 | `final-execution-plan.md:508` | live/gpu/slow 不默认跑 | 单独 marker |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-1 | `final-execution-plan.md:190` | P5 工作台账 | P5-01..06 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:385` | `train.sovits.yaml` | P5-02 | ✅ 复用 | config |
| A-3 | `final-execution-plan.md:438` | `sovits_adapter.py` | P5-02 | ✅ 复用 | adapter |
| A-4 | `final-execution-plan.md:457` | checkpoints/registry | P5-05 | ✅ 复用 | artifacts |
| A-5 | `final-execution-plan.md:466` | `Dockerfile.train` | P5-01 | ✅ 复用 | infra |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 长训脚本绕过 jobs/model_runs | Q6 要可审计 |
| ⛔2 | resume 新建无关 run | lineage 断裂 |
| ⛔3 | CUDA 版本写死不实测 | final 要环境实测 |
| ⛔4 | failed run 删除 checkpoint | debugging/recovery 需要 artifact |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：P5 不执行 release；P7 锚为 `final-execution-plan.md:213`。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据（四元组） |
|---------|--------|------|----|------|------|-----------|
| P5-T01 | env digest capture | 短途 | unit | 🆕 新增 `tests/unit/eval/test_env_digest.py` | P5-01 → env report | commit {sha} + pytest tests/unit/eval/test_env_digest.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P5-T02 | So-VITS fake prepare/train/export | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_sovits_adapter.py` | P5-02 → adapter contract | commit {sha} + pytest tests/unit/adapters/test_sovits_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P5-T03 | feature cache hit/miss | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_feature_cache.py` | P5-03 → cache 可控 | commit {sha} + pytest tests/unit/pipelines/test_feature_cache.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P5-T04 | resume/cancel state machine | 短途 | unit | 🆕 新增 `tests/unit/jobs/test_resume.py` | P5-04 → lineage 不断 | commit {sha} + pytest tests/unit/jobs/test_resume.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P5-T05 | model registry query | 短途 | unit | 🆕 新增 `tests/unit/storage/test_model_registry.py` | P5-05 → 可复现 | commit {sha} + pytest tests/unit/storage/test_model_registry.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P5-T06 | long train report | 短途 | unit | 🆕 新增 `tests/unit/eval/test_train_report.py` | P5-06 → report 入库 | commit {sha} + pytest tests/unit/eval/test_train_report.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P4 long_train_ready gate fixture | ♻️ 沿用 | gate true/false 输入 | P4 完成后可用 |
| P1 job/model_run schema tests | ♻️ 沿用 | 回归 lineage | P1 完成后可用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit tests/unit/adapters tests/unit/jobs tests/unit/eval` | unit | 每次 P5 改动 |
| spike | `pytest -m gpu` | live/gpu | 小规模训练 rehearsal |
| mega | 不适用 | - | P8 |
| soak | `pytest -m slow` | slow | 长训前手动 |

### 8.4 测试缺口

- 不覆盖 24h+ 真实收敛质量（理由：不能作为默认测试）→ P5 slow rehearsal/P6 eval。

### 8.5 测试保真

- fake train PASS 不代表 CUDA 可用。
- gpu/slow 失败不得用 unit PASS 掩盖。
- cancel/resume 必须验证 terminal state。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| CUDA/PyTorch 不兼容 | 长训无法启动 | high | env digest + gpu smoke |
| OOM/长训中断 | checkpoint 丢失 | high | resume/cancel tests |
| 外部仓维护风险 | So-VITS 依赖老旧 | medium | adapter + lock commit |

### 9.2 约束与前提

- **技术前提**：P3 manifest 和 P4 gate 可用。
- **运行时前提**：默认 fake adapter，真实训练手动。
- **组织协作前提**：GPU 资源可用时再跑 slow。
- **上线 / 合并前提**：P5 unit 全 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：training adapter contract。
- 需要同步更新的说明文档 / README：P8 train docs。
- 需要同步更新的测试说明：gpu/slow marker。

### 9.4 完成后的预期状态

1. So-VITS long run 可通过 job/model_run 跟踪。
2. Checkpoint 和 report 可被 P6 eval 消费。
3. 环境和配置可复现。

---

## 10. 收口

### 10.1 收口硬闸

1. Adapter fake prepare/train/export PASS。
2. Resume/cancel/checkpoint lineage PASS。
3. Long-train report 入库并链接 artifacts。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组） | 状态 |
|----------|--------|---------|-----------|------|
| env digest | P5-01 | P5-T01 | commit {sha} + pytest tests/unit/eval/test_env_digest.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| adapter contract | P5-02 | P5-T02 | commit {sha} + pytest tests/unit/adapters/test_sovits_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| feature cache | P5-03 | P5-T03 | commit {sha} + pytest tests/unit/pipelines/test_feature_cache.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| resume/cancel | P5-04 | P5-T04 | commit {sha} + pytest tests/unit/jobs/test_resume.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| registry | P5-05 | P5-T05 | commit {sha} + pytest tests/unit/storage/test_model_registry.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| train report | P5-06 | P5-T06 | commit {sha} + pytest tests/unit/eval/test_train_report.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | long-run contract, registry, report 完成 |
| 测试 | P5-T01..P5-T06 全 PASS |
| 文档 | GPU/slow 限制写明 |
| 风险收敛 | 环境、resume、checkpoint 风险可诊断 |
| 可交付性 | 可进入 P6 |

### 10.4 NOT-成功识别

长训绕过 job/model_run、resume 断链、或真实环境失败被标成成功，均不得标 `executed`。
