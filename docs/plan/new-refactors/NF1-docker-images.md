# Nano-Agent 行动计划模板

> 服务业务簇: `myvoiceclone`
> 计划对象: `NF1 docker images and container-only runtime refactor`
> 类型: `migration | refactor | remove`
> 作者: `Codex`
> 时间: `2026-07-07`
> 文件位置: `docs/plan/new-refactors/NF1-docker-images.md`
> 上游前序 / closure:
> - `docs/closure/first-build/08-ops-handoff-closure.md`
> - `docs/closure/first-test/first-test-closure.md`
> - `user directive 2026-07-07: host venv must be removed; run only in ai-voiceclone container; expose only port 658`
> 下游交接:
> - `NF1 execution closure: docs/closure/new-refactors/NF1-docker-images-closure.md`
> - `NF2 live adapter hardening / security-gateway plan, if external exposure becomes public-facing`
> 关联设计 / 调研文档:
> - `README.md`
> - `docs/ops/local-setup.md`
> - `docs/baseline/device_stacks.md`
> - `infra/docker/compose.yaml`
> - `infra/docker/Dockerfile.train`
> 冻结决策来源:
> - `user directive 2026-07-07`（只读引用；本 action-plan 不填写 Q/A）
> grounding 来源:
> - `见 §7 内置锚区`（本 AP 的 grounding 真源）
> 关联 reference-anchor:
> - `见 §7 内置锚区`
> 文档状态: `executed`

---

## 0. 执行背景与目标

业主要求将 `myvoiceclone` 从宿主机 Python/venv 执行模式迁移到专用容器执行模式。迁移完成后，宿主机只承担 Git 工作区、Docker/NVIDIA runtime、持久化数据目录和端口转发；所有 CLI、API、测试、数据库初始化、推理和训练入口必须在 `ai-voiceclone` 容器内执行。

当前仓库已有 `infra/docker/Dockerfile.train` 与 `infra/docker/compose.yaml`，并且本机存在 `docker-train:latest` 历史镜像。调查确认 `docker-train:latest` 内已有 `torch 2.12.0+cu130`、`torchaudio 2.11.0+cu130`、`TTS 0.27.5`、`fastapi`、`uvicorn`、`sqlite_vec` 等关键依赖，但缺少 `pytest`，且现有 compose 仍按 `preprocess` / `train` 分服务设计，不提供唯一的外部通讯端口 658。因此本计划目标不是小修 compose，而是重构为专用 `ai-voiceclone` 镜像与单容器服务。

本文件是执行计划，不是 closure。所有 PASS 证据需要在后续执行后回填到 closure；本 AP 保持 `draft`，直到后续实施、验证与清理全部完成。

- **服务业务簇**：`myvoiceclone`
- **计划对象**：`ai-voiceclone dedicated container runtime`
- **本次计划解决的问题**：
  - 宿主机 `venv/` 与脚本仍支持本地执行，违反“只能在容器内执行”的新约束。
  - 现有 Docker 服务分为 `preprocess` / `train`，没有统一的 `ai-voiceclone` 服务与唯一 658 外部通讯端口。
  - `docker-train:latest` 是历史镜像名，依赖真相可复用，但不可作为长期语义边界。
  - README、ops 文档、测试契约仍描述旧的本地 venv/多服务运行方式。
- **本次计划的直接产出**：
  - 新建 `infra/docker/Dockerfile.ai-voiceclone`，构建 `ai-voiceclone:cu130`。
  - 新建或重构 compose，形成容器名 `ai-voiceclone`、只映射 `658:658` 的运行方式。
  - 更新脚本，使宿主机脚本只封装 `docker compose` / `docker exec`，不再创建或调用宿主 `venv`。
  - 更新测试契约与文档，明确容器内执行、端口唯一性、镜像依赖和清理顺序。
  - 在验证通过后删除宿主 `venv/` 与历史 `docker-train:latest` 镜像。
- **本计划不重新讨论的设计结论**：
  - `myvoiceclone` 后续不在宿主机 Python 环境中执行（来源：`user directive 2026-07-07`）。
  - 对外通讯唯一端口为 `658`（来源：`user directive 2026-07-07`）。
  - `docker-train` 的 cu130 依赖真相可作为新镜像 substrate，但最终运行边界命名为 `ai-voiceclone`（来源：`user directive 2026-07-07` + §7 调查）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用“先事实锁定，后构建专用镜像，再迁入口，最后删除历史执行路径”的方式。先把现有 `docker-train`、`Dockerfile.train`、compose、脚本和测试契约的真实状态钉住；随后构建可复现的 `ai-voiceclone` 镜像，而不是长期依赖不可追溯的历史 tag；再把 API/CLI/测试全部切换到容器内；最后在新容器验证通过后删除宿主 `venv/` 与历史 `docker-train:latest`。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Runtime Truth Lock | `S` | 冻结当前镜像、依赖、端口、数据目录、测试起跑线事实 | `-` |
| Phase 2 | Dedicated Image Build | `L` | 新建 `Dockerfile.ai-voiceclone`，构建可复现 `ai-voiceclone:cu130` | `Phase 1` |
| Phase 3 | Single Service Runtime | `M` | 新建/重构 compose，容器名 `ai-voiceclone`，唯一发布 `658:658` | `Phase 2` |
| Phase 4 | Host Execution Removal | `M` | 脚本、文档、测试从宿主 venv 迁到容器执行；移除 `venv/` | `Phase 3` |
| Phase 5 | Legacy Image Cleanup | `S` | 验证新镜像后删除历史 `docker-train:latest` 并更新清理证据 | `Phase 4` |
| Phase 6 | Closure Evidence | `M` | 容器内测试、API health、端口唯一性、依赖探针全部收口 | `Phase 5` |

### 1.3 Phase 说明

1. **Phase 1 - Runtime Truth Lock**
   - **核心目标**：把当前宿主机、镜像、容器、依赖、端口、数据和测试现状写成可执行锚点。
   - **为什么先做**：后续会删除 `venv/` 和历史镜像，必须先知道哪些事实可复用、哪些路径是历史残留。
2. **Phase 2 - Dedicated Image Build**
   - **核心目标**：以 `Dockerfile.train` / `docker-train` 已验证依赖为 substrate，建立专用 `ai-voiceclone:cu130` 镜像。
   - **为什么放在这里**：镜像是后续 compose、脚本、测试和清理的基础。
3. **Phase 3 - Single Service Runtime**
   - **核心目标**：形成 `ai-voiceclone` 单服务运行形态，只向宿主发布 `658`。
   - **为什么放在这里**：服务边界必须先稳定，才能迁脚本和文档。
4. **Phase 4 - Host Execution Removal**
   - **核心目标**：删除宿主执行路径，所有命令改走容器。
   - **为什么放在这里**：只有新容器通过健康验证后，才可移除宿主 fallback。
