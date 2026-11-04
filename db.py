"""Optional SQLite history. Keyed by a nickname (not authentication)."""
import json, sqlite3
from datetime import datetime

DB_PATH = "imtihan.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, profile TEXT, ts TEXT, title TEXT, "
              "subject TEXT, mode TEXT, score REAL, max REAL, secs INTEGER, topics TEXT)")
    return c


def save_attempt(profile: str, title: str, subject: str, mode: str, score: float, mx: float,
                 secs: int, topics: dict[str, float]) -> None:
    with _conn() as c:
        c.execute("INSERT INTO attempts(profile,ts,title,subject,mode,score,max,secs,topics) VALUES(?,?,?,?,?,?,?,?,?)",
                  (profile, datetime.now().isoformat(timespec="minutes"), title, subject, mode, score, mx, secs,
                   json.dumps(topics)))


def history(profile: str) -> list[dict]:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM attempts WHERE profile=? ORDER BY ts", (profile,)).fetchall()
    return [dict(r) | {"topics": json.loads(r["topics"] or "{}")} for r in rows]
