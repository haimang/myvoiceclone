# first-test reference-anchor

> **对象**：`first-test` 的参考锚定
> **日期**：`2026-06-13`
> **作者**：`GPT / Codex`（panel / sub-agents：`none`）
> **文档性质**：`eval / reference-anchor`（provisional；冻结零决策，喂 design）
> **文档状态**：`draft`
> **上游权威输入**：
> - `docs/eval/first-test/initial-planning-by-GPT.md`
> - `docs/eval/first-test/state-analysis-after-FB-by-GPT.md`
> - `docs/closure/first-build/deferred-items-ledger.md`
> **下游消费者**：`first-test proposed-planning`、`first-test pre-charter-qna`、`docs/action-plan/first-test/*`

---

## 0. 如何读这份台账

### 0.1 Verdict 图例

| 符号 | 含义 |
|------|------|
| ✅ 借 | 机制与思路都可借，按路线落地 |
| 🔶 部分 | 思路可借、机制需改造（见 §5 TR 过滤） |
| ⛔ 反例 | 不可借；记为要避开的坑 |
| 🆕 净新 | 无参考可借，myvoiceclone 净新实现 |

### 0.2 置信分层

| 置信 | 含义 |
|------|------|
| `HEAD` | 已对本仓 HEAD 文档/源码/台账复核 |
| `web-high` | 官方文档、标准、论文、模型卡或上游项目 README |
| `web-low` | 社区经验或非权威补充；本文尽量不用作主锚 |

### 0.3 主题轴

本阶段 first-test 内容先按业务内聚重组为 8 个簇：

| 轴 | 业务簇 | 覆盖 first-test 内容 |
|----|--------|----------------------|
| A | Preflight / 环境与入口收敛 | `FT1-01..07`：命令、extras、env、preprocess 入口、empty guard |
| B | Real audio preprocess / 数据准备 | 真实音频 ingest、FFmpeg、diarization、separation、ASR、dataset freeze |
| C | Real inference substrate / 真实推理 | `FT1-14..18`：XTTS/VC/RVC 候选、模型缓存、artifact 输出 |
| D | Evaluation / 真实评估与 release gate | `FT1-19..23`：objective、subjective、MOS/ABX、quality gate |
| E | FastAPI e2e surface / 前端接口 | `FT1-24..28`：upload、run orchestration、status、artifact/report 查询 |
| F | Observability / evidence | `FT1-08..13`：step events、trace、adapter metadata、evidence pack |
| G | Live tests / capstone | `FT1-28..30`：live/slow markers、API capstone、closure/deferred reconciliation |
| H | Deferred boundaries / 治理与后延边界 | DEF-01..15 中本阶段只条件 reopen 的项 |

---

## 1. 逐主题轴锚定矩阵

### 1.A 轴 A — Preflight / 环境与入口收敛

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| 先修项必须先于真实 e2e，否则 day-1 命令层失败 | `docs/eval/first-test/initial-planning-by-GPT.md:44-47`, `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:180-191` | HEAD planning / snapshot | ✅ | HEAD | 借“preflight first”的排序；不把真实模型接入和文档修复混成一个大任务 |
| dataset freeze 必须拒绝空 manifest | `docs/eval/first-test/initial-planning-by-GPT.md:46`, `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:185` | HEAD snapshot | ✅ | HEAD | 借 empty guard；不允许空数据集成为后续推理/评估输入 |
| SQLite WAL 适合本地单机，但不是并发平台保证 | https://sqlite.org/wal.html | SQLite official docs | 🔶 | web-high | 借 WAL/busy_timeout 的本地可靠性；不把它解释为多 worker 调度能力 |
| pytest 环境依赖测试应显式 skip/xfail | https://docs.pytest.org/en/stable/how-to/skipping.html | pytest docs | ✅ | web-high | 借 live dependency skip-with-reason；不让缺 GPU/模型时假绿 |

