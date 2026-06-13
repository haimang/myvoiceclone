# Nano-Agent 行动计划：P1 Repo Skeleton + SQLite/vec0 Foundation

> 服务业务簇: `myvoiceclone first-build`
> 计划对象: `P1 Repo Skeleton + SQLite/vec0 Foundation`
> 类型: `new`
> 作者: `Codex`
> 时间: `2026-06-13`
> 文件位置: `myvoiceclone/docs/plan/first-build/01-storage-vec0-skeleton.md`
> 上游前序 / closure:
> - `00-scope-architecture.md`
> - `myvoiceclone/docs/eval/first-build/final-execution-plan.md:141`
> 下游交接:
> - `02-preprocess-pipeline.md`
> 关联设计 / 调研文档:
> - `final-execution-plan.md:518`（数据库与插件）
> - `final-execution-plan.md:373`（文件定位矩阵）
> 冻结决策来源:
> - `final-execution-plan.md:504`（Q3）
> grounding 来源:
> - `final-execution-plan.md:145`、`:400`、`:411`、`:555`
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

P1 建立 first-build 的工程骨架和本地数据底座。后续 P2-P8 的所有 pipeline、API、训练、报告都依赖 P1 提供的 package 结构、SQLite migration、artifact store、`VectorStore` 协议和 `sqlite-vec/vec0` 默认实现。

- **服务业务簇**：`myvoiceclone first-build`
- **计划对象**：`P1 Repo Skeleton + SQLite/vec0 Foundation`
- **本次计划解决的问题**：
  - 当前仓库没有代码 skeleton，只有 docs。
  - 缺少 SQLite schema、migration runner、job/artifact/report 审计表。
  - 缺少 `sqlite-vec/vec0` 插件安装、加载和隔离接口。
- **本次计划的直接产出**：
  - Python package skeleton、配置目录、DB migrations、storage/vector/artifact modules。
  - `pyproject.toml` extras 与 `pytest.ini`。
  - P1 storage/vector/report unit tests。
- **本计划不重新讨论的设计结论**：
  - SQLite + `sqlite-vec/vec0` 为默认，`vec1` 仅 probe（来源：`final-execution-plan.md:504`）。
  - P1 预留 security tables，但不启用 auth/security enforcement（来源：`final-execution-plan.md:503`）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采取“先 skeleton，再 migrations，再 storage/vector，再 tests”的顺序。所有 schema 先以 SQL migration 文件落地，再由 Python migration runner 执行；vector 能力通过 `VectorStore` protocol 隔离，让 domain/unit tests 不依赖 native extension。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Skeleton + deps | M | 创建项目树、pyproject、配置和测试基础 | P0 |
| Phase 2 | SQLite migrations | L | 建 core/state/report/security schema | Phase 1 |
| Phase 3 | Storage services | M | 连接、migration runner、repositories、artifact store | Phase 2 |
| Phase 4 | Vector stores | M | vec0 默认实现、Null store、vec1 probe | Phase 2 |
| Phase 5 | Unit tests | M | 覆盖 DB、migration、artifact、vector | Phase 3/4 |

### 1.3 Phase 说明

1. **Phase 1 — Skeleton + deps**
   - **核心目标**：建立所有后续文件落点。
   - **为什么先做**：P2 需要 package 和 configs。
2. **Phase 2 — SQLite migrations**
   - **核心目标**：将 DB-001..005 主线迁移落地；DB-006 作为 Phase 4 vec1 probe 迁移占位。
   - **为什么放在这里**：所有业务状态和 artifact 血缘依赖 schema。
3. **Phase 3 — Storage services**
   - **核心目标**：提供连接、迁移、CRUD、artifact registry。
   - **为什么放在这里**：P2 pipeline 必须通过 repository 读写。
4. **Phase 4 — Vector stores**
   - **核心目标**：实现 `VectorStore` protocol 和 `vec0` 默认。
   - **为什么放在这里**：P3 curation 需要 embedding search。
