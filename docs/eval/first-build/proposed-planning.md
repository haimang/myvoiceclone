# myvoiceclone first-build —— proposed-planning（by Codex）

> **stage**：`proposed`
> **作者**：`Codex`（panel / 跨模型 handoff：`none`）
> **时间**：`2026-06-13`
> **文档性质（自宣告 role）**：**取代 owner initial-thoughts，作 pre-charter-qna 前唯一精炼工作基线**
> **上游权威输入**：
> - `myvoiceclone/initial-thoughts.md` — 20+ 小时真实会话录音、高保真 voice clone、强调 So-VITS-SVC 4.1 与清洗流水线
> - `00-templates/eval-planning.md` — 本文档结构模板
> **phase 命名 & 工作项 ID 方案**：`MVC-P0..P6 / MVC-DB / MVC-API / MVC-EVAL`
> **裁定动词 rubric（§2 用）**：`KEEP / REFRAME / CLOSED / NEW`
> **文档状态**：`draft`
> **下游消费者**：`charter/qna`、`docs/plan/first-build/*`、后续 action-plan

---

## 0. TL;DR

- **核心论点**：`myvoiceclone` 不应被设计成“直接把 20+ 小时原始会话丢给某个训练仓库”的项目，而应是一个以数据治理、说话人切分、质量筛选、可追溯训练、可量化评估为核心的本地 voice-clone 工作台。技术上采用“双轨模型策略”：RVC/XTTS 类方案用于快速基线和 TTS 验证，So-VITS-SVC 4.1 或其可维护 fork 作为高保真 voice-conversion 长训主线；数据库采用 SQLite 管理关系事实，`sqlite-vec` 的 `vec0` 管理本地 embedding 检索，`vec1` 只作为后续大规模 ANN 评估项。
- **一句话**：先把 20+ 小时真实录音变成可审计、可查询、可训练、可回滚的高质量 2-5 小时目标语音语料，再谈长训高保真模型。
- **本态相对上一态做了什么**：将 `initial-thoughts.md` 中“选 So-VITS-SVC + 清洗流水线”的方向扩展为完整项目架构、接口、数据模型、向量检索、风险门禁与分阶段执行计划。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `myvoiceclone/initial-thoughts.md` | owner anchor | 目标场景、RVC 局限、So-VITS-SVC 倾向、预处理必要性 | `lines 1-74` |
| `00-templates/eval-planning.md` | template | proposed-planning 三态模板与章节骨架 | `stage=proposed` |
| So-VITS-SVC 4.1 upstream | model reference | VITS/SVC 长训候选，但维护状态需复核 | https://github.com/svc-develop-team/so-vits-svc |
| RVC upstream | model reference | 快速 voice conversion baseline | https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI |
| Demucs upstream | preprocess reference | 音源分离/人声抽取候选 | https://github.com/facebookresearch/demucs |
| pyannote.audio upstream | preprocess reference | speaker diarization / speaker embedding | https://github.com/pyannote/pyannote-audio |
| Whisper upstream | preprocess reference | ASR 转写、质检、WER/字幕锚点 | https://github.com/openai/whisper |
| sqlite-vec upstream | vector DB reference | SQLite 本地向量扩展，`vec0` 虚表 | https://github.com/asg017/sqlite-vec |
| SQLite `vec1` extension | vector DB reference | SQLite 官方 `vec1` ANN 方向，适合作为后续可选评估 | https://sqlite.org/vec1 |

- **纪律继承**：本文是 eval / planning，不冻结 owner 决策；所有模型选择、授权边界、GPU 环境、最终 schema 仍需 QnA 或 charter 冻结。
- **proposed 说明**：当前仓库没有独立 `initial-planning.md`，因此 §2 将 `initial-thoughts.md` 当作 owner initial baseline 来做 Δ 审核。

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

### 2.B [仅 proposed] Δ 审核 vs owner initial baseline

