# FT1-FT8 第2轮 Review Verified Findings Ledger

## Metadata

| Field | Value |
|---|---|
| Ledger ID | `FT1-FT8-2nd-review-VF-ledger` |
| Project | `myvoiceclone` |
| Review scope | `first-test` FT1-FT8 |
| Sources | `FT1-FT8-2nd-pass-reviewed-by-deepseek.md`; `FT1-FT8-2nd-pass-reviewed-by-kimi.md`; `FT1-FT8-2nd-pass-reviewed-by-gemini.md` |
| Verification date | `2026-06-13` |
| Verifier | Codex |
| Code anchor | `uncommitted working tree on HEAD 952fbc5` |

## 0. Methods

- Flattened all reviewer issues, merged overlapping findings across DeepSeek/Kimi/Gemini, then checked each item against current source, migrations, tests, closure docs, Docker config, and evidence exporter.
- Classification vocabulary: `true-bug`, `partial-delivery`, `delivery-gap`, `platform-fitness`, `test-gap`, `deferred-scope`, `not-reproduced`.
- Fix policy: runtime failures and first-test contract gaps were fixed in this pass; larger schema/API/productization changes outside first-test closure were recorded as deferred.

## 1. TL;DR Stats

| Bucket | Count | Notes |
|---|---:|---|
| Unified findings | 27 | Three review files merged by root cause |
| Verified true/partial/gap | 24 | Code or docs confirmed current issue |
| Fixed in this pass | 17 | Covered by targeted tests before full suite |
| Deferred | 10 | Requires broader schema/API/productization scope |
| Not reproduced | 0 | No source finding was discarded as false |

## 2. Source-To-Unified Mapping

| Unified ID | Merged source IDs | Verification |
|---|---|---|
| VF-01 | K-R1 | Closure/evidence anchors still referenced `31b4a04`; current HEAD is `952fbc5`. |
| VF-02 | G-R1 | Migration `007` recreated FK-referenced tables without FK off/on boundary. |
| VF-03 | DS-R2, K-R12, G-R3 | Evidence exporter queried `eval_reports`, omitted resolved paths, and hardcoded external default root. |
| VF-04 | G-R2 | Mock Demucs output was arbitrary bytes; mock FFmpeg slice copied full input. |
| VF-05 | DS-R1 | `run_curation(dedupe=True)` instantiated Protocol `VectorStore(conn)`. |
| VF-06 | DS-R3 | `recordings.status` did not advance after preprocess sub-steps. |
| VF-07 | DS-R11 | Release gate passed quality when no metrics existed. |
| VF-08 | K-R3 | Dataset freeze allowed blank transcript rows via `s["transcript"] or ""`. |
| VF-09 | K-R4 | Real inference accepted any artifact kind as reference. |
| VF-10 | K-R5 | Objective eval sample `input_artifact_id` and `output_artifact_id` collapsed to rendered artifact. |
| VF-11 | K-R6 | RVC conversion used `fake_source_audio.wav` fallback. |
| VF-12 | K-R7, DS-S3 | Independent step/train/infer/eval jobs lacked step-level events. |
| VF-13 | DS-R6 | Runner persisted only `str(e)` in failure events. |
| VF-14 | DS-R4, DS-R7, DS-R8, K-R8, K-R9, K-R10, G-R5 | No unified exception base, API error schema, or error handbook. |
| VF-15 | DS-R5 | Compose train service lacked `runtime: nvidia`. |
| VF-16 | DS-R10, G-R4 | Scoring used hidden mock constants even when `MOCK_ADAPTERS=false`; no first-test scoring artifact. |
| VF-17 | DS-R12 | Slice artifact metadata did not include FFmpeg adapter metadata. |
| VF-18 | DS-R14, DS-R17 | Adapter device/version metadata still partially static/unknown. |
| VF-19 | DS-R15 | `source_artifact_id` mirrors `parent_artifact_id`, collapsing semantic lineage. |
| VF-20 | DS-R16 | `pipeline_runs` remains a compatibility table, not wired to runtime workflows. |
| VF-21 | DS-R18 | `embedding_items` is retained after migration to `embedding_jobs`. |
| VF-22 | DS-R19, DS-R20, DS-R21, DS-R23, DS-R25 | API pagination/list-runs/typed status models/contract coverage remain incomplete. |
| VF-23 | DS-R22 | API error status normalization is only partially addressed route-by-route. |
| VF-24 | DS-R24 | Report/gate IDs remain caller-supplied. |
| VF-25 | K-R11 | Container/API production path and Dockerfile.api remain out of first-test scope. |
| VF-26 | K-R2 | FT7 pre-capstone gate is still mostly closure/evidence based, not a full test command gate. |
| VF-27 | DS-R13, G-R6, G-R7 | Recording `updated_at`/CHECK constraints, canonical job states, and some cleanup hardening remain broader schema/platform work. |

