-- Migration 008: first-test observability contract

ALTER TABLE job_events ADD COLUMN metadata_json TEXT DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_job_events_type ON job_events(job_id, event_type);