| item-ID | 裁定（KEEP/REFRAME/CLOSED/NEW） | 重分配 phase | 复用判定 | 理由 / 新证据 |
|---------|--------------------------------|--------------|----------|---------------|
| MVC-01 | `KEEP` | `P0/P2` | ✅ 复用 | 20+ 小时真实会话录音的核心难点确实是噪声、混响、串话、说话人混杂，而不是单纯训练时长。 |
| MVC-02 | `REFRAME` | `P4/P5` | ♻️ 重 substrate | `initial-thoughts` 将 So-VITS-SVC 4.1 视为主答案，但它本质偏 voice conversion / SVC，不等价于完整 TTS voice clone；本文改为“双轨”：TTS baseline + VC long-run。 |
| MVC-03 | `KEEP` | `P2/P3` | ✅ 复用 | pyannote / Demucs / VAD 方向合理，但需补充质检、人工复核、转写、embedding 检索、可回滚 artifact 管理。 |
| MVC-04 | `REFRAME` | `P5` | ♻️ 重 substrate | “20h 全量训练”改为“20h 原始池 -> 2-5h 高质量训练集 + 保留余量做验证/风格覆盖”。数量不应压过音频质量。 |
| MVC-05 | `NEW` | `P1/MVC-DB` | 🆕 净新 | 新增本地关系型数据库和向量检索层，支撑 segment 追踪、speaker match、去重、相似片段召回、训练集版本化。 |
| MVC-06 | `NEW` | `MVC-API/P2-P6` | 🆕 净新 | 新增接口化工作流，避免脚本散落导致训练不可复现。 |
| MVC-07 | `NEW` | `P0/P6` | 🆕 净新 | 新增授权、同意、用途边界、水印/日志、反滥用门禁。voice clone 涉及身份与合成语音风险，必须前置。 |

- **本态核心转向（一句话）**：从“选择某个最佳训练模型”转为“建设一个以数据质量、可追溯训练和模型可替换为中心的本地 voice clone 平台”。

---

## 3. 范围与非范围（In/Out-Scope）

### 3.1 In-Scope

- **[S1] 技术栈评估与推荐** — 明确预处理、训练、推理、评估、存储、接口层的默认组合和替代项。
- **[S2] 多层抽象与项目树** — 给出完整目录结构，区分 domain、pipeline、adapters、storage、api、infra、docs。
- **[S3] 接口化工作流** — 定义 CLI/API/job/artifact 的最小合同，让每一步可重跑、可审计、可并行。
- **[S4] SQLite + vector extension 本地数据层** — 关系事实放 SQLite，音频/speaker/text embedding 放向量虚表或扩展表。
- **[S5] 分阶段执行计划** — 给出 first-build 从治理到训练评估的落地顺序、退出条件和风险门禁。
- **[S6] 评估框架** — 建立 speaker similarity、ASR intelligibility、人工 ABX、artifact 回溯的评价口径。

### 3.2 Out-of-Scope / 延后

- **[O1] 云端多租户 SaaS** — first-build 以本地单用户工作台为边界；重评条件：需要团队共享或远程 GPU 队列。
- **[O2] 生产级实时语音通话替身** — 延后；重评条件：模型质量、延迟、水印和授权策略均通过 P6。
- **[O3] 绕过授权的任意人声克隆** — 不纳入；该项目只服务获得授权的目标声音。
- **[O4] 大规模分布式向量数据库** — 延后；本地 SQLite 足够覆盖 first-build，超过百万级片段再评估 Qdrant/Milvus/FAISS service。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线**：训练主线不得直接消费未经 diarization、VAD、denoise、QC 的原始会话；不得把 speaker identity、训练集版本、模型产物放在散乱文件名中隐式表达；不得把单一模型仓库当成项目架构。
- **治理冻结面**：授权/同意记录、目标说话人身份、允许用途、禁止用途、合成样本标记、删除与撤回机制需要在 P0/P1 固化为数据库字段和流程约束。
- **模型可替换性**：RVC、So-VITS-SVC、XTTS、后续 StyleTTS / OpenVoice / Seed-VC 类方案都必须通过 adapter 接入，核心数据层与工作流不绑定某个训练仓库。
- **可复现性**：每个 artifact 记录 `source_hash`、`pipeline_version`、`params_json`、`model_commit`、`env_digest`，训练集用 manifest 冻结。
- **migration inventory**：`001_init_relational_schema`、`002_vec0_embeddings`、`003_jobs_artifacts_runs`、`004_consent_ledger`、`005_eval_metrics`、`006_optional_vec1_probe`。

---

## 5. DAG（关键路径 + 并行窗）

```text
P0 Governance / requirements
  └─▶ P1 Repo skeleton + SQLite/vec0 foundation
        ├─▶ P2 Preprocess pipeline MVP
        │     └─▶ P3 Corpus curation + dataset manifest
        │           ├─▶ P4 Quick baselines: RVC + TTS smoke
        │           └─▶ P5 Long-run VC training: So-VITS-SVC track
        │                 └─▶ P6 Evaluation + inference packaging
        └─▶ API/CLI contracts can evolve in parallel with P2-P5
```

