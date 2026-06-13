-- Migration 001: Core Schema

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS speakers (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'other', 'unknown')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    source_uri TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    duration_sec REAL NOT NULL,
    sample_rate INTEGER NOT NULL,
    channels INTEGER NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS segments (
    id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL,
    speaker_id TEXT,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    audio_artifact_id TEXT,
    cleaned_artifact_id TEXT,
    transcript TEXT,
    status TEXT NOT NULL,
    quality_score REAL,
    speaker_score REAL,
    noise_score REAL,
    overlap_score REAL,
    metadata_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_recording FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    CONSTRAINT fk_speaker FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE SET NULL,
    CONSTRAINT check_duration CHECK (end_sec > start_sec)
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    manifest_artifact_id TEXT,
    manifest_sha256 TEXT,
    filter_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    frozen_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dataset_segments (
    dataset_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    split TEXT NOT NULL CHECK(split IN ('train', 'val', 'test')),
    PRIMARY KEY (dataset_id, segment_id),
    CONSTRAINT fk_dataset FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    CONSTRAINT fk_segment FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings(status);
CREATE INDEX IF NOT EXISTS idx_segments_recording ON segments(recording_id, start_sec);
CREATE INDEX IF NOT EXISTS idx_segments_status_quality ON segments(status, quality_score);