## 3. Verified Findings

| ID | Severity | Type | Status | Verification Detail | Resolution |
|---|---|---|---|---|---|
| VF-01 | High | delivery-gap | fixed | `docs/closure/first-test/*.md` had stale `HEAD 31b4a04`. | Updated to `HEAD 952fbc5`; added closure HEAD test. |
| VF-02 | High | platform-fitness | fixed | `007_reconcile_to_plan.sql` had table recreation without FK boundary. | Added `PRAGMA foreign_keys = OFF/ON`. |
| VF-03 | High | true-bug | fixed | `src/myvoiceclone/evidence.py` used `eval_reports`; default root was external. | Switched to `reports`, env fallback `/app/test-runs`, and resolved paths. |
| VF-04 | High | true-bug | fixed | Mock `.wav` outputs were invalid or wrong duration. | FFmpeg/Demucs mocks now write/copy valid WAV; slice duration tested. |
| VF-05 | High | true-bug | fixed | `VectorStore` is a Protocol. | `run_curation` now uses `Vec0Store`. |
| VF-06 | Medium | partial-delivery | fixed | Recording state stopped after ingest. | Each preprocess/curate step marks recording status. |
| VF-07 | High | true-bug | fixed | Empty `eval_metrics` allowed release quality pass. | Quality gate now requires metrics. |
| VF-08 | High | true-bug | fixed | Frozen manifest could include blank transcript. | Export query requires non-empty transcript. |
| VF-09 | High | true-bug | fixed | Inference reference was not type checked. | Reference artifact kind limited to `cleaned`/`reference_audio`. |
| VF-10 | Medium | true-bug | fixed | Eval sample lineage collapsed to rendered artifact. | `input/output/reference` artifact IDs now split from inference metadata. |
| VF-11 | Medium | true-bug | fixed | Real RVC path could silently use fake source. | Real mode requires `source_audio_path`; mock writes explicit temp source. |
| VF-12 | Medium | partial-delivery | fixed | Single jobs lacked step events. | Runner wraps ingest/train/step/infer/eval in `step_*` events. |
| VF-13 | Medium | partial-delivery | fixed | Failure metadata lacked traceback. | Job and step failure events include `error_type` and `traceback`. |
| VF-14 | High | delivery-gap | fixed | Error layer/API schema/handbook absent. | Added `errors.py`, structured API handlers, `ErrorResponse`, and ops handbook. |
| VF-15 | Medium | platform-fitness | fixed | Compose GPU runtime missing. | Added `runtime: nvidia` to train service. |
| VF-16 | Medium | partial-delivery | partial-fixed/deferred | Hidden mock constants were active in real mode; scoring artifact still absent. | Real mode now refuses scorer; scoring artifact deferred. |
| VF-17 | Medium | partial-delivery | fixed | Slice artifacts missed adapter metadata. | Added `ffmpeg_adapter.metadata()` to slice artifacts. |
| VF-18 | Low | deferred-scope | deferred | Some adapter metadata values are intentionally environment-dependent or unknown. | Deferred to adapter observability hardening. |
| VF-19 | Medium | deferred-scope | deferred | Artifact store still maps source to parent by default. | Deferred to lineage schema migration. |
| VF-20 | Medium | deferred-scope | deferred | `pipeline_runs` remains not wired. | Deferred to workflow orchestration milestone. |
| VF-21 | Low | deferred-scope | deferred | `embedding_items` still exists after migration. | Deferred to schema cleanup with compatibility plan. |
| VF-22 | Medium | delivery-gap | deferred | API list/pagination/typed status/contract breadth incomplete. | Deferred to API contract expansion. |
| VF-23 | Medium | partial-delivery | partial-fixed/deferred | Global error structure exists, route mappings still mixed. | Route-by-route status normalization deferred. |
| VF-24 | Low | deferred-scope | deferred | Report/gate IDs are caller-supplied by current API. | Deferred to API ergonomics/idempotency milestone. |
| VF-25 | Medium | deferred-scope | deferred | Docker API production path not requested by FT1-FT8 implementation close. | Deferred to container productionization. |
| VF-26 | Medium | test-gap | deferred | FT7 gate still relies on evidence/closure shape more than command execution. | Deferred to live gate harness. |
| VF-27 | Low | deferred-scope | deferred | Schema/platform cleanup remains broader than second-pass fixes. | Deferred with triggers. |

