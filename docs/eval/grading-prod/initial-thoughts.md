# Production Grading / Resource Credit Eval 可行性初探

> **对象**：生产级声音克隆评估体系：CPU/GPU credit 计量 + 生成音频还原度评分
> **日期**：2026-06-16
> **作者**：Codex（panel：none）
> **文档性质**：`eval / feasibility-study`（本文输出 go/no-go 证据，不冻结决策）
> **文档状态**：draft
> **Decision affected（必填）**：是否进入 `grading-prod` 设计与实现阶段
> **上游权威输入**：
> - 用户需求：按 API 上报 CPU/GPU 资源 credit；比较生成结果与原始音频，对训练/克隆结果做多维评分
> - 模板：`docs/templates/eval-feasibility-study.md`
> - 当前代码：`src/myvoiceclone/eval/objective.py`、`src/myvoiceclone/pipelines/evaluate.py`、`src/myvoiceclone/api/audit.py`
> **下游消费者**：`grading-prod` design/action-plan、DB migration、API contract、eval worker implementation

---

## 0. Verdict（结论先行）

- **结论 token（必填）**：`conditional-ready`
- **一句话**：可以进入实现设计，但必须把资源 credit 拆成“可审计原始计量 + 归一化 credit”，并明确单 GPU 独占与多任务共享 GPU 的归因边界。
- **gate 的决策**：生产级 grading/eval 体系 → 本结论建议 owner `推进`，但先冻结资源归因模型和评估指标口径。

---

## 1. 假设 / 问题

- **待验证假设**：
  - H1：可以为每次 run/job 记录 CPU/GPU 消耗，并转换为一个可上报的 credit 指标。
  - H2：可以对生成音频相对原始/参考音频进行多维 objective grading，覆盖说话人还原度、内容一致性、音质、韵律和安全可用性。
  - H3：这些指标能接入当前 myvoiceclone 的 `jobs`、`artifacts`、`eval_metrics`、`reports`、`api_request_logs` 链路。
- **为什么必须先验证**：资源 credit 会影响后续计费/限流/配额；还原度评分会影响训练结果是否可发布。若口径错误，会污染 API contract、DB schema、release gate 和用户信任。
- **可行的判据**：满足以下即判 `ready`：
  - 能拿到 GPU 能耗或等价硬件计量，并能按 job/run 形成可审计原始记录。
  - CPU 资源至少能拿到严格 CPU time；若要 CPU energy，则需检测 Linux powercap/RAPL 或平台等价接口。
  - 评分体系不依赖单一分数，而是有 speaker/content/quality/prosody/safety 分维度指标。
  - 所有指标能写入 SQLite，API 可按 run/job/report 查询。

---

## 2. 现状 / 锚点

| 维度 | 现状 | 锚点（file:line / 命令 / 凭据名） |
|------|------|-----------------------------------|
| API 审计 | 已有每请求 SQLite 日志，包含 trace/run/job/artifact/status/error | `src/myvoiceclone/api/audit.py`；`db/migrations/009_api_request_logs.sql` |
| Job 执行 | `JobRunner` 已有 step-level 事件，可包裹 resource span | `src/myvoiceclone/jobs/runner.py` |
| Eval 当前能力 | `evaluate_objective_metrics` 仍是 mock；`run_first_test_evaluation` 只做 WAV smoke metrics | `src/myvoiceclone/eval/objective.py`；`src/myvoiceclone/pipelines/evaluate.py` |
| DB 基础 | 已有 `eval_metrics`、`eval_samples`、`reports`，但缺少 resource usage/span 表 | `db/migrations/010_uuid_primary_ids.sql` |
| Artifact 关系 | rendered output 已能记录 reference/source artifact lineage | `src/myvoiceclone/storage/artifact_store.py` |
| ID 合约 | 新生成 ID 已统一为 `mvc_` UUID | `src/myvoiceclone/ids.py` |
| 真实 API 验证 | 端到端 XTTS API + Whisper 反向验证已跑通 | `.data/test-runs/api_clone_osr_summary.json`（本地运行产物，不入 git） |

---

## 3. 方法 · 试了什么（诚实段）

