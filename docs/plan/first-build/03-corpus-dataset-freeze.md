# Nano-Agent 行动计划：P3 Corpus Curation + Dataset Freeze

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P3 Corpus Curation + Dataset Freeze`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/03-corpus-dataset-freeze.md`
> 上游前序 / closure:
> - `02-preprocess-pipeline.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:169`
> 下游交接:
> - `04-quick-baselines.md`
> - `05-long-train-sovits.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:169`（P3 工作台账）
> - `final-execution-plan.md:393`（dataset 文件定位）
> 冻结决策来源:
> - `final-execution-plan.md:504`（Q3）
> - `final-execution-plan.md:507`（Q6）
> grounding 来源:
> - `final-execution-plan.md:173`、`:393`、`:424`、`:455`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P3 将 P2 生成的 scored segments 转成可训练、可复现、可审计的 frozen dataset。核心不是“尽量多塞数据”，而是通过 review queue、embedding dedupe、speaker purity、split leak detection 和 manifest checksum，把训练输入冻结成后续 P4/P5 可消费的稳定合同。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P3 Corpus Curation + Dataset Freeze`
- **本次计划解决的问题**：
  - scored segments 需要人工/规则审查状态。
  - embedding 检索和去重要落到 `vec0` 与 report。
  - train/val/test split 必须避免同源录音泄漏。
  - frozen manifest 必须不可变且可校验。
- **本次计划的直接产出**：
  - `pipelines/curate.py`, `export_dataset.py`
  - embedding adapters and vector upsert jobs
  - corpus audit report and dataset manifest
- **本计划不重新讨论的设计结论**：
  - `vec0` 是默认向量检索底座（来源：`final-execution-plan.md:504`）。
  - 业务流转必须可审计（来源：`final-execution-plan.md:507`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先 review 状态，再 embedding 检索，再 split/manifest freeze，最后 report”的顺序。P3 是模型训练前的硬闸，任何 P4/P5 训练都只能读取 frozen manifest，不能直接扫 `data/processed/`。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Review queue | M | keep/drop/needs_review/fixed 状态流转 | P2 |
| Phase 2 | Embedding + dedupe | M | speaker/audio/text embedding 检索与去重 | Phase 1 |
| Phase 3 | Split + freeze | M | 防泄漏 split 与 manifest checksum | Phase 2 |
| Phase 4 | Corpus report | S | 输出 audit report | Phase 3 |

### 1.3 Phase 说明

1. **Phase 1 — Review queue**
   - **核心目标**：让 segment 从 scored 状态进入人工/规则审查队列。
   - **为什么先做**：manifest 只能包含 keep/fixed。
2. **Phase 2 — Embedding + dedupe**
   - **核心目标**：用 `vec0` 做 speaker purity 和重复片段召回。
   - **为什么放在这里**：减少训练集污染。
3. **Phase 3 — Split + freeze**
   - **核心目标**：生成不可变 manifest 和 train/val/test split。
   - **为什么放在这里**：P4/P5 的输入合同在此冻结。
4. **Phase 4 — Corpus report**
   - **核心目标**：审计数据质量、drop reason、split 分布。
   - **为什么放在这里**：为 P4/P5 gate 提供 evidence。

### 1.4 执行策略说明

- **执行顺序原则**：审查状态先于 manifest，manifest 先于训练。
- **风险控制原则**：同一 recording 不得跨 split；重复片段默认不进入同一 manifest。
- **测试推进原则**：固定小向量 + synthetic segment fixtures。
- **文档同步原则**：manifest 格式写入 docs 或 P8 README。
- **回滚 / 降级原则**：embedding 缺失时 segment 保持 needs_review，不直接 keep。

### 1.5 本次 action-plan 影响结构图

```text
P3 Corpus
├── src/myvoiceclone/pipelines/{curate,export_dataset}.py
├── src/myvoiceclone/adapters/embeddings/*
├── src/myvoiceclone/eval/report.py
├── data/datasets/first-build/{manifest.jsonl,train,val,test}
├── data/artifacts/reports/corpus-audit.*
└── tests/unit/{pipelines,eval}
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** review queue 和 segment status 更新。
- **[S2]** embedding jobs、vec0 upsert/search、dedupe decisions。
- **[S3]** train/val/test split leak detection。
- **[S4]** frozen dataset manifest 和 corpus audit report。

### 2.2 Out-of-Scope

- **[O1]** 模型训练，交给 P4/P5。
- **[O2]** API/CLI review UX，交给 P6。
- **[O3]** 真实 speaker embedding 模型质量评估，live marker 后置。
- **[O4]** 发布安全 gate，交给 P7。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| frozen manifest | in-scope | P4/P5 输入合同 | manifest 格式不满足训练 adapter |
| API review route | out-of-scope | P6 负责 API | P6 开始 |
| embedding dedupe | in-scope | Q3/Q6 支撑 | vec0 不可用时 defer |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P3-01 | Phase 1 | Segment review queue | add | `pipelines/curate.py` | keep/drop/fixed 可审计 | P3-T01 | medium |
| P3-02 | Phase 2 | Embedding upsert jobs | add | `adapters/embeddings/*.py`, `storage/vec0_store.py` | vec0 search stable | P3-T02 | high |
| P3-03 | Phase 2 | Embedding-based dedupe | add | `pipelines/curate.py` | 重复片段不进同一 manifest | P3-T03 | medium |
| P3-04 | Phase 3 | Train/val/test split | add | `pipelines/export_dataset.py` | source recording 不泄漏 | P3-T04 | high |
| P3-05 | Phase 3 | Dataset manifest freeze | add | `export_dataset.py`, `data/datasets/first-build/manifest.jsonl` | manifest checksum 稳定 | P3-T05 | high |
| P3-06 | Phase 4 | Corpus audit report | add | `eval/report.py`, `data/artifacts/reports/` | JSON/Markdown report 入库 | P3-T06 | medium |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Review queue

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-01 | Segment review queue | a) 查询 scored segments；b) 支持 keep/drop/needs_review/fixed；c) 写 segment_reviews append-only；d) 状态变更写 job_event/report metadata；e) reason 必填 | `pipelines/curate.py` | 审查状态可追踪 | P3-T01 | transition tests PASS |

### 4.2 Phase 2 — Embedding + dedupe

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-02 | Embedding upsert jobs | a) speaker/audio/text embedder 返回固定维度；b) 写 embedding_models/embedding_jobs；c) upsert vec0；d) search 返回 distance/order | `adapters/embeddings/*.py` | 相似检索可用 | P3-T02 | fixed vectors PASS |
| P3-03 | Embedding-based dedupe | a) 对 keep candidates 搜近邻；b) 标记 duplicate cluster；c) 保留质量最高项；d) 将 drop reason 写 review/report | `pipelines/curate.py` | duplicate 不进入 manifest | P3-T03 | dedupe fixture PASS |

### 4.3 Phase 3 — Split + freeze

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-04 | Train/val/test split | a) 按 recording/source group；b) 只使用 keep/fixed；c) 检查同一 recording 不跨 split；d) 输出 split rows | `export_dataset.py` | split 无泄漏 | P3-T04 | leak detector PASS |
| P3-05 | Dataset manifest freeze | a) 生成 manifest.jsonl；b) 每行含 segment/artifact/hash/split/metadata；c) 计算 manifest_sha256；d) dataset status -> frozen；e) frozen 后拒绝变更 | `export_dataset.py` | manifest 不可变 | P3-T05 | checksum immutable PASS |

### 4.4 Phase 4 — Corpus report

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-06 | Corpus audit report | a) 汇总总时长/keep 时长/drop reason；b) speaker purity/noise/quality 分布；c) split 分布；d) 输出 JSON+Markdown artifact；e) reports row 按 `draft -> generated` 写状态事件 | `eval/report.py` | P4/P5 可消费 evidence | P3-T06 | report fixture PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2 — Review + embedding

- **Phase 目标**：把 scored segments 变成经审查和去重的 candidates。
- **本 Phase 对应编号**：P3-01 / P3-02 / P3-03
- **本 Phase 新增文件**：`pipelines/curate.py`, `adapters/embeddings/*.py`
- **具体功能预期**：
  1. 状态迁移有 reason 和 reviewer。
  2. embedding 维度与 namespace 固定。
  3. vector search 返回可排序距离。
  4. duplicate cluster 有可解释决策。
  5. embedding 缺失不会静默 keep。
- **对应测试台账项**：P3-T01..P3-T03
- **收口标准**：review + dedupe fixture 产生稳定 candidate set。
- **本 Phase 风险提醒**：embedding 相似不等于绝对重复，需要保留人工 review 覆盖。

### 5.2 Phase 3/4 — Freeze + report

- **Phase 目标**：冻结训练输入合同并输出 audit evidence。
- **本 Phase 对应编号**：P3-04 / P3-05 / P3-06
- **本 Phase 新增文件**：`pipelines/export_dataset.py`, `eval/report.py`
- **具体功能预期**：
  1. manifest 只包含可追溯 artifact。
  2. split 以 recording/source 为 group。
  3. manifest checksum 存 DB。
  4. frozen dataset 不允许追加 segment。
  5. report 能被 P4/P5 gate 读取。
- **对应测试台账项**：P3-T04..P3-T06
- **收口标准**：frozen manifest + corpus audit report 同时存在。
- **本 Phase 风险提醒**：不要让训练 adapter 直接读非 frozen 目录。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q3 | `final-execution-plan.md:504` | vec0 检索 | 使用 Null store 时标 degraded |
| Q6 | `final-execution-plan.md:507` | review/report/artifact 可审计 | 不得只生成本地文件 |
| Q7 | `final-execution-plan.md:508` | unit tests 默认无真实音频 | live embedding 后置 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `final-execution-plan.md:169` | P3 工作台账 | P3-01..06 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:393` | dataset 文件定位 | P3-04..05 | ✅ 复用 | manifest/splits |
| A-3 | `final-execution-plan.md:424` | curate/export 文件定位 | P3-01/P3-05 | ✅ 复用 | source 落点 |
| A-4 | `final-execution-plan.md:434` | embedding adapter 文件定位 | P3-02 | ✅ 复用 | embeddings |
| A-5 | `final-execution-plan.md:455` | report generator | P3-06 | ✅ 复用 | report |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 训练直接扫 `data/processed/cleaned` | 训练必须读 frozen manifest |
| ⛔2 | 同一 recording 同时进 train/test | eval 泄漏 |
| ⛔3 | 只用向量阈值自动删除 | 需要 review reason 和 report |
| ⛔4 | frozen dataset 还能被 PATCH 修改 | manifest checksum 会失效 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：P3 不启用安全 gate；P7 锚为 `final-execution-plan.md:213`。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| P3-T01 | review status transitions | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_curate.py` | P3-01 → 状态可审计 | commit {sha} + pytest tests/unit/pipelines/test_curate.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P3-T02 | embedding upsert/search stable | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_embeddings.py` | P3-02 → vec0 search | commit {sha} + pytest tests/unit/pipelines/test_embeddings.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P3-T03 | dedupe cluster decision | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_curate_dedupe.py` | P3-03 → 重复不进 manifest | commit {sha} + pytest tests/unit/pipelines/test_curate_dedupe.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P3-T04 | split leak detector | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_export_dataset.py::test_split_leak_detector` | P3-04 → no leakage | commit {sha} + pytest tests/unit/pipelines/test_export_dataset.py::test_split_leak_detector PASS + {YYYY-MM-DD HH:MM UTC} |
| P3-T05 | manifest checksum immutable | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_export_dataset.py::test_manifest_checksum_immutable` | P3-05 → frozen manifest | commit {sha} + pytest tests/unit/pipelines/test_export_dataset.py::test_manifest_checksum_immutable PASS + {YYYY-MM-DD HH:MM UTC} |
| P3-T06 | corpus audit report | 短途 | unit | 🆕 新增 `tests/unit/eval/test_corpus_report.py` | P3-06 → report artifact | commit {sha} + pytest tests/unit/eval/test_corpus_report.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P1 vec0 fixtures | ♻️ 沿用 | 用固定小向量 | P1 完成后可用 |
| P2 segment fixtures | ♻️ 沿用 | 读取 scored segments | P2 完成后可用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit tests/unit/pipelines tests/unit/eval` | unit | 每次 P3 改动 |
| spike | corpus sample review | 集成 | P3 收口可选 |
| mega | 不适用 | - | P8 |
| soak | 不适用 | - | P3 无长稳 |

### 8.4 测试缺口

- 不覆盖人工主观 review 质量（理由：unit suite 只能验证流转）→ 交实际 corpus audit。

### 8.5 测试保真

- 固定向量测试不能声称真实 speaker purity 达标。
- manifest checksum test 必须故意尝试修改 frozen dataset。
- split leak test 必须构造同一 recording 多 segment 的反例。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| embedding 误删 | 相似但非重复 | medium | review reason + report |
| split 泄漏 | 同源录音跨 split | high | group split + test |
| manifest 漂移 | frozen 后文件变更 | high | checksum + immutable status |

### 9.2 约束与前提

- **技术前提**：P2 已产生 scored segments。
- **运行时前提**：默认 tests 用 fixed vectors。
- **组织协作前提**：人工 review 可后续接 UI/API。
- **上线 / 合并前提**：P3-T01..T06 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：manifest format notes。
- 需要同步更新的说明文档 / README：P8 quickstart。
- 需要同步更新的测试说明：split leak / checksum tests。

### 9.4 完成后的预期状态

1. P4/P5 只能读取 frozen manifest。
2. corpus audit report 为 baseline/long train gate 提供 evidence。
3. 数据集版本可通过 checksum 复现。

---

## 10. 收口

### 10.1 收口硬闸

1. Review/dedupe/split/manifest/report 全链 unit PASS。
2. frozen dataset 不可变更。
3. split leak detector 覆盖反例。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| review audit | P3-01 | P3-T01 | commit b2ab537 + pytest tests/unit/pipelines/test_curate.py PASS + 2026-06-13 11:15 UTC | ✅ verified |
| vec search | P3-02 | P3-T02 | commit b2ab537 + pytest tests/unit/pipelines/test_embeddings.py PASS + 2026-06-13 11:15 UTC | ✅ verified |
| dedupe | P3-03 | P3-T03 | commit b2ab537 + pytest tests/unit/pipelines/test_curate_dedupe.py PASS + 2026-06-13 11:15 UTC | ✅ verified |
| no leak split | P3-04 | P3-T04 | commit b2ab537 + pytest tests/unit/pipelines/test_export_dataset.py::test_split_leak_detector PASS + 2026-06-13 11:15 UTC | ✅ verified |
| immutable manifest | P3-05 | P3-T05 | commit b2ab537 + pytest tests/unit/pipelines/test_export_dataset.py::test_manifest_checksum_immutable PASS + 2026-06-13 11:15 UTC | ✅ verified |
| audit report | P3-06 | P3-T06 | commit b2ab537 + pytest tests/unit/eval/test_corpus_report.py PASS + 2026-06-13 11:15 UTC | ✅ verified |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | frozen dataset manifest + corpus report |
| 测试 | P3-T01..P3-T06 全 PASS |
| 文档 | manifest contract 可被 P4/P5 引用 |
| 风险收敛 | 泄漏、重复、漂移风险有测试 |
| 可交付性 | 可进入 P4/P5 |

### 10.4 NOT-成功识别

训练能绕过 manifest、split 泄漏未被测出、或 frozen dataset 可修改，均不得标 `executed`。

## 11. Work Log

- **2026-06-13 11:11**: Started P3 implementation. Created curation transitions logic in `pipelines/curate.py` with append-only database audit logs.
- **2026-06-13 11:12**: Implemented resnet/clap/bge deterministic mock embeddings in `adapters/embeddings/speaker_embedder.py`, `audio_embedder.py`, and `text_embedder.py`.
- **2026-06-13 11:13**: Implemented similarity-based deduplication logic inside `pipelines/curate.py` using `sqlite-vec` searches.
- **2026-06-13 11:14**: Implemented leak-free dataset split partitioning, JSONL manifest generation, and dataset freeze status logic in `pipelines/export_dataset.py`. Created report generator in `eval/report.py`.
- **2026-06-13 11:15**: Wrote all P3 tests (curate, embeddings, dedupe, export, leak, report) and verified they pass under virtual environment. Committed all P3 files to repository.

