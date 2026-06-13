-- Migration 004: Reports and Metrics Schema

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    report_type TEXT NOT NULL,
    summary_json TEXT DEFAULT '{}',
    artifact_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_report_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS eval_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    step INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_metric_run FOREIGN KEY (run_id) REFERENCES model_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eval_samples (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    audio_artifact_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sample_run FOREIGN KEY (run_id) REFERENCES model_runs(id) ON DELETE CASCADE,
    CONSTRAINT fk_sample_artifact FOREIGN KEY (audio_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_eval_metrics_run ON eval_metrics(run_id);
