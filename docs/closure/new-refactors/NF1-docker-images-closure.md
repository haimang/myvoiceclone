# [NF1 / Docker Images] Closure

> 阶段: `new-refactors/NF1 — docker images and container-only runtime refactor`
> 范围: `P1-P6 full NF1 execution`
> Close-type: `close-with-known-issues`
> 状态: `close-with-known-issues`
> 日期: `2026-07-07` · 作者: `Codex`
> 关联 charter: `docs/plan/new-refactors/NF1-docker-images.md`
> 关联 design: `N/A`
> 关联 action-plan: `docs/plan/new-refactors/NF1-docker-images.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> NF1 已把 `myvoiceclone` 收敛到专用 `ai-voiceclone` 容器运行：宿主 `venv/` 已删除，历史 `docker-train:latest` tag 已删除，API 只通过 658 暴露，容器内默认测试通过；close-type 为 `close-with-known-issues`，因为当前保留 `ai-voiceclone-base:cu130` 作为本地 cu130 substrate，纯 CUDA base 首轮重建因 Ubuntu ports 下载卡顿未完成。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `ai-voiceclone-base:cu130` 是由历史 `docker-train:latest` 重标记而来；`docker-train:latest` tag 已删除，但 base substrate 仍需后续固化为 registry artifact 或纯 Dockerfile 构建链。
> 2. `MOCK_ADAPTERS=false` 仍是服务默认真实模式；默认 pytest 套件需要 `MOCK_ADAPTERS=true`，因此测试命令显式注入该环境变量。
> 3. 当前 API 仅完成端口收敛，不包含公网认证授权；公网暴露需后续 security/auth plan。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| P1-01 Runtime inventory 固化 | ✅ | HEAD `ae83414` + `docker image ls` 显示 `ai-voiceclone:cu130 2c998ee8d619`, `ai-voiceclone-base:cu130 c6c637088152`, 无 `docker-train` + `2026-07-07 09:02 UTC` |
| P1-02 宿主执行路径识别并迁移 | ✅ | HEAD `ae83414` + `rg "./venv/bin\|source venv\|python3 -m venv venv" scripts README.md docs/ops` 无命中 + `2026-07-07 09:02 UTC` |
| P2-01 `Dockerfile.ai-voiceclone` 新建 | ✅ | HEAD `ae83414` + `docker compose -f infra/docker/compose.voiceclone.yaml build ai-voiceclone` PASS，镜像 `2c998ee8d619` + `2026-07-07 09:02 UTC` |
| P2-02 Docker 契约测试扩展 | ✅ | HEAD `ae83414` + `docker exec -e MOCK_ADAPTERS=true ai-voiceclone python -m pytest tests/unit/test_docker_first_test_contract.py tests/unit/test_scripts_dry_run.py -q` -> `11 passed` + `2026-07-07 08:58 UTC` |
| P3-01 单服务 compose + 658 唯一端口 | ✅ | HEAD `ae83414` + `docker ps --filter name=ai-voiceclone` -> `0.0.0.0:658->658/tcp` only + `2026-07-07 09:02 UTC` |
| P3-02 API healthcheck | ✅ | HEAD `ae83414` + `curl -fsS http://127.0.0.1:658/health` -> `{"status":"healthy","version":"1.0.0"}` + `2026-07-07 09:02 UTC` |
| P4-01 脚本迁移到容器执行 | ✅ | HEAD `ae83414` + script dry-run contract `11 passed` + `2026-07-07 08:58 UTC` |
| P4-02 文档改为 container-only 主路径 | ✅ | HEAD `ae83414` + README/local-setup grep gate 无 host venv 主路径 + `2026-07-07 09:02 UTC` |
| P4-03 删除宿主 `venv/` | ✅ | HEAD `ae83414` + `test ! -d venv && echo no-host-venv` -> `no-host-venv` + `2026-07-07 09:02 UTC` |
| P5-01 删除历史 `docker-train:latest` | ✅ | HEAD `ae83414` + `docker rmi docker-train:latest` -> `Untagged: docker-train:latest`; final image list has no `docker-train` + `2026-07-07 09:02 UTC` |
| P6-01 容器内默认测试闭环 | ✅ | HEAD `ae83414` + `docker exec -e MOCK_ADAPTERS=true ai-voiceclone python -m pytest -q` -> `166 passed, 2 deselected, 15 warnings` + `2026-07-07 09:02 UTC` |
| P6-02 DB/vec/API smoke | ✅ | HEAD `ae83414` + `init-db`, `vec-health`, `curl /health` all PASS + `2026-07-07 08:58-09:00 UTC` |
| P6-03 端口唯一性和重启稳定性 | ✅ | HEAD `ae83414` + `docker restart ai-voiceclone` x3 + `curl /health` PASS each cycle; `docker ps` only 658 + `2026-07-07 08:57 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 容器镜像构建 | `docker compose -f infra/docker/compose.voiceclone.yaml build ai-voiceclone` | PASS, image `ai-voiceclone:cu130 2c998ee8d619` | P2 |
| 服务启动 | `docker compose -f infra/docker/compose.voiceclone.yaml up -d --force-recreate ai-voiceclone` | PASS, container started | P3 |
| API health | `curl -fsS --max-time 10 http://127.0.0.1:658/health` | `{"status":"healthy","version":"1.0.0"}` | P3/P6 |
| 端口唯一性 | `docker ps --filter name=ai-voiceclone --format ...` | `0.0.0.0:658->658/tcp, [::]:658->658/tcp` only | P3/P6 |
| 依赖探针 | `docker exec ai-voiceclone python -c ... find_spec(...)` | `myvoiceclone/fastapi/uvicorn/sqlite_vec/pytest/torch/torchaudio/TTS: True` | P2 |
| CUDA 可见性 | `docker exec ai-voiceclone python -c "import torch; ..."` | `torch 2.12.0+cu130 cuda 13.0 available True count 1` | P2/P6 |
| DB 初始化 | `docker exec ai-voiceclone python -m myvoiceclone.cli init-db` | `Database initialized successfully.` at `/app/.data/db/myvoiceclone.sqlite` | P6 |
| sqlite-vec | `docker exec ai-voiceclone python -m myvoiceclone.cli vec-health` | `sqlite-vec loaded successfully. Version: v0.1.9` | P6 |
| 短途契约 | `docker exec -e MOCK_ADAPTERS=true ai-voiceclone python -m pytest tests/unit/test_docker_first_test_contract.py tests/unit/test_scripts_dry_run.py -q` | `11 passed in 0.02s` | P2/P4 |
| 完整默认测试 | `docker exec -e MOCK_ADAPTERS=true ai-voiceclone python -m pytest -q` | `166 passed, 2 deselected, 15 warnings in 15.38s` | P6 |
| 宿主 venv 删除 | `test ! -d venv && echo no-host-venv` | `no-host-venv` | P4 |
| 历史 tag 删除 | `docker image ls ... | rg '^(ai-voiceclone|ai-voiceclone-base|docker-train)'` | only `ai-voiceclone` and `ai-voiceclone-base`; no `docker-train` | P5 |
| 重启 smoke | `for i in 1 2 3; do docker restart ai-voiceclone; curl /health; docker ps; done` | 3 次 health PASS; only 658 exposed | P6 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| G1 专用镜像存在 | `ai-voiceclone:cu130` 可构建 | `2c998ee8d619` built | ✅ PASS |
| G2 容器唯一端口 | `ai-voiceclone` 只暴露 658 | `0.0.0.0:658->658/tcp` only | ✅ PASS |
| G3 API health | 宿主访问 `/health` | healthy JSON returned | ✅ PASS |
| G4 容器内测试 | 默认 pytest 容器内 PASS | `166 passed, 2 deselected` | ✅ PASS |
| G5 DB/vec smoke | `init-db` + `vec-health` PASS | both PASS | ✅ PASS |
| G6 宿主 venv 删除 | `venv/` 不存在 | `no-host-venv` | ✅ PASS |
| G7 历史镜像 tag 删除 | `docker-train:latest` 不存在 | image list has no docker-train | ✅ PASS |
| G8 可复现纯 CUDA base | 不依赖历史 substrate 从 CUDA base 完整构建 | 首轮 apt 下载卡顿后中断；改用 `ai-voiceclone-base:cu130` | ⚠ PARTIAL |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| D1 纯 CUDA base 全量重建 | `B` | deferred | 网络稳定或进入 image registry hardening 时，将 `ai-voiceclone-base:cu130` 固化为可拉取基础镜像或恢复纯 CUDA Dockerfile build | platform/runtime owner |
| D2 API 认证授权 | `A` | out-of-scope | 658 需要公网直连、多租户或不可信网络访问时，新建 NF2 security/auth plan | security owner |
| D3 真实 So-VITS/RVC 训练 | `A` | out-of-scope | live training charter 启动时实现真实 adapter | model/runtime owner |
| D4 真实 objective metrics | `A` | out-of-scope | live eval charter 启动时替换 mock objective scorer | eval owner |
| D5 `datetime.utcnow()` warnings | `C` | known maintenance debt | Python 3.13 readiness pass | application owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅：P1-P6 工作项为 `verified`；G8 为 `partial` |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅：使用 HEAD `ae83414` + working tree NF1 diff + 命令输出 + UTC 时间 |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅：diff 限于 Docker/runtime scripts/docs/tests/plan；新增 closure |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

