# myvoiceclone production-ready gap study and state analysis

> **对象（我方）**：`myvoiceclone production-ready voiceclone runtime / API / data / environment`
> **对象**：`after NF1 containerization（new-refactors / production-readiness review）`
> **日期**：`2026-07-07`
> **作者**：`Codex`
> **文档性质**：`eval / state-analysis + gap-study`（本文是现状快照 + 缺口台账；不是 closure / verdict / charter；冻结零决策）
> **调查类型 / body 轴**：`按子系统 + 按生产执行问题`
> **范围围栏（scope-fence）**：只审查当前仓库、当前 `ai-voiceclone` 容器、当前 SQLite/runtime artifacts；不引入外部新方案，不修改业务代码。
> **对照参考**：当前目标口径：真实生产准备、容器自包含、生产级异步 voiceclone API suite。
> **文档状态**：`draft`
> **对照基线**：NF1 容器化 closure、first-build / first-test 既有实现、当前运行容器事实。
> **上游权威输入**：
> - 用户要求：抛弃 mock 思路，进入真实 production-ready voiceclone。
> - `docs/templates/eval-gap-study.md`
> - `docs/templates/eval-state-analysis.md`
> - 当前代码、测试、Docker、运行容器探针。
> **下游消费者**：后续 production-ready charter / API suite charter / image rebuild charter。

---

## 0. 水位 / Verdict（结论先行）

- **一句话现状**：NF1 已把运行边界收到 `ai-voiceclone` 容器和 658 端口，但当前产品仍处在 first-test / mock-heavy 工作台状态，离“真实生产级异步 voiceclone”有 blocker 级差距。
- **一句话缺口判断**：真实 XTTS 推理有一次 smoke 证据，但真实预处理、真实训练、真实质量评估、完整 API CRUD/状态控制、模型预置、自包含镜像均未达到 production-ready。
- **最关键的断点**：真实 So-VITS/RVC 训练未实现；容器缺真实预处理依赖；真实质量评分/客观评估不可用；API 缺取消/重试/删除/全链 orchestration；长任务没有 durable worker。
- **总体方向建议**：进入“生产化重构”，先补 execution/image/API control plane，再补数据治理和真实评估；不得把现有 mock pytest 作为 production-ready 证据。

---

## 1. 方法与可采信证据基线

- **证据来源**：
  - 代码：`src/myvoiceclone/api/*`、`src/myvoiceclone/jobs/*`、`src/myvoiceclone/pipelines/*`、`src/myvoiceclone/adapters/*`、`src/myvoiceclone/storage/*`。
  - 数据库：`db/migrations/*`、当前容器内 `.data/db/myvoiceclone.sqlite` 表统计。
  - 环境：`infra/docker/Dockerfile.ai-voiceclone`、`infra/docker/compose.voiceclone.yaml`、容器内 dependency/preflight 探针。
  - 文档：`README.md`、`docs/ops/local-setup.md`、NF1 closure。
- **可采信判据**：
  - 以当前代码 `file:line` 为主。
  - 以容器内 `docker exec ai-voiceclone ...` 的实际结果为运行事实。
  - 以 `/openapi.json` 的路径列表为当前 HTTP surface 事实。
  - 不把 `MOCK_ADAPTERS=true` pytest 通过视为真实生产证据。
- **范围围栏**：
  - 本文不评估外部 So-VITS/RVC 项目的优劣。
  - 本文不选择最终训练框架。
  - 本文不修复代码，只输出 gap 和建造建议。

---

## 2. 回看清单（交付快照）

### 2.1 交付价值台账

