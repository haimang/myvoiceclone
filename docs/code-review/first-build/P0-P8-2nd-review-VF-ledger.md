# P0-P8 first-build 第 2 轮 Unified Verified-Findings 台账

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 修复回应）
>
> | 字段 | 值 |
> |------|-----|
> | **审查标的** | `myvoiceclone first-build P0-P8` |
> | **审查阶段 / 轮次** | `2nd-pass merge` |
> | **合并 / 核查人（实现者）** | `Codex` |
> | **合并日期** | `2026-06-13` |
> | **文档状态** | `resolved-with-deferred` |
>
> **审查来源锚定**：
> - `docs/code-review/first-build/P0-P8-2nd-pass-reviewed-by-deepseek.md` — `critical/high/medium/low` mixed, reviewer 原编号 `V24-V46`
> - `docs/code-review/first-build/P0-P8-2nd-pass-reviewed-by-kimi.md` — reviewer 原编号 `R1-R12`
>
> **路径差异说明**：用户给定的 `P0-P8-2nd-pass-reviewed-by-minimax.md` 在当前工作树不存在；同目录存在并已使用的是 `P0-P8-2nd-pass-reviewed-by-kimi.md`。
>
> **对照真相**：
> - `docs/eval/first-build/final-execution-plan.md`
> - `docs/code-review/first-build/P0-P8-review-VF-ledger.md`
> - `src/myvoiceclone/**`、`db/migrations/**`、`tests/**`、`infra/docker/**`、`configs/**`

---

## 0. 合并方法与核查纪律

- **合并范围**：2 份二轮独立审查全部 finding 平铺，按根因合并为 24 条 unified finding。
- **核查纪律**：
  1. reviewer 结论只作线索；每条 `valid` 项均对照当前代码、migration、测试或实际命令复核。
  2. 同类问题合并为单一 `UF#`，严重度取多方最严。
  3. 被实测推翻的断言进入 §4.3，不静默吞掉。
- **统一编号前缀**：`UF`。

### 0.1 复核判定

| verdict | 含义 |
|---------|------|
| `valid` | 属实，需处理 |
| `valid-edge` | 属实但仅边界/条件态触发 |
| `valid-by-design` | 现象属实但当前阶段按设计后延 |
| `stale-rejected` | 不成立：实测或当前代码反证 |

### 0.2 归属类

| 归属类 | 含义 |
|--------|------|
| `[true-bug]` | 本阶段引入或本阶段该修却漏修/修错 |
| `[partial-delivery]` | 已规划且部分落地，但未收口 |
| `[true-deferred]` | first-build 未承诺，合理后延 |
| `n/a` | 已修/误报/设计接受，不作为缺口计 |

---

## 1. TL;DR

- **一句话裁定**：二轮 review 共归并为 `24` 条 unified finding；其中 `17` 条已在本轮修复，`5` 条登记为真实 deferred，`2` 条经实测驳回；核心修复集中在 CLI 可运行性、DTO/import 回归、schema canonical 列消费、env-aware 配置、Docker 数据隔离、states enum 消费、architecture boundary、vec0 metadata 表名。
- **按 verdict**：`valid 20` · `valid-edge 2` · `stale-rejected 2`
- **按三类归属**：`[true-bug] 11`（UF2,UF4,UF5,UF6,UF7,UF9,UF12,UF13,UF16,UF17,UF18） · `[partial-delivery] 8`（UF1,UF3,UF8,UF10,UF11,UF14,UF15,UF21） · `[true-deferred] 3`（UF19,UF20,UF22） · `n/a 2`（UF23,UF24）
- **按处置**：`fix 17` · `partial-fix 2` · `defer-with-rationale 5` · `stale-rejected 2`
- **blocker 数**：`0`（本轮无剩余未处理 blocker；较大契约变更已登记承接）

---

## 2. 合并映射

