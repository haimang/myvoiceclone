import os
import hashlib
import sqlite3
import logging
from typing import List

logger = logging.getLogger("myvoiceclone.storage.migrations")

def get_file_checksum(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def ensure_migration_table(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        checksum TEXT NOT NULL
    );
    """)
    conn.commit()

def get_applied_migrations(conn: sqlite3.Connection) -> dict:
    ensure_migration_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT version, checksum FROM schema_migrations ORDER BY version;")
    return {row[0]: row[1] for row in cursor.fetchall()}

def run_migrations(db_path: str, migrations_dir: str) -> List[str]:
    from myvoiceclone.storage.sqlite import get_connection
    conn = get_connection(db_path, load_vec=True)
    
    try:
        ensure_migration_table(conn)
        applied = get_applied_migrations(conn)
        
        migration_files = []
        if not os.path.exists(migrations_dir):
            raise ValueError(f"Migrations directory not found: {migrations_dir}")
            
        for file in os.listdir(migrations_dir):
            if file.endswith(".sql") and file[:3].isdigit():
                migration_files.append(file)
                
        migration_files.sort()
        
        applied_now = []
        
        for file in migration_files:
            version = int(file[:3])
            filepath = os.path.join(migrations_dir, file)
            checksum = get_file_checksum(filepath)
            
            if version in applied:
                if applied[version] != checksum:
                    raise ValueError(
                        f"Checksum drift detected for migration version {version} ({file}). "
                        f"Expected {applied[version]}, got {checksum}."
                    )
                logger.debug(f"Migration version {version} ({file}) is already applied.")
                continue
                
            logger.info(f"Applying migration version {version} ({file})...")
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
                
            # Execute migration script
            conn.executescript(sql)
            
            # Record migration
            conn.execute(
                "INSERT INTO schema_migrations (version, name, checksum) VALUES (?, ?, ?);",
                (version, file, checksum)
            )
            conn.commit()
            applied_now.append(file)
            
        return applied_now
    finally:
        conn.close()