| 单元 | 声称交付 | 真实落地（代码核） | 评级 | 锚点 |
|---|---|---|---|---|
| NF1 container boundary | 容器-only、658 端口 | `ai-voiceclone` compose 暴露唯一 `658:658`，运行容器 healthy | delivered-for-runtime-boundary | `infra/docker/compose.voiceclone.yaml:16` |
| API service | FastAPI 业务 API | OpenAPI 暴露 recordings/segments/datasets/jobs/training/inference/runs/reports/audit paths；HTTP `/api/jobs` 返回 200 | partial | `src/myvoiceclone/api/app.py:20` |
| Run status query | 可通过 API 查 voiceclone 状态 | `/api/runs/{run_id}/status` 聚合 jobs/events/artifacts，但依赖 JSON LIKE 和 DB 查询，不是强状态机控制面 | partial | `src/myvoiceclone/api/routes_runs.py:248` |
| Job runner | 异步 job 执行 | 支持 ingest/preprocess/train_sovits/infer/eval dispatch，写 step events；但由 API 进程/BackgroundTasks 触发，无 durable worker | partial | `src/myvoiceclone/jobs/runner.py:78` |
| Real XTTS inference | 真实参考音频推理 | `XttsAdapter.synth_to_file` 可调用 Coqui TTS；当前容器有一次 OSR XTTS smoke artifact | partial | `src/myvoiceclone/adapters/training/xtts_adapter.py:41` |
| Real preprocessing | 真实 diarize/clean/transcribe | 代码有 PyAnnote/Demucs/Whisper adapter，但当前容器缺 pyannote/whisper/demucs CLI，且 token/model access 未就绪 | missing-in-runtime | `infra/docker/Dockerfile.ai-voiceclone:15` |
| Real So-VITS/RVC training | 可真实训练 voiceclone | 非 mock 下 RVC/So-VITS 明确 `NotImplementedError` | missing | `src/myvoiceclone/adapters/training/sovits_adapter.py:27` |
| Dataset freeze | 数据集 manifest | 能冻结 cleaned/transcribed segments 并防 recording split leak | partial | `src/myvoiceclone/pipelines/export_dataset.py:46` |
| Quality scoring | 生产级数据质量打分 | 非 mock 下直接拒绝；mock 下使用固定常数 | missing | `src/myvoiceclone/pipelines/score.py:28` |
| Objective eval | 生产质量指标 | speaker_similarity/WER/noise 等是 mock，`quality_gate_eligible=false` | placeholder | `src/myvoiceclone/eval/objective.py:71` |
| Model cache/download | 镜像可自包含模型 | `download_models.sh` 只写 manifest，不下载/校验真实权重 | placeholder | `scripts/download_models.sh:17` |
| Governance | consent/release gate | release policy 默认配置关闭；waive 可人工置 passed；无 API auth | partial | `src/myvoiceclone/domain/policies.py:19` |

### 2.2 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|---|---|---|---|---|
| D-01 | 真实 So-VITS/RVC training adapter | 当前 adapter 只实现 mock DTO，非 mock 直接失败 | 用户要求执行真实训练或 API 创建 `train_sovits` job | production execution charter |
| D-02 | 自包含预处理依赖和模型 | Dockerfile 未安装 `preprocess` extra，PyAnnote 还需要 token/模型授权 | 用户要求真实 raw audio -> dataset | image rebuild charter |
| D-03 | durable async worker | 当前 BackgroundTasks/同步 runner 足够 first-test，不适合长训 | 训练/预处理超过请求生命周期或需要取消/恢复 | API control-plane charter |
| D-04 | 真实质量评估 | objective metrics 仍为 mock/placeholder | release gate 需要真实质量通过 | eval charter |
| D-05 | 完整 CRUD/API suite | 当前 API 以 POST/GET 为主，缺 delete/update/cancel/retry | 前端/外部调用方需要生产操作面 | API suite charter |
| D-06 | 安全/授权 | 本地工作台阶段未启用 API auth | 658 面向非本机网络或多人使用 | security charter |

---