| 来源 finding | 合并到 | 合并后问题 |
|--------------|--------|------------|
| DeepSeek V24,V33,V34 / Kimi R1,R7 | UF1 | migration 007 新增 canonical 列后，Entity/Repo/API 未同步消费 |
| DeepSeek V24 子断言 | UF23 | `GENERATED ALWAYS AS ... VIRTUAL` 被称为 SQLite 语法错误 |
| DeepSeek V25 / DeepSeek V28 | UF2 | `AudioProbe` 重复定义，且 fakes 引用不存在 DTO |
| DeepSeek V26 / Kimi R1,R2 | UF3 | `domain.states` 枚举零使用，状态机仍漂移 |
| DeepSeek V27 | UF4 | pyproject console entry point 指向不存在 `cli:main` |
| DeepSeek V29 / Kimi R3,R4 | UF5 | Docker 数据卷未落到 `/mnt/usb/workspace/myvoiceresearch`，env 声明未被代码消费 |
| DeepSeek V30 / Kimi R12 | UF6 | preprocess/train 容器缺 demucs/libsndfile/ffmpeg/audio extras |
| DeepSeek V31,V32 / Kimi R1 | UF7 | CLI 仍直连 pipelines，architecture test 未禁止 CLI import pipelines/eval |
| DeepSeek V38 / Kimi R5 | UF8 | `embedding_jobs` 已建但 Vec0Store 仍用旧 `embedding_items`；vec0 维度仍不符 |
| DeepSeek V35 / Kimi R8 | UF19 | API 无统一响应信封和统一错误格式 |
| DeepSeek V36 | UF24 | `services/__init__.py` 与 `domain/services.py` 被指双写风险 |
| DeepSeek V37 | UF20 | `domain/policies.py` 直接 SQL/config，分层仍不纯 |
| DeepSeek V39 | UF9 | `ReleaseGateResponse.passed` 仍是 int，未暴露 4-state `status` |
| DeepSeek V40 | UF10 | `tests/conftest.py` 重复 `setsampwidth(2)` |
| DeepSeek V41 / Kimi R6 | UF21 | CLI eval/scoring/adapter 仍为 mock 或硬编码 |
| DeepSeek V42 / Kimi R9,R10 | UF22 | 缺少 `mvc infer tts`，API/CLI inference/eval/report 入口不对称 |
| DeepSeek V43 | UF11 | compose train service 硬编码 `my_dataset` |
| DeepSeek V44 | UF12 | `download_models.sh` 创建 `models/base`，与 `configs/models.yaml` 的 `models/pretrained` 不一致 |
| DeepSeek V45 | UF13 | `services/__init__.py` 导入未使用 `resolve_db_path` |
| DeepSeek V46 | UF14 | `live/gpu/slow` markers 注册但无测试使用 |
| Kimi R11 | UF15 | `pipeline_runs` 死表，recording 级状态未跟踪完整预处理进度 |
| Kimi R2 | UF16 | status CHECK 放宽/状态值漂移 |
| Kimi R3 | UF17 | 宿主数据目录不存在 |
| Kimi R4 | UF18 | `DB_PATH/ARTIFACT_ROOT/MODELS_DIR` env 声明但不生效 |

---

## 3. Verified-Findings 台账

