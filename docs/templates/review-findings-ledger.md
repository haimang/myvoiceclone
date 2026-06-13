# Nano-Agent 跨 Reviewer 审查发现统一台账模板（review-findings-ledger）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。在收齐**全部** agent 的审查文件后，由实现者把多份独立审查平铺、合并、逐条对当前真实代码独立复核，形成单一权威台账，并给出初步修复方案。
> **为什么独立成文**：过去的做法是把这份「统一 + verified 台账」append 在某位 reviewer（通常 opus）审查文件的底部（如 `…-reviewed-by-opus.md §6/§A`）。现改为**独立文件 track**——一个标的、一轮合并 = 一份 ledger，互不污染各 reviewer 原件，便于跨轮检索与状态推进。
> **何时用**：≥2 份独立 reviewer 审查制品需要合并去重 + 独立复核 + 给出修复路线时。**何时不用**：单一 reviewer 评审 → 直接 `code-review`；实现者只对单份审查逐项回应 → `code-review-respond`（append 到那份审查 §6）；bug 根因诊断 → `bug-analysis-report`。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `{REVIEW_TARGET}`（被审的实现 / 阶段，如 `RWX20–RWX22 (bug-fixes-06)`）|
> | **审查阶段 / 轮次** | `第 1 轮合并 \| 2nd-pass \| 3rd-pass \| 4th-pass merge \| {OTHER}` |
> | **合并 / 核查人（实现者）** | `{SYNTHESIZER}` |
> | **合并日期** | `{DATE}` |
> | **文档状态** | `triaged \| fixing \| resolved \| closed` |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `{PATH}-reviewed-by-{REVIEWER_A}.md` — `{该方最高严重级别 / finding 数}`
> - `{PATH}-reviewed-by-{REVIEWER_B}.md` — `{…}`
> - `{PATH}-reviewed-by-{REVIEWER_C}.md` — `{…}`
> - `{本人自审初稿（若实现者=审查者同体）}` — `{…}`
>
> **对照真相（逐条 re-verify 时回看的源）**：
> - `{DESIGN_OR_ACTION_PLAN_OR_QNA}`
> - `{CODE_ROOTS}`：`workers/**/src`、`clients/web/src`、`migrations`、`test`（只读真实代码，不采信 docs/.tmp）
> - `{CLOSURE_OR_PRIOR_LEDGER}`（多轮场景的上一轮 ledger）
>
> **命名约定**：实例文件落在被审实现的 review 目录（如 `clients/web/docs/code-review/web-v90/`），名为 `{TARGET}-findings-ledger.md`；多轮用 `{TARGET}-findings-ledger-2nd-pass.md` 或在同文件追加 `## 第 N 轮` 段。

---

## 0. 合并方法与核查纪律

> **本节只立规矩，不写结论。** 说明合并了哪几份、用什么纪律复核。

- **合并范围**：`{N}` 份独立审查（见元信息「审查来源锚定」）全部 finding 平铺。
- **核查纪律（硬）**：
  1. **reviewer 的结论仅作线索**。每条判 `valid` 的项，均由实现者**亲自 grep / Read 当前真实代码**坐实，关键证据带 `file:line`。
  2. 与任一方（**含本人自审初稿**）冲突，**以实测为准**；自审初稿被推翻处必须在 §4.2 显式 self-correct。
  3. **已纠正的跨-reviewer 误报**必须在 §4.3 带证据列出，不得静默吞掉。
  4. 严重级别**取多方最严**；同一问题被多方提及合并为一条统一编号。
- **统一编号前缀**：`V`（verified）或 `UF`（unified-finding）——`{选定前缀}`，全文一致。

### 0.1 复核判定（verdict）图例

| verdict | 含义 |
|---------|------|
| `valid` | 属实，需处理 |
| `valid-edge` | 属实但仅边界/条件态触发（happy-path 已绿）|
| `valid-conditional` | 属实但本环境不复现；按防御性处理 |
| `valid-owner-gated` | 属实但归 owner 动作（sign-off / deploy / 复测）|
| `valid-pre-existing` | 属实但 base 即存在，非本阶段引入 |
| `valid-by-design` | 现象属实但为既定设计（如 session-scope）|
| `valid(子项 overstated)` | 主项真，个别子断言过度（须指明哪句过度）|
| `stale-rejected` | 不成立：reviewer 读了陈旧/已删的代码或误解 |
| `INVALID` | 不成立：凭空指控，无代码依据 |

