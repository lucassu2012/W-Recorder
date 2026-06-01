"""SQLite 存储层。

两张表：
- activity_samples: 每 5 分钟一次的活动窗口快照
- meetings: 当日 Outlook 日历会议
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator

from . import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_samples (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sampled_at    TEXT    NOT NULL,
    process_name  TEXT    NOT NULL,
    process_path  TEXT,
    window_title  TEXT,
    category      TEXT,
    is_idle       INTEGER NOT NULL DEFAULT 0,
    idle_seconds  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_activity_sampled_at ON activity_samples(sampled_at);

CREATE TABLE IF NOT EXISTS meetings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id     TEXT    UNIQUE,
    subject      TEXT    NOT NULL,
    start_at     TEXT    NOT NULL,
    end_at       TEXT    NOT NULL,
    organizer    TEXT,
    location     TEXT,
    is_meeting   INTEGER NOT NULL DEFAULT 1,
    body_preview TEXT,
    synced_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meetings_start_at ON meetings(start_at);
"""


def _isoformat(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat(sep=" ")


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(db_path) if db_path else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_activity_sample(
    *,
    sampled_at: datetime,
    process_name: str,
    process_path: str | None,
    window_title: str | None,
    category: str | None,
    is_idle: bool,
    idle_seconds: int,
    db_path: Path | None = None,
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO activity_samples
                (sampled_at, process_name, process_path, window_title,
                 category, is_idle, idle_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _isoformat(sampled_at),
                process_name,
                process_path,
                window_title,
                category,
                1 if is_idle else 0,
                int(idle_seconds),
            ),
        )
        return int(cur.lastrowid or 0)


def fetch_samples_for_day(
    day: date,
    db_path: Path | None = None,
) -> list[sqlite3.Row]:
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    with connect(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT * FROM activity_samples
                 WHERE sampled_at >= ? AND sampled_at < ?
                 ORDER BY sampled_at ASC
                """,
                (_isoformat(start), _isoformat(end)),
            )
        )


def upsert_meetings(
    meetings: Iterable[dict],
    db_path: Path | None = None,
) -> int:
    count = 0
    now = _isoformat(datetime.now())
    with connect(db_path) as conn:
        for m in meetings:
            conn.execute(
                """
                INSERT INTO meetings
                    (entry_id, subject, start_at, end_at, organizer,
                     location, is_meeting, body_preview, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_id) DO UPDATE SET
                    subject      = excluded.subject,
                    start_at     = excluded.start_at,
                    end_at       = excluded.end_at,
                    organizer    = excluded.organizer,
                    location     = excluded.location,
                    is_meeting   = excluded.is_meeting,
                    body_preview = excluded.body_preview,
                    synced_at    = excluded.synced_at
                """,
                (
                    m.get("entry_id"),
                    m.get("subject") or "(无主题)",
                    m["start_at"],
                    m["end_at"],
                    m.get("organizer"),
                    m.get("location"),
                    1 if m.get("is_meeting", True) else 0,
                    m.get("body_preview"),
                    now,
                ),
            )
            count += 1
    return count


def fetch_meetings_for_day(
    day: date,
    db_path: Path | None = None,
) -> list[sqlite3.Row]:
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    with connect(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT * FROM meetings
                 WHERE start_at < ? AND end_at > ?
                 ORDER BY start_at ASC
                """,
                (_isoformat(end), _isoformat(start)),
            )
        )


def last_sample_at(db_path: Path | None = None) -> datetime | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT sampled_at FROM activity_samples ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return datetime.fromisoformat(row["sampled_at"])


def total_samples(db_path: Path | None = None) -> int:
    with connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM activity_samples").fetchone()
    return int(row["n"])
