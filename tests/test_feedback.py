"""Feedback domain rules: what a 'missing result' report may contain."""

import pytest

from fullstack_pokedex.domain.errors import InvalidReportError
from fullstack_pokedex.domain.feedback import (
    MAX_QUERY_LENGTH,
    MAX_SHOWN_POKEMON,
    MissingResultReport,
    SearchKind,
    validate_report,
)


def report(query: str = "char", shown_ids: tuple[int, ...] = (4, 5)):
    return MissingResultReport(SearchKind.NAME, query, shown_ids)


def test_valid_report_is_kept() -> None:
    assert validate_report(report()) == report()


def test_whitespace_is_cleaned_up() -> None:
    cleaned = validate_report(report("  small   yellow\nmouse "))
    assert cleaned.query == "small yellow mouse"


def test_a_search_without_results_can_be_reported() -> None:
    assert validate_report(report(shown_ids=())).shown_ids == ()


def test_limits_are_inclusive() -> None:
    validate_report(
        report("a" * MAX_QUERY_LENGTH, tuple(range(1, MAX_SHOWN_POKEMON + 1)))
    )


@pytest.mark.parametrize(
    "bad, reason",
    [
        (report(""), "empty"),
        (report("   "), "empty"),
        (report("a" * (MAX_QUERY_LENGTH + 1)), "longer than"),
        (report(shown_ids=tuple(range(1, MAX_SHOWN_POKEMON + 2))), "more than"),
        (report(shown_ids=(4, 4)), "twice"),
    ],
)
def test_invalid_reports_are_rejected(bad: MissingResultReport, reason: str) -> None:
    with pytest.raises(InvalidReportError, match=reason):
        validate_report(bad)


def test_search_kinds_match_the_api_values() -> None:
    assert [k.value for k in SearchKind] == ["name", "appearance"]