### 0.2 处置（disposition）图例

| 处置 | 含义 |
|------|------|
| `fix` | 本轮修复（必配 falsifiable 测试或被既有/新增测试覆盖）|
| `partial-fix` | 部分修复 + 余项 defer（须写清切分）|
| `defer-with-rationale` | 有理由后延（带 reopen 触发器 + 承接位置）|
| `deferred-by-owner` | 归 owner session（sign-off / deploy / 复测）|
| `acknowledge` | 已修 / 无需改动（仅记录）|
| `stale-rejected` | 带证据驳回，不改代码 |

### 0.3 严重级别图例

`critical | high | medium | low | info`（取多方最严；`(nb)` = 非 blocker，`(子项)` = 仅子断言达该级）。

### 0.4 Finding 三类归属（class）图例 ★

> **目的**：对每条**经复核成立（`valid*`）且代表未了结缺口**的 finding，按它**相对本阶段计划的归属**强制三选一。这是与 `verdict`（真不真）/ `disposition`（怎么处理）**正交的问责轴**——它回答「这个缺口归谁、本阶段是否欠了账」。`stale-rejected` / `INVALID` / 已修的 `acknowledge` 不进三类，标 `n/a`。

| 归属类 | 标记 | 精确含义 | 本阶段义务 | 典型 disposition |
|--------|------|----------|------------|------------------|
| **真 deferred** | `[true-deferred]` | 该缺口**本阶段从未承诺交付**，合法属于后续阶段 / owner session 才更新或修复。含：by-design 的未来发散、owner-gated 动作（sign-off / deploy / 复测）、需 migration 而本阶段冻结 migration 的项、未在本阶段 scope 内的 pre-existing 缺陷。 | **登记承接**：带 reopen 触发器 + 承接位置（§5.4）；本阶段不修是**诚实**的。 | `defer-with-rationale` / `deferred-by-owner` |
| **真 bug** | `[true-bug]` | 该缺口是**本阶段引入的回归**，**或**本阶段计划 / 职责范围内**该修却漏修 / 修错**的内容。**本阶段欠的账。** | **必须本阶段修**（默认 `fix`）。若确实修不动，必须**显式升级为 blocker 交 owner 裁决**，**严禁**降级成 `[true-deferred]` 规避（见硬规则）。 | `fix` / 极少数 `partial-fix` |
| **部分交付** | `[partial-delivery]` | 该 item **本阶段已规划并已动手**，但**未完成 / 仅完成部分**。承诺了、做了一半。 | **本阶段补齐**（默认 `fix`）；若本轮只能完成部分，**剩余切片必须显式切分**并作为 `[true-deferred]` 子项登记 §5.4 带触发器，不许笼统留白。 | `fix` / `partial-fix` |

**三类判定决策树**（agent 逐条走）：

```text
这条 finding 代表的缺口，相对本阶段计划归谁？
├─ 复核不成立 / 已修 ───────────────────────────▶ n/a（不进三类）
├─ 本阶段从未承诺、合法属未来阶段或 owner ───────▶ [true-deferred]
├─ 本阶段已规划、动了手但没做完 ────────────────▶ [partial-delivery]
└─ 本阶段引入的回归 / 计划内该修却漏修或修错 ────▶ [true-bug]
```

**硬规则（诚实闸 · 反 no-free-defer 规避）**：
1. **`[true-bug]` 不得被改写成 `[true-deferred]`** 来回避本阶段修复。本阶段引入或本阶段欠的账，要么修、要么显式升级 blocker 由 owner 裁决，二者必居其一。
2. **`valid-pre-existing` 不自动等于 `[true-deferred]`**：base 即存在、但**本阶段计划承诺要修**它 → 仍是 `[true-bug]`；本阶段未承诺修 → `[true-deferred]`。
3. **`[partial-delivery]` 的未完成切片**必须落 §5.4 承接表并标「来源 = 某 partial item 的剩余切片」，使「做了一半」不被静默当成「做完了」。
4. 三类计数必须在 §1 TL;DR 与 §4.1-A 双向对齐（同一组 V# 不重复计、不漏计）。

