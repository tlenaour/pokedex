from unittest.mock import MagicMock, create_autospec

import pytest

from fullstack_pokedex.domain.errors import InvalidSearchQueryError
from fullstack_pokedex.domain.name_search import (
    FUZZY_THRESHOLD,
    MAX_QUERY_LENGTH,
    MatchKind,
    NameCandidate,
    SimilarityScorer,
    normalize_query,
    rank_candidates,
)

# Real Pokédex numbers and slugs, chosen for their tricky names.
CANDIDATES = [
    NameCandidate(1, "bulbasaur"),
    NameCandidate(2, "ivysaur"),
    NameCandidate(3, "venusaur"),
    NameCandidate(25, "pikachu"),
    NameCandidate(26, "raichu"),
    NameCandidate(29, "nidoran-f"),
    NameCandidate(30, "nidorina"),
    NameCandidate(32, "nidoran-m"),
    NameCandidate(33, "nidorino"),
    NameCandidate(83, "farfetchd"),
    NameCandidate(122, "mr-mime"),
    NameCandidate(150, "mewtwo"),
    NameCandidate(151, "mew"),
]


def names(query: str, limit: int = 10, **kwargs: object) -> list[str]:
    return [m.name for m in rank_candidates(query, CANDIDATES, limit, **kwargs)]


def scorer_returning(scores: dict[str, float]) -> MagicMock:
    """Scorer mock: similarity per normalized name, 0.0 for the others."""
    scorer = create_autospec(SimilarityScorer, instance=True)
    scorer.score.side_effect = lambda query, name: scores.get(name, 0.0)
    return scorer


# --- normalize_query -------------------------------------------------------------


def test_normalize_query_returns_the_normalized_form() -> None:
    assert normalize_query("  Bulba ") == "bulba"


@pytest.mark.parametrize("text", ["", "   ", "!!!", "%_"])
def test_normalize_query_rejects_queries_without_letters(text: str) -> None:
    with pytest.raises(InvalidSearchQueryError, match="no letter or digit"):
        normalize_query(text)


def test_normalize_query_rejects_too_long_queries() -> None:
    assert normalize_query("a" * MAX_QUERY_LENGTH)
    with pytest.raises(InvalidSearchQueryError, match="longer than"):
        normalize_query("a" * (MAX_QUERY_LENGTH + 1))


def test_query_length_is_measured_after_normalization() -> None:
    # Spaces and punctuation do not count.
    assert normalize_query(" - " * 100 + "bulba") == "bulba"


# --- The feature's scenario ------------------------------------------------------


def test_bulba_finds_bulbasaur() -> None:
    [match] = rank_candidates("bulba", CANDIDATES, limit=5)

    assert match.pokemon_id == 1
    assert match.kind is MatchKind.PREFIX
    assert match.span == (0, 5)  # "[bulba]saur"


@pytest.mark.parametrize("query", ["BULBA", "  Bulba ", "bülba", "ｂｕｌｂａ"])
def test_bulba_is_found_whatever_the_typing(query: str) -> None:
    assert names(query) == ["bulbasaur"]


# --- Each match kind -------------------------------------------------------------


@pytest.mark.parametrize(
    "query, name, kind, span",
    [
        # Spans are in the normalized name ("mr-mime" -> "mrmime").
        ("bulbasaur", "bulbasaur", MatchKind.EXACT, (0, 9)),
        ("Mr. Mime", "mr-mime", MatchKind.EXACT, (0, 6)),
        ("Nidoran♀", "nidoran-f", MatchKind.EXACT, (0, 8)),
        ("Farfetch'd", "farfetchd", MatchKind.EXACT, (0, 9)),
        ("pika", "pikachu", MatchKind.PREFIX, (0, 4)),
        ("mrmi", "mr-mime", MatchKind.PREFIX, (0, 4)),  # spans the hyphen
        ("mime", "mr-mime", MatchKind.WORD_PREFIX, (2, 6)),  # "mr[mime]"
        ("venu", "venusaur", MatchKind.PREFIX, (0, 4)),
        ("tchd", "farfetchd", MatchKind.SUBSTRING, (5, 9)),
    ],
)
def test_match_kind_and_span(
    query: str, name: str, kind: MatchKind, span: tuple[int, int]
) -> None:
    match = next(m for m in rank_candidates(query, CANDIDATES, 10) if m.name == name)
    assert match.kind is kind
    assert match.span == span
    assert match.score == 1.0


def test_no_match_returns_an_empty_list() -> None:
    assert rank_candidates("xyz", CANDIDATES, limit=5) == []


def test_no_candidates_returns_an_empty_list() -> None:
    assert rank_candidates("bulba", [], limit=5) == []


# --- Ordering --------------------------------------------------------------------