## 3. 对账诚实（声称 vs 真实）

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|---|---|---|---|---|
| Docker 默认真实模式后可做 production voiceclone | `MOCK_ADAPTERS=false` 是默认，但真实 preprocessing 依赖未装，真实 training 未实现 | over-claim | `infra/docker/compose.voiceclone.yaml:34`, `infra/docker/Dockerfile.ai-voiceclone:15` | 默认真实模式会在关键步骤失败 |
| 支持 RVC 快速基线、So-VITS 长训 | RVC/So-VITS adapter 非 mock 均不可训练 | over-claim | `README.md:24`, `src/myvoiceclone/adapters/training/rvc_adapter.py:22`, `src/myvoiceclone/adapters/training/sovits_adapter.py:27` | API training job 无法成为真实生产训练 |
| 支持 RVC voice conversion | RVC convert 非 mock 直接失败 | over-claim | `README.md:25`, `src/myvoiceclone/adapters/training/rvc_adapter.py:32` | 推理能力只有 XTTS 路径有真实可能 |
| 预处理可真实跑 PyAnnote/Demucs/Whisper | 当前镜像未安装 pyannote/whisper/demucs，Demucs CLI 不存在 | frozen != done | `pyproject.toml:20`, `infra/docker/Dockerfile.ai-voiceclone:15` | raw audio 到训练 dataset 不可生产闭环 |
| 质量打分支持生产筛选 | real mode 下 `run_score` 直接抛错；mock constants 不能筛真实噪声/重叠/说话人 | placeholder | `src/myvoiceclone/pipelines/score.py:28`, `src/myvoiceclone/pipelines/score.py:48` | dataset 纯净度不可保障 |
| release gate 可作为生产发布闸 | 真实质量 metric 不存在，policy 默认 disabled，waive 可直接通过 | fake-zero / placeholder | `src/myvoiceclone/domain/policies.py:19`, `src/myvoiceclone/api/routes_reports.py:167` | 合规/质量闸不能作为生产放行依据 |
| API 支持生产级异步 | 长任务由 FastAPI BackgroundTasks 或同步 endpoint 执行，缺 durable worker/cancel/retry API | over-claim | `src/myvoiceclone/api/routes_jobs.py:38`, `src/myvoiceclone/api/routes_runs.py:217` | 服务重启/进程崩溃会丢失后台执行上下文 |
| 全链路状态监控 | `/runs/{id}/status` 只是 jobs/events/artifacts 聚合，状态来自 terminal jobs；无 progress/cancel/retry contract | partial | `src/myvoiceclone/api/routes_runs.py:248` | 外部系统无法稳定驱动长流程 |
| 模型下载准备已具备 | 下载脚本只写 `first-test-model-manifest.json` | placeholder | `scripts/download_models.sh:21` | 重封镜像后仍可能运行时联网下载或失败 |

- **诚实结论**：当前系统的真实价值是“容器化本地 API 工作台 + 一条 XTTS real inference smoke 路径 + mock 集成闭环”。它还不是“生产级真实 voiceclone 系统”。下一阶段必须以 blocker 清零为目标，而不是继续扩大 mock API。

---

## 4. 主体分析：四端生产化审查

### 4.1 执行端（training / inference / preprocess / job）

- **我方现状**：`JobRunner` 串接 preprocess、train、infer、eval，并写 step events（`src/myvoiceclone/jobs/runner.py:90`）。真实 XTTS `synth_to_file` 有实现（`src/myvoiceclone/adapters/training/xtts_adapter.py:55`）。
- **生产要求**：真实 voiceclone 至少需要 raw audio -> preprocess -> curate/freeze -> train 或 reference inference -> eval -> release gate 的可恢复链路。
- **差距**：
  - So-VITS/RVC training 非 mock 不可用。
  - feature cache 和 So-VITS rendered sample 仍写 fake bytes。
  - score/eval 不是生产指标。
  - 长任务没有独立 worker、锁、心跳、lease、重试、取消 API。

### 4.2 数据端（SQLite / artifact / dataset / metrics）

- **我方现状**：artifact 有 sha256、bytes、kind、job lineage（`src/myvoiceclone/storage/artifact_store.py:58`）；dataset freeze 会拒绝空 manifest（`src/myvoiceclone/pipelines/export_dataset.py:67`）。
- **生产要求**：真实数据必须可审计、可恢复、可删除/归档，有明确 lineage、manifest 版本、模型版本、指标来源、备份策略。
- **差距**：
  - SQLite 单文件 + bind mount，无备份/迁移锁/并发写策略。
  - artifact 写文件后再写 DB，缺事务性补偿/孤儿文件清理。
  - metrics 中仍允许 mock/placeholder 来源。
  - embeddings 是基于 MD5 的 deterministic mock vector。

### 4.3 接口端（API suite / async control plane）

- **我方现状**：OpenAPI 暴露 `GET/POST` recordings、datasets、jobs、training、inference、runs、reports、artifacts，以及 `PATCH /segments/{id}/review`。
- **生产要求**：外部调用方需要 create/start/pause/cancel/retry/list/filter/get-status/download/delete 的完整操作面；长任务必须通过 job id 可恢复查询。
- **差距**：
  - 没有 `DELETE` endpoint；几乎没有资源更新 API。
  - 没有 `POST /jobs/{id}/cancel`、`/retry`、`/resume`。
  - 没有单一 production voiceclone orchestration endpoint。
  - `/api/inference/real` 是同步直接执行，不是统一 job 化。
  - `/api/runs/{id}/status` 的 artifact 关联依赖 `metadata_json LIKE`，弱于结构化 FK。