| 步骤 | 做了什么 | 是否真跑 | 证据 / 原因 |
|------|----------|----------|-------------|
| 1 | 发起 websearch，核对 NVIDIA GPU 计量接口 | 已运行 | NVIDIA NVML 文档显示 GPU total energy field 以 mJ 表示；DCGM 文档列出 SM/DRAM/Tensor active profiling fields |
| 2 | 发起 websearch，核对 CPU energy 可行性 | 已运行 | Linux powercap 文档描述 `intel-rapl` 下 `energy_uj`/`max_energy_range_uj`；但平台依赖明显 |
| 3 | 发起 websearch，核对 speaker similarity / speech quality 指标 | 已运行 | SpeechBrain ECAPA-TDNN、WavLM speaker verification、DNSMOS、STOI/PESQ/NISQA 等资料 |
| 4 | 读取当前 myvoiceclone eval/API/DB 代码 | 已运行 | `objective.py` 仍为 mock；`api_request_logs` 已有审计链路；`JobRunner` 可插入 span |
| 5 | 实测资源采样原型 | 未运行（静态分析） | 本文是 feasibility 初探；尚未实现 NVML/DCGM/RAPL collector |
| 6 | 实测 objective grading 原型 | 未运行（静态分析） | 已有一次 Whisper 反向验证，但未实现 speaker/quality/prosody 多指标 pipeline |

---

## 4. 结果

### 4.1 原型数字（如适用）

| 指标 | 期望 | 实测 | 是否达标 |
|------|------|------|----------|
| GPU energy delta per job | `gpu_energy_mj_end - gpu_energy_mj_start` | 未测 | ⏳未测 |
| GPU SM active second | `integral(SM_ACTIVE dt)` | 未测 | ⏳未测 |
| CPU core-seconds | cgroup/process CPU time delta | 未测 | ⏳未测 |
| CPU energy joules | RAPL/powercap energy delta | 未测，且当前 ARM/GB10 平台可能无 `intel-rapl` | ⏳未测 |
| Speaker similarity | ECAPA/WavLM cosine score | 未测 | ⏳未测 |
| Content WER | ASR transcript vs target text | 先前 API smoke 中 Whisper WER=0.0，但不是本体系原型 | ⏳需正式化 |

### 4.2 分类 / 缺口矩阵（如适用）

| 项 | 判定 | 说明 |
|----|------|------|
| GPU credit | Cat-A: feasible with caveat | 单 job 独占 GPU/container 时可用设备级 energy delta；多 job 共享 GPU 需独占/MIG/调度约束，否则严格归因困难 |
| GPU profiling | Cat-A/B | DCGM 可提供 SM/Tensor/DRAM active 等 profiling fields；需要验证当前 NVIDIA GB10 + 容器权限 |
| CPU credit | Cat-B | 严格 CPU time 可行；严格 CPU energy 依赖 powercap/RAPL 或平台等价接口，ARM 平台需实测 |
| DB 接入 | Cat-A | 新增 `resource_usage_spans`、`resource_samples`、扩展 `eval_metrics` 即可接入 |
| API 接入 | Cat-A | 现有 audit middleware 和 run/job status 可扩展 `resource_usage` 与 `grading_report` |
| Speaker similarity | Cat-A/B | ECAPA-TDNN/WavLM 可行，但阈值必须用本项目数据校准；不能直接当人类还原度 |
| 音质评分 | Cat-A/B | DNSMOS/NISQA 可做 non-intrusive MOS proxy；PESQ/STOI 等 intrusive metrics 仅适合同文本/同内容对齐场景 |
| Prosody/韵律 | Cat-B | 可做 F0、energy envelope、pause/speech rate、DTW 对齐；需要处理 TTS 文本与参考音频文本不同的问题 |
| 总分 | Cat-B | 可以输出 weighted grade，但必须保留原始维度和置信度，不建议只展示一个分 |

---

## 5. 技术可行性分析

### 5.1 Resource Credit 口径

建议 credit 分两层：

1. **Raw measurements（审计真相）**
   - `gpu_energy_mj`
   - `gpu_power_samples_mw`
   - `gpu_sm_active_seconds`
   - `gpu_dram_active_seconds`
   - `gpu_tensor_active_seconds`
   - `gpu_memory_peak_bytes`
   - `cpu_time_us`
   - `cpu_energy_uj`（若平台支持）
   - `wall_time_ms`（仅用于解释，不作为主 credit）

