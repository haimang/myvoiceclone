-- Migration 009: API request audit log

CREATE TABLE IF NOT EXISTS api_request_logs (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER,
    error_code TEXT,
    run_id TEXT,
    job_id TEXT,
    artifact_id TEXT,
    request_json TEXT DEFAULT '{}',
    response_json TEXT DEFAULT '{}',
    client_host TEXT,
    user_agent TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_api_request_logs_trace_id ON api_request_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_api_request_logs_path ON api_request_logs(path);
CREATE INDEX IF NOT EXISTS idx_api_request_logs_run_id ON api_request_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_api_request_logs_job_id ON api_request_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_api_request_logs_artifact_id ON api_request_logs(artifact_id);
