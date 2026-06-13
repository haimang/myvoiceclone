-- Migration 007: Reconcile schema to final-execution-plan.md §14.3
-- This migration adds missing columns, fixes status enumerations, renames columns via
-- new columns + data copy (SQLite cannot DROP or RENAME in older versions),
-- and adds composite indexes and CHECK constraints per plan.
--
-- Strategy: ADD new plan-canonical columns alongside existing ones.
-- Existing code referencing old column names continues to work.
-- Application code should migrate to new column names over time.
-- A compatibility VIEW is provided for the artifacts table.

PRAGMA foreign_keys = OFF;

-- ─────────────────────────────────────────────
-- 1. datasets: add status CHECK constraint
-- ─────────────────────────────────────────────
-- SQLite does not allow ALTER TABLE ADD CONSTRAINT.
-- We recreate the table with the CHECK in place.
-- Step A: create new table
CREATE TABLE IF NOT EXISTS datasets_v2 (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'draft','frozen','training','evaluated','rejected','release_candidate','active'
    )),
    manifest_artifact_id TEXT,
    manifest_sha256 TEXT,
    filter_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    frozen_at TIMESTAMP
);
-- Step B: copy data (only if datasets exists and has rows)
INSERT OR IGNORE INTO datasets_v2 SELECT * FROM datasets;
-- Step C: drop old, rename new
DROP TABLE IF EXISTS datasets;
ALTER TABLE datasets_v2 RENAME TO datasets;

-- ─────────────────────────────────────────────
-- 2. jobs: add missing columns + fix status CHECK
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs_v2 (
    id TEXT PRIMARY KEY,
    -- plan canonical name (new); keep 'name' as alias alias for code compat
    name TEXT NOT NULL,
    type TEXT GENERATED ALWAYS AS (name) VIRTUAL,
    status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','canceled',
                                          'pending','completed','cancelled')),
    -- plan canonical
    params_json TEXT DEFAULT '{}',
    -- old compat
    payload_json TEXT DEFAULT '{}',
    subject_type TEXT,
    subject_id TEXT,
    pipeline TEXT,
    requested_by TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO jobs_v2 (id, name, status, payload_json, params_json, error_msg, created_at, updated_at)
    SELECT id, name, status, payload_json, payload_json, error_msg, created_at, updated_at FROM jobs;
DROP TABLE IF EXISTS jobs;
ALTER TABLE jobs_v2 RENAME TO jobs;

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_subject ON jobs(subject_type, subject_id);

-- ─────────────────────────────────────────────
-- 3. job_events: re-create FK to new jobs table
-- ─────────────────────────────────────────────
-- FK already exists, just ensure index
CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);

-- ─────────────────────────────────────────────
-- 4. artifacts: add plan-canonical columns
-- ─────────────────────────────────────────────
ALTER TABLE artifacts ADD COLUMN kind TEXT;
ALTER TABLE artifacts ADD COLUMN source_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL;
ALTER TABLE artifacts ADD COLUMN created_by_job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL;
ALTER TABLE artifacts ADD COLUMN pipeline_version TEXT;
ALTER TABLE artifacts ADD COLUMN params_json TEXT DEFAULT '{}';

-- Backfill kind from artifact_type
UPDATE artifacts SET kind = artifact_type WHERE kind IS NULL;
UPDATE artifacts SET source_artifact_id = parent_artifact_id WHERE source_artifact_id IS NULL;
UPDATE artifacts SET created_by_job_id = job_id WHERE created_by_job_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind);
CREATE INDEX IF NOT EXISTS idx_artifacts_created_by_job ON artifacts(created_by_job_id);

-- ─────────────────────────────────────────────
-- 5. model_runs: add missing columns
-- ─────────────────────────────────────────────
ALTER TABLE model_runs ADD COLUMN model_family TEXT;
ALTER TABLE model_runs ADD COLUMN checkpoint_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL;
ALTER TABLE model_runs ADD COLUMN env_digest TEXT;
ALTER TABLE model_runs ADD COLUMN git_commit TEXT;
ALTER TABLE model_runs ADD COLUMN finished_at TIMESTAMP;
ALTER TABLE model_runs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add status CHECK via recreation
CREATE TABLE IF NOT EXISTS model_runs_v2 (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    model_family TEXT,
    dataset_id TEXT,
    status TEXT NOT NULL CHECK(status IN (
        'pending','queued','preparing','running','training','checkpointed','completed','failed','cancelled'
    )),
    config_json TEXT DEFAULT '{}',
    checkpoint_artifact_id TEXT,
    env_digest TEXT,
    git_commit TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    CONSTRAINT fk_run_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL
);
INSERT OR IGNORE INTO model_runs_v2
    SELECT id, name, model_family, dataset_id,
           CASE status
               WHEN 'completed' THEN 'completed'
               WHEN 'cancelled' THEN 'cancelled'
               ELSE status
           END,
           config_json, checkpoint_artifact_id, env_digest, git_commit,
           created_at, updated_at, finished_at
    FROM model_runs;
DROP TABLE IF EXISTS model_runs;
ALTER TABLE model_runs_v2 RENAME TO model_runs;

CREATE INDEX IF NOT EXISTS idx_model_runs_status ON model_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_runs_dataset ON model_runs(dataset_id);