## 4. Verification Summary

- Valid blockers fixed: VF-01 through VF-15 plus VF-17.
- Partial fixes with explicit deferred residue: VF-16 and VF-23.
- Deferred items are real but require broader schema/API/platform work beyond safe second-pass closure.

## 5. Fix Plan

| Step | Scope | Status |
|---|---|---|
| 1 | Runtime/data correctness fixes | done |
| 2 | API/error/evidence/closure fixes | done |
| 3 | Targeted regression tests | done |
| 4 | Full test↔fix loop | done |
| 5 | Evidence refresh and final response append | done |

## 6. Implementer Response

### 6.1 Response Summary

- Fixed true blockers and high-signal partial deliveries from the three second-pass reviews.
- Preserved broader schema/API/container/live-gate work as explicit deferred items instead of overstating closure.
- Refreshed first-test closure anchors and evidence pack to current HEAD `952fbc5`.

### 6.2 Code Fixes

- Evidence exporter: `eval_reports` -> `reports`, portable default evidence root, resolved DB/artifact/model/evidence paths.
- Runtime correctness: concrete `Vec0Store` for curation dedupe, recording status progression, non-empty transcript dataset freeze guard, reference artifact kind validation, objective eval lineage split, RVC real-mode source guard.
- Adapter behavior: mock FFmpeg slicing now emits duration-correct WAV; mock Demucs emits/copies valid WAV and real temp output is cleaned.
- Observability/errors: step events for single jobs/train/infer/eval, traceback metadata on failures, structured API error response with `trace_id`, and `docs/ops/error-handbook.md`.
- Release/container/schema: quality gate no longer passes with empty metrics, compose train service declares `runtime: nvidia`, migration 007 wraps table recreation with FK off/on.

### 6.3 Tests Added Or Updated

- Added regression coverage for structured API errors, closure HEAD anchors, evidence `reports` export/resolved paths, mock WAV validity, dataset transcript guard, inference reference kind guard, objective lineage, real-mode scoring refusal, runner step events/tracebacks, compose GPU runtime, and release gate empty metrics.
- Updated existing fixtures that became invalid under stricter first-test contracts.

### 6.4 Deferred Items

- Added FTD-18 through FTD-27 to `docs/closure/first-test/deferred-items-ledger.md`.
- Key residuals: scoring artifacts, adapter metadata hardening, artifact lineage schema cleanup, `pipeline_runs`, embedding table cleanup, API pagination/typed models/full contract coverage, route-level error code normalization, Docker API production path, FT7 live gate harness, and schema/platform hardening.

### 6.5 Verification Commands

| Command | Result |
|---|---|
| `./venv/bin/python -m pytest -q` | `156 passed, 1 skipped, 2 deselected, 14 warnings` |
| `./venv/bin/python -m pytest tests/integration/test_first_test_http_smoke.py tests/integration/test_first_test_capstone.py -m live -q -rs` | `2 skipped, 1 deselected` because live env flags are not set |
| `SKIP_REASON='RUN_FIRST_TEST_CAPSTONE=1 is required for live first-test capstone' RUN_ID='first-test-capstone-skipped-20260613T0850Z' ./scripts/collect_first_test_evidence.sh` | validator `ok=true` |
| `./venv/bin/python -m myvoiceclone.evidence validate /mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z --repo-root .` | `ok=true` |
| `./venv/bin/python -m compileall -q src tests` | pass |
| `git diff --check` | pass |

### 6.6 Evidence Notes

- Refreshed evidence pack: `/mnt/usb/workspace/myvoiceresearch/test-runs/first-test-capstone-skipped-20260613T0850Z`.
- `env.json` now records `git_commit=952fbc5` and resolved `DB_PATH`, `ARTIFACT_ROOT`, `MODELS_DIR`, and `EVIDENCE_ROOT`.
- `trace.json` now includes the `reports` key from the real `reports` table.

## Revision History

| Time | Change |
|---|---|
| 2026-06-13T10:43:45Z | Created verified findings ledger from second-pass review files. |
| 2026-06-13T10:49:00Z | Appended implementation response, verification results, and deferred handoff summary. |