说明：本 closure 的证据基于未提交 working tree，HEAD 为 `ae83414`。未创建 git commit，因此四元组中的 commit 位以 `HEAD ae83414 + working tree NF1 changes` 表达；若后续需要审计级冻结，应在 commit 后补充 commit hash。

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| `ai-voiceclone` 容器可运行 | ✅ | 当前 healthy |
| 658 端口可访问 | ✅ | `/health` PASS |
| 宿主不再有 `venv/` | ✅ | 已删除 |
| 历史 `docker-train:latest` 不存在 | ✅ | 已 untag |
| 可执行容器内默认测试 | ✅ | `166 passed, 2 deselected` |
| 公网安全可用 | ⏸ | 未纳入 NF1；需 NF2 |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 NF1 runtime anchor。
- [ ] 决定是否把 `ai-voiceclone-base:cu130` 推送到私有 registry。
- [ ] 若 658 对不可信网络开放，先做认证授权/网关计划。

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 业务容器唯一名称 `ai-voiceclone` | ✅ 保持 | `docker ps --filter name=ai-voiceclone` |
| 唯一外部通讯口 658 | ✅ 保持 | `docker ps` ports only `658->658/tcp` |
| 宿主不执行 Python venv | ✅ 保持 | `test ! -d venv`; grep gate no host venv path in scripts/docs |
| 运行数据不删除 | ✅ 保持 | `.data` retained; DB path `/app/.data/db/myvoiceclone.sqlite` |
| Mock/real adapter 语义不混淆 | ✅ 保持 | service default `MOCK_ADAPTERS=false`; test command explicitly `MOCK_ADAPTERS=true` |