关键路径：`P0 consent/requirements -> P1 data model -> P2 clean segments -> P3 train manifest -> P5 long train -> P6 eval gate`。

并行窗：API/CLI 框架、文档、Docker 基础镜像、评估脚本可与 P2/P3 并行；模型长训不可早于 P3 的 manifest freeze。

---

## 6. 逐 phase 工作台账

### 6.1 `P0 Governance / Owner QnA`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P0-01 | 明确目标产物：TTS、VC、SVC、语音风格库，还是组合 | `initial-thoughts` 偏 SVC；需 owner 选择 | ♻️ | S |
| MVC-P0-02 | 授权与用途登记 | 新增 `consent_ledger`，禁止非授权声音 | 🆕 | S |
| MVC-P0-03 | GPU/OS/驱动/容器基线盘点 | Blackwell/PyTorch 版本需实测，不写死幻想版本 | ♻️ | M |
| MVC-P0-04 | 质量目标定义 | 人工相似度、自然度、可懂度、噪声容忍度 | 🆕 | S |

### 6.2 `P1 Project Skeleton + Storage Foundation`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P1-01 | 建立项目树 | 见 §6.8，按 domain/pipeline/adapters/storage/api 分层 | 🆕 | M |
| MVC-P1-02 | SQLite schema + migrations | 关系事实、jobs、artifacts、runs、metrics | 🆕 | M |
| MVC-P1-03 | `sqlite-vec/vec0` 向量表 | speaker/audio/text embeddings；本地相似检索 | 🆕 | M |
| MVC-P1-04 | Artifact store | 音频文件仍落文件系统，DB 存 URI/hash/metadata | 🆕 | S |
| MVC-P1-05 | Config/env registry | 训练仓库路径、模型权重、HF token、GPU caps | 🆕 | S |

### 6.3 `P2 Preprocessing Pipeline MVP`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P2-01 | Ingest + source hashing | FFmpeg normalize，不覆盖原始文件 | 🆕 | S |
| MVC-P2-02 | Diarization | pyannote speaker turns；人工确认目标 speaker | ✅ | M |
| MVC-P2-03 | VAD + slicing | 2-10s segment，去静音、去重叠说话 | ✅ | M |
| MVC-P2-04 | Denoise / dereverb / separation | Demucs / UVR adapter；保留 before/after | ✅ | M |
| MVC-P2-05 | ASR transcript | Whisper/faster-whisper adapter；辅助过滤、字幕和评估 | 🆕 | M |
| MVC-P2-06 | QC scoring | SNR、clip、duration、speech ratio、ASR confidence、speaker similarity | 🆕 | M |

### 6.4 `P3 Corpus Curation + Dataset Manifest`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P3-01 | Segment review queue | 人工标注 keep/drop/fix；保留理由 | 🆕 | M |
| MVC-P3-02 | Embedding-based dedupe | `vec0` 召回近似重复、同一句重复、噪声簇 | 🆕 | M |
| MVC-P3-03 | Speaker purity filter | 目标 speaker embedding centroid + 阈值 | 🆕 | M |
| MVC-P3-04 | Dataset manifest freeze | `manifest.jsonl` + DB version + hashes | 🆕 | S |
| MVC-P3-05 | Train/val/test split | 按 source recording 分组，避免泄漏 | 🆕 | S |

### 6.5 `P4 Quick Baselines`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P4-01 | RVC quick baseline | 用 30-90 分钟 clean set 验证声线可学性 | ♻️ | M |
| MVC-P4-02 | XTTS/OpenVoice-style TTS smoke | 若 owner 需要文字转语音，先验证 TTS 路线 | 🆕 | M |
| MVC-P4-03 | Baseline eval pack | 固定 prompts、reference clips、ABX 表 | 🆕 | S |
| MVC-P4-04 | 决策 gate | 是否进入 24h+ 长训，或回炉 P2/P3 | 🆕 | S |

