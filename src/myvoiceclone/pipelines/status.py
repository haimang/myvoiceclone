import sqlite3


def mark_recording_status(conn: sqlite3.Connection, recording_id: str, status: str) -> None:
    conn.execute("UPDATE recordings SET status = ? WHERE id = ?;", (status, recording_id))