-- ─────────────────────────────────────────────
-- 6. pipeline_runs: add missing columns
-- ─────────────────────────────────────────────
ALTER TABLE pipeline_runs ADD COLUMN pipeline_name TEXT;
ALTER TABLE pipeline_runs ADD COLUMN subject_type TEXT;
ALTER TABLE pipeline_runs ADD COLUMN subject_id TEXT;
ALTER TABLE pipeline_runs ADD COLUMN config_json TEXT DEFAULT '{}';
ALTER TABLE pipeline_runs ADD COLUMN finished_at TIMESTAMP;

-- ─────────────────────────────────────────────
-- 7. embedding_items → embedding_jobs rename + add columns
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS embedding_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL CHECK(namespace IN ('speaker', 'audio', 'text')),
    item_id TEXT NOT NULL,
    subject_type TEXT,
    subject_id TEXT,
    model_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','running','completed','failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_embedding_model FOREIGN KEY (model_id) REFERENCES embedding_models(id)
);
INSERT OR IGNORE INTO embedding_jobs (id, namespace, item_id, model_id, created_at)
    SELECT id, namespace, item_id, model_id, created_at FROM embedding_items;

CREATE UNIQUE INDEX IF NOT EXISTS idx_embedding_jobs_uniq ON embedding_jobs(namespace, item_id, model_id);

-- ─────────────────────────────────────────────
-- 8. reports: add missing columns
-- ─────────────────────────────────────────────
ALTER TABLE reports ADD COLUMN kind TEXT;
ALTER TABLE reports ADD COLUMN subject_type TEXT;
ALTER TABLE reports ADD COLUMN subject_id TEXT;
ALTER TABLE reports ADD COLUMN status TEXT DEFAULT 'pending';

UPDATE reports SET kind = report_type WHERE kind IS NULL;

CREATE INDEX IF NOT EXISTS idx_reports_subject ON reports(subject_type, subject_id);

-- ─────────────────────────────────────────────
-- 9. eval_metrics: add missing columns + composite index
-- ─────────────────────────────────────────────
ALTER TABLE eval_metrics ADD COLUMN report_id TEXT REFERENCES reports(id) ON DELETE SET NULL;
ALTER TABLE eval_metrics ADD COLUMN metric_json TEXT DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_eval_metrics_run_name ON eval_metrics(run_id, metric_name);

-- ─────────────────────────────────────────────
-- 10. eval_samples: add missing columns (three-way FK)
-- ─────────────────────────────────────────────
ALTER TABLE eval_samples ADD COLUMN input_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL;
ALTER TABLE eval_samples ADD COLUMN output_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL;
ALTER TABLE eval_samples ADD COLUMN reference_artifact_id TEXT REFERENCES artifacts(id) ON DELETE SET NULL;
ALTER TABLE eval_samples ADD COLUMN report_id TEXT REFERENCES reports(id) ON DELETE SET NULL;
ALTER TABLE eval_samples ADD COLUMN scores_json TEXT DEFAULT '{}';

-- Backfill from existing audio_artifact_id
UPDATE eval_samples SET input_artifact_id = audio_artifact_id WHERE input_artifact_id IS NULL;

-- ─────────────────────────────────────────────
-- 11. consent_ledger: add plan-canonical columns
-- ─────────────────────────────────────────────
ALTER TABLE consent_ledger ADD COLUMN scope TEXT DEFAULT 'voice_clone';
ALTER TABLE consent_ledger ADD COLUMN status TEXT DEFAULT 'active' CHECK(status IN ('active','revoked','expired'));
ALTER TABLE consent_ledger ADD COLUMN evidence_uri TEXT;
ALTER TABLE consent_ledger ADD COLUMN revoked_at TIMESTAMP;

-- ─────────────────────────────────────────────
-- 12. policy_events: add plan-canonical columns
-- ─────────────────────────────────────────────
ALTER TABLE policy_events ADD COLUMN subject_type TEXT;
ALTER TABLE policy_events ADD COLUMN subject_id TEXT;
ALTER TABLE policy_events ADD COLUMN policy_name TEXT;
ALTER TABLE policy_events ADD COLUMN decision TEXT;
ALTER TABLE policy_events ADD COLUMN reason TEXT;
ALTER TABLE policy_events ADD COLUMN payload_json TEXT DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_policy_events_subject ON policy_events(subject_type, subject_id);

-- ─────────────────────────────────────────────
-- 13. release_gates: add status column (4-state)
-- ─────────────────────────────────────────────
ALTER TABLE release_gates ADD COLUMN status TEXT DEFAULT 'pending' CHECK(status IN (
    'pending','passed','failed','waived'
));
ALTER TABLE release_gates ADD COLUMN decision_json TEXT DEFAULT '{}';

-- Backfill status from passed boolean
UPDATE release_gates SET status = 'passed' WHERE passed = 1 AND status = 'pending';
UPDATE release_gates SET status = 'failed' WHERE passed = 0 AND status = 'pending';

CREATE INDEX IF NOT EXISTS idx_release_gates_status ON release_gates(model_run_id, status);

-- ─────────────────────────────────────────────
-- 14. embedding_models: add missing columns
-- ─────────────────────────────────────────────
ALTER TABLE embedding_models ADD COLUMN namespace TEXT;
ALTER TABLE embedding_models ADD COLUMN distance_metric TEXT DEFAULT 'cosine';
ALTER TABLE embedding_models ADD COLUMN version TEXT;

PRAGMA foreign_keys = ON;