### 4.4 环境端（Docker / image / model cache / GPU）

- **我方现状**：`ai-voiceclone` 镜像运行健康，只暴露 658；CUDA 可见；XTTS/TTS 包可 import。
- **生产要求**：镜像必须自包含执行逻辑、固定依赖版本、包含或可验证拉取模型权重、可重复重建。
- **差距**：
  - Dockerfile 只安装 `.[cli,db,api,test] soundfile`，没有安装 `audio/preprocess/first-test` extra。
  - 当前基础镜像是本地 `ai-voiceclone-base:cu130`，缺可重建 base Dockerfile/source anchor。
  - 依赖未 pin 版本，模型未 pin hash，权重下载脚本是 manifest stub。
  - 镜像包含 docs/tests，生产镜像和 test 镜像未分层。

---

## 5. 缺口 / 断点台账（核心产出）

| 编号 | 缺口 / 断点 | 严重度 | 证据（file:line） | 影响 |
|---|---|---|---|---|
| B1 | 真实 So-VITS training 未实现 | blocker | `src/myvoiceclone/adapters/training/sovits_adapter.py:27` | `train_sovits` API/job 在生产模式下不可用 |
| B2 | 真实 RVC training/conversion 未实现 | blocker | `src/myvoiceclone/adapters/training/rvc_adapter.py:22`, `src/myvoiceclone/adapters/training/rvc_adapter.py:32` | RVC baseline 和 VC 路径不可生产执行 |
| B3 | So-VITS pipeline 内仍生成 fake feature/rendered bytes | blocker | `src/myvoiceclone/pipelines/train.py:278`, `src/myvoiceclone/pipelines/train.py:422` | 即使 adapter 补齐，pipeline 仍可能产出假训练证据 |
| B4 | 真实 segment scoring 不可用 | blocker | `src/myvoiceclone/pipelines/score.py:28` | 无法自动筛选真实可训练语料 |
| B5 | objective metrics 是 mock，不可作为 release gate | blocker | `src/myvoiceclone/eval/objective.py:71`, `src/myvoiceclone/eval/objective.py:79` | release quality gate 没有真实依据 |
| B6 | 容器未安装真实预处理依赖 | blocker | `infra/docker/Dockerfile.ai-voiceclone:15`, `pyproject.toml:20` | `MOCK_ADAPTERS=false` 时 PyAnnote/Demucs/Whisper 链路不完整 |
| B7 | 模型下载/缓存脚本未下载真实权重 | high | `scripts/download_models.sh:17`, `scripts/download_models.sh:21` | 镜像重封后不能保证离线/可复现运行 |
| B8 | 长任务使用 FastAPI BackgroundTasks/同步 run，没有 durable worker | blocker | `src/myvoiceclone/api/routes_jobs.py:38`, `src/myvoiceclone/api/routes_runs.py:217` | 服务重启、进程崩溃、超长训练会破坏状态一致性 |
| B9 | 缺 job cancel/retry/resume API | high | `src/myvoiceclone/api/routes_jobs.py:15` | 外部系统不能控制生产异步任务生命周期 |
| B10 | API CRUD 不完整，动词偏 `GET/POST` | high | `src/myvoiceclone/api/routes_artifacts.py:24`, `src/myvoiceclone/api/routes_datasets.py:15`, `src/myvoiceclone/api/routes_training.py:19` | 无法生产管理资源、清理产物、更新配置 |
| B11 | 没有单一 production voiceclone orchestration endpoint | high | `src/myvoiceclone/api/routes_runs.py:194`, `src/myvoiceclone/api/routes_runs.py:217`, `src/myvoiceclone/api/routes_runs.py:236` | 外部调用方必须拼接多步流程，状态语义分散 |
| B12 | `/runs/{id}/status` 使用 `metadata_json LIKE` 弱关联 | high | `src/myvoiceclone/api/routes_runs.py:275` | artifact/status 查询可能漏报或误报 |
| B13 | API 无认证/授权，658 对外暴露后风险高 | blocker | `src/myvoiceclone/api/app.py:20`, `infra/docker/compose.voiceclone.yaml:16` | 任意可达调用方可能上传、推理、下载 artifact |
| B14 | consent policy 默认关闭 | high | `src/myvoiceclone/domain/policies.py:19` | production release gate 默认绕过授权检查 |
| B15 | release gate waive 可人工置 passed，缺生产审批模型 | high | `src/myvoiceclone/api/routes_reports.py:167`, `src/myvoiceclone/api/routes_reports.py:189` | 治理链可被单接口绕过 |
| B16 | API audit log 记录 request/response JSON，缺敏感字段策略 | med | `src/myvoiceclone/api/audit.py:69`, `src/myvoiceclone/api/audit.py:122` | 文本、路径、潜在身份信息可能被长期落库 |
| B17 | artifact 写入缺原子性/清理机制 | med | `src/myvoiceclone/storage/artifact_store.py:43`, `src/myvoiceclone/storage/artifact_store.py:59` | 文件写成功但 DB 写失败时产生孤儿产物 |
| B18 | embeddings 全是 MD5 mock vector | high | `src/myvoiceclone/adapters/embeddings/speaker_embedder.py:9`, `src/myvoiceclone/adapters/embeddings/audio_embedder.py:9` | 说话人相似度/去重/检索不可生产可信 |
| B19 | Docker base 不可从仓库重建 | high | `infra/docker/Dockerfile.ai-voiceclone:5` | `ai-voiceclone-base:cu130` 依赖宿主机本地历史镜像 |
| B20 | README 仍有生产能力过度声称 | med | `README.md:24`, `README.md:25` | 使用者会误以为 RVC/So-VITS 真实可用 |

