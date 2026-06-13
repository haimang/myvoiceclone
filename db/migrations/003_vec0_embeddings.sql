-- Migration 003: vec0 Embeddings Schema

CREATE TABLE IF NOT EXISTS embedding_models (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    provider TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS embedding_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL CHECK(namespace IN ('speaker', 'audio', 'text')),
    item_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_embedding_model FOREIGN KEY (model_id) REFERENCES embedding_models(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_embedding_items_uniq ON embedding_items(namespace, item_id, model_id);

-- Virtual tables for sqlite-vec. Note: Must be executed with sqlite-vec extension loaded.
CREATE VIRTUAL TABLE IF NOT EXISTS vec_speaker USING vec0(
    embedding float[128]
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_audio USING vec0(
    embedding float[128]
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_text USING vec0(
    embedding float[128]
);