---

## 1. 一句话裁定 + 合并统计（TL;DR）

> 先给结论，再给数字。

- **一句话裁定**：`{ONE_LINE_VERDICT}`（如：`5 方第 1 轮共 26 条合并项，18 fix / 5 defer / 1 stale-rejected / 1 ack；最关键缺口=…`）。
- **合并后统一 finding 数**：`{TOTAL}`（来自 `{RAW_COUNT}` 条原始 finding 去重）。
- **按 verdict**：`valid {N}` · `valid-* {N}` · `stale-rejected {N}` · `INVALID {N}`。
- **按三类归属 ★**：`[true-bug] {N}（{V_IDS}）` · `[partial-delivery] {N}（{V_IDS}）` · `[true-deferred] {N}（{V_IDS}）` · `n/a {N}`。
- **按处置**：`fix {N}` · `partial-fix {N}` · `defer {N}` · `owner-gated {N}` · `ack {N}`。
- **blocker 数**：`{N}`（编号：`{V_IDS}`；含所有修不动而升级的 `[true-bug]`）。
- **净增承重盲区（peer 相对实现者自审初稿净增的最高价值 finding）**：`{1-3 句}`（详见 §4.2）。

---

## 2. 合并映射（reviewer finding → 统一编号）

> 把每位 reviewer 的原始编号映射到统一 `V#`。一条统一项可由多方贡献。

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| `{REVIEWER_A}-R1` / `{REVIEWER_B}-R8` | `V1` | `{ISSUE}` |
| `{REVIEWER_B}-R2` / `{自审}-R6` | `V2` | `{ISSUE}` |
| `{REVIEWER_C}-R3` | `V3` | `{ISSUE}` |

### 2.2 宽对照表（可选 · 多方密集重叠时用）

> 当 5 方对同一批 finding 高度重叠、需要一眼看出「谁抓到了谁漏了」时，用这张 cross-tab；否则省略。

| 统一编号 | 合并后的问题 | `{A}` | `{B}` | `{C}` | `{D}` | `{自审}` |
|----------|--------------|-------|-------|-------|-------|----------|
| `V1` | `{ISSUE}` | `R1` | `R8` | `R1` | `R2` | `—` |
| `V2` | `{ISSUE}` | `—` | `R2` | `R5` | `—` | `R6` |

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

> **本节是整份文档的灵魂。** 每条统一项给出：严重级别（取最严）、来源、复核判定、**亲自坐实的关键证据（file:line）**、初步处置/修法。
> 复核判定**不得**只复述 reviewer 的话——必须有实现者本人 grep/Read 的证据。

### 3.1 台账主表

| V# | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line / 命令）| 初步处置（→ §5 细化）|
|----|------|------|------|----------|--------|--------------------------------------|----------------------|
| V1 | `{TITLE}` | `high` | `{A}/{B}` | `valid` | `[true-bug]` | `{file:line + 一句证据}` | `fix` |
| V2 | `{TITLE}` | `high` | `{B}/{自审}` | `valid` | `[partial-delivery]` | `{file:line}` | `fix` |
| V3 | `{TITLE}` | `critical` | `{B}` | `valid-owner-gated` | `[true-deferred]` | `{file:line}` | `defer-by-owner` |
| V4 | `{TITLE}` | `medium` | `多方` | `valid` | `[true-bug]` | `见 §3.2 子表` | `fix` |
| V5 | `{TITLE}` | `high` | `{C}` | `stale-rejected` | `n/a` | `{file:line 反证}` | `stale-rejected` |

*（按需继续扩展 V6 / V7 / …）*

### 3.2 簇子表（可选 · 多文件同类簇逐条展开）

> 当某条统一项（如「docs 漂移簇」「多端点同类违规」）涉及很多文件时，主表写一行 `见 §3.2 子表`，在此逐文件/逐位点展开。

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `{file:line}` | `{DRIFT_FACT}` | `valid` | `{FIX}` |
| `{file:line}` | `{DRIFT_FACT}` | `valid` | `{FIX}` |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图 · ★主视图）** — 每条 valid 缺口必属其一；`n/a` 为非缺口（rejected / 已修）：

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | `{N}` | `{V_IDS}` | §5.2 本阶段**必修**（漏修则升 blocker，不许 defer）|
| `[partial-delivery]` | `{N}` | `{V_IDS}` | §5.2 补齐 + 剩余切片登记 §5.4 |
| `[true-deferred]` | `{N}` | `{V_IDS}` | §5.4 承接（带 reopen 触发器）|
| `n/a`（rejected / 已修）| `{N}` | `{V_IDS}` | 不进三类 |

