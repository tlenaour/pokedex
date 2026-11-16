"""JaroWinklerScorer: the real rapidfuzz implementation of SimilarityScorer."""

import pytest

from fullstack_pokedex.domain.name_search import FUZZY_THRESHOLD, SimilarityScorer
from fullstack_pokedex.infrastructure.similarity import JaroWinklerScorer

scorer = JaroWinklerScorer()


def test_implements_the_port() -> None:
    port_methods = {n for n in vars(SimilarityScorer) if not n.startswith("_")}
    assert all(hasattr(JaroWinklerScorer, n) for n in port_methods)


def test_identical_names_score_one() -> None:
    assert scorer.score("bulbasaur", "bulbasaur") == 1.0


def test_nothing_in_common_scores_zero() -> None:
    assert scorer.score("xyz", "bulbasaur") == 0.0


@pytest.mark.parametrize(
    "query, name", [("bulbsaur", "bulbasaur"), ("a", "abra"), ("", "mew")]
)
def test_score_is_between_zero_and_one(query: str, name: str) -> None:
    assert 0.0 <= scorer.score(query, name) <= 1.0


def test_score_is_symmetric() -> None:
    assert scorer.score("pikachoo", "pikachu") == scorer.score("pikachu", "pikachoo")


# Cases from the benchmark (docs/benchmark-fuzzy-name-matching.md), with the
# domain threshold: they document what the chosen measure does and does not do.


@pytest.mark.parametrize(
    "query, name",
    [
        ("bulbsaur", "bulbasaur"),  # deletion
        ("vulbasaur", "bulbasaur"),  # first letter wrong
        ("bulbs", "bulbasaur"),  # short beginning + typo
        ("pikachoo", "pikachu"),  # phonetic
        ("ninetails", "ninetales"),  # phonetic, classic mistake
        ("onyx", "onix"),  # 4-letter name
        ("mewtoo", "mewtwo"),
    ],
)
def test_typos_reach_the_threshold(query: str, name: str) -> None:
    assert scorer.score(query, name) >= FUZZY_THRESHOLD


@pytest.mark.parametrize(
    "query, name",
    [
        ("xyz", "ivysaur"),
        ("bulbsaur", "ivysaur"),  # a typo must not match a sibling name
        ("pikachoo", "ivysaur"),
        ("mwe", "mew"),  # known limit: 3-letter names with a transposition
    ],
)
def test_unrelated_names_stay_below_the_threshold(query: str, name: str) -> None:
    assert scorer.score(query, name) < FUZZY_THRESHOLD