---

## 6. 优先级建造建议

| 优先级 | 建造项 | 对应缺口 | 工作量 / 工作块 | 依赖 |
|---|---|---|---|---|
| P0 | 生产镜像重构：安装 preprocess/audio 依赖，固定 torch/cu130/TTS/whisper/demucs/pyannote 版本，生成可重建 base Dockerfile | B6, B7, B19 | L / WB-IMAGE | 明确模型许可证和缓存目录 |
| P0 | Durable job worker：独立 worker 进程、DB lease、heartbeat、cancel/retry/resume endpoint、状态机规范 | B8, B9, B12 | L / WB-WORKER | DB schema migration |
| P0 | 真实 training adapter 选型和实现：先冻结 So-VITS 或 RVC 单一路径，不同时扩两条 | B1, B2, B3 | XL / WB-TRAIN | image/model cache ready |
| P0 | 真实 scoring/eval：噪声、静音、重叠、speaker similarity、WER/MOS proxy 的真实 metric contract | B4, B5, B18 | L / WB-EVAL | preprocess/embedding models |
| P1 | Production API suite：resources CRUD、voiceclone orchestration endpoint、status/progress schema、artifact delete/archive | B10, B11, B12 | L / WB-API | durable worker |
| P1 | 安全基线：API token、local-only/bind control、consent default-on、waive 审批字段和审计 | B13, B14, B15, B16 | M / WB-SEC | owner policy |
| P1 | Artifact/data hardening：atomic write, orphan cleanup, backup/export, structured lineage indexes | B17, B12 | M / WB-DATA | DB migration |
| P2 | 文档降噪：README/ops/openapi 标注真实可用、实验可用、mock-only 三类能力 | B20 | S / WB-DOC | P0 scope decision |

---

## 7. Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|---|---|---|
| 交付价值 | medium | 容器边界、API 骨架、artifact/job ledger 和 XTTS smoke 有真实价值 |
| 累积债务 | high | mock 逻辑混在生产 adapter，训练/评分/评估核心缺失 |
| 愿景/目标达成度 | low-to-medium | 本地工作台达成一部分；production-ready voiceclone 尚未达成 |
| **综合健康** | high-risk / not-production-ready | 可以作为重构基座，不能作为生产服务交付 |

- **反镀金提醒**：下一阶段不要扩展 UI、报表样式、更多 mock endpoint；先让一条真实 voiceclone 路径在容器内可重复运行。

---

## 8. 前瞻交接 / start-gate

