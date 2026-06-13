# [first-test / FT1-FT8] 第 2 轮代码审查

> 审查对象: `myvoiceclone first-test FT1-FT8`
> 审查类型: `rereview`
> 审查时间: `2026-06-13`
> 审查人: `Kimi`
> 审查范围:
> - `src/myvoiceclone/`
> - `tests/`
> - `docs/closure/first-test/`
> - `infra/docker/`
> - `db/migrations/`
> 对照真相:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/closure/first-test/first-test-closure.md`
> - `docs/closure/first-test/deferred-items-ledger.md`
> - `docs/baseline/device_stacks.md`
> 文档状态: `reviewed`

---

## 0. 总结结论

- **整体判断**：默认测试套件全绿，但数据 lineage、报错体系、API 错误契约、容器化落地与 evidence 审计链存在真实 gap；当前状态更适合维持 `implementation-complete-awaiting-live-verification`，不宜直接推进真实 live capstone。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `closure` 与 `evidence pack` 的 git 锚点停留在 `31b4a04`，而当前 HEAD 为 `952fbc5`，审计链失真。
  2. 数据流存在 silent fallback：空 transcript 可进入 frozen manifest、RVC 训练使用 `fake_source_audio.wav` 回退、objective eval 的 `eval_samples` 输入/输出/引用三者指向同一 artifact。
  3. Python 报错缺乏统一异常基类与错误码，无专门报错速查手册；API 错误响应为 FastAPI 默认 `{"detail": "..."}`，未与 job/run trace 关联。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/eval/first-test/proposed-planning.md`（FT1-FT8 范围、DAG、测试注入、TR 纪律）
  - `docs/closure/first-test/first-test-closure.md` 及 FT1-FT8 各 closure 文件
  - `docs/closure/first-test/deferred-items-ledger.md`
  - `docs/baseline/device_stacks.md`
- **核查实现**：
  - `src/myvoiceclone/pipelines/export_dataset.py`
  - `src/myvoiceclone/pipelines/infer_real.py`
  - `src/myvoiceclone/pipelines/train.py`
  - `src/myvoiceclone/eval/objective.py`
  - `src/myvoiceclone/jobs/runner.py`
  - `src/myvoiceclone/jobs/events.py`
  - `src/myvoiceclone/api/app.py`、`routes_runs.py`、`routes_jobs.py`、`routes_inference.py`
  - `src/myvoiceclone/adapters/training/sovits_adapter.py`
  - `src/myvoiceclone/evidence.py`
  - `infra/docker/Dockerfile.train`、`Dockerfile.preprocess`、`compose.yaml`
  - `tests/api/test_audit_trace.py`、`tests/api/test_first_test_runs.py`
  - `tests/unit/pipelines/test_export_dataset.py`、`test_real_inference_wrapper.py`
- **执行过的验证**：
  - `git rev-parse --short HEAD` → `952fbc5`
  - `git status --short` → `?? docs/baseline/`、`?? docs/code-review/first-test/FT1-FT8-2nd-pass-reviewed-by-deepseek.md`、`?? docs/code-review/first-test/FT1-FT8-2nd-pass-reviewed-by-gemini.md`
  - `./venv/bin/python -m pytest -q` → `148 passed, 1 skipped, 2 deselected, 14 warnings`
  - `./venv/bin/python -m pytest tests/integration/test_first_test_http_smoke.py tests/integration/test_first_test_capstone.py -m live -q -rs` → `2 skipped, 1 deselected`
  - `./venv/bin/python -m myvoiceclone.evidence validate /mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z --repo-root .` → `{"ok": true, ...}`
  - 直接读取 evidence pack `env.json` 确认 `git_commit: 31b4a04`
- **复用 / 对照的既有审查**：
  - 未读取 `docs/code-review/first-test/FT1-FT8-reviewed-by-kimi.md`、`FT1-FT8-reviewed-by-deepseek.md` 或其他 2nd-pass 报告；仅将 `proposed-planning` 与 `closure` 作为权威输入，对代码进行独立复核。

### 1.1 已确认的正面事实

