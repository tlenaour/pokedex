"""Feedback storage: a separate, read-write SQLite database (feedback.db)."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from fullstack_pokedex.domain.feedback import MissingResultReport

SCHEMA = Path(__file__).with_name("feedback_schema.sql")


def init_feedback_db(path: Path) -> None:
    """Create the database and its tables if missing; keep existing data."""
    with closing(sqlite3.connect(path)) as conn:
        # WAL: a write does not block concurrent reads.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def connect_feedback_db(path: Path) -> sqlite3.Connection:
    """Read-write connection to an existing feedback database (see init)."""
    return sqlite3.connect(
        # as_uri(): a "?", "#" or "%" in the path must not break the URI.
        f"{path.resolve().as_uri()}?mode=rw",
        uri=True,
        # FastAPI may create the connection and use it in different threads
        # (one connection per request, never used concurrently).
        check_same_thread=False,
    )


class SqliteFeedbackRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, report: MissingResultReport) -> int:
        with self._conn:  # commit, or rollback on error
            cursor = self._conn.execute(
                "INSERT INTO missing_result_report (kind, query, shown_ids)"
                " VALUES (?, ?, ?)",
                (report.kind.value, report.query, json.dumps(list(report.shown_ids))),
            )
        assert cursor.lastrowid is not None
        return cursor.lastrowid
