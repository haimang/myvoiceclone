import sqlite3
import os
import logging
from typing import Generator

logger = logging.getLogger("myvoiceclone.storage.sqlite")

def load_vector_extension(conn: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
        logger.info("Successfully loaded sqlite-vec extension.")
        return True
    except ImportError:
        logger.warning("sqlite-vec package is not installed. Vector virtual tables will not work.")
        return False
    except Exception as e:
        logger.error(f"Failed to load sqlite-vec extension: {e}")
        return False

def get_connection(db_path: str, load_vec: bool = True) -> sqlite3.Connection:
    # Ensure parent directory exists for file-based DB
    if db_path != ":memory:" and not os.path.exists(os.path.dirname(db_path)) and os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    # In-memory databases do not support WAL journal mode.
    if db_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.row_factory = sqlite3.Row
    
    if load_vec:
        load_vector_extension(conn)
        
    return conn

class SQLiteSessionManager:
    def __init__(self, db_path: str, load_vec: bool = True):
        self.db_path = db_path
        self.load_vec = load_vec

    def session(self) -> Generator[sqlite3.Connection, None, None]:
        conn = get_connection(self.db_path, self.load_vec)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
