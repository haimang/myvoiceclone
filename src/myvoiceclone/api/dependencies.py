import sqlite3
from myvoiceclone.config import resolve_db_path
from myvoiceclone.storage.sqlite import get_connection


def get_db():
    """FastAPI dependency that yields a SQLite connection with vec extension loaded.

    V14 fix: Now uses config.resolve_db_path() to correctly resolve relative db_path
    to absolute path from project root. Previously, relative paths were passed directly
    to sqlite3.connect(), causing DB to be created in the CWD instead of project root.
    """
    db_path = resolve_db_path()
    conn = get_connection(db_path, load_vec=True)
    try:
        yield conn
    finally:
        conn.close()