### 6.6 `P5 Long-run High-fidelity Training`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P5-01 | So-VITS-SVC 4.1/fork 环境封装 | upstream 维护风险需 lock commit / fork | ✅ | L |
| MVC-P5-02 | Feature extraction cache | HuBERT/content units、F0、spectrogram、speaker stats | 🆕 | M |
| MVC-P5-03 | Long-run training orchestration | checkpoint、resume、tensorboard、OOM fallback | ♻️ | L |
| MVC-P5-04 | Hyperparameter sweep | sample rate、batch size、segment length、augmentation | 🆕 | M |
| MVC-P5-05 | Model registry | checkpoint lineage、manifest id、eval score、notes | 🆕 | S |

### 6.7 `P6 Evaluation + Inference Packaging`

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + 蓝本 + HEAD 锚 + 避坑 + TR | 复用 | 规模 |
|------|--------|--------------------------------------------|------|------|
| MVC-P6-01 | Objective eval | speaker similarity、WER、duration drift、noise residual | 🆕 | M |
| MVC-P6-02 | Subjective eval | ABX/MOS 表单，盲听目标/基线/候选 | 🆕 | S |
| MVC-P6-03 | Inference API | VC convert、TTS synth、batch render、watermark/log | 🆕 | M |
| MVC-P6-04 | Release gate | 质量、授权、误用风险、撤回机制 | 🆕 | S |

### 6.8 完整项目树状结构建议

```text
myvoiceclone/
  README.md
  pyproject.toml
  .env.example
  configs/
    local.yaml
    models.yaml
    pipelines/
      preprocess.default.yaml
      train.rvc.yaml
      train.sovits.yaml
      eval.default.yaml
  data/
    raw/                         # 原始录音，只读；DB 记录 hash
    staging/                     # ingest 后的 wav/flac normalized copies
    processed/
      diarized/                  # speaker turns / RTTM / JSON
      sliced/                    # VAD 后 clips
      cleaned/                   # denoise/dereverb 后 clips
      transcripts/               # ASR 输出
    datasets/
      first-build/
        manifest.jsonl
        train/
        val/
        test/
    artifacts/
      jobs/
      eval/
      reports/
  db/
    myvoiceclone.sqlite
    migrations/
      001_init_relational_schema.sql
      002_vec0_embeddings.sql
      003_jobs_artifacts_runs.sql
      004_consent_ledger.sql
      005_eval_metrics.sql
      006_optional_vec1_probe.sql
  src/
    myvoiceclone/
      domain/
        entities.py              # Recording, Segment, Speaker, Dataset, Run
        policies.py              # consent, usage, quality gates
      storage/
        sqlite.py
        migrations.py
        vector_store.py          # VecStore interface
        vec0_store.py
        vec1_store.py            # optional probe only
        artifact_store.py
      pipelines/
        ingest.py
        diarize.py
        slice.py
        clean.py
        transcribe.py
        score.py
        curate.py
        export_dataset.py
        train.py
        evaluate.py
      adapters/
        audio/
          ffmpeg.py
          torchaudio_io.py
        diarization/
          pyannote_adapter.py
        separation/
          demucs_adapter.py
          uvr_adapter.py
        asr/
          whisper_adapter.py
        embeddings/
          speaker_embedder.py
          audio_embedder.py
          text_embedder.py
        training/
          rvc_adapter.py
          sovits_adapter.py
          xtts_adapter.py
      api/
        app.py                   # FastAPI
        schemas.py
        routes_recordings.py
        routes_segments.py
        routes_jobs.py
        routes_training.py
        routes_inference.py
      cli.py                     # typer/click CLI
      jobs/
        runner.py
        queue.py                 # local process queue first
      eval/
        objective.py
        subjective.py
        report.py
  models/
    pretrained/                  # downloaded base weights, gitignored
    checkpoints/                 # training outputs, gitignored
    registry/                    # metadata tracked or DB-backed
  notebooks/
    corpus_audit.ipynb
    eval_review.ipynb
  scripts/
    bootstrap_env.sh
    download_models.sh
    run_preprocess.sh
    run_train_sovits.sh
  infra/
    docker/
      Dockerfile.preprocess
      Dockerfile.train
      compose.yaml
    systemd/
  docs/
    eval/
      first-build/
        proposed-planning.md
    plan/
    api/
    ops/
```

### 6.9 抽象层次说明