5. **Phase 5 - Legacy Image Cleanup**
   - **核心目标**：删除历史 `docker-train:latest`，避免后续误用。
   - **为什么放在这里**：删除历史镜像是不可逆清理，应在新镜像闭环后执行。
6. **Phase 6 - Closure Evidence**
   - **核心目标**：用测试台账逐项证明新运行方式真实可用。
   - **为什么放在这里**：本 AP 的成功条件不是“写了 Dockerfile”，而是容器内执行闭环。

### 1.4 执行策略说明

- **执行顺序原则**：先保留历史环境作为对照，构建和验证 `ai-voiceclone` 后再删除宿主 `venv/` 与 `docker-train:latest`。
- **风险控制原则**：端口暴露、GPU runtime、模型目录、SQLite 数据目录、权限归属和历史镜像删除都设硬闸；任何一项未观察不得标 `executed`。
- **测试推进原则**：短途契约测试先保证文件和 compose 正确，spike 验证镜像依赖与 API health，mega 验证容器内默认测试套件，soak 验证重启后端口与 DB 仍稳定。
- **文档同步原则**：README、ops 文档、脚本 dry-run 文案、Docker 契约测试必须与新运行方式一致。
- **回滚 / 降级原则**：若 `ai-voiceclone` 构建失败，保留 `docker-train:latest` 和宿主 `venv/`；若 API 658 不健康，不删除旧镜像；若 CUDA 不可用，只能标为 partial，不能声称 live GPU ready。

### 1.5 本次 action-plan 影响结构图

```text
NF1 docker images and container-only runtime refactor
├── Phase 1: Runtime Truth Lock
│   ├── local image inventory: docker-train / docker-preprocess / ai-neo / cu130 vllm
│   └── repository anchors: Dockerfile, compose, scripts, tests, README
├── Phase 2: Dedicated Image Build
│   ├── infra/docker/Dockerfile.ai-voiceclone
│   └── image tag ai-voiceclone:cu130
├── Phase 3: Single Service Runtime
│   ├── compose service ai-voiceclone
│   ├── uvicorn myvoiceclone.api.app:create_app on 0.0.0.0:658
│   └── one exposed host port: 658
├── Phase 4: Host Execution Removal
│   ├── scripts/bootstrap_env.sh
│   ├── scripts/run_preprocess.sh
│   ├── scripts/run_train_sovits.sh
│   └── host venv/ removal
├── Phase 5: Legacy Image Cleanup
│   ├── docker image rm docker-train:latest
│   └── contract tests block reintroduction
└── Phase 6: Closure Evidence
    ├── container-internal pytest
    ├── /health smoke on 658
    ├── init-db and vec-health in container
    └── docker ps port uniqueness check
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 新建专用 `ai-voiceclone:cu130` 镜像定义，替代语义不准确的 `docker-train:latest` 运行边界。
- **[S2]** 新建或重构 compose，使 `ai-voiceclone` 容器只暴露宿主 `658` 端口。
- **[S3]** 将宿主脚本改为容器执行包装，不再创建或调用宿主 `venv`。
- **[S4]** 更新 Docker 契约测试、脚本 dry-run 测试、README 与 ops 文档。
- **[S5]** 在新容器验证通过后删除宿主 `venv/` 与历史 `docker-train:latest`。
- **[S6]** 建立容器内测试、API health、DB migration、sqlite-vec、依赖探针和端口唯一性的收口标准。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 不实现真实 So-VITS/RVC 训练逻辑；现有 adapter 缺口保持后续专项。
- **[O2]** 不把 FastAPI 改造成公网认证授权服务；NF1 只收敛端口和运行边界。
- **[O3]** 不重构 SQLite schema 或 artifact lineage。
- **[O4]** 不改 `ai-neo`、`web-neo` 等其他容器。
- **[O5]** 不删除 `.data/`、模型缓存、artifact、数据库运行数据。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `ai-voiceclone:cu130` 镜像 | `in-scope` | 业主要求建立专用执行环境 | 新镜像无法在 GB10/cu130 环境启动 |
| 唯一 `658` 外部端口 | `in-scope` | 业主明确要求唯一外部通讯口 | 需要反向代理或多服务拆分时 |
| 宿主 `venv/` 删除 | `in-scope` | 业主要求不能在宿主执行 | 容器内测试未通过时暂缓 |
| 删除 `docker-train:latest` | `in-scope-after-gate` | 业主要求删除历史残留镜像 | 新镜像验证未完成时禁止 |
| `docker-preprocess:latest` | `defer` | 它是历史轻量镜像，不是本次明确删除目标 | NF1 closure 后执行 image hygiene pass |
| API 认证授权 | `out-of-scope` | 当前 AP 目标是容器执行环境，不是公网安全方案 | 658 需公网直连或多租户访问时 |
| 真实训练实现 | `out-of-scope` | 当前代码仍显式未实现真实 So-VITS/RVC | live training charter 启动时 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | 固化 runtime inventory | `add` | `docs/action-plan/new-refactors/NF1-docker-images.md:§7` | 当前镜像、端口、依赖和测试起跑线被记录为真相层 | `NF1-T01` | `medium` |
| P1-02 | Phase 1 | 识别宿主执行路径 | `add` | `scripts/bootstrap_env.sh:17`, `scripts/run_preprocess.sh:53`, `scripts/run_train_sovits.sh:79` | 所有宿主 venv 入口被列入迁移清单 | `NF1-T02` | `medium` |
| P2-01 | Phase 2 | 新建 `Dockerfile.ai-voiceclone` | `add` | `infra/docker/Dockerfile.ai-voiceclone` | 可复现构建 `ai-voiceclone:cu130`，包含 API/CLI/test/runtime 依赖 | `NF1-T03` | `high` |
| P2-02 | Phase 2 | 镜像依赖探针 | `add` | `tests/unit/test_docker_first_test_contract.py:14` | 契约测试覆盖新镜像依赖与迁移文件复制 | `NF1-T04` | `medium` |
| P3-01 | Phase 3 | 新建单服务 compose | `add` | `infra/docker/compose.voiceclone.yaml` | `ai-voiceclone` 容器只映射 `658:658` | `NF1-T05` | `high` |
| P3-02 | Phase 3 | API 启动命令与 healthcheck | `add` | `src/myvoiceclone/api/app.py:110`, `infra/docker/compose.voiceclone.yaml` | `curl http://127.0.0.1:658/health` 返回 healthy | `NF1-T06` | `medium` |
| P4-01 | Phase 4 | 脚本迁移到容器执行 | `update` | `scripts/bootstrap_env.sh:17`, `scripts/run_preprocess.sh:53`, `scripts/run_train_sovits.sh:79` | 脚本不创建/调用宿主 `venv`，只包装 Docker 命令 | `NF1-T07` | `medium` |
| P4-02 | Phase 4 | 文档改为容器-only 运行方式 | `update` | `README.md`, `docs/ops/local-setup.md` | 文档不再指示宿主安装 venv 作为主路径 | `NF1-T08` | `medium` |
| P4-03 | Phase 4 | 删除宿主 `venv/` | `remove` | `venv/` | 仓库根目录不存在宿主虚拟环境 | `NF1-T09` | `high` |
| P5-01 | Phase 5 | 删除历史 `docker-train:latest` | `remove` | Docker local image store | 新镜像验证后 `docker image ls` 不再出现 `docker-train:latest` | `NF1-T10` | `high` |
| P6-01 | Phase 6 | 容器内默认测试闭环 | `add` | `pytest.ini:1`, `tests/` | 默认测试套件在 `ai-voiceclone` 容器内通过 | `NF1-T11` | `high` |
| P6-02 | Phase 6 | DB/vec/API smoke 闭环 | `add` | `src/myvoiceclone/storage/sqlite.py:220`, `src/myvoiceclone/api/app.py:110` | 容器内 `init-db`、`vec-health`、`/health` 都通过 | `NF1-T12` | `medium` |
| P6-03 | Phase 6 | 端口唯一性和重启稳定性 | `add` | `infra/docker/compose.voiceclone.yaml` | 重启后仍只有 `658` 暴露，数据目录不丢失 | `NF1-T13` | `high` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 - Runtime Truth Lock

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-01 | 固化 runtime inventory | a) 记录本地镜像清单；b) 记录 `docker-train` 真实依赖；c) 记录 `docker-preprocess` 缺少真实预处理依赖；d) 记录 `ai-neo` 仅作为宿主状态参考，不作为 myvoiceclone 执行环境；e) 记录宿主 GB10/driver/cu130 事实 | `docs/action-plan/new-refactors/NF1-docker-images.md:§7` | 方案内包含 reference-anchor 真相层 | `NF1-T01` | §7 事实可由命令复现 |
| P1-02 | 识别宿主执行路径 | a) 标记 `bootstrap_env.sh` 创建 `venv`；b) 标记 preprocess/train 脚本调用 `./venv/bin/python`；c) 标记 README/local-setup 中 venv 指令；d) 标记测试中对 dry-run 文案的旧断言 | `scripts/bootstrap_env.sh:17`, `scripts/run_preprocess.sh:53`, `scripts/run_train_sovits.sh:79`, `tests/unit/test_scripts_dry_run.py:71` | 所有待迁移入口形成清单 | `NF1-T02` | 后续 P4 不漏入口 |

