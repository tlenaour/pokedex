"""Feedback storage on a real SQLite file (feedback.db)."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from fullstack_pokedex.domain.feedback import MissingResultReport, SearchKind
from fullstack_pokedex.infrastructure.sqlite.feedback import (
    SqliteFeedbackRepository,
    connect_feedback_db,
    init_feedback_db,
)

REPORT = MissingResultReport(SearchKind.APPEARANCE, "blue noodles", (7, 12, 60))


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "feedback.db"
    init_feedback_db(path)
    return path


@pytest.fixture
def conn(db: Path) -> Iterator[sqlite3.Connection]:
    conn = connect_feedback_db(db)
    yield conn
    conn.close()


def rows(db: Path) -> list[tuple]:
    with sqlite3.connect(db) as check:
        result = check.execute(
            "SELECT id, kind, query, shown_ids, created_at FROM missing_result_report"
        ).fetchall()
    check.close()
    return result


def test_add_saves_the_report_with_a_date(db: Path, conn: sqlite3.Connection) -> None:
    report_id = SqliteFeedbackRepository(conn).add(REPORT)

    [(row_id, kind, query, shown_ids, created_at)] = rows(db)
    assert row_id == report_id
    assert (kind, query) == ("appearance", "blue noodles")
    assert json.loads(shown_ids) == [7, 12, 60]  # display order kept
    assert created_at  # set by the database


def test_ids_are_distinct(conn: sqlite3.Connection) -> None:
    repository = SqliteFeedbackRepository(conn)
    assert repository.add(REPORT) != repository.add(REPORT)


def test_init_keeps_existing_reports(db: Path, conn: sqlite3.Connection) -> None:
    """Restarting the API must never erase feedback."""
    SqliteFeedbackRepository(conn).add(REPORT)

    init_feedback_db(db)

    assert len(rows(db)) == 1


def test_database_rejects_an_unknown_search_kind(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO missing_result_report (kind, query, shown_ids)"
            " VALUES ('other', 'x', '[]')"
        )


def test_connect_does_not_create_a_missing_database(tmp_path: Path) -> None:
    with pytest.raises(sqlite3.OperationalError):
        connect_feedback_db(tmp_path / "missing.db")


def test_feedback_db_in_a_folder_with_uri_characters(tmp_path: Path) -> None:
    folder = tmp_path / "odd ?#%41 name"
    folder.mkdir()
    path = folder / "feedback.db"
    init_feedback_db(path)

    with closing(connect_feedback_db(path)) as conn:
        report = MissingResultReport(SearchKind.NAME, "nido", (29,))
        assert SqliteFeedbackRepository(conn).add(report) == 1