### 1.B 轴 B — Real audio preprocess / 数据准备

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| 真实预处理当前已有 adapter 入口，但依赖/token/缓存未自动检测 | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:140-154`, `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:227-240` | HEAD snapshot | ✅ | HEAD | 借 T1/T2 smoke 边界；不把 conditional adapter 当 ready |
| FFmpeg 是通用 media converter，适合做格式统一、probe、转码 | https://ffmpeg.org/ffmpeg.html | FFmpeg official docs | ✅ | web-high | 借格式规范化能力；不把 FFmpeg 当语音质量评估器 |
| `loudnorm` 可提供 EBU R128 loudness normalization，`silencedetect` 可做静音检测 | https://ffmpeg.org/ffmpeg-filters.html | FFmpeg filter docs | ✅ | web-high | 借 loudness/silence smoke metrics；不把它们当 MOS |
| pyannote diarization 模型需要接受条件才能访问 | https://huggingface.co/pyannote/speaker-diarization-3.1 | pyannote HF model card | ✅ | web-high | 借 token/terms preflight；不在测试中隐式下载失败后 fallback |
| Whisper Python API 可直接 load model 并 transcribe | https://github.com/openai/whisper | OpenAI Whisper repo | ✅ | web-high | 借本地 ASR 接入方式；不把完整文件 sliding-window 行为隐藏在 metadata 外 |
| Demucs 可分离 vocals 等 stems | https://github.com/facebookresearch/demucs | Demucs repo | 🔶 | web-high | 借 vocal extraction smoke；不把 music-source-separation 结果等同干净 speech enhancement |

### 1.C 轴 C — Real inference substrate / 真实推理

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| 当前真实 RVC/SoVITS/XTTS adapter 未实现，本阶段必须选一条最小真实推理路 | `docs/eval/first-test/initial-planning-by-GPT.md:48`, `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:180` | HEAD snapshot | ✅ | HEAD | 借“单主路 substrate”的约束；不同时铺开三套模型栈 |
| XTTS-v2 支持短参考音频 voice cloning、17 种语言、24kHz 输出 | https://huggingface.co/coqui/XTTS-v2 | Coqui HF model card | 🔶 | web-high | 借“预训练模型 + speaker_wav → wav artifact”路线；需先复核 CPML license 和模型缓存 |
| Coqui TTS Python/CLI 支持 `speaker_wav`、`tts_to_file`、voice conversion to file | https://coqui-tts.readthedocs.io/en/latest/inference.html | Coqui TTS docs | 🔶 | web-high | 借最小推理 API 形态；不把 Coqui CLI 直接暴露为我方 contract |
| RVC library/API 形态可提供 `rvc infer -m model -i input -o output` | https://github.com/RVC-Project/Retrieval-based-Voice-Conversion | RVC project repo | 🔶 | web-high | 借“model/input/output artifact”抽象；不借其工作目录强假设 |
| RVC WebUI 需要 HuBERT/pretrained/UVR/RMVPE/FFmpeg 等多项前置 | https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/blob/main/docs/en/README.en.md | RVC WebUI docs | ⛔ | web-high | 作为反例：不能把大量隐式权重下载塞进 first-test 主路 |
| XTTS-v2 模型卡标明 Coqui Public Model License | https://huggingface.co/coqui/XTTS-v2 | Coqui HF model card | ⛔ | web-high | 作为治理反例：不能默认可商用/可发布；first-test 只能做本地研究验证 |

### 1.D 轴 D — Evaluation / 真实评估与 release gate

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| 当前 objective/scoring 多为 mock，真实评估必须显式标记 metric source | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:150-154`, `docs/eval/first-test/initial-planning-by-GPT.md:162-166` | HEAD snapshot / planning | ✅ | HEAD | 借 mock/real separation；不把 mock score 放进 quality pass |
| DNS Challenge 使用 P.835 维度：SIG、BAK、OVRL，并结合 WAcc | https://github.com/microsoft/dns-challenge | Microsoft DNS Challenge repo | 🔶 | web-high | 借 SIG/BAK/OVRL 的指标语义；不直接承诺完整 DNSMOS 接入 |
| ITU P.808 是 crowdsourcing 主观语音质量评估建议 | https://www.itu.int/rec/T-REC-P.808/en | ITU recommendation | 🔶 | web-high | 借 MOS/ACR 的评估方向；first-test 降级为本地小样本人工录入 |
| Microsoft P.808 Toolkit 支持 ACR/DCR/CCR/P.835 crowdsourcing 方法 | https://github.com/microsoft/P.808 | Microsoft P.808 repo | 🔶 | web-high | 借表单字段与分析思路；不借 AMT/Prolific 平台机制 |
| TorchAudio-SQUIM 可估计 PESQ/STOI/SI-SDR 与 MOS | https://docs.pytorch.org/audio/2.7.0/tutorials/squim_tutorial.html | PyTorch/TorchAudio docs | 🔶 | web-high | 借 reference-free objective proxy 候选；不把代理指标当最终主观质量 |

