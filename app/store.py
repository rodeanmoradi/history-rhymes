import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone

from app.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    source TEXT,
    url TEXT,
    status TEXT NOT NULL,
    steps TEXT NOT NULL DEFAULT '[]',
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def lesson_id(headline):
    normalized = re.sub(r"\W+", " ", headline.lower()).strip()
    return hashlib.sha1(normalized.encode()).hexdigest()[:12]


def get(id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM lessons WHERE id = ?", (id,)).fetchone()
    if row is None:
        return None
    record = dict(row)
    record["steps"] = json.loads(record["steps"])
    record["result"] = json.loads(record["result"]) if record["result"] else None
    return record


def create(id, headline, source, url):
    """Insert a queued lesson. Returns False if it already exists."""
    with connect() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO lessons (id, headline, source, url, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'queued', ?, ?)",
            (id, headline, source, url, now(), now()),
        )
        return cursor.rowcount == 1


def requeue(id):
    with connect() as conn:
        conn.execute(
            "UPDATE lessons SET status = 'queued', steps = '[]', error = NULL, updated_at = ? WHERE id = ?",
            (now(), id),
        )


def add_step(id, message):
    with connect() as conn:
        steps = json.loads(conn.execute("SELECT steps FROM lessons WHERE id = ?", (id,)).fetchone()["steps"])
        steps.append({"at": now(), "message": message})
        conn.execute(
            "UPDATE lessons SET status = 'running', steps = ?, updated_at = ? WHERE id = ?",
            (json.dumps(steps), now(), id),
        )


def finish(id, result):
    with connect() as conn:
        conn.execute(
            "UPDATE lessons SET status = 'done', result = ?, updated_at = ? WHERE id = ?",
            (json.dumps(result, ensure_ascii=False), now(), id),
        )


def fail(id, error):
    with connect() as conn:
        conn.execute(
            "UPDATE lessons SET status = 'failed', error = ?, updated_at = ? WHERE id = ?", (error, now(), id)
        )


def recent(limit=10):
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, headline, source, result, created_at FROM lessons WHERE status = 'done' "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        result = json.loads(row["result"])
        out.append({
            "id": row["id"],
            "headline": row["headline"],
            "source": row["source"],
            "title": result["lesson"]["title"],
            "created_at": row["created_at"],
        })
    return out


def created_today():
    today = datetime.now(timezone.utc).date().isoformat()
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM lessons WHERE created_at >= ?", (today,)).fetchone()[0]


def interrupted():
    """Lessons left queued/running by a previous process, which the server marks failed on startup."""
    with connect() as conn:
        return [r["id"] for r in conn.execute("SELECT id FROM lessons WHERE status IN ('queued', 'running')")]
