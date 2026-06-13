# [FT8 / Closure Deferred] Closure

> 阶段: `first-test/FT8 — Closure 与 deferred reconciliation`
> 范围: `FT8-P1..P3`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-06-13` · 作者: `Codex`
> 关联 charter: `docs/eval/first-test/proposed-planning.md`
> 关联 design: `docs/eval/first-test/reference-anchor.md`
> 关联 action-plan: `docs/plan/first-test/FT8-closure-deferred.md`
> 关联 evidence: `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z`
> 关联 review: `inline §5`

---

## 0. 一句话 verdict

> FT8 已完成 first-build deferred reconciliation、first-test closure/deferred ledger、final input pack 与 docs-check；由于 FT7 evidence 是 skipped pack，本阶段如实维持 `implementation-complete-awaiting-live-verification`。

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| FT8-P1-01 first-build deferred reconciliation | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `docs/closure/first-build/deferred-items-ledger.md#6-first-test-reconciliation-snapshot2026-06-13` + `2026-06-13 08:57 UTC` |
| FT8-P1-02 retained deferred boundary | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `docs/closure/first-test/deferred-items-ledger.md` + `2026-06-13 08:57 UTC` |
| FT8-P2-01 first-test closure ledger | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `docs/closure/first-test/first-test-closure.md` + `2026-06-13 08:57 UTC` |
| FT8-P2-02 first-test deferred ledger | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `docs/closure/first-test/deferred-items-ledger.md` + `2026-06-13 08:57 UTC` |
| FT8-P3-01 final input pack index | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `docs/eval/first-test/final-input-pack.md` + `2026-06-13 08:57 UTC` |
| FT8-P3-02 docs/check | ✅ closed | `uncommitted working tree on HEAD 952fbc5` + `tests/unit/test_first_test_closure_docs.py` + `2026-06-13 08:57 UTC` |

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| FT8 docs/check | `./venv/bin/python -m pytest tests/unit/test_first_test_closure_docs.py -q` | `5 passed` | FT8-T01..T03 |
| Evidence pack anchor | `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z/manifest.json` | `status=skipped`, live denominator `1` | closure close type |
| Deferred reconciliation | `docs/closure/first-build/deferred-items-ledger.md` | DEF-01..15 classified retained/partial | FT8-P1 |

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| first-build deferred reconciliation | DEF-01..15 retained/partial status recorded | ledger snapshot appended | ✅ PASS |
| first-test closure ledger | closure exists and close type matches FT7 skipped evidence | `first-test-closure.md` | ✅ PASS |
| first-test deferred ledger | retained items have triggers and target phases | `deferred-items-ledger.md` | ✅ PASS |
| final input pack | references core planning/test/schema/API/evidence inputs | `final-input-pack.md` | ✅ PASS |
| live full close | non-skipped live evidence exists | skipped evidence only | ⏸ PENDING |

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| FT7 live capstone real execution | C | pending-live | `docs/closure/first-test/deferred-items-ledger.md#ftd-01--live-capstone-真实执行` | owner / next live runner |
| Non-skipped evidence pack | C | retained | `docs/closure/first-test/deferred-items-ledger.md#ftd-02--非-skipped-evidence-pack` | owner / next live runner |
| first-build retained deferred | B/C | retained/partial | `docs/closure/first-build/deferred-items-ledger.md#6-first-test-reconciliation-snapshot2026-06-13` | future owner |

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ `observed-OK-at-closure` for docs/check artifacts; live full close remains pending |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 使用 `uncommitted working tree on HEAD 952fbc5`，本轮未请求 commit |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ FT8 改动集中在 closure/deferred/final-input/docs-check |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| ✅ live full-close gate pending |
