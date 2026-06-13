-- Migration 005: Security Placeholders Schema

CREATE TABLE IF NOT EXISTS consent_ledger (
    id TEXT PRIMARY KEY,
    speaker_id TEXT NOT NULL,
    recording_id TEXT NOT NULL,
    granted INTEGER NOT NULL CHECK(granted IN (0, 1)),
    signature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_consent_speaker FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE CASCADE,
    CONSTRAINT fk_consent_recording FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS policy_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS release_gates (
    id TEXT PRIMARY KEY,
    model_run_id TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    approved_by TEXT,
    approved_at TIMESTAMP,
    details_json TEXT DEFAULT '{}',
    CONSTRAINT fk_gate_run FOREIGN KEY (model_run_id) REFERENCES model_runs(id) ON DELETE CASCADE
);