### 4.2 Phase 2 - Dedicated Image Build

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-01 | 新建 `Dockerfile.ai-voiceclone` | a) 以 `Dockerfile.train` 的 cu130 substrate 为来源，复制 app、configs、db migrations、tests；b) 安装 API/CLI/DB/test 依赖，补齐 `pytest`；c) 保留 `torch/torchaudio/TTS` cu130 组合，禁止无约束重装 torchaudio；d) 设置工作目录 `/app`；e) 默认 `CMD` 启动 uvicorn 到 `0.0.0.0:658`；f) 保留 `python -m myvoiceclone.cli` 作为 exec 命令入口；g) 加入构建标签说明源 commit 和 CUDA target | `infra/docker/Dockerfile.ai-voiceclone`, `infra/docker/Dockerfile.train:6`, `infra/docker/Dockerfile.train:36`, `infra/docker/Dockerfile.train:59` | `docker build -t ai-voiceclone:cu130` 可完成 | `NF1-T03` | 镜像可启动 API 且可执行 CLI |
| P2-02 | 镜像依赖探针 | a) 新增/更新 Docker 契约测试，检查新 Dockerfile 复制 migrations/configs/tests；b) 检查安装 pytest；c) 检查不再依赖宿主 venv；d) 检查 image 名和 service 名不再使用 `docker-train` 作为主运行边界 | `tests/unit/test_docker_first_test_contract.py:14` | 契约测试阻止旧模式回归 | `NF1-T04` | 契约测试 PASS |

### 4.3 Phase 3 - Single Service Runtime

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-01 | 新建单服务 compose | a) 新建 `compose.voiceclone.yaml`；b) service 名固定 `ai-voiceclone`；c) `container_name: ai-voiceclone`；d) image 固定 `ai-voiceclone:cu130`；e) 仅发布 `"658:658"`；f) 配置 NVIDIA GPU device reservation；g) 挂载 `.data/db`、`.data/artifacts`、`.data/raw`、`.data/models`、`.data/test-runs`、`configs:ro`；h) 不暴露 SSH、668、669、670 或其他 debug 端口 | `infra/docker/compose.voiceclone.yaml`, `infra/docker/compose.yaml:46` | `docker compose` 只启动一个 myvoiceclone 业务容器 | `NF1-T05` | `docker ps` 只看到 `ai-voiceclone` 发布 658 |
| P3-02 | API healthcheck | a) compose command 启动 `uvicorn myvoiceclone.api.app:create_app --host 0.0.0.0 --port 658`；b) 添加 healthcheck 调 `/health`；c) 环境变量指向容器路径；d) 确认 DB 初始化由 CLI 命令执行，不在 API 启动时隐式破坏 DB | `src/myvoiceclone/api/app.py:110`, `src/myvoiceclone/config.py:156`, `infra/docker/compose.voiceclone.yaml` | API 可被外部通过 658 访问 health | `NF1-T06` | `/health` 返回 `{"status":"healthy","version":"1.0.0"}` |

### 4.4 Phase 4 - Host Execution Removal

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P4-01 | 脚本迁移到容器执行 | a) `bootstrap_env.sh` 改为构建镜像、创建数据目录、提示/执行容器内依赖探针；b) `run_preprocess.sh` 改为 `docker compose exec ai-voiceclone python -m myvoiceclone.cli ...`；c) `run_train_sovits.sh` 同样改为容器 exec；d) dry-run 文案更新为容器路径；e) 如果容器未运行，脚本应给出明确错误或自动提示启动命令；f) 不再出现 `./venv/bin/python` | `scripts/bootstrap_env.sh:17`, `scripts/run_preprocess.sh:53`, `scripts/run_train_sovits.sh:79`, `tests/unit/test_scripts_dry_run.py:71` | 宿主脚本不再创建或调用 venv | `NF1-T07` | dry-run tests 和 grep gate PASS |
| P4-02 | 文档改为容器-only | a) README quickstart 改为 compose build/up/exec；b) local setup 文档移除宿主 venv 作为主路径；c) 明确 `.data` 是持久化 bind mount；d) 明确 `MOCK_ADAPTERS` 默认与容器环境；e) 明确 API 外部端口唯一为 658；f) 明确真实训练缺口不因容器迁移而消失 | `README.md`, `docs/ops/local-setup.md` | 用户按文档不会再创建宿主 venv | `NF1-T08` | 文档 grep 不出现主路径 `source venv/bin/activate` |
| P4-03 | 删除宿主 `venv/` | a) 在 `NF1-T03` 至 `NF1-T08` 通过后删除 `venv/`；b) 确认 `.dockerignore` 仍排除 `venv/`；c) 确认无脚本或文档依赖该路径；d) 保留 `.data/` 不删除 | `venv/`, `.dockerignore:2` | 宿主没有 Python 虚拟环境残留 | `NF1-T09` | `test ! -d venv` PASS |