- 默认全量回归测试通过：`148 passed, 1 skipped, 2 deselected, 14 warnings`。
- `FT1` 准入项落地：主命令 `myvoiceclone`、env-aware artifact root、preprocess job payload、empty manifest guard 均有测试覆盖。
- `FT2` schema/observability 基础到位：WAL、外键、busy_timeout、`metadata_json`、schema drift inventory 测试、`/api/audit/trace` 存在。
- `FT6` FastAPI 上传即落 artifact，`start preprocess/infer/eval` 仅创建 DB job，未使用 `BackgroundTasks` 承载长任务。
- mock/real 分离纪律在 release gate、artifact metadata、evidence validator 中保持。
- live/gpu/slow marker 与 skip denominator 机制存在且默认不执行 live。

### 1.2 已确认的负面事实

- `docs/closure/first-test/*.md` 与 evidence pack 均锚定在 `HEAD 31b4a04`，与当前 `952fbc5` 不一致。
- `run_export_dataset` 允许 transcript 为 `None` 的 segment 进入 frozen manifest，写入空字符串。
- `run_real_inference` 仅校验 `reference_artifact_id` 存在，不校验 artifact kind（cleaned/reference）。
- `evaluate_objective_metrics` 将 `audio_artifact_id`/`input_artifact_id`/`output_artifact_id` 均指向 rendered artifact。
- `run_train_rvc` 在未提供 `source_audio_path` 时使用 `fake_source_audio.wav` 作为回退。
- `JobRunner` 对 `train_sovits`、`infer_real`、`eval_first_test` 及单步 preprocess（diarize/slice/clean/transcribe/score/curate）未调用 `write_step_event`。
- 全项目仅定义 `FFmpegAdapterError` 一个自定义异常；无统一异常基类、错误码枚举或分类体系。
- `docs/ops/` 下不存在报错速查手册（error-handbook / troubleshooting）。
- API 无全局异常处理器，错误响应为 FastAPI 默认 `{"detail": "..."}`，无 `trace_id`/`error_code`。
- `Dockerfile.train` 引用的 SoVITS 真实训练未实现；无 `Dockerfile.api`；`compose.yaml` 默认命令依赖前置 dataset 与占位 WAV。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 直接阅读 `src/`、`tests/`、`infra/docker/`、`docs/closure/` 关键文件并记录行号。 |
| 本地命令 / 测试 | yes | 运行全量 pytest、live marker 子集、evidence validator，并检查 git HEAD。 |
| schema / contract 反向校验 | yes | 核对 migration、job_events schema、API response schema snapshot、audit trace 查询。 |
| live / deploy / preview 证据 | no | live capstone 未在本机执行；容器未实际 build/run。 |
| 与上游 design / QNA 对账 | yes | 逐条对照 `proposed-planning.md` FT1-FT8 工作台账与 closure claim。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | closure/evidence 锚点与当前 HEAD 不一致 | high | docs-gap | yes | 更新 closure 锚点至 `952fbc5` 并重新生成 evidence pack |
| R2 | FT7 前置闸仅检查 closure 文件存在性 | medium | test-gap | no | 扩展 gate 为实际运行 FT1-FT6 目标子集并断言通过 |
| R3 | frozen manifest 可包含空 transcript | high | correctness | yes | 在 dataset freeze 时拒绝 transcript 为空/过短的 segment |
| R4 | real inference 未校验 reference artifact kind | medium | protocol-drift | no | 限制 reference artifact 类型为 cleaned 或 reference_audio |
| R5 | objective eval 样本 lineage 断裂 | high | correctness | yes | 正确填充 input/output/reference artifact id |
| R6 | RVC 训练使用 fake source audio 回退 | medium | correctness | no | 要求 source_audio_path 或为 real conversion 显式失败 |
| R7 | train/infer/eval 阶段缺少 step-level job_events | medium | observability-gap | no | 为关键阶段写入 `write_step_event` 并携带 adapter_mode |
| R8 | 无统一异常基类、错误码与分类体系 | high | platform-fitness | no | 引入 `MyVoiceCloneException`、错误码枚举、分类标签 |
| R9 | 缺少报错速查手册 | medium | docs-gap | no | 新增 `docs/ops/error-handbook.md` |
| R10 | API 错误响应未结构化、无 trace_id | high | protocol-drift | no | 增加全局异常处理器与统一错误 envelope |
| R11 | 容器化训练未实现真实路径，FastAPI 未容器化 | high | platform-fitness | no | 实现 SoVITS 真实训练或新增 Dockerfile.api；完善 compose 默认流程 |
| R12 | evidence pack env.json 未捕获解析后的 DB_PATH/ARTIFACT_ROOT | medium | observability-gap | no | 在 env.json 中写入解析后的配置值与模型目录 |