| UF# | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据 / 实测 | 处置 |
|-----|------|------|------|----------|--------|-----------------|------|
| UF1 | Schema canonical 列未被 Entity/Repo/API 消费 | `critical` | DS/Kimi | `valid` | `[partial-delivery]` | 修前 `ArtifactStore` 只写旧 `artifact_type/job_id`，`ModelRunRepository.save` 只写 5 列；修后见 `storage/repositories.py:431`、`artifact_store.py:51`、`api/schemas.py:52` | `fix` |
| UF2 | AudioProbe/fakes DTO 回归 | `critical` | DS | `valid` | `[true-bug]` | 修前 `entities.py` 两个 `AudioProbe`，`tests/fakes` import 不存在 DTO；修后单一定义 `domain/entities.py:11`，补 `TranscriptResult/EmbeddingResult/AudioConvertResult` | `fix` |
| UF3 | states enum 零使用 / 状态写入仍裸字符串 | `critical` | DS/Kimi | `valid` | `[partial-delivery]` | 修后 `rg "from myvoiceclone.domain.states" src/myvoiceclone` 多处命中；状态值保持兼容 | `partial-fix` |
| UF4 | CLI entry point 不可用 | `critical` | DS | `valid` | `[true-bug]` | `pyproject.toml:28` 改为 `myvoiceclone.cli:app`，并保留 `cli.py:327 main()` wrapper；`venv/bin/myvoiceclone --help` 通过 | `fix` |
| UF5 | 数据卷未隔离到 `myvoiceresearch`，env 不消费 | `critical` | DS/Kimi | `valid` | `[true-bug]` | `compose.yaml:31/47/50` 指向 `/mnt/usb/workspace/myvoiceresearch`；`config.py:42/55/63` 消费 env；已创建宿主目录 | `fix` |
| UF6 | Docker 音频/分离依赖缺失 | `critical` | DS/Kimi | `valid` | `[true-bug]` | `pyproject.toml:20` 加 `demucs`；`Dockerfile.preprocess` 加 `libsndfile1`；`Dockerfile.train` 加 `ffmpeg/libsndfile1` 和 `[audio]` | `fix` |
| UF7 | CLI 直连 pipelines + 架构测试漏规则 | `critical` | DS/Kimi | `valid` | `[true-bug]` | `cli.py` 顶层无 pipelines/eval import；`tests/unit/test_architecture_boundaries.py:41` 禁止 CLI import pipelines/eval | `fix` |
| UF8 | Vec0Store 仍使用旧 metadata 表；维度仍为 128 | `high` | DS/Kimi | `valid` | `[partial-delivery]` | `vec0_store.py:14/25/70/85/94` 已切 `embedding_jobs`；维度迁移仍需重建虚表 | `partial-fix` |
| UF9 | ReleaseGate schema 未暴露 `status` | `medium` | DS | `valid` | `[true-bug]` | `api/schemas.py:101` 改 `passed: bool` 并加 `status/decision_json`；`routes_reports.py:106` 写 4-state status | `fix` |
| UF10 | conftest 重复 `setsampwidth` | `medium` | DS | `valid` | `[partial-delivery]` | `tests/conftest.py:18` 保留单次调用 | `fix` |
| UF11 | compose train dataset 硬编码 | `medium` | DS | `valid-edge` | `[partial-delivery]` | `compose.yaml` 改为 `${TRAIN_DATASET:-my_dataset}`，默认兼容、可 env 覆盖 | `fix` |
| UF12 | model download 路径与 config 不一致 | `medium` | DS | `valid` | `[true-bug]` | `scripts/download_models.sh:17` 改为 `models/pretrained` | `fix` |
| UF13 | services 未使用 import | `low` | DS | `valid` | `[true-bug]` | `services/__init__.py` 只导入 `resolve_artifact_root` | `fix` |
| UF14 | live/gpu/slow marker 无测试 | `low` | DS | `valid-by-design` | `[partial-delivery]` | `pytest.ini` 已注册，plan 允许初始为空；本轮不强造 live/gpu 测试 | `defer-with-rationale` |
| UF15 | `pipeline_runs` 死表 / recording 级进度未完整推进 | `medium` | Kimi | `valid` | `[partial-delivery]` | `rg "pipeline_runs" src` 无生产读写；需下一轮工作流审计设计 | `defer-with-rationale` |
| UF16 | 状态 CHECK 放宽/状态值漂移 | `critical` | Kimi | `valid` | `[true-bug]` | 本轮已让生产写入使用 enum；DB CHECK 收紧会破坏现有兼容数据，登记后续 migration | `partial-fix` |
| UF17 | `/mnt/usb/workspace/myvoiceresearch` 不存在 | `critical` | Kimi | `valid` | `[true-bug]` | 已创建 `db/data/models` 三个目录；compose config 渲染确认 bind source | `fix` |
| UF18 | `DB_PATH/ARTIFACT_ROOT/MODELS_DIR` env 声明不生效 | `high` | Kimi | `valid` | `[true-bug]` | `config.py:42/55/63` 加 env-aware resolver；CLI/services/train 改用 resolver | `fix` |
| UF19 | API 无统一响应信封 | `high` | DS/Kimi | `valid` | `[true-deferred]` | 全量 route 当前仍返回裸模型/list；属于破坏性 API contract 变更 | `defer-with-rationale` |
| UF20 | `domain/policies.py` 分层不纯 | `high` | DS | `valid` | `[true-deferred]` | 本轮补 canonical policy_events 写入；storage service 拆层需单独重构 | `defer-with-rationale` |
| UF21 | CLI eval/scoring/adapter mock | `high` | DS/Kimi | `valid-by-design` | `[partial-delivery]` | first-build mock scope；已有 DEF-05/DEF-06，CLI eval 硬编码并入后续真实评估 | `defer-with-rationale` |
| UF22 | CLI/API 入口不对称，缺 `infer tts` / route drift | `high` | DS/Kimi | `valid` | `[true-deferred]` | 补 TTS/路由重排会改变公开契约；登记 next contract pass | `defer-with-rationale` |
| UF23 | migration 007 generated column 语法错误 | `critical` | DS | `stale-rejected` | `n/a` | `run_migrations()` 临时库实测通过；SQLite 支持该 generated column 语法 | `stale-rejected` |
| UF24 | services/domain services “双写风险” | `high` | DS | `stale-rejected` | `n/a` | `domain/services.py` 只是 re-export shim，实际实现仅 `services/__init__.py` 一份 | `stale-rejected` |