2. **Normalized credits（产品口径）**
   - `gpu_credit = gpu_energy_j / GPU_J_PER_CREDIT`
   - `gpu_compute_credit = gpu_sm_active_seconds / GPU_SM_SEC_PER_CREDIT`
   - `cpu_credit = cpu_energy_j / CPU_J_PER_CREDIT`，若无 CPU energy，则使用 `cpu_core_seconds / CPU_CORE_SEC_PER_CREDIT` 并标记 `credit_quality=estimated`
   - `total_credit = max(gpu_credit, gpu_compute_credit * compute_weight) + cpu_credit`

关键原则：

- credit 不是 wall time。wall time 只作为 debug 字段。
- GPU 首选能耗 delta，因为 NVML 有 total energy counter；若设备不支持 total energy，则轮询 power 并积分。
- CPU 首选 energy counter；没有 energy counter 时用 CPU time，不用 wall time。
- 多任务共享同一 GPU 时，设备级能耗不能天然归因到单个 job。要做到严格归因，必须引入执行约束：单 GPU 同时只跑一个 job、MIG 分片、或调度器保证 GPU 独占。

### 5.2 数据采集方案

建议新增 `ResourceMeter`：

- `ResourceMeter.start_span(subject_type, subject_id, job_id, step_name)`
- 启动后台 sampler，采样间隔建议 250ms-1000ms。
- stop 时写入 aggregate row，并可选保存 raw samples。
- JobRunner 在 `_run_observed_step()` 外层包裹 resource span。
- API middleware 不直接采集硬件，只关联 `trace_id`、`run_id`、`job_id` 和最终 `resource_usage_span_id`。

DB 草案：

```sql
CREATE TABLE resource_usage_spans (
    id TEXT PRIMARY KEY,
    trace_id TEXT,
    run_id TEXT,
    job_id TEXT,
    step_name TEXT,
    subject_type TEXT,
    subject_id TEXT,
    meter_mode TEXT NOT NULL, -- nvml_total_energy | nvml_power_integral | dcgm | cgroup | rapl | mixed
    credit_quality TEXT NOT NULL, -- measured | estimated | unavailable | shared_gpu_unattributed
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    wall_time_ms INTEGER,
    cpu_time_us INTEGER,
    cpu_energy_uj INTEGER,
    gpu_index INTEGER,
    gpu_uuid TEXT,
    gpu_energy_mj INTEGER,
    gpu_sm_active_sec REAL,
    gpu_dram_active_sec REAL,
    gpu_tensor_active_sec REAL,
    gpu_mem_peak_bytes INTEGER,
    gpu_credit REAL,
    cpu_credit REAL,
    total_credit REAL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE resource_samples (
    id TEXT PRIMARY KEY,
    span_id TEXT NOT NULL,
    sampled_at TIMESTAMP NOT NULL,
    cpu_time_us INTEGER,
    cpu_energy_uj INTEGER,
    gpu_power_mw INTEGER,
    gpu_util_pct REAL,
    gpu_mem_used_bytes INTEGER,
    gpu_sm_active REAL,
    gpu_dram_active REAL,
    gpu_tensor_active REAL,
    metadata_json TEXT DEFAULT '{}',
    FOREIGN KEY (span_id) REFERENCES resource_usage_spans(id) ON DELETE CASCADE
);
```

### 5.3 Grading 指标体系

建议按维度输出，不把所有信息压成一个不可解释分数：

| 维度 | 指标 | 工具候选 | 输入 | 注意事项 |
|------|------|----------|------|----------|
| speaker_identity | `speaker_similarity_ecapa`, `speaker_similarity_wavlm` | SpeechBrain ECAPA-TDNN；WavLM speaker verification | reference audio + generated audio | 需要同语言/长度/噪声校准；短音频不稳定 |
| content | `wer`, `cer`, `text_coverage` | Whisper/faster-whisper | target text + generated audio | 用于证明说了目标文本，不等同还原度 |
| quality | `dnsmos_ovrl`, `dnsmos_sig`, `dnsmos_bak`, clipping/rms/silence | DNSMOS/NISQA + 本地 smoke | generated audio | DNSMOS 是 MOS proxy，不是人类评审替代 |
| intelligibility | `stoi`/`pesq`/`si_sdr` | TorchMetrics/speechmetrics | 同文本或 voice conversion paired audio | arbitrary TTS 文本时不适合直接比较 reference |
| prosody | F0 RMSE/correlation, pause ratio, speech rate, energy envelope DTW | librosa/pyworld/praat-parselmouth | reference + generated, preferably same prompt | 若参考音频文本不同，只能做 speaker-level prosody profile |
| robustness | length, sample rate, non-silence, artifact validity | existing smoke metrics | generated artifact | 可作为 release gate 前置硬检查 |
| safety/provenance | consent, model/source, mock/real, license | existing metadata/policy | DB metadata | 评分报告必须标明是否 quality-gate eligible |

