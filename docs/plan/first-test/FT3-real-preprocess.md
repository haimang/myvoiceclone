# FT3 Real Preprocess Action Plan

> 服务业务簇: `FT3 · 真实音频预处理与 dataset contract`
> 计划对象: `real audio preprocess, live adapter preflight, dataset manifest contract`
> 类型: `upgrade`
> 作者: `GPT / Codex`
> 时间: `2026-06-13`
> 文件位置: `docs/plan/first-test/FT3-real-preprocess.md`
> 上游前序 / closure:
> - `docs/plan/first-test/FT1-preflight.md`
> - `docs/plan/first-test/FT2-schema-observability.md`
> 下游交接:
> - `docs/plan/first-test/FT4-real-inference.md`
> 关联设计 / 调研文档:
> - `docs/eval/first-test/proposed-planning.md`
> - `docs/eval/first-test/reference-anchor.md`
> 冻结决策来源:
> - `docs/eval/first-test/proposed-planning.md` + `docs/eval/first-test/reference-anchor.md` non-blocking planning baseline
> grounding 来源:
> - `proposed-planning FT3`, `reference-anchor axis B/C/G`
> 关联 reference-anchor:
> - `docs/eval/first-test/reference-anchor.md`
> 文档状态: `draft`

---

## 0. 执行背景与目标

FT3 将 first-test 从 mock/conditional 预处理推进到真实音频 smoke：FFmpeg normalize/probe、PyAnnote diarization、Demucs optional separation、Whisper ASR、非空 dataset manifest 和推理 reference artifact contract。

- **服务业务簇**：`Real audio preprocess / 数据准备`
- **计划对象**：real preprocess pipeline and dataset contract
- **本次计划解决的问题**：
  - 真实 adapter 缺 preflight 与 metadata。
  - 真实预处理失败不可诊断。
  - dataset freeze 与推理 reference 输入缺稳定合同。
- **本次计划的直接产出**：
  - 真实预处理 smoke path。
  - adapter live skip/fail reason。
  - 非空 manifest 与 reference artifact contract。
- **本计划不重新讨论的设计结论**：
  - PyAnnote/Whisper/Demucs/FFmpeg 是 FT3 的真实预处理参考栈（来源：`docs/eval/first-test/reference-anchor.md:63-72`）。
  - Demucs 只作为 separation smoke，不等同 speech enhancement 质量保证（来源：`docs/eval/first-test/reference-anchor.md:67-72`）。

---

## 1. 执行综述

### 1.1 总体执行方式

先实现各 adapter 的 preflight/metadata，再接 pipeline artifact/status，最后用 dataset freeze 和 reference selector 收口给 FT4。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | Audio adapter preflight | M | FFmpeg/PyAnnote/Demucs/Whisper 探针和 metadata | FT1/FT2 |
| Phase 2 | Pipeline integration | M | 真实 preprocess 产物写 DB/artifact/event | Phase 1 |
| Phase 3 | Dataset/reference contract | M | 非空 manifest 与 reference artifact selector | Phase 2 |

### 1.3 Phase 说明

1. **Phase 1 — Audio adapter preflight**
   - **核心目标**：每个外部依赖能明确 available/unavailable/skip reason。
   - **为什么先做**：live 缺依赖不能假绿。
2. **Phase 2 — Pipeline integration**
   - **核心目标**：真实音频经过 ingest→diarize→slice→clean→transcribe→score。
   - **为什么放在这里**：FT4 需要真实 reference artifact。
3. **Phase 3 — Dataset/reference contract**
   - **核心目标**：manifest 非空，artifact lineage 完整，reference selector 可用。
   - **为什么放在这里**：这是 FT4 输入合同。

### 1.4 执行策略说明

- **执行顺序原则**：adapter preflight → pipeline metadata → dataset/reference contract。
- **风险控制原则**：live tests gated；无 token/model 只 skip with reason。
- **测试推进原则**：unit with fake subprocess + live smoke optional。
- **文档同步原则**：记录 live dependency list 与 run instructions。
- **回滚 / 降级原则**：某 live adapter unavailable 时保留 unit contract，不假称 real pass。

### 1.5 影响结构图