| 层 | 名称 | 责任 | 不应承担 |
|----|------|------|----------|
| L0 | File / Artifact layer | 保存原始音频、派生音频、manifest、checkpoint、报告 | 不编码业务状态 |
| L1 | Relational DB layer | 记录 recording/segment/job/run/eval 的事实、状态、血缘 | 不存大音频 blob |
| L2 | Vector layer | speaker/audio/text embedding 检索、去重、相似召回 | 不替代关系约束 |
| L3 | Domain service layer | consent、quality gate、dataset freeze、run lineage | 不直接调用外部训练仓库细节 |
| L4 | Pipeline layer | ingest/diarize/clean/train/eval 的可重跑步骤 | 不隐式修改 source truth |
| L5 | Adapter layer | pyannote、Demucs、Whisper、RVC、So-VITS-SVC 等外部工具适配 | 不泄漏到 API 合同 |
| L6 | API/CLI layer | 面向人和自动化的稳定接口 | 不承载长任务计算本身 |

---

## 7. Owner decision gates

### 7.A [initial / proposed] 开放 gates

| 编号 | 决策点 | 影响 | 当前建议 / 倾向 | 状态 |
|------|--------|------|------------------|------|
| G-MVC-1 | 最终目标是 TTS、voice conversion，还是二者都要 | 决定是否必须引入 XTTS/OpenVoice 类 TTS 基线 | 先双轨，P4 后收敛 | OPEN |
| G-MVC-2 | 原始数据授权与目标 speaker 身份 | 决定是否允许进入 P2/P5 | 必须 P0 关闭 | OPEN |
| G-MVC-3 | 可接受的本地硬件与训练时长 | 决定 batch、sample rate、模型候选 | 先实测 GPU/驱动 | OPEN |
| G-MVC-4 | 是否允许使用需 token/license 的模型 | 影响 pyannote、部分 TTS 模型下载 | 配置化，不写死 | OPEN |
| G-MVC-5 | `vec1` 是否纳入 first-build | 影响 DB 复杂度 | 默认不纳入主线，仅 probe | OPEN |

- **结论**：设计阶段仍有 5 个 OPEN 决策项；本文可转入 QnA/charter，但不应直接冻结执行。

---

## 8. 测试计划

- **A 短途（unit / local route）**：SQLite migration 可重复执行；artifact hash 稳定；CLI dry-run；API schema validation；adapter mock tests。
- **B spike（live tools）**：用 10-20 分钟样本跑 `ingest -> diarize -> slice -> clean -> transcribe -> score -> manifest`；记录耗时、GPU/CPU 占用、错误率。
- **C corpus gate**：随机抽样 100 个 segment 做人工 keep/drop 与 speaker purity 检查；检查 train/val/test 是否按 source 分组。
- **D model smoke**：RVC baseline 与 TTS smoke 各跑最小训练/推理；不追求最终质量，只验证数据和接口完整。
- **E long-run rehearsal**：So-VITS-SVC 小规模 1-2 小时训练，验证 resume/checkpoint/eval/report；通过后再启动 24h+ 长训。
- **Evidence pack（每 phase 收口）**：`db dump summary`、`manifest hash`、`config snapshot`、`git commit`、`env digest`、`sample audio before/after`、`eval report`。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 授权/身份风险 | 使用未获授权的人声或不可证明授权 | 项目不可发布，甚至不能继续训练 | P0 建 consent ledger，数据入口强制绑定授权 |
| 原始录音质量不足 | 餐厅、会议、远场、重叠说话过多 | 模型学到噪声/混响/他人声线 | P2/P3 强 QC，宁可缩小训练集 |
| So-VITS-SVC 维护风险 | 上游依赖老旧、CUDA/PyTorch 不匹配 | 环境搭建和长训失败 | lock commit，Docker 化，准备 fork/替代 adapter |
| 混淆 TTS 与 VC | owner 期待输入文字直接生成声音，但只训练了 SVC | 产物不符合预期 | P0 明确目标，P4 做 TTS smoke |
| 向量库过早复杂化 | 直接引入外部 DB 或未成熟扩展 | first-build 维护成本过高 | 默认 SQLite + `vec0`，`vec1` 只 probe |
| 训练集泄漏 | 同一原始录音切片同时进 train/test | eval 虚高 | 按 recording/source 分组 split |
| 长训不可复现 | 参数、数据、commit 未记录 | 无法比较或回滚 | run registry + manifest freeze + env digest |
| 过度自动化删除好样本 | VAD/diarization 错误 | 损失情绪/音色覆盖 | review queue + 阈值可调 + 保留 rejected artifacts |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：一个可审计的本地 voice clone 工程底座，支持快速 baseline、长训主线、数据回滚、模型比较、合成样本追踪。

