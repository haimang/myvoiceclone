# first-test deferred items ledger

> 项目: `myvoiceclone`
> 阶段: `first-test`
> 文档性质: `deferred-items-ledger`
> 日期: `2026-06-13` · 作者: `Codex`
> 状态: `active`
> evidence anchor: `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z`

本台账只记录 first-test 执行后仍需要后续承接的事项。每一项必须有触发器；没有触发器的“后续处理”不允许入账。

## 1. 总览

| ID | 类型 | 状态 | 简要问题 | 触发器 | 目标阶段 |
|----|------|------|----------|--------|----------|
| FTD-01 | C | pending-live | live capstone harness 已完成，但本机只有 skipped evidence | `RUN_FIRST_TEST_CAPSTONE=1` 且合法短音频、模型/cache/token 配齐 | live-verification |
| FTD-02 | C | retained | 非 skipped evidence pack 尚未包含真实 artifacts/trace | FT7 live capstone 真实执行成功 | live-verification |
| FTD-03 | B | retained | 真实 objective proxy/DNSMOS/SQUIM 未接入 | 选择并安装 objective scorer 后 | training/eval phase |
| FTD-04 | B | retained | XTTS/RVC/Coqui 模型真实下载和缓存仍需 owner 环境 | 模型 license/source/cache 复核并允许下载 | model-cache phase |
| FTD-05 | A | retained | vec0/embedder 真实维度迁移仍非 first-test 主路 | ECAPA/CLAP/SBERT embedding 进入关键路径 | second-build |
| FTD-06 | A | retained | 多 worker / production queue / SQLite 并发 hardening 未做 | 引入 worker pool 或并发 job runner | infra-hardening |
| FTD-07 | B | retained | 全局 API response envelope 未冻结 | 前端或外部 consumer contract freeze | api-contract-pass |
| FTD-08 | A | retained | 完整 OTel collector/exporter 未接入 | 多服务 trace 或持续监控成为目标 | observability phase |
| FTD-09 | A | retained | 众包 MOS/P.808 平台不在 first-test scope | 发布级外部评审成为目标 | quality-review phase |
| FTD-10 | B | retained | fake adapter Protocol/ABC 未冻结 | adapter interface freeze | second-build |

## 2. retained deferred detail

### FTD-01 · live capstone 真实执行

- **来源**：`docs/closure/first-test/FT7-live-capstone-closure.md`
- **当前状态**：`pending-live`
- **证据**：`tests/integration/test_first_test_capstone.py -m live -q -rs` 结果为 skipped，reason: `RUN_FIRST_TEST_CAPSTONE=1 is required for live first-test capstone`
- **触发器**：owner 提供合法短音频、模型/cache/token、并设置 `RUN_FIRST_TEST_CAPSTONE=1`
- **目标阶段**：`live-verification`

### FTD-02 · 非 skipped evidence pack

- **来源**：FT7 evidence exporter/validator
- **当前状态**：`retained`
- **证据**：当前 pack `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z` 的 `status=skipped`
- **触发器**：live capstone 真实执行产生非空 artifact manifest 与 trace
- **目标阶段**：`live-verification`

### FTD-03 · 真实 objective proxy

- **来源**：FT5 closure
- **当前状态**：`retained`
- **证据**：objective proxy 具备 explicit unavailable 语义，但无真实 scorer dependency
- **触发器**：DNSMOS/SQUIM 或等价 scorer 选型、依赖和模型缓存完成
- **目标阶段**：`training/eval phase`

### FTD-04 · 模型下载/cache/license liveization

- **来源**：FT4 closure
- **当前状态**：`retained`
- **证据**：`scripts/download_models.sh` 能写 manifest，但不下载真实权重；XTTS-v2 license/provenance 已进入 metadata
- **触发器**：owner 允许模型下载并提供 cache 目录与 license 使用边界
- **目标阶段**：`model-cache phase`

### FTD-05 · vec0/embedder 真实维度迁移

- **来源**：first-build DEF-01/05/09
- **当前状态**：`retained`
- **证据**：first-test 未把 embedding 作为关键路径
- **触发器**：真实 ECAPA/CLAP/SBERT embedder 接入
- **目标阶段**：`second-build`

### FTD-06 · 多 worker / queue / SQLite 并发

- **来源**：first-build DEF-07、reference-anchor TR-1/TR-4
- **当前状态**：`retained`
- **证据**：FT2 只验证 WAL/busy_timeout 本地边界；FT6 使用 DB job ledger，不引入 broker
- **触发器**：worker pool、Celery/RQ、或多 JobRunner 并发执行成为目标
- **目标阶段**：`infra-hardening`

### FTD-07 · 全局 API envelope

- **来源**：first-build DEF-12、FT6 closure
- **当前状态**：`retained`
- **证据**：first-test 只冻结 `/api/runs` 等阶段字段
- **触发器**：前端/外部 API consumer 进入 contract freeze
- **目标阶段**：`api-contract-pass`

### FTD-08 · 完整 OTel 平台

- **来源**：reference-anchor axis F/H
- **当前状态**：`retained`
- **证据**：FT2/FT7 以 DB events/trace JSON/evidence pack 替代平台化 OTel
- **触发器**：多服务 trace、collector/exporter、持续监控成为目标
- **目标阶段**：`observability phase`

### FTD-09 · 众包 MOS/P.808 平台

- **来源**：FT5 closure、reference-anchor axis D
- **当前状态**：`retained`
- **证据**：FT5 实现本地 MOS/ABX 录入，未接 AMT/Prolific/外部 panel
- **触发器**：发布级质量评估要求外部评审
- **目标阶段**：`quality-review phase`

### FTD-10 · fake adapter Protocol/ABC

- **来源**：first-build DEF-02
- **当前状态**：`retained`
- **证据**：first-test 以 adapter metadata/preflight 与 `MOCK_ADAPTERS` 真实隔离为主，未冻结 fakes
- **触发器**：adapter Protocol/ABC 冻结
- **目标阶段**：`second-build`