```text
FT3 Real Preprocess
├── adapters
│   ├── ffmpeg / pyannote / demucs / whisper
├── pipelines
│   ├── ingest / diarize / slice / clean / transcribe / score
├── dataset
│   ├── export_dataset.py
│   └── artifact manifest
└── tests
    ├── unit/adapters
    ├── unit/pipelines
    └── live/skip
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

- **[S1]** FFmpeg probe/normalize/loudness/silence smoke metadata.
- **[S2]** PyAnnote token/terms/cache preflight.
- **[S3]** Demucs optional vocal extraction path with clear caveat.
- **[S4]** Whisper ASR metadata and transcript artifact.
- **[S5]** dataset manifest non-empty and reference audio contract.

### 2.2 Out-of-Scope

- **[O1]** True speech quality evaluation; FT5 owns it.
- **[O2]** Real inference; FT4 owns it.
- **[O3]** Full source-separation quality claims.
- **[O4]** Training dataset quality tuning beyond smoke thresholds.

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| PyAnnote live diarization | in-scope gated | 真实 speaker turns needed | token/model unavailable |
| Demucs quality claim | out-of-scope | source separation not speech quality | FT5 chooses metric |
| reference selector | in-scope | FT4 input contract | FT4 substrate changes |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| FT3-P1-01 | Phase 1 | FFmpeg metadata contract | update | `src/myvoiceclone/adapters/audio/ffmpeg.py`, `src/myvoiceclone/pipelines/ingest.py`, `src/myvoiceclone/pipelines/slice.py` | normalize/probe metadata 可查 | FT3-T01 | medium |
| FT3-P1-02 | Phase 1 | PyAnnote preflight | update | `src/myvoiceclone/adapters/diarization/pyannote_adapter.py`, `src/myvoiceclone/pipelines/diarize.py` | token/cache unavailable 可 skip/fail | FT3-T02 | medium |
| FT3-P1-03 | Phase 1 | Demucs optional path | update | `src/myvoiceclone/adapters/separation/demucs_adapter.py`, `src/myvoiceclone/pipelines/clean.py` | separation smoke 有 metadata | FT3-T03 | medium |
| FT3-P1-04 | Phase 1 | Whisper ASR contract | update | `src/myvoiceclone/adapters/asr/whisper_adapter.py`, `src/myvoiceclone/pipelines/transcribe.py` | transcript artifact + model metadata | FT3-T04 | medium |
| FT3-P2-01 | Phase 2 | preprocess all integration | update | `src/myvoiceclone/jobs/runner.py:138-163` | 真实 preprocess 写 step evidence | FT3-T05 | high |
| FT3-P3-01 | Phase 3 | dataset manifest contract | update | `src/myvoiceclone/pipelines/export_dataset.py:105-147` | manifest 非空且 lineage 完整 | FT3-T06 | medium |
| FT3-P3-02 | Phase 3 | reference artifact selector | add | `src/myvoiceclone/pipelines/reference_select.py` | FT4 可选择 reference audio | FT3-T07 | medium |

### 3.1 Proposed-ID Crosswalk

| proposed 工作项 | AP 执行项 | proposed 测试项 | AP 测试项 |
|----------------|-----------|----------------|-----------|
| `FT3.1` | FT3-P1-01 | `T-FT3.1` | FT3-T01 |
| `FT3.2` | FT3-P1-02 | `T-FT3.2` | FT3-T02 |
| `FT3.3` | FT3-P1-03 | `T-FT3.3` | FT3-T03 |
| `FT3.4` | FT3-P1-04 | `T-FT3.4` | FT3-T04 |
| `FT3.5` | FT3-P2-01 | `T-FT3.5` | FT3-T05 |
| `FT3.6` | FT3-P3-01 / FT3-P3-02 | `T-FT3.6` | FT3-T06 / FT3-T07 |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — Audio adapter preflight

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT3-P1-01 | FFmpeg metadata contract | 记录 input format、duration、sample rate、loudnorm/silence smoke metrics；subprocess 失败写 reason。 | `src/myvoiceclone/adapters/audio/ffmpeg.py`, `src/myvoiceclone/pipelines/ingest.py` | audio probe 可诊断 | FT3-T01 | metadata pass |
| FT3-P1-02 | PyAnnote preflight | 校验 token/terms/cache；无 token live skip；有 token 可跑短音频 smoke。 | `src/myvoiceclone/adapters/diarization/pyannote_adapter.py`, `src/myvoiceclone/pipelines/diarize.py` | diarization availability 清晰 | FT3-T02 | skip/live pass |
| FT3-P1-03 | Demucs optional path | 标记 separation smoke；失败写 stderr summary；不做 quality claim。 | `src/myvoiceclone/adapters/separation/demucs_adapter.py`, `src/myvoiceclone/pipelines/clean.py` | clean step 可观察 | FT3-T03 | failure metadata pass |
| FT3-P1-04 | Whisper ASR contract | 记录 model name/device/duration；写 transcript artifact/segment transcript。 | `src/myvoiceclone/adapters/asr/whisper_adapter.py`, `src/myvoiceclone/pipelines/transcribe.py` | ASR artifact 可追 | FT3-T04 | ASR contract pass |

### 4.2 Phase 2 — Pipeline integration

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT3-P2-01 | preprocess all integration | a) 使用 FT2 event contract 包裹 6 步；b) 每步产物写 artifact refs；c) partial failure 汇总；d) real mode 不 fallback mock。 | `src/myvoiceclone/jobs/runner.py:138-163`, `src/myvoiceclone/pipelines/*` | 真实预处理链可 smoke | FT3-T05 | integration pass |

### 4.3 Phase 3 — Dataset/reference contract

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------|----------|----------|----------|
| FT3-P3-01 | dataset manifest contract | 当前 manifest 只写 `id/audio_path/transcript/split/speaker_id/duration`；目标 schema 应扩为 `segment_id/cleaned_artifact_id/uri/sha256/duration_sec/split`，且 rows 必须来自 cleaned/transcribed segment。 | `src/myvoiceclone/pipelines/export_dataset.py:105-147` | non-empty lineage manifest | FT3-T06 | manifest test pass |
| FT3-P3-02 | reference artifact selector | 新增 selector 选取可追溯 reference audio，拒绝无 cleaned artifact/短时长/无 transcript 项。 | `src/myvoiceclone/pipelines/reference_select.py` | FT4 输入稳定 | FT3-T07 | selector test pass |

---

## 5. Phase 详情

### 5.1 Phase 1 — Audio adapter preflight

- **目标**：真实依赖状态机器可读。
- **新增文件**：无，必要时新增 adapter utility。
- **修改文件**：adapters + pipelines。
- **具体功能预期**：
  1. FFmpeg 失败时错误包含 command/tool/version。
  2. PyAnnote 无 token 时 live test skip，不 failed 假绿。
  3. Demucs 不可用时 clean step 可诊断。
  4. Whisper 模型名和 device 写入 metadata。
  5. 所有 adapter metadata 去 secret。
- **测试项**：FT3-T01..FT3-T04
- **收口标准**：adapter preflight tests 通过。
- **风险提醒**：不要把 external stderr 全量写 DB。

### 5.2 Phase 2 — Pipeline integration

- **目标**：真实短音频可从 preprocess_all 走到 scored segments。
- **修改文件**：`src/myvoiceclone/jobs/runner.py`, `src/myvoiceclone/pipelines/*`
- **具体功能预期**：
  1. ingest 生成 raw/staging artifacts。
  2. diarize 生成非空 speaker turns 或明确 failed reason。
  3. clean/transcribe partial failure 汇总。
  4. score 仍可 mock，但标明 source。
  5. job_events 反映每一步。
- **测试项**：FT3-T05
- **收口标准**：preprocess smoke integration 通过。
- **风险提醒**：真实 live 可能慢，unit 与 live 必须分层。

### 5.3 Phase 3 — Dataset/reference contract

- **目标**：FT4 能安全消费 FT3 产物。
- **新增文件**：`src/myvoiceclone/pipelines/reference_select.py`, tests。
- **具体功能预期**：
  1. manifest 不为空。
  2. 每行有 artifact lineage。
  3. split leak guard 仍工作。
  4. reference selector 过滤不合格 segments。
  5. selector 输出 artifact id/path/metadata。
- **测试项**：FT3-T06 / FT3-T07
- **收口标准**：manifest 和 selector tests 通过。
- **风险提醒**：selector 不应依赖 absolute repo path。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Real preprocess uses FFmpeg/PyAnnote/Demucs/Whisper | `docs/eval/first-test/reference-anchor.md:63-72` | 定义 adapter work | 回 reference |
| Live tests gated | `docs/eval/first-test/reference-anchor.md:193-195` | 缺依赖 skip with reason | 回 FT7 policy |
| FT3 proposed baseline | `docs/eval/first-test/proposed-planning.md:196-218` | 定义 work/test | 回 proposed |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-FT3-1 | `src/myvoiceclone/jobs/runner.py:138-163` | preprocess sequence | FT3-P2-01 | ✅ 复用 | 6-step chain |
| A-FT3-2 | `src/myvoiceclone/pipelines/export_dataset.py:105-147` | manifest creation | FT3-P3-01 | ♻️ 重 substrate | 当前字段不足，需扩 lineage rows |
| A-FT3-3 | `src/myvoiceclone/pipelines/reference_select.py` | new selector | FT3-P3-02 | 🆕 净新 | FT4 input |
| A-FT3-4 | `tests/unit/adapters/test_ffmpeg_adapter.py` | adapter tests | FT3-T01 | 🔱 fork | existing test family |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 |
|----|--------------|--------|
| ⛔1 | Demucs output = speech quality pass | reference-anchor 明确不等同 speech enhancement |
| ⛔2 | 无 token 时 live test pass | 必须 skip with reason |
| ⛔3 | manifest 含无 artifact lineage rows | FT4 无法追溯输入 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-test/reference-anchor.md`。
- **威胁模型锚**：真实音频路径、HF token、model cache、stderr 是信任边界；不得把 token/stderr secret 写 DB。锚定 `TR-5/TR-6/TR-7`。

---

## 8. 测试台账

### 8.1 测试清单

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据 |
|---------|--------|------|----|------|------|-----------|
| FT3-T01 | FFmpeg metadata | 短途 | unit/adapter | 🔱 fork `tests/unit/adapters/test_ffmpeg_adapter.py` | FT3-P1-01 | commit + pytest + run-time |
| FT3-T02 | PyAnnote preflight/skip | spike | live/skip | 🔱 fork `tests/unit/adapters/test_pyannote_adapter.py` | FT3-P1-02 | commit + pytest -m live + run-time |
| FT3-T03 | Demucs failure metadata | 短途 | unit/adapter | 🔱 fork `tests/unit/adapters/test_demucs_adapter.py` | FT3-P1-03 | commit + pytest + run-time |
| FT3-T04 | Whisper metadata | 短途/live | unit/adapter | 🔱 fork `tests/unit/adapters/test_whisper_adapter.py` | FT3-P1-04 | commit + pytest + run-time |
| FT3-T05 | preprocess_all integration | spike | integration | 🆕 新增 `tests/integration/test_real_preprocess_smoke.py` | FT3-P2-01 | commit + pytest + run-time |
| FT3-T06 | non-empty manifest lineage | 短途 | unit/pipeline | 🔱 fork `tests/unit/pipelines/test_export_dataset.py` | FT3-P3-01 | commit + pytest + run-time |
| FT3-T07 | reference selector | 短途 | unit/pipeline | 🆕 新增 `tests/unit/pipelines/test_reference_select.py` | FT3-P3-02 | commit + pytest + run-time |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/adapters/*` | 🔱 fork | 增加 metadata/preflight 断言 | 已存在 |
| `tests/unit/pipelines/test_export_dataset.py` | 🔱 fork | 加 lineage/non-empty 断言 | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `pytest tests/unit/adapters tests/unit/pipelines -q` | unit | 每 PR |
| spike | `pytest -m live tests/integration/test_real_preprocess_smoke.py -q` | live/integration | Phase 收口 |

### 8.4 测试缺口

- 不验证合成语音质量 → FT5。
- 不验证真实 inference output → FT4。

### 8.5 测试保真

- live unavailable 必须 skip with reason。
- adapter metadata 不得含 token。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| HF token/model gated | PyAnnote 访问受限 | high | preflight + skip reason |
| Demucs slow/heavy | CPU 环境慢 | medium | optional live marker |
| Whisper model cache | 下载失败 | medium | cache preflight |

### 9.2 约束与前提

- **技术前提**：FT1 entry 和 FT2 event contract 已完成。
- **运行时前提**：真实短音频、外部 tools、可写 artifact root。
- **组织协作前提**：source provenance 可记录。
- **上线 / 合并前提**：unit 全 PASS，live 缺依赖有 skip reason。

### 9.3 文档同步要求

- first-test run instructions。
- dependency probe notes。
- dataset/reference contract note。

### 9.4 完成后的预期状态

1. 真实短音频可跑 preprocess smoke。
2. 每步有 adapter metadata 与 job events。
3. dataset manifest 非空且可追溯。
4. FT4 有稳定 reference audio 输入。

---

## 10. 收口

### 10.1 收口硬闸

1. Adapter metadata/preflight tests PASS（FT3-T01..04）。
2. preprocess integration PASS 或 live skip reason 完整（FT3-T05）。
3. manifest/reference contract PASS（FT3-T06..07）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| real preprocess adapter metadata | FT3-P1-01..04 | FT3-T01..04 | commit + pytest + run-time | 未观察 |
| preprocess integration | FT3-P2-01 | FT3-T05 | commit + pytest + run-time | 未观察 |
| dataset/reference contract | FT3-P3-01..02 | FT3-T06..07 | commit + pytest + run-time | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 真实预处理 smoke 可诊断 |
| 测试 | §8 全 PASS/skip reason |
| 文档 | 依赖与 reference contract 已记录 |
| 风险收敛 | 无 silent fallback |
| 可交付性 | 可进入 FT4 |

### 10.4 NOT-成功识别

若真实 adapter 失败只表现为 generic exception、无 job_event/metadata，或 manifest 可空成功，不得标 `executed`。