建议输出：

```json
{
  "overall_grade": 0.0,
  "quality_gate_eligible": true,
  "dimensions": {
    "speaker_identity": {"score": 0.0, "metrics": {}},
    "content": {"score": 0.0, "metrics": {}},
    "quality": {"score": 0.0, "metrics": {}},
    "prosody": {"score": 0.0, "metrics": {}},
    "robustness": {"score": 0.0, "metrics": {}}
  },
  "resource_usage": {
    "gpu_credit": 0.0,
    "cpu_credit": 0.0,
    "total_credit": 0.0,
    "credit_quality": "measured"
  }
}
```

### 5.4 评分流程

1. 输入：
   - `reference_artifact_id`
   - `generated_artifact_id`
   - `target_text`
   - optional `source_artifact_id` / `training_dataset_id`
2. 预处理：
   - resample to 16kHz for speaker models
   - trim silence
   - loudness normalize for metrics only，不覆盖原 artifact
3. 计算：
   - smoke metrics
   - ASR transcript + WER/CER
   - speaker embeddings cosine
   - quality MOS proxy
   - prosody profile
4. 记录：
   - raw per-metric rows 写 `eval_metrics`
   - sample linkage 写 `eval_samples`
   - aggregate report 写 `reports`
   - resource span 写 `resource_usage_spans`
5. API：
   - `POST /api/runs/{run_id}/grade`
   - `GET /api/reports/{report_id}`
   - `GET /api/runs/{run_id}/resource-usage`

---

## 6. 风险与残余

### 6.1 风险 × 缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 多任务共享 GPU 时 energy delta 不能严格归因 | credit 可能被其他任务污染 | P0 先要求单 GPU 单 active job；后续接 MIG/队列互斥/容器 GPU 独占 |
| NVML total energy 在部分设备/驱动不可用 | GPU energy 缺失 | fallback 到 power polling integral，并记录 `meter_mode=nvml_power_integral` |
| DCGM profiling fields 需要权限/设备支持 | SM/DRAM/Tensor active 无法采 | 将 DCGM profiling 作为 P1 增强；P0 只依赖 NVML energy + utilization |
| CPU energy 在 ARM/GB10 平台可能没有 RAPL | CPU energy credit 不可测 | P0 使用 cgroup/process CPU time；若 powercap 可用再升级为 measured energy |
| speaker similarity 与人类听感不完全一致 | 自动评分误判 | 使用多模型 ensemble + 校准集 + 人工 MOS 小样本做阈值校准 |
| PESQ/STOI 被误用于不同文本 TTS | 指标无意义 | 只在 paired/same-content 场景启用 intrusive metrics |
| Whisper WER 因 ASR 误差误判内容 | 内容评分不稳定 | 使用固定 ASR model/version，记录 transcript 与 confidence；必要时双 ASR |
| 单一 overall grade 掩盖问题 | 用户误解结果 | API 默认返回维度分和 raw metrics；overall 只作排序辅助 |

### 6.2 残余风险 / 硬前置条件（带进下一相位）

- **硬前置**：冻结 credit 公式和 `credit_quality` 语义；没有归因保证时不得标 `measured`。
- **硬前置**：准备 20-50 条本项目授权 reference/generated 样本，用于 speaker similarity 与 grading 阈值校准。
- **硬前置**：确认当前宿主机是否支持 NVML total energy、DCGM profiling、Linux powercap/RAPL。
- **携带约束**：所有评分报告必须记录 model/version/device/cache/source/license，避免不同模型版本的分数混在一起。

---

## 7. 实施计划草案

### P0：ResourceMeter 最小可用闭环