### 4.5 Phase 5 - Legacy Image Cleanup

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P5-01 | 删除历史 `docker-train:latest` | a) 确认 `ai-voiceclone:cu130` 已构建；b) 确认 `ai-voiceclone` 容器正在运行且健康；c) 确认 compose 不再引用 `docker-train`; d) 执行 `docker image rm docker-train:latest`；e) 记录 `docker image ls` 证据；f) 若镜像被容器占用，先定位占用容器，不强制删除业务容器 | Docker local image store, `infra/docker/compose.voiceclone.yaml` | 历史镜像不再出现在本地镜像清单 | `NF1-T10` | `docker image ls docker-train` 无结果 |

### 4.6 Phase 6 - Closure Evidence

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P6-01 | 容器内默认测试闭环 | a) 在 `ai-voiceclone` 容器内运行默认 pytest；b) 保持 marker 选择与 `pytest.ini` 一致；c) 记录 pass/skipped/deselected/warnings；d) 不接受宿主 venv 测试作为 NF1 成功证据 | `pytest.ini:1`, `tests/` | 默认测试套件容器内 PASS | `NF1-T11` | `python -m pytest -q` 容器内 PASS |
| P6-02 | DB/vec/API smoke 闭环 | a) 容器内执行 `init-db`；b) 执行 `vec-health`；c) 调 `http://127.0.0.1:658/health`；d) 检查 `.data/db/myvoiceclone.sqlite` 仍在预期挂载路径；e) 不在宿主 Python 执行任何一步 | `src/myvoiceclone/storage/sqlite.py:220`, `src/myvoiceclone/api/app.py:110` | DB、sqlite-vec、API 三件套可用 | `NF1-T12` | 三个 smoke 全 PASS |
| P6-03 | 端口唯一性和重启稳定性 | a) `docker ps` 检查 `ai-voiceclone` 仅发布 658；b) `docker restart ai-voiceclone` 后重复 health；c) 检查没有 22/668/669/670 暴露；d) 检查重启后 DB 文件仍存在；e) 记录 runtime/GPU 可见性，若 CUDA 不可用如实标记 | `infra/docker/compose.voiceclone.yaml` | 单容器外部通信面收敛 | `NF1-T13` | 端口、health、持久化三项 PASS |

---

## 5. Phase 详情

### 5.1 Phase 1 - Runtime Truth Lock

- **Phase 目标**：建立本次迁移的事实真相层。
- **本 Phase 对应编号**：`P1-01` / `P1-02`
- **本 Phase 新增文件**：`docs/action-plan/new-refactors/NF1-docker-images.md`
- **本 Phase 修改文件**：无
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 记录 `docker-train:latest` 是 arm64 历史镜像，包含 `torch 2.12.0+cu130`、`torchaudio 2.11.0+cu130`、`TTS 0.27.5`，但缺少 `pytest`。
  2. 记录 `docker-preprocess:latest` 是轻量镜像，缺少 torch/torchaudio/pyannote/whisper/demucs，不适合作为专用全功能环境。
  3. 记录 `vllm/vllm-openai:gemma-aarch64-cu130` 是 cu130 vLLM 镜像，但它服务于 LLM 推理参考，不是 myvoiceclone 的应用镜像。
  4. 记录宿主 `venv/` 当前仍存在，且测试曾通过，但后续不能作为执行证据。
  5. 记录现有脚本中创建/调用 `venv` 的具体行。
- **对应测试台账项**：`NF1-T01` / `NF1-T02`
- **收口标准**：§7 锚区完整；后续执行时可复跑命令验证。
- **本 Phase 风险提醒**：如果事实层过时，后续删除镜像或 venv 可能切断唯一可运行路径。

### 5.2 Phase 2 - Dedicated Image Build

- **Phase 目标**：建立可复现、专用、命名准确的 `ai-voiceclone:cu130` 镜像。
- **本 Phase 对应编号**：`P2-01` / `P2-02`
- **本 Phase 新增 / 修改 / 删除文件**：新增 `infra/docker/Dockerfile.ai-voiceclone`；修改 `tests/unit/test_docker_first_test_contract.py`
- **具体功能预期**：
  1. 镜像包含 `myvoiceclone` 包、CLI/API、db migrations、configs、tests。
  2. 镜像包含默认测试运行所需的 `pytest` 和 `httpx`。
  3. 镜像继承或安装 cu130 兼容的 `torch`、`torchaudio`、`TTS`，不进行无约束 torchaudio 重装。
  4. 镜像默认启动 API，但仍能通过 `docker exec` 执行 CLI。
  5. 镜像构建不复制 `.data/`、模型权重、音频文件、宿主 `venv/`。
  6. 构建失败时不得删除 `docker-train:latest`。
- **对应测试台账项**：`NF1-T03` / `NF1-T04`
- **收口标准**：`docker build -t ai-voiceclone:cu130 -f infra/docker/Dockerfile.ai-voiceclone .` 成功；依赖探针 PASS。
- **本 Phase 风险提醒**：cu130 Python wheel 组合敏感，Coqui/Torch/Torchaudio 不匹配会导致 import 或运行时失败。

### 5.3 Phase 3 - Single Service Runtime

- **Phase 目标**：把运行形态收敛为 `ai-voiceclone` 单服务、唯一 658 端口。
- **本 Phase 对应编号**：`P3-01` / `P3-02`
- **本 Phase 新增 / 修改 / 删除文件**：新增 `infra/docker/compose.voiceclone.yaml`，可选择修改旧 `infra/docker/compose.yaml` 为 deprecated 注释或保留历史对照。
- **具体功能预期**：
  1. `docker compose -f infra/docker/compose.voiceclone.yaml up -d ai-voiceclone` 可启动容器。
  2. 容器名固定为 `ai-voiceclone`，便于 `docker exec ai-voiceclone ...`。
  3. 宿主只暴露 `0.0.0.0:658->658/tcp`。
  4. 容器内 API 监听 `0.0.0.0:658`。
  5. `.data` 子目录作为 bind mount，容器重启不丢 DB/artifact/model/evidence。
  6. GPU device reservation 保留，但 CUDA 可用性必须由 runtime probe 证明。
  7. 不引入 SSH 或额外 debug 端口。
