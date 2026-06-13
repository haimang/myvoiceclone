# Nano-Agent 行动计划：P2 Preprocess Pipeline

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P2 Preprocess Pipeline`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/02-preprocess-pipeline.md`
> 上游前序 / closure:
> - `01-storage-vec0-skeleton.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:156`
> 下游交接:
> - `03-corpus-dataset-freeze.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:156`（P2 工作台账）
> - `final-execution-plan.md:383`（preprocess 文件定位）
> 冻结决策来源:
> - `final-execution-plan.md:506`（Q5）
> - `final-execution-plan.md:507`（Q6）
> grounding 来源:
> - `final-execution-plan.md:160`、`:387`、`:418`、`:428`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P2 将 P1 的数据库和 artifact 底座转成可审计的音频预处理流水线。目标不是追求最高质量模型效果，而是让 `ingest -> diarize -> slice -> clean -> transcribe -> score` 每一步都能独立运行、失败可定位、产物可追溯。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P2 Preprocess Pipeline`
- **本次计划解决的问题**：
  - 原始音频进入系统后缺少 hash、status、artifact lineage。
  - pyannote/Demucs/Whisper/FFmpeg 等外部工具需要 adapter 隔离。
  - pipeline step 需要 job 化，写入 jobs/job_events/artifacts。
- **本次计划的直接产出**：
  - `pipelines/ingest.py`, `diarize.py`, `slice.py`, `clean.py`, `transcribe.py`, `score.py`
  - audio/diarization/separation/asr adapters
  - preprocess unit tests and adapter mock tests
- **本计划不重新讨论的设计结论**：
  - 外部工具全部经 adapter 接入（来源：`final-execution-plan.md:506`）。
  - 每个步骤必须记录状态、日志、artifact、report/metrics 链路（来源：`final-execution-plan.md:507`）。

---

## 1. 执行综述

### 1.1 总体执行方式

P2 采取“先定义标准 DTO，再实现 adapter mockable contract，再实现 pipeline steps，最后接入 job runner”的方式。所有真实外部工具调用默认可 mock，unit suite 不依赖真实音频、GPU、模型权重或网络。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | DTO + adapter contracts | M | 固化 FFmpeg/pyannote/Demucs/Whisper 输出格式 | P1 |
| Phase 2 | Ingest and audio adapters | M | source hash、normalize、artifact registry | Phase 1 |
| Phase 3 | Diarize/slice/clean/transcribe | L | 标准预处理链路 | Phase 2 |
| Phase 4 | Score and job integration | M | 质量评分、job_events、失败重试 | Phase 3 |
| Phase 5 | Tests | M | mock adapters + pipeline unit tests | Phase 4 |

### 1.3 Phase 说明

1. **Phase 1 — DTO + adapter contracts**
   - **核心目标**：所有外部工具输出统一成内部 DTO。
   - **为什么先做**：避免 pipeline 泄漏工具私有格式。
2. **Phase 2 — Ingest and audio adapters**
   - **核心目标**：原始文件入库、hash、probe、normalize。
   - **为什么放在这里**：后续步骤依赖 normalized artifact。
3. **Phase 3 — Diarize/slice/clean/transcribe**
   - **核心目标**：生成 segments、cleaned artifacts、transcripts。
   - **为什么放在这里**：P3 corpus curation 的输入来自这些产物。
4. **Phase 4 — Score and job integration**
   - **核心目标**：让每一步可作为 job 运行并可审计。
   - **为什么放在这里**：业务流转要可失败、可重试、可查询。

### 1.4 执行策略说明

- **执行顺序原则**：DTO/contract 先于 pipeline，pipeline 先于 CLI/API。
- **风险控制原则**：任何 subprocess 命令先做 command construction test，再做 live marker。
- **测试推进原则**：默认用 fake adapters；live FFmpeg/model smoke 后置。
- **文档同步原则**：preprocess DAG 参数同步到 `configs/pipelines/preprocess.default.yaml`。
- **回滚 / 降级原则**：外部工具不可用时 job failed + error，不生成假 artifact。

### 1.5 本次 action-plan 影响结构图

```text
P2 Preprocess
├── configs/pipelines/preprocess.default.yaml
├── data/raw, staging, processed/*
├── src/myvoiceclone/pipelines/{ingest,diarize,slice,clean,transcribe,score}.py
├── src/myvoiceclone/adapters/{audio,diarization,separation,asr}
├── src/myvoiceclone/jobs/{runner,queue,events}.py
└── tests/unit/{pipelines,adapters}
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** source ingest、hash、normalized artifact。
- **[S2]** FFmpeg command adapter 与 audio metadata helper。
- **[S3]** diarization、slicing、cleaning、transcription、scoring pipeline steps。
- **[S4]** job runner/event integration for preprocess steps。

### 2.2 Out-of-Scope

- **[O1]** corpus review/dataset manifest，交给 P3。
- **[O2]** RVC/So-VITS training，交给 P4/P5。
- **[O3]** HTTP routes/CLI UX，交给 P6。
- **[O4]** 安全/授权拦截，交给 P7。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| fake adapter unit tests | in-scope | Q7 要默认无模型测试 | live smoke 启动 |
| pyannote real model download | out-of-scope | 需要 token/license | live marker |
| status/job_events | in-scope | Q6 审计要求 | 无 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P2-01 | Phase 2 | Ingest + source hashing | add | `src/myvoiceclone/pipelines/ingest.py` | 重复 ingest 不重复入库 | P2-T01 | medium |
| P2-02 | Phase 2 | Adapter DTO + FFmpeg/audio adapter | add | `domain/entities.py`, `adapters/audio/ffmpeg.py`, `torchaudio_io.py` | DTO serialization 与 probe/normalize/extract 命令可测试 | P2-T02 | medium |
| P2-03 | Phase 3 | Diarization step | add | `pipelines/diarize.py`, `pyannote_adapter.py` | 标准 speaker turns 转 segments draft | P2-T03 | high |
| P2-04 | Phase 3 | VAD/slicing step | add | `pipelines/slice.py` | 2-10s segment artifacts | P2-T04 | high |
| P2-05 | Phase 3 | Clean step | add | `pipelines/clean.py`, `demucs_adapter.py`, `uvr_adapter.py` | before/after lineage 完整 | P2-T05 | high |
| P2-06 | Phase 3 | Transcribe step | add | `pipelines/transcribe.py`, `whisper_adapter.py` | transcript artifact + segment text | P2-T06 | medium |
| P2-07 | Phase 4 | QC scoring | add | `pipelines/score.py` | scores 可重复计算 | P2-T07 | medium |
| P2-08 | Phase 4 | Job integration | add/update | `jobs/runner.py`, `queue.py`, `events.py` | failed job 有 error/events | P2-T08 | high |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — DTO + adapter contracts

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-02 | 标准 DTO + FFmpeg adapter contract | a) 定义 `AudioProbe`, `DiarizationTurn`, `TranscriptSegment`, `SeparationResult`；b) adapter 返回 DTO，不返回 vendor object；c) pipeline 只消费 DTO；d) FFmpeg command construction 使用同一 DTO 约束 | `domain/entities.py`, `adapters/audio/ffmpeg.py`, `adapters/**` | 工具格式被隔离，音频命令可测试 | P2-T02 | DTO + command snapshot PASS |

### 4.2 Phase 2 — Ingest and audio adapters

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-01 | Ingest + source hashing | a) 计算 sha256；b) 查重 recordings.sha256；c) 写 recording new/ingested；d) 调 audio normalize；e) 写 normalized artifact；f) 出错写 failed event | `pipelines/ingest.py` | 原始文件可入库可追溯 | P2-T01 | duplicate ingest PASS |
| P2-02 | FFmpeg adapter | a) probe 命令构造；b) normalize 命令构造；c) extract segment 命令构造；d) subprocess failed 映射为 adapter error；e) 输出遵守 Phase 1 DTO contract | `adapters/audio/ffmpeg.py` | 命令不需真实 FFmpeg 也可测 | P2-T02 | DTO + command snapshot PASS |

### 4.3 Phase 3 — Diarize/slice/clean/transcribe

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-03 | Diarization step | a) 读取 normalized artifact；b) 调 diarizer；c) 标准 turns JSON/RTTM artifact；d) 建 draft segments；e) 重叠说话标记 metadata | `pipelines/diarize.py`, `pyannote_adapter.py` | diarization 可审计 | P2-T03 | turns -> segments PASS |
| P2-04 | VAD/slicing step | a) 基于 turns/VAD 生成 2-10s windows；b) 裁切 artifact；c) duration/overlap check；d) 写 segment audio artifact | `pipelines/slice.py` | segment artifacts 稳定 | P2-T04 | duration bounds PASS |
| P2-05 | Clean step | a) 对 segment audio 调 separation adapter；b) 写 cleaned artifact；c) 保留 source_artifact_id；d) failure 不覆盖原始 segment | `pipelines/clean.py`, `demucs_adapter.py`, `uvr_adapter.py` | before/after lineage 完整 | P2-T05 | lineage PASS |
| P2-06 | Transcribe step | a) 调 ASR adapter；b) 标准 transcript JSON；c) 更新 segment transcript；d) 保存 ASR confidence metadata | `pipelines/transcribe.py`, `whisper_adapter.py` | transcript 可用于 QC | P2-T06 | transcript update PASS |

### 4.4 Phase 4 — Score and job integration

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-07 | QC scoring | a) duration score；b) clip/noise/speech ratio；c) speaker similarity 占位读取；d) 可重复更新同一 segment；e) 低质片段标 needs_review | `pipelines/score.py` | score 可重跑 | P2-T07 | score idempotent PASS |
| P2-08 | Job integration | a) queue 创建 job；b) runner 执行 step；c) events 记录 started/progress/succeeded/failed；d) error 写 jobs.error；e) artifact 必须关联 job | `jobs/runner.py`, `queue.py`, `events.py` | pipeline 可作为 job 运行 | P2-T08 | failed path PASS |

---

## 5. Phase 详情

### 5.1 Phase 1/2 — DTO + ingest/audio

- **Phase 目标**：建立预处理输入和音频基础 adapter。
- **本 Phase 对应编号**：P2-01 / P2-02
- **本 Phase 新增文件**：`pipelines/ingest.py`, `adapters/audio/ffmpeg.py`, `adapters/audio/torchaudio_io.py`
- **具体功能预期**：
  1. 原始文件不被覆盖。
  2. sha256 是 recording 去重主键。
  3. normalized artifact 写入 `data/staging/`。
  4. adapter errors 不泄漏 subprocess 原始异常到 domain。
  5. 所有输出 artifact 都有 job/source linkage。
- **对应测试台账项**：P2-T01..P2-T02
- **收口标准**：使用 fake wav fixture 可完成 ingest。
- **本 Phase 风险提醒**：不要把真实音频 fixture 放入仓库。

### 5.2 Phase 3 — preprocessing steps

- **Phase 目标**：完成 diarize/slice/clean/transcribe 的可重跑步骤。
- **本 Phase 对应编号**：P2-03..P2-06
- **本 Phase 新增文件**：`pipelines/diarize.py`, `slice.py`, `clean.py`, `transcribe.py`, corresponding adapters
- **具体功能预期**：
  1. pyannote 输出先标准化再入库。
  2. slicing duration 默认 2-10 秒，可从 config 调整。
  3. clean 失败不删除原始 segment。
  4. ASR transcript 可空但必须有 artifact/error 记录。
  5. 每个 step 可单独重跑且不会重复创建不可追踪产物。
- **对应测试台账项**：P2-T03..P2-T06
- **收口标准**：fake adapter journey 完成到 transcript。
- **本 Phase 风险提醒**：真实工具输出格式可能变化，adapter test 要锁标准 DTO。

### 5.3 Phase 4 — Score and jobs

- **Phase 目标**：让预处理链路具备状态、日志、失败审计。
- **本 Phase 对应编号**：P2-07 / P2-08
- **本 Phase 新增 / 修改文件**：`pipelines/score.py`, `jobs/runner.py`, `queue.py`, `events.py`
- **具体功能预期**：
  1. job 从 queued 到 running/succeeded/failed。
  2. 每个 terminal 状态有 job_event。
  3. failed job 保留 error 和已生成 artifacts。
  4. score 可重复运行，更新而非无序追加。
  5. pipeline step 不直接操作 API schema。
- **对应测试台账项**：P2-T07 / P2-T08
- **收口标准**：failed path 和 success path 均可查询。
- **本 Phase 风险提醒**：不要使用 FastAPI BackgroundTasks 执行实际长任务。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q5 | `final-execution-plan.md:506` | adapter/pipeline 分层 | 回到 P0/P1 修正 |
| Q6 | `final-execution-plan.md:507` | jobs/artifacts/events 必填 | 不得绕过审计写文件 |
| Q7 | `final-execution-plan.md:508` | 默认 mock unit tests | live tests 单独 marker |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `final-execution-plan.md:156` | P2 工作台账 | P2-01..08 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:383` | preprocess config/data 文件定位 | P2-01..08 | ✅ 复用 | 目录落点 |
| A-3 | `final-execution-plan.md:418` | pipeline 文件定位 | P2-01..07 | ✅ 复用 | source 落点 |
| A-4 | `final-execution-plan.md:428` | adapter 文件定位 | P2-02..06 | ✅ 复用 | adapter 落点 |
| A-5 | `final-execution-plan.md:450` | job runner 文件定位 | P2-08 | ✅ 复用 | jobs 落点 |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | pipeline 直接保存散乱文件不入 artifacts | Q6 要可审计 |
| ⛔2 | adapter 返回 pyannote/Whisper 私有对象 | Q5 要低耦合 |
| ⛔3 | 真实模型测试进入默认 unit suite | Q7 明确 live/GPU 单独 marker |
| ⛔4 | 清洗失败覆盖原始 segment | artifact lineage 必须可回滚 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：P2 不实现安全控制；P7 威胁模型锚为 `final-execution-plan.md:213`。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| P2-T01 | ingest duplicate/hash/artifact | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_ingest.py` | P2-01 → 去重入库 | commit {sha} + pytest tests/unit/pipelines/test_ingest.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T02 | adapter DTO serialization + FFmpeg command construction | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_dto_contracts.py` + `tests/unit/adapters/test_ffmpeg_adapter.py` | P2-02 → 工具格式隔离与命令可测 | commit {sha} + pytest tests/unit/adapters/test_dto_contracts.py tests/unit/adapters/test_ffmpeg_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T03 | pyannote adapter DTO + diarization turns -> segments | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_pyannote_adapter.py` + `tests/unit/pipelines/test_diarize.py` | P2-03 → draft segments | commit {sha} + pytest tests/unit/adapters/test_pyannote_adapter.py tests/unit/pipelines/test_diarize.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T04 | slicing duration/overlap bounds | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_slice.py` | P2-04 → segment artifacts | commit {sha} + pytest tests/unit/pipelines/test_slice.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T05 | Demucs/UVR adapter DTO + clean artifact lineage | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_demucs_adapter.py` + `tests/unit/pipelines/test_clean.py` | P2-05 → before/after 完整 | commit {sha} + pytest tests/unit/adapters/test_demucs_adapter.py tests/unit/pipelines/test_clean.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T06 | Whisper adapter DTO + transcript artifact/update | 短途 | unit | 🆕 新增 `tests/unit/adapters/test_whisper_adapter.py` + `tests/unit/pipelines/test_transcribe.py` | P2-06 → transcript 入库 | commit {sha} + pytest tests/unit/adapters/test_whisper_adapter.py tests/unit/pipelines/test_transcribe.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T07 | score idempotency | 短途 | unit | 🆕 新增 `tests/unit/pipelines/test_score.py` | P2-07 → 可重跑 | commit {sha} + pytest tests/unit/pipelines/test_score.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P2-T08 | job success/fail event trace | 短途 | 集成 | 🆕 新增 `tests/unit/jobs/test_runner.py` | P2-08 → 可审计 | commit {sha} + pytest tests/unit/jobs/test_runner.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| P1 storage fixtures | ♻️ 沿用 | 使用 tmp DB/artifact root | P1 完成后可用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit tests/unit/pipelines tests/unit/adapters tests/unit/jobs` | unit·集成 | 每次 P2 改动 |
| spike | `pytest -m live` | live | P2 收口后可选 |
| mega | 不适用 | - | P8 |
| soak | 不适用 | - | P2 无长稳 |

### 8.4 测试缺口

- 不覆盖真实 pyannote/Demucs/Whisper 模型质量（理由：unit suite 不依赖模型）→ P2 live spike 或后续 P3/P4 evidence。

### 8.5 测试保真

- Fake adapter PASS 不代表真实模型可用，live marker 必须单独报告。
- failed path 必须验证 jobs.error 和 job_events，不只 assert exception。
- artifact test 必须验证 sha/source linkage。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| 外部工具输出格式漂移 | pyannote/Whisper 更新 | high | DTO contract + adapter tests |
| 真实音频质量低 | preprocess 可跑但质量差 | medium | P3 QC/review 接管 |
| job 失败留下半成品 | 产物难追踪 | high | artifact source/job linkage |

### 9.2 约束与前提

- **技术前提**：P1 DB/artifact/job schema 已完成。
- **运行时前提**：默认 tests 无真实模型。
- **组织协作前提**：真实模型 token/license 后续配置。
- **上线 / 合并前提**：P2 unit tests 全 PASS。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/architecture/layers.md` 如 adapter 边界变化。
- 需要同步更新的说明文档 / README：P8 汇总 preprocess quickstart。
- 需要同步更新的测试说明：live marker 用法。

### 9.4 完成后的预期状态

1. P3 可读取 scored segments。
2. 每个 preprocess step 有 artifact/job/event trace。
3. fake end-to-end preprocess journey 可跑。

---

## 10. 收口

### 10.1 收口硬闸

1. Fake adapter preprocess chain 到 transcript/score 全 PASS（P2-T01..P2-T07）。
2. Job success/failure 可审计（P2-T08）。
3. 外部工具私有格式不泄漏到 pipeline/domain（P2-T02）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| ingest 去重 | P2-01 | P2-T01 | commit {sha} + pytest tests/unit/pipelines/test_ingest.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| DTO 隔离 + FFmpeg 命令可测 | P2-02 | P2-T02 | commit {sha} + pytest tests/unit/adapters/test_dto_contracts.py tests/unit/adapters/test_ffmpeg_adapter.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| turns -> segments | P2-03 | P2-T03 | commit {sha} + pytest tests/unit/adapters/test_pyannote_adapter.py tests/unit/pipelines/test_diarize.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| slicing bounds | P2-04 | P2-T04 | commit {sha} + pytest tests/unit/pipelines/test_slice.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| clean lineage | P2-05 | P2-T05 | commit {sha} + pytest tests/unit/adapters/test_demucs_adapter.py tests/unit/pipelines/test_clean.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| transcript 入库 | P2-06 | P2-T06 | commit {sha} + pytest tests/unit/adapters/test_whisper_adapter.py tests/unit/pipelines/test_transcribe.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| score idempotent | P2-07 | P2-T07 | commit {sha} + pytest tests/unit/pipelines/test_score.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| job trace | P2-08 | P2-T08 | commit {sha} + pytest tests/unit/jobs/test_runner.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | ingest/diarize/slice/clean/transcribe/score/job 全链 mock 可跑 |
| 测试 | P2-T01..P2-T08 全 PASS |
| 文档 | preprocess config 与 quickstart 待 P8 汇总 |
| 风险收敛 | 外部工具被 adapter 隔离 |
| 可交付性 | 可进入 P3 |

### 10.4 NOT-成功识别

任一步骤绕过 artifacts/job_events、真实工具失败被吞掉、或 unit suite 依赖真实模型，均不得标 `executed`。