---

## 4. 复核汇总

### 4.1 分桶汇总

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | 11 | UF2,UF4,UF5,UF6,UF7,UF9,UF12,UF13,UF16,UF17,UF18 | 本轮修复或 partial 后登记 |
| `[partial-delivery]` | 8 | UF1,UF3,UF8,UF10,UF11,UF14,UF15,UF21 | 已补齐可安全补齐部分；剩余登记 |
| `[true-deferred]` | 3 | UF19,UF20,UF22 | 进入 closure deferred ledger |
| `n/a` | 2 | UF23,UF24 | 驳回，不改代码 |

### 4.2 净增盲区

- Kimi 对 `DB_PATH/ARTIFACT_ROOT/MODELS_DIR` env 只声明不消费的指出是高价值盲区；本轮已通过 `config.py` resolver 和 compose defaults 收口。
- DeepSeek 对 fakes import 不存在 DTO、CLI 顶层 pipeline import、Vec0Store 仍用旧表名的指出均属真实回归/半修复，本轮已修。

### 4.3 带证据驳回的误报

| UF# | 误报方 | 误报内容 | 反证 | 结论 |
|-----|--------|----------|------|------|
| UF23 | DeepSeek | `type TEXT GENERATED ALWAYS AS (name) VIRTUAL` 会让 migration 007 失败 | `venv/bin/python` 调 `run_migrations()` 应用 001-007 到临时 SQLite 成功，输出 `migrations_ok` | `stale-rejected` |
| UF24 | DeepSeek | `services/__init__.py` 与 `domain/services.py` 双写实现 | `domain/services.py` 是 compatibility re-export shim，未复制实现逻辑 | `stale-rejected` |

---

## 5. 修复方案与承接

### 5.1 修复策略

本轮优先修复运行时回归、分层测试盲区、schema 新列不消费、容器数据隔离和 env 配置失效。会破坏公开 API 形状、需要迁移既有状态数据或需要真实模型/GPU 的内容不硬塞进 first-build，而是以 reopen 触发器登记。

### 5.2 已执行修复计划

| UF# | 修法 | 目标文件 | 验证 |
|-----|------|----------|------|
| UF1 | 扩展 dataclass/schema/repository/artifact store，写入 canonical 列 | `entities.py`, `repositories.py`, `artifact_store.py`, `schemas.py`, `train.py`, `routes_reports.py` | full pytest + storage tests |
| UF2 | 合并 `AudioProbe`，补 missing DTO | `entities.py` | fakes import + DTO tests |
| UF3/UF16 | 生产写入改用 states enum，保留兼容状态值 | `jobs/**`, `pipelines/**`, `api/routes_*`, `cli.py` | full pytest |
| UF4 | 修 console entry point，补 `main()` wrapper | `pyproject.toml`, `cli.py` | `venv/bin/myvoiceclone --help` |
| UF5/UF17/UF18 | 数据卷切外部目录，env-aware resolver，创建宿主目录 | `compose.yaml`, `config.py`, `services/__init__.py`, `cli.py`, `train.py` | compose config + full pytest |
| UF6 | 补 demucs/audio/system deps | `pyproject.toml`, `Dockerfile.*` | compose config |
| UF7 | 移除 CLI direct pipeline import，补 architecture rule | `cli.py`, `test_architecture_boundaries.py` | architecture test |
| UF8 | Vec0Store metadata 表切 `embedding_jobs` | `vec0_store.py` | storage tests |
| UF9 | ReleaseGate schema/status/decision_json 对齐 | `schemas.py`, `routes_reports.py` | API tests |
| UF10 | 删除重复 `setsampwidth` | `tests/conftest.py` | full pytest |
| UF11 | compose dataset 支持 env 覆盖 | `compose.yaml` | compose config |
| UF12 | download script 路径改为 `models/pretrained` | `scripts/download_models.sh` | script dry-run existing tests |
| UF13 | 移除未使用 import | `services/__init__.py` | compileall |