5. **Phase 5 — Unit tests**
   - **核心目标**：让 P1 所有基础设施可验证。
   - **为什么放在最后**：测试覆盖 skeleton/schema/storage/vector 的组合。

### 1.4 执行策略说明

- **执行顺序原则**：文件结构先于代码，schema 先于 repository，protocol 先于实现。
- **风险控制原则**：`sqlite-vec` pre-v1 风险用版本 pin + `VectorStore` 隔离。
- **测试推进原则**：全部默认 unit tests，不跑 live/GPU。
- **文档同步原则**：DB schema 与 final §14.3 保持一致。
- **回滚 / 降级原则**：若 `sqlite-vec` 加载失败，默认 unit suite 使用 `NullVectorStore`，vec0 health test 明确 failed/deferred。

### 1.5 本次 action-plan 影响结构图

```text
P1 Storage Foundation
├── pyproject.toml / pytest.ini / configs
├── db/migrations/001..006
├── src/myvoiceclone/storage
│   ├── sqlite.py
│   ├── migrations.py
│   ├── repositories.py
│   ├── artifact_store.py
│   ├── vector_store.py
│   ├── vec0_store.py
│   └── vec1_store.py
└── tests/unit/storage
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** 创建 repo/package/config/test skeleton。
- **[S2]** 实现 DB-001..006 migration 文件和 runner。
- **[S3]** 实现 SQLite connection PRAGMA、repositories、artifact store。
- **[S4]** 实现 `VectorStore` protocol、`vec0_store`、`NullVectorStore`、`vec1` probe placeholder。

### 2.2 Out-of-Scope

- **[O1]** 真实音频 ingest，交给 P2。
- **[O2]** embedding 模型生成，交给 P3。
- **[O3]** API/CLI routes，交给 P6。
- **[O4]** 安全策略拦截，交给 P7。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| SQLite WAL/FK/JSON | in-scope | Q3 冻结 | DB 不再本地化 |
| `vec1` 默认启用 | out-of-scope | Q3 冻结为 probe | `vec0` 100k+ 查询不足 |
| consent tables | in-scope placeholder | Q2 要后置安全但避免重构 | P7 启用策略 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | 创建项目树和 package skeleton | add | `pyproject.toml`, `src/myvoiceclone/**`, `configs/**`, `tests/**` | final §12 文件落点存在 | P1-T01 | medium |
| P1-02 | Phase 1 | 定义 dependencies/extras | add | `pyproject.toml`, `.env.example`, `configs/*.yaml` | extras 可安装设计闭环 | P1-T02 | medium |
| P1-03 | Phase 2 | SQLite connection manager | add | `src/myvoiceclone/storage/sqlite.py` | PRAGMA WAL/FK/busy_timeout 生效 | P1-T03 | medium |
| P1-04 | Phase 2 | core schema migration | add | `db/migrations/001_core_schema.sql` | core 表和约束可重复创建 | P1-T04 | high |
| P1-05 | Phase 2 | job/artifact/run/event/review schema | add | `db/migrations/002_state_jobs_artifacts.sql` | audit 表可查询 job/artifact/review 血缘 | P1-T05 | high |
| P1-06 | Phase 4 | sqlite-vec/vec0 store + embedding metadata | add | `src/myvoiceclone/storage/vec0_store.py`, `db/migrations/003_vec0_embeddings.sql` | embedding_models/jobs 与 vec0 health/upsert/search 通过 | P1-T06 | high |
| P1-07 | Phase 4 | VectorStore protocol + Null store | add | `src/myvoiceclone/storage/vector_store.py` | domain tests 不依赖 native extension | P1-T07 | medium |
| P1-08 | Phase 2 | reports/eval schema | add | `db/migrations/004_reports_metrics.sql` | report summary 可入库 | P1-T08 | medium |
| P1-09 | Phase 2 | security placeholder schema | add | `db/migrations/005_security_placeholders.sql` | 表存在但无拦截 | P1-T09 | medium |
| P1-10 | Phase 4 | vec1 probe placeholder | add | `src/myvoiceclone/storage/vec1_store.py`, `006_optional_vec1_probe.sql` | 默认 off 且不影响 tests | P1-T10 | low |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Skeleton + deps

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-01 | 创建项目树和 package skeleton | a) 按 final §12.2 创建目录；b) 每个 package 放 `__init__.py`；c) tests/fixtures/fakes 建空结构；d) 不放真实音频/模型 | `final-execution-plan.md:373` | 文件落点支持 P2-P8 | P1-T01 | tree snapshot 符合 final |
| P1-02 | 定义 dependencies/extras | a) `pyproject.toml` 定义 api/cli/db/audio/preprocess/test/dev；b) `.env.example` 放本地路径和 feature flags；c) configs 放 local/models/pipeline yaml | `pyproject.toml`, `.env.example`, `configs/**` | 安装面清晰，不写死 token | P1-T02 | package metadata 可解析 |

### 4.2 Phase 2 — SQLite migrations

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-03 | SQLite connection manager | a) 建连接函数；b) 设置 `PRAGMA foreign_keys=ON`、`journal_mode=WAL`、`busy_timeout`、row factory；c) 提供 tmp DB test helper | `src/myvoiceclone/storage/sqlite.py` | 连接基线稳定 | P1-T03 | PRAGMA tests PASS |
| P1-04 | core schema migration | a) 建 `schema_migrations`；b) 建 speakers/recordings/segments/datasets/dataset_segments；c) 加 FK/check/index；d) migration checksum 防漂移 | `db/migrations/001_core_schema.sql` | core schema idempotent | P1-T04 | migration repeat PASS |
| P1-05 | job/artifact/run/event/review schema | a) 建 jobs/job_events/artifacts/pipeline_runs/model_runs/segment_reviews；b) artifacts 含 `metadata_json`；c) artifact self FK；d) job status check；e) event/review append-only 语义 | `db/migrations/002_state_jobs_artifacts.sql`, `repositories.py`, `artifact_store.py` | 审计链路和 review 链路可写可查 | P1-T05 | lineage query PASS |
| P1-08 | reports/eval schema | 建 reports/eval_metrics/eval_samples，支持 JSON summary 与 artifact linkage | `db/migrations/004_reports_metrics.sql` | report 可入库 | P1-T08 | report fixture PASS |
| P1-09 | security placeholder schema | 建 consent_ledger/policy_events/release_gates，不在 service 中启用拦截 | `db/migrations/005_security_placeholders.sql` | P7 可接入 | P1-T09 | 表存在且无 early gate |

### 4.3 Phase 3 — Storage services

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-05 | repositories/artifact store | a) repository 封装 CRUD；b) artifact store 计算 sha256/bytes/uri/metadata_json；c) 只存 metadata，不存 audio blob；d) 状态变更通过 event writer 留痕 | `repositories.py`, `artifact_store.py` | P2 可登记 artifacts，P7 可写 synthetic metadata | P1-T05 | artifact lineage PASS |

### 4.4 Phase 4 — Vector stores

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-06 | sqlite-vec/vec0 store | a) `pyproject` 加 `sqlite-vec`；b) connection load `sqlite_vec.load()`；c) `db/migrations/003_vec0_embeddings.sql` 建 `embedding_models` / `embedding_jobs` 和 3 张 vec0 virtual tables；d) upsert/search/delete；e) extension missing 时返回明确错误 | `vec0_store.py`, `db/migrations/003_vec0_embeddings.sql` | vec0 可用且 embedding jobs 可审计 | P1-T06 | vec health PASS |
| P1-07 | VectorStore protocol + Null store | a) 定义 protocol；b) Null store 返回空 search；c) tests 用 Null store；d) 禁止 domain import vec0 | `vector_store.py` | 低耦合 | P1-T07 | protocol test PASS |
| P1-10 | vec1 probe placeholder | a) 建 `vec1_store.py` 但 feature flag off；b) `db/migrations/006_optional_vec1_probe.sql` 不默认执行；c) docs 标注条件 | `vec1_store.py`, `db/migrations/006_optional_vec1_probe.sql` | 不污染主线 | P1-T10 | default test skips vec1 |

---

## 5. Phase 详情

### 5.1 Phase 1 — Skeleton + deps

- **Phase 目标**：让 final §12.2 的文件树具备实际落点。
- **本 Phase 对应编号**：P1-01 / P1-02
- **本 Phase 新增文件**：`pyproject.toml`, `.env.example`, `configs/**`, `src/myvoiceclone/**`, `tests/**`
- **具体功能预期**：
  1. 所有 package 可被 Python import。
  2. `pyproject.toml` 包含 CLI entrypoint 占位。
  3. extras 不强制安装 GPU/模型重依赖到默认环境。
  4. configs 不包含 secrets，只引用 env var。
  5. tests 目录含 fixtures/fakes/unit/api/cli/integration 结构。
- **对应测试台账项**：P1-T01 / P1-T02
- **收口标准**：`python -m pytest -m unit` 能发现测试配置。
- **本 Phase 风险提醒**：不要提交真实模型权重或私人音频。

### 5.2 Phase 2 — SQLite migrations

- **Phase 目标**：实现 DB-001..005 的可重复迁移；DB-006 由 Phase 4 vec1 probe 占位并默认关闭。
- **本 Phase 对应编号**：P1-03 / P1-04 / P1-05 / P1-08 / P1-09
- **本 Phase 新增文件**：`db/migrations/*.sql`, `storage/sqlite.py`, `storage/migrations.py`, `storage/repositories.py`
- **具体功能预期**：
  1. migration runner 按 version 顺序执行。
  2. 已执行 migration 的 checksum 变化会报错。
  3. FK/check/index 在 tmp DB 中可验证。
  4. `metadata_json` / `summary_json` 统一 TEXT JSON，不依赖非标准类型。
  5. `segment_reviews` 在 DB-002 中创建，供 P3 review audit 使用。
  6. P7 placeholder 表存在但不被 P1-P6 policy 强制消费。
- **对应测试台账项**：P1-T03..P1-T05 / P1-T08 / P1-T09
- **收口标准**：tmp DB 迁移两次结果稳定。
- **本 Phase 风险提醒**：SQLite ALTER 能力有限，首版 schema 要保持简单且可迁移。

### 5.3 Phase 3/4 — Storage + Vector

- **Phase 目标**：提供 P2-P3 可消费的 persistence 和 vector abstraction。
- **本 Phase 对应编号**：P1-06 / P1-07 / P1-10
- **本 Phase 新增文件**：`artifact_store.py`, `vector_store.py`, `vec0_store.py`, `vec1_store.py`
- **具体功能预期**：
  1. artifact store 只管理 metadata、metadata_json 和 sha256。
  2. VectorStore 定义 `upsert/search/delete`。
  3. DB-003 同时创建 `embedding_models` / `embedding_jobs` 和 vec0 virtual tables。
  4. vec0 实现支持 namespace 固定维度。
  5. vec1 默认关闭，不在默认 tests 中加载。
  6. 缺失 sqlite-vec 时错误可诊断，不 silent fallback 到假结果。
- **对应测试台账项**：P1-T06 / P1-T07 / P1-T10
- **收口标准**：vector tests 和 artifact tests 全 PASS。
- **本 Phase 风险提醒**：不要让 domain 依赖 native extension。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q2 | `final-execution-plan.md:503` | security tables placeholder only | 移到 P7 重设 |
| Q3 | `final-execution-plan.md:504` | SQLite + vec0 默认 | 重开 DB 方案 |
| Q5 | `final-execution-plan.md:506` | storage/vector 分层 | 不允许 domain 直连 vec0 |
| Q6 | `final-execution-plan.md:507` | job/artifact/report audit tables | 不得删除审计表 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `final-execution-plan.md:141` | P1 工作台账 | P1-01..10 | ✅ 复用 | 主台账 |
| A-2 | `final-execution-plan.md:373` | 文件定位矩阵 | P1-01 | ✅ 复用 | skeleton 来源 |
| A-3 | `final-execution-plan.md:400` | DB 文件定位 | P1-03..10 | ✅ 复用 | migrations/storage |
| A-4 | `final-execution-plan.md:518` | DB/插件安排 | P1-02..10 | ✅ 复用 | sqlite-vec install |
| A-5 | `final-execution-plan.md:566` | table baseline | P1-04..09 | ✅ 复用 | schema 字段 |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 把音频 blob 存 SQLite | final 要求大产物在文件系统 |
| ⛔2 | vec1 默认启用 | Q3 冻结为 optional probe |
| ⛔3 | domain 直接 import sqlite_vec | Q5 要求分层隔离 |
| ⛔4 | P1 启用 consent enforcement | Q2 要求 P7 后置 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`myvoiceclone/docs/eval/first-build/final-execution-plan.md`
- **安全 / 信任边界类工作项的威胁模型锚**：`final-execution-plan.md:217`；P1 只创建 DB-005 placeholder，不启用 policy。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| P1-T01 | 项目树和 package imports | 短途 | unit | 🆕 新增 `tests/unit/test_package_skeleton.py` | P1-01 → 文件落点存在 | commit {sha} + pytest tests/unit/test_package_skeleton.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T02 | pyproject extras/config parse | 短途 | unit | 🆕 新增 `tests/unit/test_project_config.py` | P1-02 → deps/config 可解析 | commit {sha} + pytest tests/unit/test_project_config.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T03 | SQLite PRAGMA connection | 短途 | unit | 🆕 新增 `tests/unit/storage/test_sqlite_connection.py` | P1-03 → WAL/FK 生效 | commit {sha} + pytest tests/unit/storage/test_sqlite_connection.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T04 | core migration idempotent | 短途 | unit | 🆕 新增 `tests/unit/storage/test_migrations.py` | P1-04 → core schema 可重复 | commit {sha} + pytest tests/unit/storage/test_migrations.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T05 | job/artifact/review lineage query | 短途 | unit | 🆕 新增 `tests/unit/storage/test_artifact_store.py` | P1-05 → 审计链可查 | commit {sha} + pytest tests/unit/storage/test_artifact_store.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T06 | vec0 load/upsert/search + embedding metadata | 短途 | unit | 🆕 新增 `tests/unit/storage/test_vec0_store.py` | P1-06 → vec0 可用 | commit {sha} + pytest tests/unit/storage/test_vec0_store.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T07 | VectorStore protocol/Null store | 短途 | unit | 🆕 新增 `tests/unit/storage/test_vector_store.py` | P1-07 → domain 可隔离 | commit {sha} + pytest tests/unit/storage/test_vector_store.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T08 | report/eval schema fixture | 短途 | unit | 🆕 新增 `tests/unit/storage/test_reports_schema.py` | P1-08 → report 可入库 | commit {sha} + pytest tests/unit/storage/test_reports_schema.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T09 | security placeholder no enforcement | 短途 | unit | 🆕 新增 `tests/unit/storage/test_security_placeholders.py` | P1-09 → 表存在不拦截 | commit {sha} + pytest tests/unit/storage/test_security_placeholders.py PASS + {YYYY-MM-DD HH:MM UTC} |
| P1-T10 | vec1 default disabled | 短途 | unit | 🆕 新增 `tests/unit/storage/test_vec1_probe.py` | P1-10 → 默认 off | commit {sha} + pytest tests/unit/storage/test_vec1_probe.py PASS + {YYYY-MM-DD HH:MM UTC} |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| N/A | 🆕 新增 | P1 创建首批 code tests | 无既有代码 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest -m unit tests/unit/storage` | unit | 每次 P1 改动 |
| spike | 不适用 | - | P2 开始 |
| mega | 不适用 | - | P8 |
| soak | 不适用 | - | P1 无 race/长稳 |

### 8.4 测试缺口

- 不覆盖真实 pyannote/Demucs/Whisper/RVC（理由：P1 只建底座）→ 交 P2/P4/P5 live markers。

### 8.5 测试保真

- sqlite-vec 缺失时 P1-T06 不得假绿，应标 degraded/deferred 并给出安装错误。
- NullVectorStore PASS 不代表 vec0 PASS，二者分开。
- security placeholder test 只证明“不拦截”，不声称具备安全能力。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| sqlite-vec pre-v1 | API/SQL 可能破坏 | high | pin version + protocol 隔离 |
| SQLite migration 漂移 | 手改 SQL 与 DB 不一致 | medium | checksum + idempotent tests |
| skeleton 过宽 | 建太多空文件无价值 | medium | 只建 final §12 明确文件 |

### 9.2 约束与前提

- **技术前提**：Python package 以 `src/` layout。
- **运行时前提**：本地 SQLite，不启外部 DB service。
- **组织协作前提**：P2-P8 不直接绕过 storage/service。
- **上线 / 合并前提**：P1 unit tests 全 PASS 或清晰 deferred。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/architecture/layers.md`
- 需要同步更新的说明文档 / README：P8 quickstart 汇总
- 需要同步更新的测试说明：`pytest.ini`

### 9.4 完成后的预期状态

1. P2 可使用 repositories/artifact store 创建 recording/segment/job/artifact。
2. P3 可使用 VectorStore 进行 embedding 检索。
3. P6 可在 tmp DB 上跑 TestClient。

---

## 10. 收口

### 10.1 收口硬闸

1. DB migrations idempotent（P1-T04）。
2. SQLite PRAGMA 和 artifact lineage 可验证（P1-T03/P1-T05）。
3. VectorStore 协议和 vec0 health 有明确 PASS/deferred（P1-T06/P1-T07）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 文件落点存在 | P1-01 | P1-T01 | commit {sha} + pytest tests/unit/test_project_structure.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| deps/config 可解析 | P1-02 | P1-T02 | commit {sha} + pytest tests/unit/test_config.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| SQLite baseline | P1-03 | P1-T03 | commit {sha} + pytest tests/unit/test_db_migrations.py::test_sqlite_baseline PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| core schema | P1-04 | P1-T04 | commit {sha} + pytest tests/unit/test_db_schema_core.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| audit schema | P1-05 | P1-T05 | commit {sha} + pytest tests/unit/test_db_schema_audit.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| vec0 | P1-06 | P1-T06 | commit {sha} + pytest tests/unit/test_vec0_migrations.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| VectorStore | P1-07 | P1-T07 | commit {sha} + pytest tests/unit/test_vector_store.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| report schema | P1-08 | P1-T08 | commit {sha} + pytest tests/unit/test_report_schema.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| placeholders | P1-09 | P1-T09 | commit {sha} + pytest tests/unit/test_pipeline_placeholders.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |
| vec1 off | P1-10 | P1-T10 | commit {sha} + pytest tests/unit/test_vec1_probe.py PASS + {YYYY-MM-DD HH:MM UTC} | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | skeleton、migrations、storage/vector/artifact modules 可用 |
| 测试 | P1-T01..P1-T10 全 PASS 或有明确 deferred |
| 文档 | DB/plugin 说明同步 |
| 风险收敛 | sqlite-vec 与 vec1 风险被隔离 |
| 可交付性 | 可进入 P2 |

### 10.4 NOT-成功识别

迁移不可重复、FK 未启用、vec0 错误被吞掉、或 P1 引入安全拦截，均不得标 `executed`。
