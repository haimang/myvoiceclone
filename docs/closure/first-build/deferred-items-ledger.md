# myvoiceclone first-build 遗留项台账 (Deferred Items Ledger)

> **文档性质**：`deferred-items-ledger`
>
> | 字段 | 值 |
> |------|-----|
> | **项目** | `myvoiceclone` |
> | **build 阶段** | `first-build` |
> | **来源** | `P0-P8-review-VF-ledger.md §5.4` |
> | **台账创建日期** | `2026-06-13` |
> | **创建人** | `Antigravity` |
> | **文档状态** | `active` |
>
> **使用说明**：本台账为 append-only 记录，每一项均带 reopen 触发器条件。当触发器条件满足时，对应 item 应 reopen 并创建对应修复工单进入下一轮 build。

---

## 1. 台账总览

| ID | VF 来源 | 归属类 | 简要问题 | 触发 reopen 条件 | 目标 build |
|----|---------|--------|---------|-----------------|-----------|
| DEF-01 | V2.r | `[partial-delivery]` | vec0 虚表维度仍为 128（plan 要求 768/192/384）| 切换到真实 embedder 时 | second-build |
| DEF-02 | V10.r | `[partial-delivery]` | tests/fakes/ 仅为 stub 骨架（6 fake class 未完整实现）| adapter 接口冻结后 | second-build |
| DEF-03 | V16.r | `[partial-delivery]` | runner.py 补齐了 6 步 dispatch，但完整 14 种 job type 待实现 | pipeline step 接口稳定后 | second-build |
| DEF-04 | V17 | `[partial-delivery]` | 预处理链缺幂等性保护（已完成 step 不再重跑）| V15 states enum 稳定后 | second-build |
| DEF-05 | V18 | `[true-deferred]` | 3 embedder adapter 永久 mock（无真实 CLAP/ECAPA 模型路径）| 切换到 GPU 环境后 | training-phase |
| DEF-06 | V19 | `[true-deferred]` | scoring 硬编码 mock 值（无 pyannote/DNSMOS）| 切换到 live adapter 时 | training-phase |
| DEF-07 | V21 | `[true-deferred]` | 无 SQLite 并发写 WAL 测试 | second-build infra-hardening 阶段 | second-build |
| DEF-08 | V22 | `[partial-delivery]` | evaluate.py 缺主观评估集成（无真实语音合成）| 切换到真实训练+推理后 | training-phase |

---

## 2. 逐项详情

### DEF-01 · vec0 维度固定在 128

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V2.r (partial-delivery 剩余切片)` |
| **发现方** | `DeepSeek-R2 + MiniMax-R2` |
| **归属类** | `[partial-delivery]` |
| **严重度** | `critical`（影响 speaker 分离质量） |
| **当前状态** | `deferred` |

**现状描述**：

`db/migrations/003_vec0_embeddings.sql` 创建了 3 张 vec0 虚表，维度均硬编码为 `float[128]`：
```sql
CREATE VIRTUAL TABLE vec_speaker USING vec0(embedding float[128] ...);
CREATE VIRTUAL TABLE vec_audio   USING vec0(embedding float[128] ...);
CREATE VIRTUAL TABLE vec_text    USING vec0(embedding float[128] ...);
```

`final-execution-plan.md §14.5` 要求：
- `vec_speaker` → 192 dim（ECAPA-TDNN）
- `vec_audio` → 128 dim（CLAP, OK 如保持）
- `vec_text` → 768 dim（BERT/Sentence-Transformers）

**当前 mock 逻辑**：`AudioEmbedder.embed()` 返回 `[0.1] * 128`（mock），与 vec0(128) 兼容，所以测试通过。但切换到真实模型时会维度不匹配。

**reopen 触发器**：`AudioEmbedder` 或 `SpeakerEmbedder` 切换到真实模型实现时。

**修法预判**（second-build）：
1. 创建 `008_fix_vec0_dimensions.sql`，重建正确维度的 vec0 虚表（SQLite-vec 不支持 ALTER VIRTUAL TABLE，需 DROP + CREATE）
2. 更新 `vec0_store.py` 中 `_infer_dim()` 逻辑或接受 `dim` 参数
3. 更新 `embedding_models` 表中 CLAP/ECAPA/SBERT 的 `dimension` 字段

---

### DEF-02 · tests/fakes/ stub 骨架未完整实现

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V10.r (partial-delivery 剩余切片)` |
| **发现方** | `DeepSeek-R6 + MiniMax-R6` |
| **归属类** | `[partial-delivery]` |
| **严重度** | `medium` |
| **当前状态** | `deferred` |