### 1.E 轴 E — FastAPI e2e surface / 前端接口

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| FastAPI e2e surface 必须覆盖 run、upload、preprocess、infer、eval、trace | `docs/eval/first-test/initial-planning-by-GPT.md:168-178` | HEAD planning | ✅ | HEAD | 借接口面分层；不只做 `/jobs/{id}/run` wrapper |
| FastAPI `UploadFile`/`File` 是上传文件的标准入口 | https://fastapi.tiangolo.com/tutorial/request-files/ | FastAPI docs | ✅ | web-high | 借上传 surface；上传后应立即落 artifact，不保留临时文件对象为长任务依赖 |
| FastAPI BackgroundTasks 适合响应后执行慢处理，例如返回 202 后处理文件 | https://fastapi.tiangolo.com/tutorial/background-tasks/ | FastAPI docs | 🔶 | web-high | 借 202 + async trigger 思路；真实 GPU/长推理仍应落 DB job，可恢复、可查询 |
| FastAPI TestClient 可在不建真实 socket 的情况下测试 app | https://fastapi.tiangolo.com/tutorial/testing/ | FastAPI docs | ✅ | web-high | 借 in-worker API tests；live HTTP capstone 仍需单独跑 |

### 1.F 轴 F — Observability / evidence

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| 当前 DB 能记录主体对象，但 step event、stderr、model version、policy trace 不足 | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:119-138` | HEAD snapshot | ✅ | HEAD | 借“最小可观测性先补”的边界；不先建设完整监控平台 |
| OpenTelemetry span 可加 attributes、events、status、exception | https://opentelemetry.io/docs/languages/python/instrumentation/ | OpenTelemetry docs | 🔶 | web-high | 借 trace vocabulary；first-test 先映射为 DB `job_events`/trace JSON |
| OpenTelemetry logging 可注入 trace/span/service 信息 | https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html | OTel Python contrib docs | 🔶 | web-high | 借 correlation-id 思路；不把 OTel SDK 作为 P0 硬依赖 |
| evidence pack 应记录 env、commands、stdout/stderr、DB summary、artifact manifest | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:308-331` | HEAD snapshot | ✅ | HEAD | 借 run folder 结构；不把大音频产物放入 repo |

### 1.G 轴 G — Live tests / capstone

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| first-test capstone 必须含真实输入、真实推理输出、真实评估报告、API trace、evidence pack | `docs/eval/first-test/initial-planning-by-GPT.md:186-187` | HEAD planning | ✅ | HEAD | 借 capstone evidence shape；不接受单脚本成功作为完成标准 |
| pytest skip/xfail 适合依赖外部资源的测试 | https://docs.pytest.org/en/stable/how-to/skipping.html | pytest docs | ✅ | web-high | 借 live/slow marker 语义；缺 token/模型时必须报告 skipped reason |
| pytest monkeypatch 可安全设置/删除 env vars | https://docs.pytest.org/en/stable/how-to/monkeypatch.html | pytest docs | ✅ | web-high | 借 env isolation；不让测试污染 `DB_PATH/ARTIFACT_ROOT/MOCK_ADAPTERS` |