### R1. closure/evidence 锚点与当前 HEAD 不一致

- **严重级别**：`high`
- **类型**：`docs-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `docs/closure/first-test/FT1-preflight-closure.md:24` 等全部 closure 文件证据列为 `uncommitted working tree on HEAD 31b4a04`。
  - `docs/closure/first-test/first-test-closure.md:28`、`first-test-closure.md:34` 同样锚定 `HEAD 31b4a04`。
  - evidence pack `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z/env.json:5` 记录 `"git_commit": "31b4a04"`。
  - 当前 `git rev-parse --short HEAD` 为 `952fbc5`。
- **为什么重要**：
  - closure 的证据四元组要求 commit + query/test + run-time；锚点与真实 HEAD 不一致时，无法证明 evidence 是在当前代码上产生的。
  - evidence pack 的 `git_status_short` 仍显示 R1 修复前的修改清单，造成审计链污染。
- **审查判断**：
  - 这是 first-test 诚实收口声明中的硬性违背；即使默认测试全绿，也不能用旧 commit 的 evidence 证明新 commit 的状态。
- **建议修法**：
  1. 将全部 closure 文件中的 `HEAD 31b4a04` 更新为 `952fbc5`。
  2. 使用当前 HEAD 重新执行验证命令并刷新 evidence pack。
  3. 在 `tests/unit/test_first_test_closure_docs.py` 中增加 assertion：closure 中的 git commit 与 `git rev-parse --short HEAD` 一致。

### R2. FT7 前置闸仅检查 closure 文件存在性

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `tests/integration/test_first_test_capstone.py:18-26` 的 `test_first_test_capstone_requires_ft1_ft6_closures` 仅断言 `docs/closure/first-test/FT1..FT6-closure.md` 文件存在。
  - `docs/eval/first-test/proposed-planning.md:303` 中 `FT7.4` 要求“FT1-FT6 必须绿，live skipped reason 计数必须可见”。
- **为什么重要**：
  - 文件存在性不能替代测试实际通过；未来若 closure 被手动创建而对应测试失败，gate 仍会放行 capstone。
- **审查判断**：
  - gate 语义不完整，属于测试设计 gap。
- **建议修法**：
  - 在 pre-capstone gate 中调用 pytest 子集（或读取 closure 中的测试结果字段）并断言 `passed`。

### R3. frozen manifest 可包含空 transcript

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/pipelines/export_dataset.py:52-62` 查询 `status IN (processed, keep, fixed, cleaned, transcribed)` 且 `cleaned_artifact_id IS NOT NULL`。
  - `src/myvoiceclone/pipelines/export_dataset.py:128` 写入 `"transcript": s["transcript"] or ""`，将 `None` 静默转为空字符串。
  - `src/myvoiceclone/pipelines/export_dataset.py:139-140` 的 empty manifest guard 只检查行数，不检查 transcript 内容。
- **为什么重要**：
  - first-test 是 TTS 推理闭环；空 transcript 进入 frozen dataset 会导致训练/推理输入是“无文本”样本，属于 silent data-quality regression。
- **审查判断**：
  - 违反 proposed-planning 中“禁止 silent fallback 到 mock/无效数据”的技术路线红线。
- **建议修法**：
  - 在 `run_export_dataset` 中拒绝 transcript 为空或仅含空白的 segment；或至少标记为 `transcript_missing` 并在 release gate 中拦截。