> 三类合计（不含 `n/a`）= 全部 valid 缺口数，须与 §1 TL;DR「按三类归属」一致。

**B. 按处置（disposition 视图）**：

- **`fix`（本会话修）**：`{V_IDS}` = **`{N}` 项**
- **`partial-fix`**：`{V_IDS}` = `{N}`
- **`defer-with-rationale`（登记承接）**：`{V_IDS}` = `{N}`
- **`deferred-by-owner`**：`{V_IDS}` = `{N}`
- **`stale-rejected`（带证据驳回）**：`{V_IDS}` = `{N}`
- **`acknowledge`（已修/无操作）**：`{V_IDS}` = `{N}`

### 4.2 净增承重盲区 + 与自审初稿的差异（self-correction）

> **仅当实现者=审查者同体时必填。** 老实写：哪些是同事抓到、而本人 §0–§5 自审初稿漏报或误判的——这是多 reviewer 制度的最高价值产物。

- **净增盲区（peer 相对本人净增的最高价值 finding）**：
  - `{V#}`（`{某 reviewer}` 独家）：`{为什么本人漏了 + 现已采纳}`
- **本人自审初稿被推翻 / 修正处**：
  - `{初稿断言}` → **实测纠正**：`{file:line 证据}` → `{现判定}`

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证（file:line）| 结论 |
|----|--------|----------|-------------------|------|
| `{V#}` | `{REVIEWER}` | `{CLAIM}` | `{COUNTER_EVIDENCE}` | `stale-rejected \| INVALID` |

---

## 5. 初步修复方案（preliminary fix plan）

> 本节是台账的**前瞻产物**：在动手前先排定修法、目标文件、falsification 手段、依赖与批次。落地后由 §6 回填实际结果。

### 5.1 修复策略

> 一段话给出优先级与原则。典型排序：**安全 / 正确性 > 测试缺口补真 > 治理收口 > docs 漂移同步**；每条 code fix 的断言强度**只增不减**（零放水）。
>
> **三类 → 义务映射**：`[true-bug]` 与 `[partial-delivery]` 默认进**本轮** §5.2 修复计划（`[true-bug]` 漏修须升 blocker，绝不 defer）；`[true-deferred]` 进 §5.4 承接登记；`[partial-delivery]` 本轮不补的剩余切片须作为 `[true-deferred]` 子项落 §5.4。

`{STRATEGY_PARAGRAPH}`

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证（修前应 RED）| 需 migration / owner-gate? | 依赖 / 批次 |
|----|----------|----------|-------------------------------|----------------------------|-------------|
| V1 | `{FIX_APPROACH}` | `{FILES}` | `{TEST_OR_CMD}` | `no` | `批次 1` |
| V2 | `{FIX_APPROACH}` | `{FILES}` | `{TEST_OR_CMD}` | `no` | `批次 1` |
| V4 | `{FIX_APPROACH}` | `{见 §3.2}` | `docs:check 复绿` | `no` | `批次 2` |
| V7 | （defer）| `(doc 登记)` | `—` | `migration + owner deploy` | `承接` |

### 5.3 批次 / 依赖（可选）

> 仅当 finding 之间有依赖边或需分波时填。

- **批次 1（{主题}）**：`{V_IDS}` — `{为何先做}`
- **批次 2（{主题}）**：`{V_IDS}` — `{依赖批次 1 的什么}`

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

