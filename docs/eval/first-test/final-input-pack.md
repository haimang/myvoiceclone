# first-test final input pack

> 项目: `myvoiceclone`
> 阶段: `first-test`
> 文档性质: `final-input-pack`
> 日期: `2026-06-13` · 作者: `Codex`
> 状态: `active`

本文件是索引，不复制原始 evidence。下一阶段 planning 应以这里列出的路径为入口，避免重新考古或复制漂移。

## 1. Verdict

first-test 的代码与默认验证已完成，真实 close type 为 `implementation-complete-awaiting-live-verification`。原因是 FT7 live capstone 只有 skipped evidence，路径为：

- `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z`

## 2. Authority Inputs

| 类别 | 路径 | 用途 |
|------|------|------|
| proposed planning | `docs/eval/first-test/proposed-planning.md` | FT1-FT8 scope、DAG、test matrix baseline |
| reference anchor | `docs/eval/first-test/reference-anchor.md` | web anchors、TR-1..TR-7、反例 ledger |
| action-plan index | `docs/plan/first-test/index.md` | 执行顺序和依赖图 |
| first-build deferred | `docs/closure/first-build/deferred-items-ledger.md` | DEF-01..15 reconciliation source |
| first-test closure | `docs/closure/first-test/first-test-closure.md` | FT1-FT8 close type 与 known gaps |
| first-test deferred | `docs/closure/first-test/deferred-items-ledger.md` | retained/pending-live deferred triggers |

## 3. Phase Closures

| Phase | Closure | Close state |
|-------|---------|-------------|
| FT1 | `docs/closure/first-test/FT1-preflight-closure.md` | closed |
| FT2 | `docs/closure/first-test/FT2-schema-observability-closure.md` | closed |
| FT3 | `docs/closure/first-test/FT3-real-preprocess-closure.md` | implementation complete, live-gated adapters |
| FT4 | `docs/closure/first-test/FT4-real-inference-closure.md` | implementation complete, live model pending |
| FT5 | `docs/closure/first-test/FT5-real-evaluation-closure.md` | implementation complete, manual/live evidence pending |
| FT6 | `docs/closure/first-test/FT6-fastapi-e2e-closure.md` | implementation complete, live HTTP pending |
| FT7 | `docs/closure/first-test/FT7-live-capstone-closure.md` | implementation complete, live capstone pending |
| FT8 | `docs/closure/first-test/FT8-closure-deferred-closure.md` | closure/deferred docs-check |

## 4. Test Matrix Entrypoints

| 目的 | 命令 / 路径 |
|------|-------------|
| default regression | `./venv/bin/python -m pytest -q` |
| architecture boundary | `./venv/bin/python -m pytest tests/unit/test_architecture_boundaries.py -q` |
| FT6 API contract | `./venv/bin/python -m pytest tests/api/test_first_test_runs.py -q` |
| FT7 evidence validator | `./venv/bin/python -m pytest tests/unit/test_first_test_evidence_validator.py -q` |
| FT8 docs/check | `./venv/bin/python -m pytest tests/unit/test_first_test_closure_docs.py -q` |
| live capstone gated | `./venv/bin/python -m pytest tests/integration/test_first_test_capstone.py -m live -q -rs` |

## 5. Schema / API / Evidence Contracts

| Contract | 路径 | 说明 |
|----------|------|------|
| schema drift inventory | `tests/unit/storage/test_schema_drift.py` | migration/table/column drift guard |
| observability event contract | `src/myvoiceclone/jobs/events.py` | step event metadata and failure summary |
| artifact metadata contract | `src/myvoiceclone/storage/artifact_store.py` | adapter_mode, metric_source, metadata version |
| first-test run API | `src/myvoiceclone/api/routes_runs.py` | create/upload/start/status surface |
| first-test API fixture | `tests/api/contracts/first_test_run_create.json` | create-run response drift guard |
| evidence exporter/validator | `src/myvoiceclone/evidence.py` | run folder exporter and validator |
| evidence shell wrapper | `scripts/collect_first_test_evidence.sh` | operator/CI entrypoint |

## 6. Deferred Boundary Index

| Boundary | Source | Trigger |
|----------|--------|---------|
| live capstone real run | `docs/closure/first-test/deferred-items-ledger.md#ftd-01--live-capstone-真实执行` | owner live env |
| non-skipped evidence | `docs/closure/first-test/deferred-items-ledger.md#ftd-02--非-skipped-evidence-pack` | real artifacts/trace present |
| vec0/embedder dimensions | `docs/closure/first-build/deferred-items-ledger.md#6-first-test-reconciliation-snapshot2026-06-13` | real embedder enters path |
| production queue/multi-worker | `docs/closure/first-test/deferred-items-ledger.md#ftd-06--多-worker--queue--sqlite-并发` | worker pool introduced |
| API envelope | `docs/closure/first-test/deferred-items-ledger.md#ftd-07--全局-api-envelope` | API contract freeze |
| full OTel | `docs/closure/first-test/deferred-items-ledger.md#ftd-08--完整-otel-平台` | multi-service observability target |

## 7. Live Re-run Checklist

- Set `RUN_FIRST_TEST_CAPSTONE=1`.
- Set `FIRST_TEST_AUDIO_PATH` to a legal short audio sample outside the repo.
- Set `ARTIFACT_ROOT` and `DB_PATH` to the intended external test-run paths.
- Configure model/cache/token/license inputs required by the chosen real substrate.
- Run `./venv/bin/python -m pytest tests/integration/test_first_test_capstone.py -m live -q -rs`.
- Export and validate evidence with `scripts/collect_first_test_evidence.sh`.