### 10.A [proposed] action-plan 派生与排序建议

| phase 簇 | 派生的 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|--------------------------|--------------|-------------|
| P0 | `docs/plan/first-build/00-governance-qna.md` | MVC-P0-01..04 | 最先执行，关闭授权与目标形态 |
| P1 | `docs/plan/first-build/01-storage-skeleton.md` | MVC-P1-01..05 | 依赖 P0 最小结论 |
| P2/P3 | `docs/plan/first-build/02-preprocess-corpus.md` | MVC-P2-01..06, MVC-P3-01..05 | 依赖 P1 schema |
| P4 | `docs/plan/first-build/03-baseline-models.md` | MVC-P4-01..04 | 依赖 P3 manifest |
| P5 | `docs/plan/first-build/04-long-train-sovits.md` | MVC-P5-01..05 | 依赖 P4 gate |
| P6 | `docs/plan/first-build/05-eval-inference-release.md` | MVC-P6-01..04 | 依赖 P4/P5 outputs |

---

## 11. 技术栈建议

### 11.1 推荐默认栈

| 层面 | 默认选择 | 说明 | 替代/备注 |
|------|----------|------|-----------|
| Runtime | Python 3.11/3.12 + PyTorch + CUDA Docker | 训练和音频工具生态最成熟 | Blackwell 具体 torch/cu 版本必须实测 |
| Audio IO | FFmpeg + torchaudio/soundfile | 统一转码、采样率、声道、响度 | librosa 用于分析，不做唯一 IO |
| Diarization | pyannote.audio | 目标 speaker turn 检测与 embedding | 需处理模型许可/token |
| VAD | Silero VAD / pyannote VAD | 切片、去静音、speech ratio | WebRTC VAD 可作轻量 fallback |
| Denoise/separation | Demucs / UVR adapter | 人声抽取、背景降噪 | 需保留原始和清洗后版本 |
| ASR | Whisper / faster-whisper | transcript、WER、脏样本过滤 | 语言和口音需实测 |
| Quick VC | RVC | 快速验证声线可学性 | 不作为 20h 长训主路线 |
| Long VC/SVC | So-VITS-SVC 4.1 或维护 fork | 高保真转换主线候选 | 需 lock commit 和环境镜像 |
| TTS baseline | XTTS/OpenVoice-style adapter | 若需要文字转语音，必须有 TTS 轨 | 与 SVC 分开评估 |
| Relational DB | SQLite | 本地单用户、易备份、可迁移 | WAL + migrations |
| Vector DB | sqlite-vec `vec0` | segment/speaker/text embedding 检索 | `vec1` 后续 probe |
| API | FastAPI + Pydantic | 稳定接口与后台 job 查询 | CLI 同步使用同一 service |
| CLI | Typer/Click | 本地批处理入口 | 不绕过 domain policy |
| Jobs | 本地进程队列 | first-build 足够 | 后续再上 Redis/Celery |

### 11.2 模型路线口径

- **RVC**：用于 `P4` 快速 baseline。优点是训练快、反馈快；缺点是依赖检索索引，面对 20h 大规模真实会话数据时更容易被噪声、多场景、多说话人污染。结论：保留，但不押注。
- **So-VITS-SVC 4.1**：用于 `P5` 长训 voice conversion / SVC。它适合将输入语音转换为目标声线，但不是完整 TTS 产品。结论：作为高保真 VC 主线候选，但必须处理上游维护和环境兼容问题。
- **XTTS/OpenVoice-style TTS**：用于 owner 需要“输入文字 -> 输出目标声线语音”的场景。结论：作为单独 adapter 和 baseline，不与 SVC 混成一个模糊目标。
- **数据优先级**：高质量 2-5 小时目标纯净语音通常比低质量 20 小时更有价值；20 小时原始数据的价值在于筛选、覆盖情绪和构建验证集。

---

## 12. 接口化工作流程

### 12.1 Workflow 状态机

```text
recording: NEW
  -> INGESTED
  -> DIARIZED
  -> SLICED
  -> CLEANED
  -> TRANSCRIBED
  -> SCORED
  -> CURATED
  -> EXPORTED_TO_DATASET

dataset:
  DRAFT -> FROZEN -> TRAINING -> EVALUATED -> RELEASE_CANDIDATE | REJECTED

run:
  QUEUED -> RUNNING -> SUCCEEDED | FAILED | CANCELED
```

### 12.2 CLI contract

