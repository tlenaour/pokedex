"""ReportMissingResult use case: the repositories are mocked."""

from unittest.mock import MagicMock, create_autospec

import pytest

from fullstack_pokedex.domain.errors import InvalidReportError
from fullstack_pokedex.domain.feedback import MissingResultReport, SearchKind
from fullstack_pokedex.domain.repositories import (
    FeedbackRepository,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.report_missing_result import ReportMissingResult
from tests.factories import make_pokemon

KNOWN = {4: make_pokemon(id=4, name="charmander"), 5: make_pokemon(id=5)}


@pytest.fixture
def feedback() -> MagicMock:
    feedback = create_autospec(FeedbackRepository, instance=True)
    feedback.add.return_value = 42
    return feedback


@pytest.fixture
def pokemon() -> MagicMock:
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.get_many.side_effect = lambda ids: [KNOWN[i] for i in ids if i in KNOWN]
    return pokemon


@pytest.fixture
def report_use_case(feedback: MagicMock, pokemon: MagicMock) -> ReportMissingResult:
    return ReportMissingResult(feedback=feedback, pokemon=pokemon)


def test_saves_the_cleaned_up_report_and_returns_its_id(
    report_use_case: ReportMissingResult, feedback: MagicMock
) -> None:
    report = MissingResultReport(SearchKind.NAME, "  char ", (5, 4))

    assert report_use_case.execute(report) == 42

    feedback.add.assert_called_once_with(
        MissingResultReport(SearchKind.NAME, "char", (5, 4))
    )


def test_a_search_without_results_needs_no_pokemon_lookup(
    report_use_case: ReportMissingResult, feedback: MagicMock, pokemon: MagicMock
) -> None:
    report_use_case.execute(MissingResultReport(SearchKind.APPEARANCE, "xyz", ()))

    pokemon.get_many.assert_not_called()
    feedback.add.assert_called_once()


def test_invalid_report_is_rejected_before_any_access(
    report_use_case: ReportMissingResult, feedback: MagicMock, pokemon: MagicMock
) -> None:
    with pytest.raises(InvalidReportError):
        report_use_case.execute(MissingResultReport(SearchKind.NAME, " ", (4,)))

    pokemon.get_many.assert_not_called()
    feedback.add.assert_not_called()


def test_unknown_pokemon_are_rejected_without_saving(
    report_use_case: ReportMissingResult, feedback: MagicMock
) -> None:
    with pytest.raises(InvalidReportError, match=r"unknown Pokémon ids: \[998, 999\]"):
        report_use_case.execute(
            MissingResultReport(SearchKind.NAME, "char", (999, 4, 998))
        )

    feedback.add.assert_not_called()
