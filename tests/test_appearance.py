"""Domain rules of appearance identification (no model, no database)."""

import math

import pytest

from fullstack_pokedex.domain.appearance import (
    MAX_DESCRIPTION_LENGTH,
    AppearanceCandidate,
    AppearanceDescription,
    cosine_similarity,
    rank_by_appearance,
    validate_description,
)
from fullstack_pokedex.domain.errors import InvalidSearchQueryError

# --- Reference text --------------------------------------------------------------


def test_reference_text_joins_the_three_descriptions() -> None:
    description = AppearanceDescription(
        pokemon_id=25,
        glance="small yellow mouse",
        detailed="red cheeks; lightning tail",
        everyday="looks like a hamster",
    )
    assert description.reference_text == (
        "small yellow mouse. red cheeks; lightning tail. looks like a hamster"
    )


# --- Validation ------------------------------------------------------------------


def test_validation_collapses_whitespace() -> None:
    assert validate_description("  small \n yellow\tmouse ") == "small yellow mouse"


@pytest.mark.parametrize("text", ["", "   ", "!!!", "--- ..."])
def test_description_without_letters_is_rejected(text: str) -> None:
    with pytest.raises(InvalidSearchQueryError, match="no letter or digit"):
        validate_description(text)


def test_too_long_description_is_rejected() -> None:
    assert validate_description("a" * MAX_DESCRIPTION_LENGTH)
    with pytest.raises(InvalidSearchQueryError, match="longer than"):
        validate_description("a" * (MAX_DESCRIPTION_LENGTH + 1))


def test_length_is_measured_after_collapsing_whitespace() -> None:
    assert validate_description(" " * 500 + "yellow mouse") == "yellow mouse"


# --- Cosine similarity -----------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ([1.0, 0.0], [2.0, 0.0], 1.0),  # same direction, any length
        ([1.0, 0.0], [0.0, 3.0], 0.0),  # orthogonal
        ([1.0, 2.0], [-1.0, -2.0], -1.0),  # opposite
        ([1.0, 1.0], [1.0, 0.0], 1 / math.sqrt(2)),
    ],
)
def test_cosine_similarity(a: list[float], b: list[float], expected: float) -> None:
    assert cosine_similarity(a, b) == pytest.approx(expected)


def test_cosine_similarity_with_a_zero_vector_is_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_cosine_similarity_rejects_vectors_of_different_sizes() -> None:
    with pytest.raises(ValueError, match="different sizes"):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


# --- Ranking ---------------------------------------------------------------------

CANDIDATES = [
    AppearanceCandidate(1, [1.0, 0.0, 0.0]),
    AppearanceCandidate(2, [0.9, 0.1, 0.0]),
    AppearanceCandidate(3, [0.0, 1.0, 0.0]),
    AppearanceCandidate(4, [-1.0, 0.0, 0.0]),
]


def test_ranks_closest_first() -> None:
    ranked = rank_by_appearance([1.0, 0.0, 0.0], CANDIDATES, limit=4)
    assert [m.pokemon_id for m in ranked] == [1, 2, 3, 4]
    assert ranked[0].score == pytest.approx(1.0)
    assert ranked[-1].score == pytest.approx(-1.0)


def test_limit_keeps_the_best() -> None:
    ranked = rank_by_appearance([0.0, 1.0, 0.0], CANDIDATES, limit=2)
    assert [m.pokemon_id for m in ranked] == [3, 2]


def test_ties_are_broken_by_pokedex_number() -> None:
    candidates = [
        AppearanceCandidate(7, [1.0, 0.0]),
        AppearanceCandidate(3, [2.0, 0.0]),
    ]
    ranked = rank_by_appearance([1.0, 0.0], candidates, limit=2)
    assert [m.pokemon_id for m in ranked] == [3, 7]


def test_ranking_does_not_depend_on_candidate_order() -> None:
    query = [0.5, 0.5, 0.0]
    assert rank_by_appearance(query, CANDIDATES, 4) == rank_by_appearance(
        query, list(reversed(CANDIDATES)), 4
    )


def test_no_candidates_gives_no_match() -> None:
    assert rank_by_appearance([1.0], [], limit=5) == []


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_must_be_positive(limit: int) -> None:
    with pytest.raises(ValueError, match="limit"):
        rank_by_appearance([1.0, 0.0, 0.0], CANDIDATES, limit)