> 每条后延项必须带 **reopen 触发器** 与 **承接位置**，不许裸 defer。**本表收录两类**：全部 `[true-deferred]`，以及 `[partial-delivery]` 本轮未补齐的剩余切片（标来源）。**`[true-bug]` 不得出现在此表**——它要么本轮修、要么升 blocker（§6.2 对账）。

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置（doc / phase / charter / issue）|
|----|--------------|------|----------|----------------|-------------------------------------------|
| `{V#}` | `[true-deferred]` | `defer-with-rationale` | `{RATIONALE}` | `{TRIGGER}` | `{HANDOFF}` |
| `{V#}` | `[true-deferred]` | `deferred-by-owner` | `{owner 动作}` | `{owner session}` | `{HANDOFF}` |
| `{V#}.r` | `[partial-delivery] 剩余切片` | `defer-with-rationale` | `{本轮已完成 X，剩余 Y 未完成}` | `{TRIGGER}` | `{HANDOFF}` |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> **规则**（沿用 `docs/templates/code-review-respond.md` 纪律）：
> 1. 本节只 append，**不改写 §0–§5**（合并与初步方案一旦写定即冻结，纠正走 self-correction 段或新轮次）。
> 2. 逐条按统一 `V#` 对应，禁止「修了一些」式模糊回应。
> 3. 必须写明：哪些修了、怎么修、改了哪些文件、跑了什么验证。
> 4. `fixed` 不得停留在自评——补「独立复核状态」。
> 5. 多轮回填保留历史，在后面追加 `## 6B / 6C` 或 dated section。

### 6.1 逐项处置结果表

| V# | 处理结果 | 处理方式 | 修改文件 | 独立复核状态 |
|----|----------|----------|----------|--------------|
| V1 | `fixed \| partially-fixed \| deferred-with-rationale \| deferred-by-owner \| stale-rejected \| acknowledged \| blocked` | `{HOW}` | `{FILES}` | `independently-verified \| self-claimed-only \| stale-rejected-by-code \| deferred-by-owner/charter` |

### 6.2 Blocker / Follow-up 状态汇总

| 分类 | 数量 | 编号 | 说明 |
|------|------|------|------|
| 已完全修复 | `{N}` | `{V_IDS}` | `{DETAIL}` |
| 部分修复，需二审 | `{N}` | `{V_IDS}` | `{DETAIL}` |
| 有理由 deferred | `{N}` | `{V_IDS}` | `{HANDOFF}` |
| 拒绝 / stale-rejected | `{N}` | `{V_IDS}` | `{WHY}` |
| 仍 blocked | `{N}` | `{V_IDS}` | `{BLOCKER}` |
| acknowledge（无需改）| `{N}` | `{V_IDS}` | `{WHY}` |

> **三类对账（诚实闸 · 必填）**：本表最终结果须与 §4.1-A 三类对齐——
> - 所有 `[true-bug]` 应落「已完全修复」或「仍 blocked（已升级 owner）」，**不得**落「有理由 deferred」；
> - 所有 `[partial-delivery]` 应落「已完全修复」或「部分修复」，且剩余切片在 §5.4 有承接；
> - 出现任何 `[true-bug] → deferred` 的迁移，必须在此**显式说明缘由并交 owner 裁决**，不许静默改类。

### 6.3 变更文件清单

> 按 产品代码 / 测试 / 治理·runner / docs 分组，每条标对应 `V#`。

- **产品代码（`{N}`）**：`{FILE}` — `{V#}（why）`
- **测试（`{N}`）**：`{FILE}` — `{V#}`
- **docs（`{N}`）**：`{FILE}` — `{V#}`

### 6.4 验证结果

> 只写与本台账 findings 直接相关的验证；命令失败必须保留失败摘要与当前判断，不要写成 success-shaped fallback。

| 验证项 | 命令 / 证据 | 结果 | 覆盖的 V# |
|--------|-------------|------|-----------|
| `{VALIDATION}` | `{COMMAND_OR_EVIDENCE}` | `pass \| fail \| skipped-with-rationale` | `{V_IDS}` |

```text
{TEST_OR_BUILD_OUTPUT_SUMMARY}
```

### 6.5 残留与下一轮 entry

- **本轮自评状态**：`ready-for-rereview \| partially-closed \| blocked`
- **是否请求二次审查**：`yes \| no`（范围：`all \| only V{N} \| validation only`）
- **承接到下一轮 / charter / owner session 的项**：`{V_IDS → HANDOFF}`

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `{DATE}` | `{SYNTHESIZER}` | 初次合并：`{N}` 方 `{RAW}` finding → `{TOTAL}` 统一项；triaged |
| `v0.2` | `{DATE}` | `{SYNTHESIZER}` | §6 回填执行结果；状态 → `resolved \| closed` |