- **下一周期建议**：开一个 production-ready refactor charter，目标只选一条真实路径：`reference audio + text -> XTTS rendered audio` 或 `dataset -> So-VITS/RVC train -> rendered sample`。建议先把 XTTS real inference API 产品化，再进入训练。
- **start-gate 前置（下一 charter day-1 必须满足）**：
  - 确认第一条生产路径：XTTS-only、RVC-only、So-VITS-only 三选一。
  - 明确模型许可证、Hugging Face/Coqui cache 策略、是否允许构建时下载权重。
  - 明确 658 是否暴露到非本机网络；若暴露，API token 必须进入 P0。
  - 明确生产 DB 是否继续 SQLite；若继续，必须加入 backup/lock/maintenance 策略。
  - 明确真实验收音频集和通过标准：输出 wav、反向 ASR、speaker similarity、smoke metric、人工 MOS/ABX。
- **需 owner 拍板的问题**：
  - 训练路线优先级：So-VITS、RVC、还是先只交付 XTTS reference inference？
  - 模型权重是否允许封入镜像，还是运行时挂载 `.data/models`？
  - 生产 API 是否需要鉴权、审计保留期、artifact 删除能力？

---

## 9. 复现命令

```bash
# 容器状态
docker ps --filter name=ai-voiceclone --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker image ls --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}' | rg '^(ai-voiceclone|ai-voiceclone-base|docker-train)'

# API surface
curl -fsS http://127.0.0.1:658/api/jobs
docker exec ai-voiceclone bash -lc "python - <<'PY'
from myvoiceclone.api.app import create_app
paths=create_app().openapi()['paths']
for p, spec in sorted(paths.items()):
    methods=','.join(sorted(k.upper() for k in spec.keys() if k in {'get','post','put','patch','delete'}))
    print(methods.ljust(18), p)
PY"

# Runtime dependency facts
docker exec ai-voiceclone bash -lc "python - <<'PY'
import importlib.util, shutil, os
mods=['torch','torchaudio','TTS','whisper','pyannote','pyannote.audio','demucs','sqlite_vec','fastapi','uvicorn','soundfile']
for m in mods:
    try:
        ok=bool(importlib.util.find_spec(m))
    except Exception as e:
        ok=f'ERROR {type(e).__name__}: {e}'
    print(f'{m}: {ok}')
for b in ['ffmpeg','demucs','python','nvidia-smi']:
    print(f'bin {b}: {shutil.which(b)}')
print('MOCK_ADAPTERS:', os.getenv('MOCK_ADAPTERS'))
PY"

# Adapter real-mode preflight
docker exec ai-voiceclone bash -lc "python - <<'PY'
from myvoiceclone.adapters.training.xtts_adapter import XttsAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter
for a in [XttsAdapter(), PyannoteAdapter(), DemucsAdapter(), WhisperAdapter()]:
    print(a.__class__.__name__, a.preflight())
PY"

# Code evidence grep
rg -n "MOCK_ADAPTERS|fake_|placeholder|NotImplementedError|BackgroundTasks|cancel|retry|delete|put\\(|patch\\(" src tests infra docs -g '*.py' -g '*.md' -g '*.yaml' -g '*.toml'
```

---

## 附录 A. 运行时事实摘录

| 事实 | 结果 |
|---|---|
| 当前容器 | `ai-voiceclone` / `ai-voiceclone:cu130` / healthy / `0.0.0.0:658->658/tcp` |
| 当前镜像 | `ai-voiceclone:cu130`、`ai-voiceclone-base:cu130` |
| 容器 `MOCK_ADAPTERS` | `false` |
| 容器依赖 | `torch=True`, `torchaudio=True`, `TTS=True`, `sqlite_vec=True`, `fastapi=True`, `uvicorn=True` |
| 缺失依赖 | `whisper=False`, `pyannote=False`, `demucs=False`, `bin demucs=None` |
| adapter preflight | XTTS available；PyAnnote 缺 `HUGGINGFACE_TOKEN`；Demucs CLI missing；Whisper import missing |
| 当前 DB 统计 | `jobs=5`, `job_events=23`, `artifacts=21`, `model_runs=1`, `datasets=2`, `reports=0`, `eval_metrics=2` |
| 真实 smoke 痕迹 | `.data/test-runs/api_clone_osr_summary.json` 记录一次 `infer_real` rendered artifact；不是全链训练证据 |

---

## 附录 B. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| v0.1 | 2026-07-07 | Codex | 初稿：production-ready 状态分析 + gap study |
