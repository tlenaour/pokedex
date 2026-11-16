"""Product feedback: a trainer says a search did not show what they wanted.

Saved to improve the searches later (e.g. turn real failed searches into
evaluation cases); for now they are only recorded.
"""

from dataclasses import dataclass
from enum import StrEnum

from fullstack_pokedex.domain.errors import InvalidReportError

MAX_QUERY_LENGTH = 300
MAX_SHOWN_POKEMON = 10


class SearchKind(StrEnum):
    NAME = "name"
    APPEARANCE = "appearance"


@dataclass(frozen=True)
class MissingResultReport:
    """'I did not find my Pokémon' for one search, with what it showed."""

    kind: SearchKind
    query: str
    shown_ids: tuple[int, ...]
    """Pokémon displayed when the trainer reported, in display order."""


def validate_report(report: MissingResultReport) -> MissingResultReport:
    """The report to save, cleaned up; raises InvalidReportError."""
    query = " ".join(report.query.split())
    if not query:
        raise InvalidReportError("the search text is empty")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidReportError(
            f"the search text is longer than {MAX_QUERY_LENGTH} characters"
        )
    if len(report.shown_ids) > MAX_SHOWN_POKEMON:
        raise InvalidReportError(f"more than {MAX_SHOWN_POKEMON} Pokémon shown")
    if len(set(report.shown_ids)) != len(report.shown_ids):
        raise InvalidReportError("a Pokémon is shown twice")
    return MissingResultReport(report.kind, query, tuple(report.shown_ids))