def test_match_kinds_are_ordered_by_priority() -> None:
    # Ids are in reverse order to prove they do not drive the ranking.
    candidates = [
        NameCandidate(1, "xabc"),  # substring
        NameCandidate(2, "x-abc"),  # word prefix
        NameCandidate(3, "abcd"),  # prefix
        NameCandidate(4, "abc"),  # exact
    ]
    ranked = rank_candidates("abc", candidates, limit=10)
    assert [m.kind for m in ranked] == [
        MatchKind.EXACT,
        MatchKind.PREFIX,
        MatchKind.WORD_PREFIX,
        MatchKind.SUBSTRING,
    ]


def test_exact_match_comes_before_longer_names() -> None:
    assert names("mew") == ["mew", "mewtwo"]


def test_prefix_beats_word_prefix() -> None:
    # "f" starts farfetchd, and only the second word of nidoran-f.
    assert names("f") == ["farfetchd", "nidoran-f"]


def test_same_kind_prefers_the_closest_length() -> None:
    # ivysaur (7) < venusaur (8) < bulbasaur (9) for "saur" (4).
    assert names("saur") == ["ivysaur", "venusaur", "bulbasaur"]
    assert names("chu") == ["raichu", "pikachu"]


def test_ties_are_broken_by_pokedex_number() -> None:
    # Four 8-letter names starting with "nido".
    assert names("nido") == ["nidoran-f", "nidorina", "nidoran-m", "nidorino"]


def test_ranking_does_not_depend_on_candidate_order() -> None:
    reversed_candidates = list(reversed(CANDIDATES))
    for query in ("nido", "saur", "mew", "f"):
        assert rank_candidates(query, reversed_candidates, 10) == rank_candidates(
            query, CANDIDATES, 10
        )


# --- Limit -----------------------------------------------------------------------


def test_limit_keeps_the_best_matches() -> None:
    assert names("nido", limit=2) == ["nidoran-f", "nidorina"]


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_must_be_positive(limit: int) -> None:
    with pytest.raises(ValueError, match="limit"):
        rank_candidates("bulba", CANDIDATES, limit)


def test_invalid_query_is_rejected() -> None:
    with pytest.raises(InvalidSearchQueryError):
        rank_candidates("  !! ", CANDIDATES, limit=5)


# --- Fuzzy matching (scorer port mocked) -----------------------------------------


def test_typo_is_found_by_fuzzy_matching() -> None:
    scorer = scorer_returning({"bulbasaur": 0.93})

    [match] = rank_candidates("bulbsaur", CANDIDATES, limit=5, scorer=scorer)

    assert match.name == "bulbasaur"
    assert match.kind is MatchKind.FUZZY
    assert match.score == 0.93
    assert match.span is None


def test_scorer_receives_normalized_strings() -> None:
    scorer = scorer_returning({})

    rank_candidates("Mr. Mimme", CANDIDATES, limit=5, scorer=scorer)

    scorer.score.assert_any_call("mrmimme", "mrmime")


def test_fuzzy_threshold_is_inclusive() -> None:
    scorer = scorer_returning(
        {"bulbasaur": FUZZY_THRESHOLD, "ivysaur": FUZZY_THRESHOLD - 0.01}
    )
    assert names("bulbsaur", scorer=scorer) == ["bulbasaur"]


def test_fuzzy_threshold_can_be_tuned() -> None:
    scorer = scorer_returning({"bulbasaur": 0.7})
    assert names("bulbsaur", scorer=scorer) == []
    assert names("bulbsaur", scorer=scorer, fuzzy_threshold=0.6) == ["bulbasaur"]


def test_fuzzy_matches_are_ordered_by_score() -> None:
    scorer = scorer_returning({"venusaur": 0.88, "bulbasaur": 0.95, "ivysaur": 0.9})
    assert names("vbulsaur", scorer=scorer) == ["bulbasaur", "ivysaur", "venusaur"]


def test_strict_matches_always_come_before_fuzzy_ones() -> None:
    # Even a perfect fuzzy score ranks after a substring match.
    scorer = scorer_returning({"mewtwo": 1.0, "pikachu": 1.0})
    ranked = rank_candidates("mew", CANDIDATES, limit=5, scorer=scorer)
    assert [(m.name, m.kind) for m in ranked] == [
        ("mew", MatchKind.EXACT),
        ("mewtwo", MatchKind.PREFIX),
        ("pikachu", MatchKind.FUZZY),
    ]


def test_strict_matches_are_not_scored_again() -> None:
    scorer = scorer_returning({})

    rank_candidates("mew", CANDIDATES, limit=5, scorer=scorer)

    scored = {call.args[1] for call in scorer.score.call_args_list}
    assert "mew" not in scored
    assert "mewtwo" not in scored
    assert len(scored) == len(CANDIDATES) - 2


def test_scorer_is_not_called_when_strict_matches_fill_the_limit() -> None:
    scorer = scorer_returning({})

    rank_candidates("nido", CANDIDATES, limit=2, scorer=scorer)

    scorer.score.assert_not_called()


def test_no_fuzzy_matching_without_scorer() -> None:
    assert names("bulbsaur") == []