- 新增 `myvoiceclone/resources/`：
  - `nvml_meter.py`
  - `cpu_meter.py`
  - `resource_meter.py`
- 新增 migrations：
  - `resource_usage_spans`
  - `resource_samples`
- 在 `JobRunner._run_observed_step()` 包裹 span。
- API status/report 返回 resource aggregate。
- 验收：
  - mock job 也能生成 CPU time span。
  - real XTTS job 生成 GPU energy/credit 或明确 `unavailable`。

### P1：GPU/DCGM 增强

- 引入 DCGM exporter 或 DCGM Python/CLI collector。
- 支持 SM/DRAM/Tensor active seconds。
- 若进入多 job 并发，先实现队列层 GPU 独占锁。

### P2：Grading objective pipeline

- 新增 `myvoiceclone/eval/grading.py`：
  - `compute_speaker_similarity()`
  - `compute_content_metrics()`
  - `compute_quality_metrics()`
  - `compute_prosody_metrics()`
  - `aggregate_grade()`
- 接入 ECAPA-TDNN 或 WavLM speaker verification。
- 接入 Whisper/faster-whisper WER。
- 接入 DNSMOS/NISQA 或先做可选依赖探测。
- 写入 `eval_metrics`/`eval_samples`/`reports`。

### P3：API 与异步任务

- `POST /api/runs/{run_id}/grade`
- `GET /api/runs/{run_id}/resource-usage`
- `GET /api/jobs/{job_id}/resource-usage`
- `GET /api/reports/{report_id}` 增加 grading/resource section。

### P4：校准与 release gate

- 建立小型授权 calibration set。
- 记录人工 MOS/ABX 结果。
- 给每个维度设阈值：
  - speaker similarity minimum
  - WER/CER maximum
  - quality MOS minimum
  - clipping/silence hard fail
- release gate 只消费 `quality_gate_eligible=true` 的 measured metrics。

---

## 8. Websearch 来源摘要

- NVIDIA NVML 文档列出 GPU total energy field，单位为 mJ，适合作为 GPU energy delta 的首选来源：https://docs.nvidia.com/deploy/nvml-api/group__nvmlFieldValueEnums.html
- NVIDIA DCGM field identifiers 包含 SM active、SM occupancy、Tensor active、DRAM active 等 profiling fields，可用于“资源强度”而不只是时间：https://docs.nvidia.com/datacenter/dcgm/latest/dcgm-api/dcgm-api-field-ids.html
- DCGM Exporter 可把 GPU metrics 暴露为 Prometheus `/metrics`，适合后续生产化 telemetry：https://docs.nvidia.com/datacenter/dcgm/latest/gpu-telemetry/dcgm-exporter.html
- Linux powercap 文档说明 `intel-rapl` 下有 `energy_uj`、`max_energy_range_uj` 等能耗计数器；但它是平台相关能力：https://docs.kernel.org/power/powercap/powercap.html
- SpeechBrain ECAPA-TDNN pretrained model 支持 speaker verification，并通过 speaker embedding cosine distance 做验证：https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb
- Microsoft WavLM speaker verification model 要求 16kHz speech input，可作为第二套 speaker identity 指标：https://huggingface.co/microsoft/wavlm-base-sv
- Microsoft DNSMOS 是 non-intrusive speech quality MOS proxy，并声称与人类评分有较高相关性：https://www.microsoft.com/en-us/research/publication/dnsmos-a-non-intrusive-perceptual-objective-speech-quality-metric-to-evaluate-noise-suppressors-2/
- TorchMetrics 文档列出 STOI/PESQ/DNSMOS/NISQA 等音频指标，并明确 STOI 是 intrusive、依赖 clean/degraded paired signals：https://lightning.ai/docs/torchmetrics/stable/audio/short_time_objective_intelligibility.html

---

## 9. 结论与交接

- **最终 token**：`conditional-ready`
- **交给谁**：`grading-prod` design/action-plan — 在下一阶段落地真正实现。
- **若 `conditional-ready`，解锁条件**：
  - 确认本机/容器中 NVML total energy 与 DCGM profiling 可用性。
  - 冻结 credit 公式和 `credit_quality` 标记。
  - 准备校准数据集，不用未校准 speaker cosine 直接做发布判定。

---

## 附录

### A. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-16 | Codex | 初稿：资源 credit 与多维 grading 可行性分析 |