```bash
mvc ingest data/raw/meeting_001.m4a --speaker-owner owner_a
mvc diarize --recording rec_001 --pipeline preprocess.default
mvc slice --recording rec_001 --min-sec 2 --max-sec 10
mvc clean --recording rec_001 --method demucs
mvc transcribe --recording rec_001 --model whisper
mvc score --recording rec_001
mvc curate --dataset first-build --strategy speaker-pure-v1
mvc dataset freeze first-build
mvc train rvc --dataset first-build --profile quick
mvc train sovits --dataset first-build --profile long
mvc eval run run_20260613_001 --suite default
mvc infer vc --model model_001 --input samples/source.wav --out out.wav
mvc infer tts --model model_002 --text "..." --out out.wav
```

### 12.3 HTTP API surface

| Method | Path | 作用 |
|--------|------|------|
| `POST` | `/recordings` | 登记原始录音，返回 `recording_id` |
| `GET` | `/recordings/{id}` | 查询录音、处理状态和 artifacts |
| `POST` | `/jobs` | 创建 `ingest/diarize/slice/clean/transcribe/score/train/eval/infer` job |
| `GET` | `/jobs/{id}` | 查询 job 状态、日志和产物 |
| `GET` | `/segments` | 按 speaker、score、duration、status 过滤片段 |
| `PATCH` | `/segments/{id}` | 人工 keep/drop/fix 标注 |
| `POST` | `/datasets` | 创建 dataset draft |
| `POST` | `/datasets/{id}/freeze` | 冻结 manifest |
| `POST` | `/runs/train` | 提交训练任务 |
| `POST` | `/runs/eval` | 提交评估任务 |
| `POST` | `/inference/vc` | voice conversion 推理 |
| `POST` | `/inference/tts` | TTS 推理 |

### 12.4 Job payload 示例

```json
{
  "type": "diarize",
  "recording_id": "rec_001",
  "pipeline": "preprocess.default",
  "params": {
    "model": "pyannote-speaker-diarization",
    "min_speakers": 1,
    "max_speakers": 6
  }
}
```

### 12.5 Artifact contract

每个输出文件必须登记：

- `artifact_id`
- `kind`: `raw_audio | normalized_audio | diarization | segment_audio | cleaned_audio | transcript | embedding | manifest | checkpoint | eval_report | rendered_audio`
- `uri`
- `sha256`
- `source_artifact_id`
- `pipeline_version`
- `params_json`
- `created_by_job_id`

---

## 13. 本地 SQLite + vec0/vec1 数据库设计

### 13.1 关系型主 schema

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE speakers (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner', 'other', 'unknown')),
  consent_status TEXT NOT NULL CHECK (consent_status IN ('granted', 'denied', 'unknown', 'revoked')),
  created_at TEXT NOT NULL
);

CREATE TABLE recordings (
  id TEXT PRIMARY KEY,
  source_uri TEXT NOT NULL,
  sha256 TEXT NOT NULL UNIQUE,
  duration_sec REAL,
  sample_rate INTEGER,
  channels INTEGER,
  captured_at TEXT,
  status TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE segments (
  id TEXT PRIMARY KEY,
  recording_id TEXT NOT NULL REFERENCES recordings(id),
  speaker_id TEXT REFERENCES speakers(id),
  start_sec REAL NOT NULL,
  end_sec REAL NOT NULL,
  audio_uri TEXT,
  cleaned_audio_uri TEXT,
  transcript TEXT,
  status TEXT NOT NULL CHECK (status IN ('new', 'keep', 'drop', 'needs_review')),
  quality_score REAL,
  speaker_score REAL,
  noise_score REAL,
  overlap_score REAL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')),
  params_json TEXT NOT NULL DEFAULT '{}',
  started_at TEXT,
  finished_at TEXT,
  error TEXT
);

CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  uri TEXT NOT NULL,
  sha256 TEXT,
  source_artifact_id TEXT REFERENCES artifacts(id),
  created_by_job_id TEXT REFERENCES jobs(id),
  pipeline_version TEXT,
  params_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE datasets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'frozen', 'training', 'evaluated', 'rejected')),
  manifest_uri TEXT,
  manifest_sha256 TEXT,
  created_at TEXT NOT NULL,
  frozen_at TEXT
);

CREATE TABLE dataset_segments (
  dataset_id TEXT NOT NULL REFERENCES datasets(id),
  segment_id TEXT NOT NULL REFERENCES segments(id),
  split TEXT NOT NULL CHECK (split IN ('train', 'val', 'test')),
  PRIMARY KEY (dataset_id, segment_id)
);

