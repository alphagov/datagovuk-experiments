from datetime import datetime, timezone
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "prospector.db")

def get_connection():
    return sqlite3.connect(DB_PATH)


def setup_db() -> sqlite3.Connection:
    """Create the database and table if they don't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            url            TEXT PRIMARY KEY,
            status_code    INTEGER,
            html           TEXT,
            error          TEXT,
            fetched_at     TEXT,
            dataset_score DECIMAL(10, 2)
        )
    """)
    conn.commit()
    return conn


def persist_page(
    url: str,
    status_code: int | None, html: str | None,
    error: str | None
):
    """Insert or update a row in the pages table."""
    conn = get_connection()
    fetched_at = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO pages (url, status_code, html, error, fetched_at)
        VALUES (?, ?, ?, ?, ?)
    """, (url, status_code, html, error, fetched_at))
    conn.commit()