### R4. real inference 未校验 reference artifact kind

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/pipelines/infer_real.py:48-50` 仅检查 `reference_artifact` 存在，未检查 `artifact_type`/`kind`。
  - `src/myvoiceclone/pipelines/infer_real.py:56` 直接使用 `artifact_store.get_absolute_path(reference_artifact)`。
- **为什么重要**：
  - 任意 artifact（如 raw、uploaded_audio）都可作为 reference，破坏“cleaned/reference” provenance 合同。
- **审查判断**：
  - 当前测试可能通过，但真实 live 运行时会导致不可预期的 reference 音频质量。
- **建议修法**：
  - 在 `validate_inference_request` 或 `run_real_inference` 中限制 `reference_artifact.artifact_type` 为 `cleaned` 或 `reference_audio`。

### R5. objective eval 样本 lineage 断裂

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/myvoiceclone/eval/objective.py:91-106` 插入 `eval_samples` 时：
    - `audio_artifact_id=rendered_art_id`
    - `input_artifact_id=rendered_art_id`
    - `output_artifact_id=rendered_art_id`
- **为什么重要**：
  - 输入、输出、参考音频应指向不同 artifact；全部指向 rendered output 使 eval 结果无法审计，也无法做 ABX/MOS 对比。
- **审查判断**：
  - 该字段设计原本用于支持主观/客观评估的样本级 lineage，当前实现使其失去语义。
- **建议修法**：
  - `input_artifact_id` 指向 prompt/text 或 source audio；`audio_artifact_id`/`output_artifact_id` 指向 rendered output；`reference_artifact_id` 指向 reference artifact。

### R6. RVC 训练使用 fake source audio 回退

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/pipelines/train.py:76`：`src_path = source_audio_path or "fake_source_audio.wav"`。
  - `src/myvoiceclone/pipelines/train.py:96`：`"source_audio_path": src_path` 写入 rendered artifact metadata。
- **为什么重要**：
  - 真实模式下若未传 source audio，会读取不存在的占位文件；mock 模式下则把 fake provenance 写入 metadata。
- **审查判断**：
  - 与 proposed-planning 中“禁止 silent fallback 到 mock”的红线冲突。
- **建议修法**：
  - 在真实模式下要求 `source_audio_path` 必须存在；mock 模式下显式标记 synthetic provenance，不写入虚假路径。

### R7. train/infer/eval 阶段缺少 step-level job_events

- **严重级别**：`medium`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/jobs/runner.py:272-293` `_execute_train_sovits` 直接调用 `run_train_sovits`，无 `_run_observed_step` 包裹。
  - `src/myvoiceclone/jobs/runner.py:365-383` `_execute_infer_real`、`:385-398` `_execute_eval_first_test` 同样无 step 事件。
  - `_execute_step_diarize/slice/clean/transcribe/score/curate` 直接调用 pipeline，未写 step 事件。
- **为什么重要**：
  - proposed-planning `FT2.2` 要求 step-level `job_events` contract；训练、推理、评测作为 first-test 核心阶段，缺少事件会导致无法通过事件日志理解进度。
- **审查判断**：
  - schema 已支持，但业务填充不完整。
- **建议修法**：
  - 为核心 job 类型包裹 `write_step_event`，并在 metadata 中显式写入 `adapter_mode`。

### R8. 无统一异常基类、错误码与分类体系

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - 全项目仅 `src/myvoiceclone/adapters/audio/ffmpeg.py:8` 定义 `FFmpegAdapterError`。
  - 其余位置大量使用 `ValueError`、`RuntimeError`、`NotImplementedError`、`HTTPException`，无统一基类。
  - 无 `ErrorCode` 枚举，无 `config/preflight/adapter/runtime/license` 等分类标签。
- **为什么重要**：
  - 调用方无法按错误类型做差异化重试或提示；日志/事件中的错误不可机器分类；API 无法返回稳定错误码。
- **审查判断**：
  - 当前报错机制不足以支撑 robust ops。
- **建议修法**：
  - 引入 `MyVoiceCloneException(Exception)` 基类与 `ErrorCode` 枚举；为适配器层定义专用异常（`AdapterError`、`PreflightError`、`LicenseError` 等）。

### R9. 缺少报错速查手册

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `docs/ops/` 下仅 `local-setup.md`、`security-governance.md`。
  - `glob` 与内容搜索均未发现 `error-handbook`、`troubleshooting`、`runbook` 类文档。