CREATE TABLE model_runs (
  id TEXT PRIMARY KEY,
  model_family TEXT NOT NULL,
  dataset_id TEXT NOT NULL REFERENCES datasets(id),
  status TEXT NOT NULL,
  config_json TEXT NOT NULL DEFAULT '{}',
  checkpoint_uri TEXT,
  env_digest TEXT,
  git_commit TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE eval_metrics (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES model_runs(id),
  metric_name TEXT NOT NULL,
  metric_value REAL,
  metric_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE consent_ledger (
  id TEXT PRIMARY KEY,
  speaker_id TEXT NOT NULL REFERENCES speakers(id),
  scope TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('granted', 'revoked')),
  evidence_uri TEXT,
  created_at TEXT NOT NULL
);
```

### 13.2 `sqlite-vec` / `vec0` 默认方案

`sqlite-vec` 的 `vec0` 虚表适合 first-build：嵌入式、无服务、和 SQLite 同文件/同进程工作，能覆盖目标 speaker 匹配、相似片段召回、去重、文本/音频检索。

```sql
-- extension load 由应用启动时控制：
-- SELECT load_extension('vec0');

CREATE VIRTUAL TABLE segment_audio_embeddings USING vec0(
  segment_id TEXT PRIMARY KEY,
  embedding FLOAT[768]
);

CREATE VIRTUAL TABLE speaker_embeddings USING vec0(
  speaker_id TEXT PRIMARY KEY,
  embedding FLOAT[192]
);

CREATE VIRTUAL TABLE transcript_embeddings USING vec0(
  segment_id TEXT PRIMARY KEY,
  embedding FLOAT[384]
);
```

典型查询：

```sql
-- 找出和目标 speaker embedding 最相近的片段，用于 speaker purity review。
SELECT
  s.id,
  s.recording_id,
  s.start_sec,
  s.end_sec,
  v.distance
FROM segment_audio_embeddings v
JOIN segments s ON s.id = v.segment_id
WHERE v.embedding MATCH :query_embedding
  AND k = 50
ORDER BY v.distance;
```

使用规则：

- embedding 维度必须由 `embeddings/*_embedder.py` 明确声明，禁止同表混维度。
- relation truth 永远在普通表中；vector table 只存 `id + embedding`。
- 插入 segment 后不立即要求 embedding 完成；用 job 异步补齐。
- 删除或撤回 speaker 数据时，必须同时删除相关 vector rows。
- 训练集 freeze 时记录 embedding model name/version，避免后续 embedding 重算导致检索口径变化。

### 13.3 `vec1` 可选评估口径

`vec1` 不作为 first-build 主线默认项，只在以下条件满足时进入 probe：

- segment 规模超过 `100k`，`vec0` 查询延迟无法接受；
- 需要 ANN/量化索引能力；
- extension 在目标 OS/GPU/CPU 环境下可稳定构建、备份、恢复；
- SQL API 与应用 `VectorStore` 接口可兼容，不污染 domain 层。

建议保留接口：

```python
class VectorStore:
    def upsert(self, namespace: str, item_id: str, embedding: list[float]) -> None: ...
    def search(self, namespace: str, embedding: list[float], k: int, filters: dict | None = None) -> list[dict]: ...
    def delete(self, namespace: str, item_id: str) -> None: ...
```

`vec0_store.py` 是默认实现；`vec1_store.py` 只在 `006_optional_vec1_probe.sql` 和 feature flag 中启用。

---

## 14. Final recommendation

- **推荐序列**：`P0 关闭授权与目标形态 -> P1 建 SQLite/vec0/项目骨架 -> P2 跑 10-20 分钟样本预处理 spike -> P3 冻结 first-build dataset manifest -> P4 做 RVC/TTS baseline -> P5 做 So-VITS-SVC 长训 -> P6 以客观+主观评估决定 release candidate`。
- **一句话总结**：`myvoiceclone` 的胜负手不是押中某个模型名字，而是把真实会话录音系统性地变成干净、授权、可追溯、可比较的语音资产。

---

## 15. 交叉引用与修订历史

- **交叉引用**：
  - `myvoiceclone/initial-thoughts.md`
  - `00-templates/eval-planning.md`

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-13 | Codex | 初稿（stage=`proposed`） |
