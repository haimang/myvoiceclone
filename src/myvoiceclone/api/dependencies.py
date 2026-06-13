import sqlite3
from myvoiceclone.config import load_local_config
from myvoiceclone.storage.sqlite import get_connection

def get_db():
    config = load_local_config()
    db_path = config.get("db_path", "db/myvoiceclone.sqlite")
    conn = get_connection(db_path, load_vec=True)
    try:
        yield conn
    finally:
        conn.close()