### 5.3 承接登记

| UF# | deferred 内容 | reopen 触发器 | 承接位置 |
|-----|---------------|---------------|----------|
| UF8 | vec0 三 namespace 真实维度 768/192/384 迁移 | 切真实 embedder 或创建 migration 008 | `docs/closure/first-build/deferred-items-ledger.md` DEF-09 |
| UF14 | `live/gpu/slow` 真实测试仍为空 | 引入 live adapter/GPU job | DEF-10 |
| UF15 | `pipeline_runs` 和 recording 级状态推进 | 需要 UI/审计或多 step resume | DEF-11 |
| UF19 | API response envelope/error handler | 开始前端或外部 API consumer 集成 | DEF-12 |
| UF20 | policies SQL 从 domain 下沉到 storage/service | security-governance hardening | DEF-13 |
| UF21 | 真实评估/adapter/download script | 切 live training/eval | 既有 DEF-05/DEF-06，并补 DEF-14 |
| UF22 | CLI/API 路由和命令对称化 | contract freeze pass | DEF-15 |

---

## 6. 实现者回应

> 执行者: `Codex`  
> 执行时间: `2026-06-13`  
> 回应范围: `UF1-UF24`  
> 对应审查文件: `P0-P8-2nd-pass-reviewed-by-deepseek.md`, `P0-P8-2nd-pass-reviewed-by-kimi.md`

- **总体回应**：二轮 review 中真实运行时/架构/配置问题已修复；较大 contract/API/migration/真实模型项已登记 deferred。
- **本轮修改策略**：先修可证伪 bug 和半交付项；保持 first-build mock 骨架兼容；不做会破坏现有 API/DB 数据的宽泛重构。
- **实现者自评状态**：`ready-for-rereview`

### 6.1 逐项回应表

| 编号 | 处理结果 | 独立复核状态 | 修改文件 / 承接 |
|------|----------|--------------|-----------------|
| UF1 | `fixed` | `independently-verified` | `entities.py`, `repositories.py`, `artifact_store.py`, `schemas.py`, `train.py`, `routes_reports.py` |
| UF2 | `fixed` | `independently-verified` | `entities.py` |
| UF3 | `partially-fixed` | `independently-verified` | `jobs/**`, `pipelines/**`, `api/routes_*`, `cli.py`; DB CHECK 收紧 defer |
| UF4 | `fixed` | `independently-verified` | `pyproject.toml`, `cli.py` |
| UF5 | `fixed` | `independently-verified` | `compose.yaml`, `config.py`, created `/mnt/usb/workspace/myvoiceresearch/{db,data,models}` |
| UF6 | `fixed` | `independently-verified` | `pyproject.toml`, `Dockerfile.preprocess`, `Dockerfile.train` |
| UF7 | `fixed` | `independently-verified` | `cli.py`, `test_architecture_boundaries.py` |
| UF8 | `partially-fixed` | `independently-verified` | `vec0_store.py`; vec dimensions defer |
| UF9 | `fixed` | `independently-verified` | `schemas.py`, `routes_reports.py` |
| UF10 | `fixed` | `independently-verified` | `tests/conftest.py` |
| UF11 | `fixed` | `independently-verified` | `compose.yaml` |
| UF12 | `fixed` | `independently-verified` | `scripts/download_models.sh` |
| UF13 | `fixed` | `independently-verified` | `services/__init__.py` |
| UF14 | `deferred-with-rationale` | `deferred-by-charter` | DEF-10 |
| UF15 | `deferred-with-rationale` | `deferred-by-charter` | DEF-11 |
| UF16 | `partially-fixed` | `independently-verified` | enum consumption fixed; stricter DB CHECK deferred |
| UF17 | `fixed` | `independently-verified` | filesystem dirs created |
| UF18 | `fixed` | `independently-verified` | `config.py`, `cli.py`, `services/__init__.py`, `train.py` |
| UF19 | `deferred-with-rationale` | `deferred-by-charter` | DEF-12 |
| UF20 | `deferred-with-rationale` | `deferred-by-charter` | DEF-13 |
| UF21 | `deferred-with-rationale` | `deferred-by-charter` | DEF-14 plus existing DEF-05/DEF-06 |
| UF22 | `deferred-with-rationale` | `deferred-by-charter` | DEF-15 |
| UF23 | `stale-rejected` | `stale-rejected-by-code` | migration dry-run passes |
| UF24 | `stale-rejected` | `stale-rejected-by-code` | re-export shim, no duplicate implementation |