- **对应测试台账项**：`NF1-T05` / `NF1-T06`
- **收口标准**：`docker ps` 端口唯一；`curl http://127.0.0.1:658/health` PASS。
- **本 Phase 风险提醒**：当前 API 未内建认证授权；唯一端口不等于公网安全。

### 5.4 Phase 4 - Host Execution Removal

- **Phase 目标**：从工具链、文档和文件系统移除宿主 Python 执行路径。
- **本 Phase 对应编号**：`P4-01` / `P4-02` / `P4-03`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `scripts/*.sh`、`README.md`、`docs/ops/local-setup.md`、测试；删除 `venv/`
- **具体功能预期**：
  1. `bootstrap_env.sh` 不再执行 `python3 -m venv venv`。
  2. `run_preprocess.sh` 和 `run_train_sovits.sh` 不再调用 `./venv/bin/python`。
  3. dry-run 输出明确说明将使用 `ai-voiceclone` 容器。
  4. README 与 ops 文档主路径为 Docker build/up/exec。
  5. `.dockerignore` 继续排除 `venv/`，防止未来误复制宿主环境。
  6. 删除 `venv/` 后，所有验证仍可在容器内完成。
- **对应测试台账项**：`NF1-T07` / `NF1-T08` / `NF1-T09`
- **收口标准**：`rg "venv/bin|source venv|python3 -m venv venv" scripts README.md docs/ops` 无主路径命中；`test ! -d venv` PASS。
- **本 Phase 风险提醒**：过早删除 `venv/` 会让测试暂时失去 fallback，因此必须在容器内测试通过后执行。

### 5.5 Phase 5 - Legacy Image Cleanup

- **Phase 目标**：删除历史 `docker-train:latest` 镜像，消除误用入口。
- **本 Phase 对应编号**：`P5-01`
- **本 Phase 新增 / 修改 / 删除文件**：删除 Docker local image tag `docker-train:latest`；不删除源码文件。
- **具体功能预期**：
  1. `ai-voiceclone:cu130` 存在且已通过 smoke。
  2. `ai-voiceclone` 容器运行健康。
  3. compose 和脚本不再引用 `docker-train`。
  4. 删除 `docker-train:latest` 后，重新构建/启动路径仍可用。
  5. 如删除失败，记录占用原因，不强制删除未知容器。
- **对应测试台账项**：`NF1-T10`
- **收口标准**：`docker image ls --format '{{.Repository}}:{{.Tag}}' | rg '^docker-train:latest$'` 无命中。
- **本 Phase 风险提醒**：若 `Dockerfile.ai-voiceclone` 仍 `FROM docker-train:latest`，则不得删除历史镜像；最终 Dockerfile 必须可复现。

### 5.6 Phase 6 - Closure Evidence

- **Phase 目标**：以容器内证据证明 NF1 迁移完成。
- **本 Phase 对应编号**：`P6-01` / `P6-02` / `P6-03`
- **本 Phase 新增 / 修改 / 删除文件**：新增 closure 文档（后续执行阶段）：`docs/closure/new-refactors/NF1-docker-images-closure.md`
- **具体功能预期**：
  1. 容器内 `python -m pytest -q` PASS。
  2. 容器内 `python -m myvoiceclone.cli init-db` PASS。
  3. 容器内 `python -m myvoiceclone.cli vec-health` PASS。
  4. 宿主 `curl http://127.0.0.1:658/health` PASS。
  5. `docker ps` 证明 `ai-voiceclone` 只暴露 658。
  6. 容器重启后 API 和 DB 仍可用。
  7. 若 CUDA 不可用，closure 必须如实记录，不得声称 live GPU ready。
