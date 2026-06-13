# Nano-Agent Eval 模板 · feasibility-study

> **模板类型**：`eval / feasibility-study`
> **一句话用途**：在 charter/design 提交前，对**单个关键决策**做 go/no-go 探针——"这条路走得通吗？approach Y 可行吗？"，给一个 token 化结论。
> **何时用**：要拍板一个会牵动下游一整条 design/action-plan 的技术选型/前提（如 `wrangler dev vs preview deploy`、`.mjs→.ts 迁移可行性`、`抽 type-only 包是否可行`）。
> **何时不用**：① 不 gate 具体决策、只是泛泛找缺口 → 用 `eval-gap-study.md`；② 提案整个阶段范围 → 用 `eval-general-purpose.md`。
>
> **使用纪律（共有脊 · 所有 eval 模板一致）**：
> 1. 本文是 **eval**，**冻结零决策**——它**输出 go/no-go 证据**喂给 owner，但拍板与冻结仍由 charter / `qna.md` 完成。
> 2. **诚实红线**：若实际未真跑测量，**必须在 §3 显式声明"未运行 / 静态分析"**，不得把"看起来可行"写成"已验证可行"。
> 3. 头部 / 性质声明 / TL;DR / 输入锚定 / 修订历史为**共有脊**，跨 eval 模板一致。

---

# `{FEASIBILITY_TITLE}`

> **对象**：`{WHAT_IS_BEING_DE-RISKED}`
> **日期**：`{DATE}`
> **作者**：`{AUTHOR}`（panel：`{PANEL_OR_NONE}`）
> **文档性质**：`eval / feasibility-study`（本文输出 go/no-go 证据，不冻结决策）
> **文档状态**：`draft | reviewed | superseded`
> **Decision affected（必填）**：`{QNN_OR_CHARTER_DECISION_THIS_GATES}`
> **上游权威输入**：
> - `{INPUT_1}`
> **下游消费者**：`{PHASE_OR_DESIGN_THAT_CONSUMES_VERDICT}`

---

## 0. Verdict（结论先行）

- **结论 token（必填）**：`ready | conditional-ready | ready-with-<caveat> | not-ready | needs-more-evidence`
- **一句话**：`{ONE_LINER_VERDICT}`
- **gate 的决策**：`{DECISION}` → 本结论建议 owner `{推进 / 暂缓 / 换路}`

---

## 1. 假设 / 问题

> 写清"要验证的是什么"，以及它为什么必须先验证。

- **待验证假设**：`{HYPOTHESIS}`
- **为什么必须先验证**：`{WHY_GATE}`（若错，会牵动 `{DOWNSTREAM_BLAST_RADIUS}`）
- **可行的判据**：满足以下即判 `ready`：
  - `{CRITERION_1}`
  - `{CRITERION_2}`

---

## 2. 现状 / 锚点

> 当前环境、凭据、源码锚点等"做这次验证所依赖的事实基线"。

| 维度 | 现状 | 锚点（file:line / 命令 / 凭据名） |
|------|------|-----------------------------------|
| `{DIMENSION}` | `{STATE}` | `{ANCHOR}` |

---

## 3. 方法 · 试了什么（诚实段）

> **诚实红线在这里落地**：逐条写清"实际做了什么"。**凡未真跑的，标 `未运行（静态分析）` 并说明原因**。

| 步骤 | 做了什么 | 是否真跑 | 证据 / 原因 |
|------|----------|----------|-------------|
| 1 | `{WHAT}` | `已运行 / 未运行（静态分析）` | `{EVIDENCE_OR_WHY_DEFERRED}` |
| 2 | `{WHAT}` | `已运行 / 未运行（静态分析）` | `{EVIDENCE_OR_WHY_DEFERRED}` |

---

## 4. 结果

> 两种形态二选一（或并存）：**原型数字** 或 **分类/缺口矩阵**。未跑的指标留空并在上表已声明。

### 4.1 原型数字（如适用）

| 指标 | 期望 | 实测 | 是否达标 |
|------|------|------|----------|
| `{METRIC}` | `{TARGET}` | `{MEASURED_OR_DEFERRED}` | `✅/❌/⏳未测` |

### 4.2 分类 / 缺口矩阵（如适用）

| 项 | 判定 | 说明 |
|----|------|------|
| `{ITEM}` | `Cat-A / Cat-B / Cat-C` 或 `gap: high/med/low` | `{NOTE}` |

---

## 5. 风险与残余

### 5.1 风险 × 缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| `{RISK}` | `{IMPACT}` | `{MITIGATION}` |

### 5.2 残余风险 / 硬前置条件（带进下一相位）

- **硬前置**：`{HARD_PRECONDITION}`（不满足则结论失效）
- **携带约束**：`{CONSTRAINT_CARRIED_FORWARD}`

---

## 6. 结论与交接

- **最终 token**：`{VERDICT_TOKEN}`（与 §0 一致）
- **交给谁**：`{DOWNSTREAM}` — 在 `{PHASE}` 落地真正实现。
- **若 `conditional-ready`，解锁条件**：`{UNLOCK_CONDITION}`

---

## 附录

### A. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | `{DATE}` | `{AUTHOR}` | 初稿 |