- **为什么重要**：
  - first-test 涉及 FFmpeg、PyAnnote token、Whisper、XTTS license 等外部依赖；缺少速查手册会延长 live 失败时的定位时间。
- **审查判断**：
  - 运维文档缺口。
- **建议修法**：
  - 新增 `docs/ops/error-handbook.md`，覆盖常见错误、退出码、修复步骤、对应 DB 查询。

### R10. API 错误响应未结构化、无 trace_id

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/api/app.py` 未注册 `@app.exception_handler`。
  - `src/myvoiceclone/api/routes_jobs.py:44-45`、`routes_inference.py:21-22,39-40` 等捕获裸 `Exception` 后返回 `HTTPException(400/500, detail=str(e))`。
  - 成功响应与错误响应形状不一致；错误体仅为 `{"detail": "..."}`，无 `trace_id`/`error_code`/`job_id`。
- **为什么重要**：
  - API consumer 无法通过错误响应关联到审计日志；500 响应可能泄露内部异常字符串。
- **审查判断**：
  - 不符合 proposed-planning 中“API response contract”与“融合报错体系”的要求。
- **建议修法**：
  - 增加全局异常处理器，返回统一错误 envelope（含 `error_code`、`trace_id`、`job_id`、`detail`、`links`）。

### R11. 容器化训练未实现真实路径，FastAPI 未容器化

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/adapters/training/sovits_adapter.py:27` 真实模式抛 `NotImplementedError`。
  - 无 `Dockerfile.api`；`src/myvoiceclone/api/app.py` 未在任何容器镜像中交付。
  - `infra/docker/compose.yaml:41` 预处理命令硬编码 `ingest /app/data/raw/sample.wav`；`:68` 训练命令依赖前置 frozen dataset。
  - `Dockerfile.train:6` 注释说可 override base image，但无 `ARG DOCKER_BASE_IMAGE`。
- **为什么重要**：
  - first-test 虽将真实训练 deferred，但容器化训练是基础设施承诺；当前配置无法一键运行真实 GPU 训练或 API 服务。
- **审查判断**：
  - 容器化落地为“配置骨架 + mock smoke”，未形成真实 e2e 交付物。
- **建议修法**：
  - 实现 SoVITS/RVC 真实训练路径或明确 deferred；新增 `Dockerfile.api` 与 compose `api` service；修复 `DOCKER_BASE_IMAGE` 注释与实际行为一致；补充 `shm_size` 与 CUDA 健康检查。

### R12. evidence pack env.json 未捕获解析后的 DB_PATH/ARTIFACT_ROOT

- **严重级别**：`medium`
- **类型**：`observability-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/myvoiceclone/evidence.py:199-218` 的 `env.json` 只记录 `os.getenv` 显式设置的环境变量；若依赖 `configs/local.yaml` 默认值，则 `DB_PATH`/`ARTIFACT_ROOT`/`MODELS_DIR` 不会被写入。
  - 实际 evidence pack `env.json:4` 的 `"env": {}` 为空。
- **为什么重要**：
  - 无法从 evidence pack 还原真实运行环境，调试时难以确认数据落盘位置。
- **审查判断**：
  - evidence 完整性不足。
- **建议修法**：
  - 在 `env.json` 中写入 `resolved_db_path`、`resolved_artifact_root`、`resolved_models_dir` 等解析后配置值。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / closure claim | 审查结论 | 说明 |