- **对应测试台账项**：`NF1-T11` / `NF1-T12` / `NF1-T13`
- **收口标准**：§8 测试台账所有 hard gate PASS，证据四元组齐全。
- **本 Phase 风险提醒**：测试通过必须来自容器，不接受宿主 `venv` 的历史结果。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| NF1-D1: 禁止宿主执行 | `user directive 2026-07-07` | Phase 4 删除 host venv 与脚本本地执行路径 | 若撤销，则本 AP 需降级为 hybrid runtime plan |
| NF1-D2: 唯一外部端口 658 | `user directive 2026-07-07` | Phase 3 compose 只发布 658 | 若需要多端口，必须回 design/QNA，不在执行中临时加端口 |
| NF1-D3: 构建专用 ai-voiceclone 镜像 | `user directive 2026-07-07` | Phase 2 新 Dockerfile 与 image tag | 若放弃专用镜像，则不能删除 docker-train |
| NF1-D4: 删除历史 docker-train 镜像 | `user directive 2026-07-07` | Phase 5 cleanup gate | 若新镜像未验证，不执行删除 |
| NF1-D5: 不改 ai-neo | 本次用户澄清 | ai-neo 只作为宿主状态参考，不纳入 myvoiceclone 执行环境 | 若未来共用模型服务，另开集成 AP |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `infra/docker/Dockerfile.train:6` | 训练镜像 base arg，默认 NGC PyTorch | P2-01 的 cu130/GB10 substrate 参考 | `♻️ 重 substrate` | 现有 compose 覆盖为 `nvidia/cuda:13.0.0-devel-ubuntu24.04` |
| A-2 | `infra/docker/Dockerfile.train:22` | 容器内 `/opt/venv` | P2-01 可复用容器内 venv 模式 | `✅ 复用` | 允许容器内 venv，禁止宿主 venv |
| A-3 | `infra/docker/Dockerfile.train:29` | copy app 和 migrations | P2-01 确保 init-db 可用 | `✅ 复用` | 新镜像还需复制 configs/tests |
| A-4 | `infra/docker/Dockerfile.train:36` | 安装 `.[cli,db,api]` 与 soundfile | P2-01 依赖安装基线 | `♻️ 重 substrate` | 需补 `pytest`，保持 torchaudio 约束 |
| A-5 | `infra/docker/Dockerfile.train:59` | 安装 torchaudio/transformers/torchcodec | P2-01 保持 Coqui/Torch 兼容组合 | `✅ 复用` | 禁止无约束重装 |
| A-6 | `infra/docker/Dockerfile.preprocess:1` | 轻量 Python 预处理镜像 | P1-01 反例参考 | `✅ 复用` | 不作为 ai-voiceclone base |
| A-7 | `infra/docker/compose.yaml:25` | 旧 compose services 根 | P3-01 迁移边界 | `♻️ 重 substrate` | 旧服务名不再作为主入口 |
| A-8 | `infra/docker/compose.yaml:57` | 旧 train service NVIDIA runtime | P3-01 GPU 配置参考 | `✅ 复用` | 新 compose 保留 GPU reservation |
| A-9 | `infra/docker/compose.yaml:58` | 旧 volume mount 设计 | P3-01 数据持久化参考 | `✅ 复用` | 保留 `.data` bind mount 策略 |
| A-10 | `src/myvoiceclone/api/app.py:110` | `/health` endpoint | P3-02 / P6-02 health smoke | `✅ 复用` | 不重写 API app |
| A-11 | `src/myvoiceclone/config.py:156` | DB/env resolver | P3-02 / P6-02 容器路径解析 | `✅ 复用` | compose env 指向 `/app/...` |
| A-12 | `src/myvoiceclone/storage/sqlite.py:220` | SQLite connection + WAL + vec load | P6-02 DB/vec smoke | `✅ 复用` | 不改 schema |
| A-13 | `scripts/bootstrap_env.sh:17` | 宿主 venv 创建 | P4-01 删除/替换 | `♻️ 重 substrate` | 迁到 docker build/up |
| A-14 | `scripts/run_preprocess.sh:53` | 宿主 venv CLI 调用 | P4-01 删除/替换 | `♻️ 重 substrate` | 迁到 docker exec |
| A-15 | `scripts/run_train_sovits.sh:79` | 宿主 venv CLI 调用 | P4-01 删除/替换 | `♻️ 重 substrate` | 迁到 docker exec |
| A-16 | `tests/unit/test_docker_first_test_contract.py:14` | Docker 契约测试 | P2-02 / P3-01 更新测试 | `✅ 复用` | 扩展为 ai-voiceclone 契约 |
| A-17 | `tests/unit/test_scripts_dry_run.py:71` | 脚本 dry-run 测试 | P4-01 更新测试 | `✅ 复用` | 文案改为容器执行 |
| A-18 | `.dockerignore:1` | 排除 `.git/`、`venv/`、`.data/`、大文件 | P2-01 防止复制宿主环境 | `✅ 复用` | 保持 migrations 例外 |
| A-19 | `.env.example:1` | 容器路径与 runtime key 示例 | P4-02 文档同步 | `✅ 复用` | 需补 658 / compose.voiceclone |
| A-20 | `pytest.ini:1` | 默认测试 marker | P6-01 容器内测试口径 | `✅ 复用` | 不接受宿主测试替代 |
| A-21 | `infra/docker/Dockerfile.ai-voiceclone` | 将新建专用镜像 Dockerfile | P2-01 | `🆕 净新` | 最终不能 `FROM docker-train:latest` |
| A-22 | `infra/docker/compose.voiceclone.yaml` | 将新建专用 compose | P3-01 / P3-02 | `🆕 净新` | 唯一发布 658 |
| A-23 | `docs/closure/new-refactors/NF1-docker-images-closure.md` | 后续执行 closure | P6-01..P6-03 | `🆕 净新` | 本 AP 不回填 executed |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 继续让脚本调用 `./venv/bin/python` | 违反 NF1-D1；现有命中在 `scripts/run_preprocess.sh:53` 和 `scripts/run_train_sovits.sh:79` |
| ⛔2 | 在最终 `Dockerfile.ai-voiceclone` 中 `FROM docker-train:latest` | 删除 `docker-train:latest` 后无法复现；只能短期 spike 使用，不能作为最终收口 |
| ⛔3 | 暴露 SSH、668、669、670 或随机 debug 端口 | 违反唯一 658 外部通讯口；ai-neo 的 668/669 只是宿主状态参考 |
| ⛔4 | 删除 `.data/` 或模型缓存 | NF1 只删除执行环境残留，不删除业务数据 |
| ⛔5 | 用宿主 `venv/bin/python -m pytest` 作为 NF1 通过证据 | NF1 成功标准要求容器内执行 |
| ⛔6 | 容器迁移后声称真实 So-VITS/RVC 训练已实现 | adapter 真实训练缺口仍存在，NF1 不实现算法训练 |
| ⛔7 | 把“只有 658 端口”解释为“公网安全” | 当前 API 无内建认证授权，端口收敛不是访问控制 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**（如有）：`N/A`。本 AP 的 §7.1 是 grounding 真源。
- **调查事实摘录**：
  - `docker-train:latest`：arm64，约 12.8GB，容器内探针显示 `torch 2.12.0+cu130`、`torchaudio 2.11.0+cu130`、`TTS 0.27.5`、`fastapi`、`uvicorn`、`sqlite_vec` 存在，`pytest` 缺失。
  - `docker-preprocess:latest`：约 688MB，容器内探针显示 `torch`、`torchaudio`、`pyannote`、`whisper`、`demucs` 缺失，只适合轻量 CLI/DB/mock 验证。
  - `vllm/vllm-openai:gemma-aarch64-cu130`：arm64，约 21GB，探针显示 `torch 2.11.0+cu130`、`vllm 0.22.1rc1...`、`nvcc 13.0`，但它不是 myvoiceclone 应用镜像。
  - 宿主 `nvidia-smi --query-gpu` 显示 `NVIDIA GB10, 580.159.03, 12.1` compute capability；host `nvidia-smi` 页面显示 CUDA Version 13.0。
  - 当前 `docker ps` 中 `ai-neo` 暴露 668/669，`web-neo` 暴露 886，`web-dev` 暴露 888；这些不属于 `myvoiceclone` 新执行环境。
  - 当前仓库 `venv/` 存在；宿主 venv 测试曾为 `162 passed, 1 skipped, 2 deselected`，但 NF1 后不可作为执行路径。