**现状描述**：

`tests/fakes/__init__.py` 已创建 6 个 fake class stub（`FakeDiarizer`, `FakeSeparator`, `FakeASR`, `FakeTrainer`, `FakeEmbedder`, `FakeInference`），但：
- `FakeDiarizer.diarize()` 返回硬编码的 2 个 speaker turn
- `FakeSeparator.separate()` 直接 copy 输入文件
- Fakes 尚未被任何测试实际引用（当前测试仍用 MOCK_ADAPTERS 环境变量）

**reopen 触发器**：adapter 接口（Protocol/ABC）冻结后。

**修法预判**（second-build）：
1. 将各 fake class 改为实现正式 adapter Protocol/ABC
2. 将 conftest.py 中的 MOCK_ADAPTERS 依赖改为依赖注入 fakes
3. 为每个 fake class 加 parametrize fixtures

---

### DEF-03 · runner.py 完整 14 种 job type 未实现

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V16.r (partial-delivery 剩余切片)` |
| **发现方** | `DeepSeek-R8 + MiniMax-R10` |
| **归属类** | `[partial-delivery]` |
| **严重度** | `high` |
| **当前状态** | `deferred` |

**现状描述**：

`jobs/runner.py` 当前支持 9 种 job dispatch（`preprocess_all`, `ingest`, `train_sovits` + 6 步 step dispatch 新增的 `diarize/slice/clean/transcribe/score/curate`）。

`final-execution-plan.md §14.2` 列出完整 14 种：还缺 `train_rvc`, `synth_xtts`, `embed_audio`, `embed_speaker`, `export_dataset`。

**reopen 触发器**：pipeline step 接口稳定（signature 冻结）后。

**修法预判**（second-build）：补充 `_execute_train_rvc`, `_execute_synth_xtts`, `_execute_embed_audio`, `_execute_embed_speaker`, `_execute_export_dataset` 5 个方法。

---

### DEF-04 · 预处理链缺幂等性保护

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V17 (partial-delivery defer)` |
| **发现方** | `DeepSeek-R9` |
| **归属类** | `[partial-delivery]` |
| **严重度** | `high` |
| **当前状态** | `deferred` |

**现状描述**：

`jobs/runner.py:_execute_preprocess_all()` 的 6 步流程（ingest→diarize→slice→clean→transcribe→score）无任何「已完成即跳过」检查。若 job 重试（网络断开、OOM），整个链从头重跑，产生重复 artifact。

**依赖**：需要 V15（states enum）先稳定，且 `Recording` / `Segment` 状态判断要基于 `RecordingStatus` 枚举而非裸字符串。

**reopen 触发器**：second-build 状态机稳定后，且有真实重试场景测试时。

**修法预判**：在每步开始前检查 `recording.status` 是否已满足该步前置状态；使用 `RecordingStatus` enum 做边界。

---

### DEF-05 · 3 embedder adapter 永久 mock

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V18 (true-deferred)` |
| **发现方** | `DeepSeek-R10` |
| **归属类** | `[true-deferred]` |
| **严重度** | `high`（影响 dedup 和 speaker 分离精度） |
| **当前状态** | `deferred` |

**现状描述**：

3 个 embedder adapter（`AudioEmbedder`, `SpeakerEmbedder`, `TextEmbedder`）全部返回 mock 向量。没有真实模型加载路径、无 checkpoint 下载逻辑、无 `MODELS_DIR` 配置读取。

**first-build 设计决策**：mock embedder 是有意为之——first-build 专注可运行性，不依赖 GPU 环境。

**reopen 触发器**：切换到 GPU 环境 + ECAPA-TDNN/CLAP/SBERT 模型下载完成后。

**修法预判**（training-phase build）：
1. `SpeakerEmbedder` → 接入 pyannote.audio 的 ECAPA-TDNN
2. `AudioEmbedder` → 接入 LAION-CLAP
3. `TextEmbedder` → 接入 sentence-transformers (SBERT)
4. 同时触发 DEF-01（vec0 维度修正）

---

### DEF-06 · scoring 硬编码 mock 值

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V19 (true-deferred)` |
| **发现方** | `DeepSeek-R11` |
| **归属类** | `[true-deferred]` |
| **严重度** | `high`（直接影响数据集质量）|
| **当前状态** | `deferred` |