|------|------------------------|----------|------|
| S1 | FT1 准入收敛 | done | 命令、env、preprocess payload、empty manifest guard、artifact root resolver 均落地并通过测试。 |
| S2 | FT2 schema 与 observability contract | partial | schema/WAL/busy_timeout/FK、job_events 表结构、audit trace API 已落地；但 train/infer/eval/release 缺少 step-level 事件，adapter_mode 未进入事件流。 |
| S3 | FT3 真实音频预处理 | partial | 适配器合同、manifest lineage、reference selector 完成；真实 FFmpeg/PyAnnote/Demucs/Whisper 未在本机执行；空 transcript 可进入 manifest。 |
| S4 | FT4 真实推理 substrate | partial | XTTS wrapper、license/provenance、no silent fallback 完成；仅支持单一 model_id；reference artifact kind 未校验。 |
| S5 | FT5 真实评估与 release gate | partial | smoke/proxy/manual 分层与 release gate 落地；objective eval 样本 lineage 断裂；真实 objective scorer 仍 deferred。 |
| S6 | FT6 FastAPI e2e surface | partial | upload 立即落 artifact、start 只创建 DB job、status/trace API 存在；但错误响应未结构化、无全局异常处理器、长任务同步执行。 |
| S7 | FT7 live tests 与 capstone | partial | evidence exporter/validator、live marker、gated skip 完成；pre-capstone gate 仅检查文件存在性；真实 capstone 未执行。 |
| S8 | FT8 closure/deferred reconciliation | partial | closure/deferred 台账、final input pack 齐全；但 closure/evidence 锚点 stale，与当前 HEAD 不一致。 |

### 3.1 对齐结论

- **done**: `1`
- **partial**: `7`
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像“核心骨架与默认测试已绿，但数据 lineage、报错体系、API 错误契约、容器化与 evidence 审计链仍未收口”，而不是 `full-close`。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 同时实现 RVC/SoVITS/XTTS 全部真实训练 | 遵守 | first-test 明确只追求一条真实推理闭环；RVC/SoVITS 真实训练 deferred（FTD-17）。 |
| O2 | 完整 ECAPA/CLAP/SBERT embedding 平台 | 遵守 | vec0/embedder 真实维度迁移 deferred（FTD-05）。 |
| O3 | 生产级任务队列与分布式 worker | 部分违反 | FastAPI 未使用 BackgroundTasks，但 `/api/jobs/{job_id}/run` 同步执行长任务，存在超时风险；未引入 broker 符合 scope。 |
| O4 | 完整 OTel 平台化接入 | 遵守 | 仅以 DB events/trace JSON 替代 OTel（FTD-08）。 |
| O5 | 众包 MOS 流程 | 遵守 | 本地 MOS/ABX 录入实现，外部 panel deferred（FTD-09）。 |
| FTD-01 | live capstone 真实执行 | 遵守 | 仅 skipped evidence，状态如实标为 pending-live。 |
| FTD-10 | fake adapter Protocol/ABC 未冻结 | 遵守 | first-test 以 adapter metadata/preflight 与 `MOCK_ADAPTERS` 隔离为主。 |
| FTD-11/12 | live HTTP / capstone 真实执行体 | 遵守 | 已作为 pending-live deferred 登记。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`implementation-complete-awaiting-live-verification with blockers`——默认路径已绿，但数据 lineage、报错体系、API 错误契约、容器化落地与 evidence 审计链存在必须修复的真实 gap，不建议直接进入真实 live capstone。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. 更新全部 closure 文件与 evidence pack 的 git 锚点至当前 HEAD `952fbc5`，并重新生成 evidence pack。
  2. 修复 `run_export_dataset` 对空 transcript segment 的 silent fallback（拒绝写入空 transcript 或增加明确标记）。
  3. 修复 `evaluate_objective_metrics` 中 `eval_samples` 的 lineage 字段（input/output/reference 必须区分）。
- **可以后续跟进的 non-blocking follow-up**：
  1. 为 `train_sovits`、`infer_real`、`eval_first_test` 及单步 preprocess 写入 `write_step_event`。
  2. 限制 real inference 的 reference artifact kind。
  3. 移除 RVC 的 `fake_source_audio.wav` 回退。
  4. 引入统一异常基类、错误码与分类体系；新增 `docs/ops/error-handbook.md`。
  5. 增加 API 全局异常处理器与统一错误 envelope（含 `trace_id`/`error_code`/`job_id`）。
  6. 实现 `Dockerfile.api` 与 compose `api` service；修复训练容器默认命令与 `DOCKER_BASE_IMAGE` 注释一致性。
  7. 增强 evidence pack 的 `env.json`，写入解析后的 `DB_PATH`/`ARTIFACT_ROOT`/`MODELS_DIR`。
- **建议的二次审查方式**：`independent reviewer`（由未参与 R1/R2 的同事复核 blocker 修复）。
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