- **安全 / 信任边界类工作项的威胁模型锚**：`P3-01` / `P3-02` / `P6-03`。
  - 资产：SQLite DB、artifact、模型缓存、训练/推理 job、API 写接口。
  - 入口：宿主对外 `658/tcp`。
  - 威胁：误暴露其他端口、无认证 API 被非授权调用、容器挂载数据被错误删除、debug/SSH 面扩张。
  - NF1 控制：只发布 658，configs readonly，`.data` 显式挂载，不暴露 SSH/debug，API health 作为最小外部 smoke。
  - NF1 不控制：认证授权、TLS、公网访问策略、rate limit。若 658 需要公网直连，必须新建 security gateway/auth plan。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NF1-T01` | runtime inventory 可复现 | `短途` | `契约` | `🆕 新增 closure command log` | `P1-01 → 当前镜像、端口、依赖和测试起跑线被记录` | `commit + docker image/ps/probe log PASS + run-time UTC` |
| `NF1-T02` | 宿主 venv 入口清单完整 | `短途` | `契约` | `🆕 新增 rg gate` | `P1-02 → 所有宿主 venv 入口被列入迁移清单` | `commit + rg "venv/bin|python3 -m venv" baseline + run-time UTC` |
| `NF1-T03` | `ai-voiceclone:cu130` 镜像可构建 | `spike` | `集成` | `🆕 新增 docker build smoke` | `P2-01 → 可复现构建专用镜像` | `commit + docker build PASS + run-time UTC` |
| `NF1-T04` | 新镜像依赖与 Dockerfile 契约 | `短途` | `unit·契约` | `🔱 fork tests/unit/test_docker_first_test_contract.py + 新断言` | `P2-02 → 契约测试覆盖新镜像依赖与迁移文件复制` | `commit + pytest tests/unit/test_docker_first_test_contract.py PASS + run-time UTC` |
| `NF1-T05` | compose 只发布 658 | `短途` | `契约` | `🆕 新增 compose config check` | `P3-01 → ai-voiceclone 只映射 658:658` | `commit + docker compose config port gate PASS + run-time UTC` |
| `NF1-T06` | API 658 health | `spike` | `e2e` | `🆕 新增 curl smoke` | `P3-02 → /health 返回 healthy` | `commit + curl /health PASS + run-time UTC` |
| `NF1-T07` | 脚本不再调用宿主 venv | `短途` | `unit·契约` | `🔱 fork tests/unit/test_scripts_dry_run.py + rg gate` | `P4-01 → 脚本只包装 Docker 命令` | `commit + pytest dry-run PASS + rg gate PASS + run-time UTC` |
| `NF1-T08` | 文档容器-only 主路径 | `短途` | `回归` | `🆕 新增 docs grep gate` | `P4-02 → 文档不再指示宿主 venv 主路径` | `commit + docs grep gate PASS + run-time UTC` |
| `NF1-T09` | 宿主 `venv/` 已删除 | `短途` | `契约` | `🆕 新增 filesystem gate` | `P4-03 → 仓库根目录不存在宿主虚拟环境` | `commit + test ! -d venv PASS + run-time UTC` |
| `NF1-T10` | 历史 `docker-train:latest` 已删除 | `短途` | `契约` | `🆕 新增 docker image ls gate` | `P5-01 → docker-train 不再出现` | `commit + docker image ls gate PASS + run-time UTC` |
| `NF1-T11` | 容器内默认 pytest | `mega` | `集成·回归` | `♻️ 沿用 pytest.ini 默认套件` | `P6-01 → 默认测试套件容器内 PASS` | `commit + docker exec ai-voiceclone python -m pytest -q PASS + run-time UTC` |
| `NF1-T12` | 容器内 DB/vec/API smoke | `spike` | `集成·e2e` | `🆕 新增 smoke command set` | `P6-02 → init-db、vec-health、/health 全 PASS` | `commit + init-db/vec-health/curl PASS + run-time UTC` |
| `NF1-T13` | 端口唯一性与重启稳定 | `soak` | `e2e` | `🆕 新增 restart smoke` | `P6-03 → 重启后仍只暴露 658 且数据持久` | `commit + restart x3 + docker ps port gate PASS + run-time UTC` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_docker_first_test_contract.py` | `🔱 fork/扩展` | 加 `Dockerfile.ai-voiceclone`、`compose.voiceclone.yaml`、658、pytest、no docker-train 主引用断言 | 已存在，当前默认测试 PASS |
| `tests/unit/test_scripts_dry_run.py` | `🔱 fork/扩展` | dry-run 文案从 host venv 改为 container-only | 已存在，当前默认测试 PASS |
| `tests/unit/test_project_config.py` | `♻️ 沿用` | 可能补充 `PORT=658` 或 compose env 文档断言 | 已存在，当前默认测试 PASS |
| `pytest.ini` 默认 marker 套件 | `♻️ 沿用` | 0 或少改动 | 当前宿主 venv PASS；NF1 收口必须容器内 PASS |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `python -m pytest tests/unit/test_docker_first_test_contract.py tests/unit/test_scripts_dry_run.py -q`，但在容器内跑 | unit·契约·回归 | 每个 Phase 修改后 |
| spike | `docker build`、`docker compose up`、`curl /health`、依赖 import probe | 集成·e2e | Phase 2 / Phase 3 / Phase 6 收口 |
| mega | `docker exec ai-voiceclone python -m pytest -q` | 容器内默认全套 | 本 AP 收口 |
| soak | `docker restart ai-voiceclone` 连续 3 次 + port gate + health + DB file check | e2e | 退出硬闸 |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖公网认证授权攻击测试（理由：NF1 只做容器运行边界和端口唯一性）→ 交后继 `NF2 security gateway/auth plan`。
- 不覆盖真实 So-VITS/RVC 训练质量（理由：当前 adapter 未实现真实训练）→ 交后继 `live training implementation plan`。
- 不覆盖长时间 GPU 训练 soak（理由：NF1 是 runtime migration，不是训练性能验证）→ 交后继 `GPU live training soak plan`。
- 不覆盖 `.data` 数据清洗或历史 artifact 修复（理由：不得删除业务数据）→ 交后继 data hygiene plan。

### 8.5 测试保真（防假绿 · 刻死）

- 每个 PASS 必带四元组证据；计数不替代价值。
- `NF1-T11` 必须在 `ai-voiceclone` 容器内运行，不接受宿主 `venv` 结果。
- `NF1-T06` 必须通过宿主访问 `127.0.0.1:658`，不接受容器内 localhost 结果替代。
- `NF1-T10` 必须在 `NF1-T03` 至 `NF1-T09` 通过后执行。
- 安全 / 信任边界测试必须包含端口负断言：不得出现 22、668、669、670 或其他 myvoiceclone 暴露端口。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| cu130 wheel 组合不稳定 | Torch/Torchaudio/Coqui/Torchcodec 版本组合可能 import 通过但运行失败 | `high` | 锁定当前 `docker-train` 已验证组合；新增 import probe；不做无约束升级 |
| 删除 `docker-train` 过早 | 如果新 Dockerfile 仍依赖 `docker-train`，删除后无法重建 | `high` | 最终 Dockerfile 不得 `FROM docker-train:latest`；删除前运行 grep gate |
| 宿主 `venv` 删除过早 | 容器未验证前删除会失去本地对照 | `high` | Phase 4 删除前要求 Phase 2/3 smoke PASS |
| API 无认证 | 658 若公网暴露，写接口存在未授权调用风险 | `high` | NF1 只允许可信网络/上游代理使用；公网认证另开 NF2 |
| `.data` 权限 | 现有 `.data` 多为 root-owned，容器/宿主用户切换可能写失败 | `medium` | compose 明确用户策略；执行前检查写权限；不删除数据 |
| pytest 缺失 | `docker-train` 当前没有 pytest，不能直接跑容器内测试 | `medium` | `Dockerfile.ai-voiceclone` 安装 test extra 或 pytest/httpx |
| 端口冲突 | 宿主 658 可能被占用 | `medium` | 启动前 `ss -ltnp | rg ':658'`；冲突时阻塞，不换端口绕过 |
| NVIDIA runtime | Docker default runtime 是 runc，但有 nvidia runtime；compose 需显式 GPU request | `medium` | 保留 device reservation；运行时 probe 记录 CUDA 可用性 |

### 9.2 约束与前提