### 1.H 轴 H — Deferred boundaries / 治理与后延边界

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| vec0 真实维度和 embedder 只在真实 embedding 进入关键路径时 reopen | `docs/closure/first-build/deferred-items-ledger.md:22-29`, `docs/eval/first-test/initial-planning-by-GPT.md:52-53` | HEAD deferred / planning | ✅ | HEAD | 借条件 reopen；不把 embedding 平台塞进 first-test 主路 |
| pipeline_runs/recording 级进度在需要 UI/audit/resume 时 reopen | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:93`, `docs/eval/first-test/initial-planning-by-GPT.md:51` | HEAD | 🔶 | HEAD | 借 recording timeline 概念；第一版可用 job_events + run summary 降级 |
| API envelope 属 contract freeze 前再处理的 breaking change | `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:92`, `docs/eval/first-test/initial-planning-by-GPT.md:50` | HEAD | 🔶 | HEAD | 借“响应契约需冻结”的纪律；不在 reference-anchor 决定 envelope |
| license/provenance 需进入真实音频与合成输出 trace | `docs/eval/first-test/initial-planning-by-GPT.md:89-90`, https://huggingface.co/coqui/XTTS-v2 | HEAD + model card | ✅ | HEAD / web-high | 借 provenance 记录；不做无来源真实音频或无许可模型输出 |

---

## 2. 反例坑表（⛔）

| 反例 | 来源 | 为什么不可借 | 我们怎么做 |
|------|------|--------------|------------|
| 把 RVC WebUI 的多权重/多目录/交互式工作流直接当 first-test 主路 | https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/blob/main/docs/en/README.en.md | 其前置包含 HuBERT、pretrained、UVR、RMVPE、FFmpeg 等大量隐式资产，容易让 first-test 变成环境排错 | 若用 RVC，只借 `model/input/output` 抽象；权重清单必须显式进入 preflight |
| 把 XTTS-v2 模型卡能力当成发布许可 | https://huggingface.co/coqui/XTTS-v2 | 模型卡标明 Coqui Public Model License；真实用途和输出发布需许可复核 | first-test 只记录本地研究用途；release gate 必须包含 license/provenance |
| 用 BackgroundTasks 承载长 GPU 推理并依赖请求内 UploadFile 生命周期 | https://fastapi.tiangolo.com/tutorial/background-tasks/ | BackgroundTasks 适合响应后慢处理，但不是可恢复 job queue；上传临时对象不应成为长任务输入 | 上传后立即写 artifact，DB job 只引用 artifact/path |
| 把 DNSMOS/SQUIM/PESQ/STOI 代理分数当最终主观质量 | https://docs.pytorch.org/audio/2.7.0/tutorials/squim_tutorial.html, https://github.com/microsoft/dns-challenge | 代理指标有用但不能替代听感和合规判断 | report 中分层标记 `objective_proxy`、`manual_mos`、`release_gate` |
| 先建完整 OTel/监控平台再跑 first-test | https://opentelemetry.io/docs/languages/python/instrumentation/ | 机制重，偏离 first-test 关键路径 | 先做 DB events、trace JSON、stderr 摘要；OTel 术语作为后续映射 |
| 缺外部依赖时让 live tests 绿过 | https://docs.pytest.org/en/stable/how-to/skipping.html | 会把不可运行误判为可运行 | 使用 `skip with reason`，并在 evidence pack 记录 skip denominator |

---

## 3. 净新表（🆕）

| 净新点 | 为什么无参考 | 落点（哪个 design/相位） |
|--------|--------------|--------------------------|
| myvoiceclone first-test run ledger | 外部工具不会知道我方 `jobs/artifacts/model_runs/eval_metrics/release_gates` schema | `FT1-P1/P4/P5` |
| `MOCK_ADAPTERS` 与真实 adapter 的证据隔离 | 这是我方 first-build 遗留的特殊风险 | `FT1-P1/P3/P5` |
| API trace 汇总 policy/release/eval/artifact 的本地 schema 视图 | FastAPI/OTel 只能给机制，不给我方 domain trace | `FT1-P4` |
| 从真实 preprocess 产物到真实 inference 的 artifact contract | 取决于我方 dataset manifest 与 adapter 输出格式 | `FT1-P2/P3` |
| first-test closure 对 DEF-01..15 的条件关闭/继续后延规则 | 外部参考无法替代我方 deferred ledger | `FT1-P5` |

---

## 4. Web 来源台账

| 主张 | URL | 置信 | 用途 |
|------|-----|------|------|
| FastAPI 文件上传使用 `File` / `UploadFile` | https://fastapi.tiangolo.com/tutorial/request-files/ | web-high | API upload surface |
| FastAPI BackgroundTasks 可在返回响应后执行慢处理 | https://fastapi.tiangolo.com/tutorial/background-tasks/ | web-high | 202 accepted + DB job trigger 的参考 |
| FastAPI TestClient 支持 in-worker API 测试 | https://fastapi.tiangolo.com/tutorial/testing/ | web-high | API unit/integration tests |
| pyannote speaker-diarization-3.1 需要接受访问条件 | https://huggingface.co/pyannote/speaker-diarization-3.1 | web-high | diarization preflight |
| OpenAI Whisper Python API 支持本地 `load_model` + `transcribe` | https://github.com/openai/whisper | web-high | ASR adapter |
| Demucs 可分离 vocals 等 stems | https://github.com/facebookresearch/demucs | web-high | separation adapter |
| FFmpeg 可做 media convert；filters 有 loudnorm/silencedetect | https://ffmpeg.org/ffmpeg.html, https://ffmpeg.org/ffmpeg-filters.html | web-high | normalize + smoke metrics |
| XTTS-v2 支持 short-reference voice cloning，但有 CPML license | https://huggingface.co/coqui/XTTS-v2 | web-high | inference substrate candidate + governance |
| Coqui TTS 支持 `speaker_wav`、voice conversion、CLI 输出 wav | https://coqui-tts.readthedocs.io/en/latest/inference.html | web-high | adapter API shape |
| RVC project exposes library/CLI inference but requires explicit assets | https://github.com/RVC-Project/Retrieval-based-Voice-Conversion | web-high | alternative inference substrate |
| RVC WebUI requires multiple pre-model assets | https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/blob/main/docs/en/README.en.md | web-high | anti-pattern/preflight warning |
| DNS Challenge uses P.835 SIG/BAK/OVRL and WAcc | https://github.com/microsoft/dns-challenge | web-high | objective eval vocabulary |
| ITU P.808 defines crowdsourced subjective speech quality evaluation | https://www.itu.int/rec/T-REC-P.808/en | web-high | subjective eval vocabulary |
| Microsoft P.808 toolkit implements ACR/DCR/CCR/P.835 methods | https://github.com/microsoft/P.808 | web-high | MOS/ABX form inspiration |
| TorchAudio-SQUIM estimates PESQ/STOI/SI-SDR/MOS proxies | https://docs.pytorch.org/audio/2.7.0/tutorials/squim_tutorial.html | web-high | objective proxy candidates |
| OpenTelemetry Python spans support attributes/events/status/exceptions | https://opentelemetry.io/docs/languages/python/instrumentation/ | web-high | observability vocabulary |
| OpenTelemetry logging can inject trace/span IDs into logs | https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html | web-high | log correlation reference |
| pytest skip/xfail and monkeypatch support live-test gating/env isolation | https://docs.pytest.org/en/stable/how-to/skipping.html, https://docs.pytest.org/en/stable/how-to/monkeypatch.html | web-high | live/slow test harness |
| SQLite WAL is documented for local DB durability/concurrency semantics | https://sqlite.org/wal.html | web-high | storage boundary |

---

## 5. Substrate-fit / 技术路线（TR）过滤复核

本 reference-anchor 使用以下本地技术路线过滤：

| TR | 路线 |
|----|------|
| `TR-1` | first-test 仍以本地单机、SQLite、同步/可恢复 DB job 为基线 |
| `TR-2` | 所有真实 e2e 证据必须落到 DB/artifact/evidence pack，不靠临时 stdout |
| `TR-3` | 真实路径禁止 silent fallback 到 mock；mock/real 必须在 metadata/report 中显式区分 |
| `TR-4` | FastAPI 提供 e2e surface，但第一版不强行引入生产级任务队列 |
| `TR-5` | 模型权重、token、license、source provenance 先显式化，再接入 capstone |
| `TR-6` | live/gpu/slow 测试必须 gated，缺依赖时 skip with reason，并计入 denominator |
| `TR-7` | 大文件和 run evidence 继续落 `/mnt/usb/workspace/myvoiceresearch`，repo 不存真实音频产物 |

| 借鉴点 | 原机制 | 与 myvoiceclone 路线是否冲突 | 过滤后落地形态（降级/重映射/直采） |
|--------|--------|------------------------------|-------------------------------------|
| FastAPI UploadFile | 请求中直接接收上传文件 | 兼容 `TR-2/TR-7`，但长任务不能依赖临时对象 | 直采 upload，立即写 artifact，再创建 DB job |
| FastAPI BackgroundTasks | 响应后执行任务 | 与 `TR-1/TR-4` 部分冲突：不可恢复，不是 job ledger | 降级为“触发 DB job 后返回 202”；实际状态由 jobs/job_events 查询 |
| OpenTelemetry spans/events | SDK trace pipeline | 与 P0 scope 部分冲突：引入平台过重 | 重映射为 `job_events` + trace JSON 字段命名；OTel 后续可接 |
| FFmpeg loudnorm/silencedetect | filter-based audio analysis | 兼容 `TR-2`，但不是质量评价 | 直采为 smoke metrics，不进入 quality pass |
| pyannote diarization | HF gated model access | 兼容 `TR-5`，但需要 token/terms | preflight 显式校验 token、模型访问、cache path |
| Whisper transcribe | 本地模型加载与整文件转写 | 兼容 `TR-2/TR-5`，但耗时和模型版本需记录 | adapter metadata 记录 model name、device、duration、cache |
| Demucs separation | music stem separation | 与 speech-quality 目标部分不完全贴合 | 只作为 optional vocal extraction smoke，不当作 speech enhancement 质量保证 |
| XTTS-v2 | short reference voice cloning | 兼容目标，但 license/VRAM/cache 风险高 | 作为优先候选之一；必须记录 CPML、模型缓存、output artifact |
| RVC Project | library/CLI VC inference | 兼容 artifact contract，但资产复杂 | 借 `model/input/output` 抽象；权重清单进入 preflight |
| RVC WebUI | UI + 多预模型资产 | 与 `TR-1/TR-5` 冲突 | 仅作反例，不作为 first-test 主路 |
| DNSMOS/P.835 | 多维客观/主观质量体系 | 兼容评估目标，但完整接入较重 | 第一版可借 SIG/BAK/OVRL 字段语义；实现可先用 smoke + proxy |
| P.808 Toolkit | crowdsourcing 平台 | 与本地 first-test scope 冲突 | 降级为本地 MOS/ABX 表单与字段，不接 AMT/Prolific |
| TorchAudio-SQUIM | pretrained objective proxy | 兼容但不是最终质量真值 | 作为 optional objective proxy，报告标 `proxy` |
| pytest skip/monkeypatch | test harness primitives | 兼容 `TR-6` | 直采 live/slow skip reason 和 env isolation |
| SQLite WAL | local WAL DB mode | 兼容 `TR-1`，但非多 worker 保证 | 直采单机测试；多 worker 并发仍 deferred |

- **substrate-fit 总结（对 HEAD）**：first-test 的外部参考应服务于“本地可复现真实闭环”，不是搬来一整套训练平台。最适配当前 HEAD 的路线是：先修 preflight/observability，选一条预训练真实推理 substrate，所有输入/输出/指标都落 artifact 与 DB trace，再由 FastAPI surface 串起来。

---

## 6. 核验记录

| 锚点 | 是否核验 | 核验方式 | 备注 |
|------|----------|----------|------|
| `docs/eval/first-test/initial-planning-by-GPT.md:44-61` | ✅ 已核 | `nl -ba` | 目标与 phase 映射 |
| `docs/eval/first-test/initial-planning-by-GPT.md:121-187` | ✅ 已核 | `nl -ba` | `FT1-01..30` 工作项 |
| `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:119-154` | ✅ 已核 | `nl -ba` | storage/pipeline 状态 |
| `docs/eval/first-test/state-analysis-after-FB-by-GPT.md:180-191` | ✅ 已核 | `nl -ba` | blocker/gap |
| `docs/closure/first-build/deferred-items-ledger.md:22-29` | ✅ 已核 | `nl -ba` | DEF-01..08 总览 |
| FastAPI request files | ✅ 已核 | web open | 官方 docs |
| FastAPI background tasks | ✅ 已核 | web open | 官方 docs |
| FastAPI testing | ✅ 已核 | web open | 官方 docs |
| pyannote speaker-diarization-3.1 | ✅ 已核 | web open | HF model card |
| OpenAI Whisper repo | ✅ 已核 | web open | GitHub official |
| Demucs repo | ✅ 已核 | web open | GitHub upstream |
| FFmpeg docs | ✅ 已核 | web open/find | 官方 docs |
| Coqui XTTS-v2 model card | ✅ 已核 | web open/find | HF model card |
| Coqui TTS inference docs | ✅ 已核 | web open/find | ReadTheDocs |
| RVC Project / RVC WebUI | ✅ 已核 | web open | GitHub upstream |
| Microsoft DNS Challenge | ✅ 已核 | web open | GitHub upstream |
| ITU P.808 | ✅ 已核 | web search/open | 标准页面 |
| Microsoft P.808 Toolkit | ✅ 已核 | web open | GitHub upstream |
| TorchAudio-SQUIM | ✅ 已核 | web open | PyTorch docs |
| OpenTelemetry Python docs | ✅ 已核 | web open | official docs |
| pytest skip/monkeypatch | ✅ 已核 | web open | official docs |
| SQLite WAL | ✅ 已核 | web open | official docs |

---

## 附录

### A. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-13 | GPT / Codex | 初稿：first-test 业务簇 + web reference anchors |
