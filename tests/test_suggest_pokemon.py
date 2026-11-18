"""SuggestPokemon use case: the repository and the scorer are mocked."""

from unittest.mock import MagicMock, create_autospec

import pytest

from fullstack_pokedex.domain.entities import Images, PokemonType
from fullstack_pokedex.domain.errors import InvalidSearchQueryError
from fullstack_pokedex.domain.name_search import (
    MatchKind,
    NameCandidate,
    NameSegment,
    SimilarityScorer,
)
from fullstack_pokedex.domain.repositories import PokemonRepository
from fullstack_pokedex.use_cases.suggest_pokemon import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_LIMIT,
    PokemonSuggestion,
    SuggestPokemon,
    SuggestPokemonQuery,
)
from tests.factories import make_pokemon

POKEMON = {
    1: make_pokemon(
        id=1,
        name="bulbasaur",
        types=(PokemonType.GRASS, PokemonType.POISON),
        images=Images(
            sprite="https://example.com/1.png",
            official_artwork="https://example.com/1-art.png",
        ),
    ),
    2: make_pokemon(id=2, name="ivysaur"),
    3: make_pokemon(id=3, name="venusaur"),
    29: make_pokemon(id=29, name="nidoran-f"),
    30: make_pokemon(id=30, name="nidorina"),
    32: make_pokemon(id=32, name="nidoran-m"),
    33: make_pokemon(id=33, name="nidorino"),
    34: make_pokemon(id=34, name="nidoking"),
    122: make_pokemon(id=122, name="mr-mime"),
    150: make_pokemon(id=150, name="mewtwo"),
    151: make_pokemon(id=151, name="mew"),
}


@pytest.fixture
def repository() -> MagicMock:
    repository = create_autospec(PokemonRepository, instance=True)
    repository.list_name_candidates.return_value = [
        NameCandidate(p.id, p.name) for p in POKEMON.values()
    ]
    repository.get_many.side_effect = lambda ids: [POKEMON[i] for i in ids]
    return repository


@pytest.fixture
def suggest(repository: MagicMock) -> SuggestPokemon:
    return SuggestPokemon(pokemon=repository)


def names(suggestions: list[PokemonSuggestion]) -> list[str]:
    return [s.name for s in suggestions]


# --- The feature's scenario ------------------------------------------------------


def test_bulba_suggests_bulbasaur_with_what_is_needed_to_recognize_it(
    suggest: SuggestPokemon,
) -> None:
    [suggestion] = suggest.execute(SuggestPokemonQuery("bulba"))

    assert suggestion == PokemonSuggestion(
        id=1,
        name="bulbasaur",
        display_name="Bulbasaur",
        sprite=POKEMON[1].images.sprite,
        types=(PokemonType.GRASS, PokemonType.POISON),
        genus=POKEMON[1].species.genus,
        match_kind=MatchKind.PREFIX,
        score=1.0,
        segments=(NameSegment("Bulba", True), NameSegment("saur", False)),
    )


def test_segments_highlight_the_display_name_not_the_slug(
    suggest: SuggestPokemon,
) -> None:
    [suggestion] = suggest.execute(SuggestPokemonQuery("mime"))

    assert suggestion.name == "mr-mime"
    assert suggestion.display_name == "Mr. Mime"
    assert suggestion.segments == (
        NameSegment("Mr. ", False),
        NameSegment("Mime", True),
    )


def test_only_the_kept_pokemon_are_loaded(
    suggest: SuggestPokemon, repository: MagicMock
) -> None:
    suggest.execute(SuggestPokemonQuery("bulba"))

    repository.list_name_candidates.assert_called_once_with()
    repository.get_many.assert_called_once_with([1])


# --- Validation happens before any data access -----------------------------------


@pytest.mark.parametrize("text", ["", "   ", "!!!"])
def test_invalid_text_is_rejected_without_reading_data(
    suggest: SuggestPokemon, repository: MagicMock, text: str
) -> None:
    with pytest.raises(InvalidSearchQueryError):
        suggest.execute(SuggestPokemonQuery(text))

    repository.list_name_candidates.assert_not_called()
    repository.get_many.assert_not_called()


@pytest.mark.parametrize("limit", [MIN_LIMIT - 1, MAX_LIMIT + 1, -5])
def test_out_of_bounds_limit_is_rejected_without_reading_data(
    suggest: SuggestPokemon, repository: MagicMock, limit: int
) -> None:
    with pytest.raises(InvalidSearchQueryError, match="limit"):
        suggest.execute(SuggestPokemonQuery("bulba", limit=limit))

    repository.list_name_candidates.assert_not_called()


@pytest.mark.parametrize("limit", [MIN_LIMIT, MAX_LIMIT])
def test_limit_bounds_are_inclusive(suggest: SuggestPokemon, limit: int) -> None:
    assert len(suggest.execute(SuggestPokemonQuery("nido", limit=limit))) == min(
        limit, 5
    )


# --- Limit and order -------------------------------------------------------------


def test_default_limit(suggest: SuggestPokemon) -> None:
    assert SuggestPokemonQuery("x").limit == DEFAULT_LIMIT
    # 5 names start with "nido": all fit in the default limit.
    assert len(suggest.execute(SuggestPokemonQuery("nido"))) == DEFAULT_LIMIT


def test_limit_is_applied_before_loading(
    suggest: SuggestPokemon, repository: MagicMock
) -> None:
    result = suggest.execute(SuggestPokemonQuery("nido", limit=2))

    assert names(result) == ["nidoran-f", "nidorina"]
    repository.get_many.assert_called_once_with([29, 30])


def test_ranking_order_is_kept_whatever_the_repository_order(
    suggest: SuggestPokemon, repository: MagicMock
) -> None:
    # The port does not guarantee any order: simulate the worst case.
    repository.get_many.side_effect = lambda ids: [POKEMON[i] for i in reversed(ids)]

    result = suggest.execute(SuggestPokemonQuery("mew"))

    assert names(result) == ["mew", "mewtwo"]
    assert [s.match_kind for s in result] == [MatchKind.EXACT, MatchKind.PREFIX]


# --- Edge cases -------------------------------------------------------------------


def test_no_match_returns_an_empty_list_without_loading(
    suggest: SuggestPokemon, repository: MagicMock
) -> None:
    assert suggest.execute(SuggestPokemonQuery("xyz")) == []
    repository.get_many.assert_not_called()


def test_pokemon_missing_from_get_many_is_skipped(
    suggest: SuggestPokemon, repository: MagicMock
) -> None:
    repository.get_many.side_effect = lambda _ids: [POKEMON[150]]

    result = suggest.execute(SuggestPokemonQuery("mew"))

    assert names(result) == ["mewtwo"]


# --- Typo tolerance (scorer port) ------------------------------------------------


def test_typo_is_found_when_a_scorer_is_provided(repository: MagicMock) -> None:
    scorer = create_autospec(SimilarityScorer, instance=True)
    scorer.score.side_effect = lambda _query, name: 0.93 if name == "bulbasaur" else 0.0
    suggest = SuggestPokemon(pokemon=repository, scorer=scorer)

    [suggestion] = suggest.execute(SuggestPokemonQuery("bulbsaur"))

    assert suggestion.name == "bulbasaur"
    assert suggestion.match_kind is MatchKind.FUZZY
    assert suggestion.score == 0.93
    # Nothing exact to point at: the whole name, unmatched.
    assert suggestion.segments == (NameSegment("Bulbasaur", False),)


def test_no_typo_tolerance_without_scorer(suggest: SuggestPokemon) -> None:
    assert suggest.execute(SuggestPokemonQuery("bulbsaur")) == []