- **技术前提**：宿主 Docker 可用；NVIDIA Container Toolkit 可用；`ai-voiceclone:cu130` 可从 Dockerfile 构建；`.data` bind mount 可写。
- **运行时前提**：端口 658 未被占用；容器可访问 `/app/db`、`/app/data/artifacts`、`/app/models`、`/app/test-runs`。
- **组织协作前提**：业主确认 NF1 不包含公网认证、不包含真实训练实现、不删除 `.data`。
- **上线 / 合并前提**：§8 所有 hard gate PASS；`docker-train:latest` 删除发生在新镜像验证之后。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/action-plan/new-refactors/NF1-docker-images.md`
- 需要同步更新的说明文档 / README：`README.md` / `docs/ops/local-setup.md`
- 需要同步更新的测试说明：`tests/unit/test_docker_first_test_contract.py` / `tests/unit/test_scripts_dry_run.py`
- 需要新增的 closure：`docs/closure/new-refactors/NF1-docker-images-closure.md`

### 9.4 完成后的预期状态

1. `myvoiceclone` 的唯一主运行环境是 `ai-voiceclone` 容器，宿主无 `venv/`。
2. 对外通讯只通过宿主 658 端口进入 `ai-voiceclone` API。
3. CLI、测试、DB 初始化和 smoke 都能通过 `docker exec ai-voiceclone ...` 完成。
4. `docker-train:latest` 不再存在于本地镜像清单，避免历史入口误用。
5. 文档、脚本、测试契约都指向容器-only 运行方式。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 PASS 且四元组证据齐全：

1. `ai-voiceclone:cu130` 可构建且可启动（由 `NF1-T03` / `NF1-T06` 证明）。
2. `ai-voiceclone` 只暴露宿主 658（由 `NF1-T05` / `NF1-T13` 证明）。
3. 容器内默认测试套件 PASS（由 `NF1-T11` 证明）。
4. 容器内 DB/vec/API smoke PASS（由 `NF1-T12` 证明）。
5. 宿主 `venv/` 和历史 `docker-train:latest` 已删除（由 `NF1-T09` / `NF1-T10` 证明）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| runtime inventory 被锁定 | `P1-01` | `NF1-T01` | `commit + inventory log + run-time` | `未观察` |
| 宿主 venv 入口全识别 | `P1-02` | `NF1-T02` | `commit + rg baseline + run-time` | `未观察` |
| 专用镜像可构建 | `P2-01` | `NF1-T03` | `commit + docker build + run-time` | `未观察` |
| Docker 契约覆盖新镜像 | `P2-02` | `NF1-T04` | `commit + pytest contract + run-time` | `未观察` |
| compose 只发布 658 | `P3-01` | `NF1-T05` | `commit + compose config gate + run-time` | `未观察` |
| API 658 health 可访问 | `P3-02` | `NF1-T06` | `commit + curl health + run-time` | `未观察` |
| 脚本不再调用宿主 venv | `P4-01` | `NF1-T07` | `commit + pytest dry-run + rg gate + run-time` | `未观察` |
| 文档容器-only | `P4-02` | `NF1-T08` | `commit + docs grep gate + run-time` | `未观察` |
| 宿主 `venv/` 已删除 | `P4-03` | `NF1-T09` | `commit + filesystem gate + run-time` | `未观察` |
| 历史 `docker-train` 已删除 | `P5-01` | `NF1-T10` | `commit + docker image ls gate + run-time` | `未观察` |
| 容器内默认 pytest PASS | `P6-01` | `NF1-T11` | `commit + docker exec pytest + run-time` | `未观察` |
| 容器内 DB/vec/API smoke PASS | `P6-02` | `NF1-T12` | `commit + init-db/vec-health/curl + run-time` | `未观察` |
| 重启后端口和持久化稳定 | `P6-03` | `NF1-T13` | `commit + restart soak + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `ai-voiceclone` 容器承载 API/CLI/test/DB smoke，宿主不再执行 Python venv |
| 测试 | §8 测试台账全 PASS（退出硬闸项四元组齐全）|
| 文档 | README、ops、脚本 dry-run 文案、Docker 契约测试全部改为 container-only |
| 风险收敛 | 删除 `venv/` 和 `docker-train` 前已有新镜像、新容器、health、pytest、DB/vec 证据 |
| 可交付性 | 新用户按文档只需 Docker/compose 即可启动 658 API 并通过容器 exec 执行 CLI |

### 10.4 NOT-成功识别

任一退出硬闸测试 `degraded / 未观察`，不得标 `executed`。以下情况必须判为 NOT-success：

- `ai-voiceclone` 需要宿主 `venv/` 才能测试或运行。
- `docker ps` 显示 myvoiceclone 业务容器暴露除 658 外的端口。
- `Dockerfile.ai-voiceclone` 最终仍依赖 `FROM docker-train:latest`。
- 删除 `docker-train:latest` 后无法重新构建或启动 `ai-voiceclone`。
- API 只能容器内访问，宿主 `127.0.0.1:658/health` 不通。
- 容器内默认 pytest 未通过，但用宿主 pytest 结果替代。
- closure 声称真实训练完成或公网安全完成。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

文档状态当前为 `draft`，本节不启用。后续 NF1 实施完成后，在 closure 文档中回填：

- **实际执行摘要**：已新增 `Dockerfile.ai-voiceclone` 与 `compose.voiceclone.yaml`；`ai-voiceclone` 容器已启动并只暴露 658；宿主 `venv/` 已删除；历史 `docker-train:latest` tag 已删除；closure 已写入 `docs/closure/new-refactors/NF1-docker-images-closure.md`。
- **Phase 偏差**：P2 原计划尝试从纯 CUDA base 完整重建，但 Ubuntu ports 在 apt 大包下载阶段长时间卡顿，已中断；最终采用业主原始建议的历史 `docker-train` substrate，并重标记为 `ai-voiceclone-base:cu130`，再构建 `ai-voiceclone:cu130`。
- **阻塞与处理**：容器初次启动继承 base `ENTRYPOINT` 导致 uvicorn 被当作 CLI 参数，已通过 `ENTRYPOINT []` 修复；DB volume 初次挂载到 `/app/db` 遮蔽 migrations，已改为 `/app/.data/db`；容器测试需要 git HEAD，已只读挂载 `.git`。
- **测试发现**：容器内 `docker exec -e MOCK_ADAPTERS=true ai-voiceclone python -m pytest -q` 通过，结果 `166 passed, 2 deselected, 15 warnings`；`curl http://127.0.0.1:658/health` 返回 healthy；`torch 2.12.0+cu130` 可见 CUDA。
- **后续 handoff**：将 `ai-voiceclone-base:cu130` 固化到 registry 或恢复纯 CUDA base 全量构建；若 658 面向不可信网络，启动 NF2 security/auth plan。
