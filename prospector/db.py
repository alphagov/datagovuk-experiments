from datetime import datetime, timezone
import os
import sqlite3
import json

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
            dataset_score DECIMAL(10, 2),
            dataset_rules_matched TEXT CHECK (dataset_rules_matched IS NULL OR json_valid(dataset_rules_matched))
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


def get_pages() -> list[tuple[str, int | None, str | None, str | None]]:
    """Return all pages as (url, status_code, html, error) tuples."""
    conn = get_connection()
    return conn.execute(
        "SELECT url, status_code, html, error FROM pages"
    ).fetchall()


def update_dataset_score(url: str, score: float, matched_rules) -> None:
    """Update the dataset_score for a given URL."""
    conn = get_connection()
    conn.execute(
        "UPDATE pages SET dataset_score = ?, dataset_rules_matched= ? WHERE url = ?",
        (score, json.dumps(matched_rules), url),
    )
    conn.commit()