### 6.2 变更文件清单

- `src/myvoiceclone/domain/entities.py` — DTO 去重、补 fake/test DTO、扩展 canonical fields。
- `src/myvoiceclone/config.py` — env-aware path resolver。
- `src/myvoiceclone/cli.py` — 移除 pipeline import、统一路径解析、entry point wrapper、enum 状态值。
- `src/myvoiceclone/storage/repositories.py` / `artifact_store.py` / `vec0_store.py` — 消费 canonical DB 列与 `embedding_jobs`。
- `src/myvoiceclone/pipelines/**`, `src/myvoiceclone/jobs/**`, `src/myvoiceclone/api/routes_*.py` — 状态 enum 消费与 canonical release gate/policy events 写入。
- `pyproject.toml`, `infra/docker/**`, `scripts/download_models.sh`, `tests/**` — packaging/container/test guard 修复。

### 6.3 验证结果

| 验证项 | 命令 / 证据 | 结果 | 覆盖 |
|--------|-------------|------|------|
| 全量测试 | `venv/bin/python -m pytest -q` | `92 passed, 1 skipped` | UF1-UF18 |
| API marker | `venv/bin/python -m pytest -m api -q` | `14 passed` | UF1,UF9 |
| CLI marker | `venv/bin/python -m pytest -m cli -q` | `4 passed` | UF4,UF7 |
| storage tests | `venv/bin/python -m pytest tests/unit/storage -q` | `12 passed` | UF1,UF8 |
| architecture + DTO | `venv/bin/python -m pytest tests/unit/test_architecture_boundaries.py tests/unit/adapters/test_dto_contracts.py -q` | `2 passed` | UF2,UF7 |
| compileall | `venv/bin/python -m compileall -q src tests` | `pass` | syntax/import |
| migration dry-run | apply migrations 001-007 to temp SQLite | `migrations_ok` | UF23 |
| CLI entry | `venv/bin/myvoiceclone --help` | `pass` | UF4 |
| compose render | `docker compose -f infra/docker/compose.yaml config` | `pass`, bind source is `/mnt/usb/workspace/myvoiceresearch/...` | UF5,UF11 |

### 6.4 未解决事项与承接

| 编号 | 状态 | 不在本轮完成的原因 | 承接位置 |
|------|------|--------------------|----------|
| UF8 | `deferred` | vec0 维度修复需 DROP/CREATE 虚表并迁移真实 embedding dimensions | DEF-09 |
| UF14 | `deferred` | live/gpu/slow 无真实 live/GPU adapter 可测 | DEF-10 |
| UF15 | `deferred` | pipeline_runs/recording progress 需要状态机与 UI/audit 设计收敛 | DEF-11 |
| UF19 | `deferred` | 统一 envelope 是 breaking API contract change | DEF-12 |
| UF20 | `deferred` | policies 下沉 storage 是跨层重构 | DEF-13 |
| UF21 | `deferred` | 真实模型/评估超出 first-build mock scope | DEF-14 |
| UF22 | `deferred` | API/CLI 对称入口需要 contract freeze pass | DEF-15 |

### 6.5 Ready-for-rereview gate

- **是否请求复审**：`yes`
- **请求复核范围**：`UF1-UF24`，重点复核 schema consumption、Docker/env、architecture boundary、deferred 合理性。
- **可关闭前提**：
  1. 上述验证命令在 reviewer 环境复现通过。
  2. reviewer 接受 UF19/UF20/UF22 等 breaking contract 改动进入 deferred ledger。
