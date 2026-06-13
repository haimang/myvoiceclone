import os
import wave
import struct
import sqlite3
import pytest
from myvoiceclone.storage.sqlite import get_connection
from myvoiceclone.storage.migrations import run_migrations
from myvoiceclone.storage.artifact_store import ArtifactStore

@pytest.fixture(scope="session")
def synthetic_wav(tmp_path_factory):
    # Programmatically create a tiny 1-second mono 16kHz WAV file
    tmp_dir = tmp_path_factory.mktemp("audio")
    wav_path = os.path.join(tmp_dir, "synthetic_16k.wav")
    
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2) # 16-bit
        w.setframerate(16000)
        # 1 second of silence
        data = struct.pack("<16000h", *[0]*16000)
        w.writeframes(data)
        
    return wav_path

@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")

@pytest.fixture
def db_conn(db_path):
    project_root = os.path.dirname(os.path.dirname(__file__))
    migrations_dir = os.path.join(project_root, "db", "migrations")
    
    # Run migrations
    run_migrations(db_path, migrations_dir)
    
    conn = get_connection(db_path, load_vec=True)
    yield conn
    conn.close()

@pytest.fixture
def artifact_store(db_conn, tmp_path):
    root_dir = str(tmp_path / "artifacts")
    return ArtifactStore(db_conn, root_dir)