**现状描述**：

`pipelines/score.py` 计算 `quality_score/speaker_score/noise_score` 的逻辑全为 mock（随机或固定值），无真实 DNSMOS-P.808/pyannote 评分。

**reopen 触发器**：接入 live adapter（DNSMOS 或 MOS predictor）后。

**修法预判**（training-phase build）：接入 Microsoft DNSMOS 或等价模型；实现真实 SNR 计算。

---

### DEF-07 · 无 SQLite 并发写 WAL 测试

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V21 (true-deferred)` |
| **发现方** | `DeepSeek-R26` |
| **归属类** | `[true-deferred]` |
| **严重度** | `medium` |
| **当前状态** | `deferred` |

**现状描述**：

`storage/sqlite.py` 已开启 WAL（`PRAGMA journal_mode = WAL`）和 `busy_timeout = 5000`，但无测试覆盖并发写场景（多 job 同时写同一 DB 文件）。

**first-build 设计决策**：first-build 是单进程模型，并发写测试属 infra-hardening 范畴。

**reopen 触发器**：second-build 引入多工作进程（多 JobRunner）或 Celery worker 时。

**修法预判**：使用 `threading.Thread` 模拟 2-4 并发 `conn.execute()` 写操作；验证 WAL + `busy_timeout` 行为。

---

### DEF-08 · evaluate.py 缺主观评估集成

| 字段 | 值 |
|------|-----|
| **VF 来源** | `V22 (partial-delivery defer)` |
| **发现方** | `DeepSeek-R23` |
| **归属类** | `[partial-delivery]` |
| **严重度** | `medium` |
| **当前状态** | `deferred` |

**现状描述**：

`eval/report.py` 实现了 `generate_baseline_report` 和 `generate_train_report`，但主观评估（MOS 人工打分集成、A/B 测试结果录入）未实现。

**reopen 触发器**：切换到真实训练 + 推理后，有真实语音合成输出可供人工评估时。

**修法预判**：设计 subjective evaluation API endpoint（提交 MOS 分数）；将 MOS 分数 → `eval_samples.scores_json`；集成到 `release_gate` 判定。

---

## 3. 变更历史 (append-only)

| 版本 | 日期 | 变更 |
|------|------|------|
| `v0.1` | `2026-06-13` | 初次创建：8 项 deferred from VF-ledger §5.4 |

---

## 4. 第 2 轮 review 追加承接项（2026-06-13）

> 来源：`docs/code-review/first-build/P0-P8-2nd-review-VF-ledger.md §5.3 / §6.4`。
> 说明：本节仅记录本轮确认真实、必要且不适合在 first-build 内强行完成的后延项；已由本轮修复关闭的 finding 不重复登记。

| ID | VF 来源 | 归属类 | 简要问题 | 触发 reopen 条件 | 目标 build |
|----|---------|--------|---------|-----------------|-----------|
| DEF-09 | UF8 | `[partial-delivery]` | vec0 metadata 表已切 `embedding_jobs`，但三类向量真实维度迁移仍未完成 | 接入真实 speaker/audio/text embedder，或创建 migration 008 时 | second-build |
| DEF-10 | UF14 | `[partial-delivery]` | `live/gpu/slow` marker 已注册但无真实测试用例 | 引入 live adapter、GPU train job 或慢速端到端训练测试时 | second-build |
| DEF-11 | UF15 | `[partial-delivery]` | `pipeline_runs` 仍未接入生产写路径，recording 级预处理进度未完整推进 | 需要 audit UI、resume UI 或多步 job 可视化时 | second-build |
| DEF-12 | UF19 | `[true-deferred]` | API 统一 response envelope 与全局错误格式未引入 | 前端/外部 API consumer contract freeze 前 | api-contract-pass |
| DEF-13 | UF20 | `[true-deferred]` | `domain/policies.py` 仍直接执行 SQL/config 读取，未下沉到 storage/service 层 | security-governance hardening 或权限策略扩展时 | security-hardening |
| DEF-14 | UF21 | `[partial-delivery]` | CLI eval 与 scoring/adapter 仍含 mock/硬编码指标，真实模型下载脚本仍是占位 | 切换 live training/eval，或需要真实 objective metrics 时 | training-phase |
| DEF-15 | UF22 | `[true-deferred]` | CLI/API 入口未完全对称，缺 `mvc infer tts` 与 plan §15 路由完全对齐 | API/CLI contract freeze pass 开始时 | api-contract-pass |

### DEF-09 · vec0 真实维度迁移

| 字段 | 值 |
|------|-----|
| **VF 来源** | `P0-P8-2nd-review-VF-ledger.md UF8` |
| **当前状态** | `deferred` |

本轮已将 `Vec0Store` 的 metadata 表从旧 `embedding_items` 切到 migration 007 新建的 `embedding_jobs`。剩余风险是 vec0 虚表仍为 mock-friendly `float[128]`，未按真实模型维度重建。

**reopen 触发器**：接入真实 ECAPA/CLAP/SBERT embedding，或准备 migration 008 时。

**预期修法**：新增 migration 008，按目标维度重建 vec 虚表；为 `Vec0Store` 增加 namespace→dimension 校验；更新 embedding model seed 数据。

### DEF-10 · live/gpu/slow marker 真实测试

| 字段 | 值 |
|------|-----|
| **VF 来源** | `UF14` |
| **当前状态** | `deferred` |

first-build 只要求 marker taxonomy 存在并默认不运行；没有真实 GPU/live adapter 时强造空测试价值低。

**reopen 触发器**：任一 live adapter 或 GPU training path 接入。

### DEF-11 · pipeline_runs 与 recording 级进度

| 字段 | 值 |
|------|-----|
| **VF 来源** | `UF15` |
| **当前状态** | `deferred` |

`pipeline_runs` 表仍未作为生产 workflow ledger 使用，recording 级状态也未随 diarize/slice/clean/transcribe/score 完整推进。

**reopen 触发器**：需要 job resume UI、audit timeline UI、或多 worker 工作流追踪。

### DEF-12 · API 统一 response envelope

| 字段 | 值 |
|------|-----|
| **VF 来源** | `UF19` |
| **当前状态** | `deferred` |

统一 `{status,data,error,meta}` envelope 会改变所有 endpoint 的响应形状，属于 breaking API contract change，不适合在 first-build 修复回归时混入。

**reopen 触发器**：前端或外部 API consumer 开始对接前的 contract freeze pass。

### DEF-13 · policies 分层下沉

| 字段 | 值 |
|------|-----|
| **VF 来源** | `UF20` |
| **当前状态** | `deferred` |

本轮已让 `policy_events` 写入新 canonical 列，但 `domain/policies.py` 仍直接收 `sqlite3.Connection` 并执行 SQL。彻底修复需要增加 storage/service 层边界。

**reopen 触发器**：security-governance hardening 或策略 DSL 扩展。

### DEF-14 · 真实 evaluation / adapter / model download

| 字段 | 值 |
|------|-----|
| **VF 来源** | `UF21` |
| **当前状态** | `deferred` |

CLI eval、scoring 和部分 adapter 仍是 mock/硬编码实现；`download_models.sh` 已修路径但仍不下载真实权重。该项承接既有 DEF-05/DEF-06。

**reopen 触发器**：切换 live training/eval 或需要发布真实 objective metrics。

### DEF-15 · CLI/API contract 对称化

| 字段 | 值 |
|------|-----|
| **VF 来源** | `UF22` |
| **当前状态** | `deferred` |

当前 CLI/API 在 inference、eval、reports、training 参数模型上仍不完全对称，且缺 `mvc infer tts`。补齐会改变公开命令/路由 contract。

**reopen 触发器**：API/CLI contract freeze pass。

## 5. 变更历史追加

| 版本 | 日期 | 变更 |
|------|------|------|
| `v0.2` | `2026-06-13` | 追加第 2 轮 review deferred：DEF-09 至 DEF-15 |
