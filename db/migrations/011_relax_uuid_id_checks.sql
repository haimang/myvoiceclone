-- Migration 011: keep UUID text primary keys while allowing legacy/manual fixture ids.

PRAGMA foreign_keys=off;

CREATE TABLE IF NOT EXISTS job_events_relaxed (
    id TEXT PRIMARY KEY DEFAULT ('mvc_' || lower(hex(randomblob(16)))),
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status_from TEXT,
    status_to TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT DEFAULT '{}',
    CONSTRAINT fk_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

INSERT INTO job_events_relaxed (
    id, job_id, event_type, status_from, status_to, message, created_at, metadata_json
)
SELECT id, job_id, event_type, status_from, status_to, message, created_at, COALESCE(metadata_json, '{}')
FROM job_events;

DROP TABLE job_events;
ALTER TABLE job_events_relaxed RENAME TO job_events;

CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);
CREATE INDEX IF NOT EXISTS idx_job_events_type ON job_events(job_id, event_type);

CREATE TABLE IF NOT EXISTS eval_metrics_relaxed (
    id TEXT PRIMARY KEY DEFAULT ('mvc_' || lower(hex(randomblob(16)))),
    run_id TEXT NOT NULL,
    report_id TEXT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_json TEXT DEFAULT '{}',
    step INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_metric_run FOREIGN KEY (run_id) REFERENCES model_runs(id) ON DELETE CASCADE,
    CONSTRAINT fk_metric_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL
);

INSERT INTO eval_metrics_relaxed (
    id, run_id, report_id, metric_name, metric_value, metric_json, step, created_at
)
SELECT id, run_id, report_id, metric_name, metric_value, COALESCE(metric_json, '{}'), step, created_at
FROM eval_metrics;

DROP TABLE eval_metrics;
ALTER TABLE eval_metrics_relaxed RENAME TO eval_metrics;

CREATE INDEX IF NOT EXISTS idx_eval_metrics_run ON eval_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_metrics_report ON eval_metrics(report_id);
CREATE INDEX IF NOT EXISTS idx_eval_metrics_run_name ON eval_metrics(run_id, metric_name);

CREATE TABLE IF NOT EXISTS policy_events_relaxed (
    id TEXT PRIMARY KEY DEFAULT ('mvc_' || lower(hex(randomblob(16)))),
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT DEFAULT '{}',
    subject_type TEXT,
    subject_id TEXT,
    policy_name TEXT,
    decision TEXT,
    reason TEXT,
    payload_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO policy_events_relaxed (
    id, event_type, status, details_json, subject_type, subject_id, policy_name,
    decision, reason, payload_json, created_at
)
SELECT
    id, event_type, status, COALESCE(details_json, '{}'), subject_type, subject_id, policy_name,
    decision, reason, COALESCE(payload_json, '{}'), created_at
FROM policy_events;

DROP TABLE policy_events;
ALTER TABLE policy_events_relaxed RENAME TO policy_events;

CREATE INDEX IF NOT EXISTS idx_policy_events_subject ON policy_events(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_policy_events_policy ON policy_events(policy_name, decision);

PRAGMA foreign_keys=on;
