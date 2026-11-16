"""IdentifyPokemon use case: the repository and the embedder are mocked."""

from unittest.mock import MagicMock, create_autospec

import pytest

from fullstack_pokedex.domain.appearance import AppearanceCandidate, TextEmbedder
from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.domain.errors import InvalidSearchQueryError
from fullstack_pokedex.domain.repositories import PokemonRepository
from fullstack_pokedex.use_cases.identify_pokemon import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_LIMIT,
    IdentifyPokemon,
    IdentifyPokemonQuery,
    PokemonIdentification,
)
from tests.factories import make_pokemon

POKEMON = {
    25: make_pokemon(id=25, name="pikachu"),
    122: make_pokemon(id=122, name="mr-mime", types=(PokemonType.PSYCHIC,)),
    1: make_pokemon(id=1, name="bulbasaur"),
}
# Candidate vectors, and the query vector the mocked embedder returns:
# pikachu is closest, then mr-mime, then bulbasaur.
CANDIDATES = [
    AppearanceCandidate(1, [0.0, 1.0]),
    AppearanceCandidate(25, [1.0, 0.0]),
    AppearanceCandidate(122, [1.0, 1.0]),
]
QUERY_VECTOR = [1.0, 0.1]


@pytest.fixture
def repository() -> MagicMock:
    repository = create_autospec(PokemonRepository, instance=True)
    repository.list_appearance_candidates.return_value = CANDIDATES
    repository.get_many.side_effect = lambda ids: [POKEMON[i] for i in ids]
    return repository


@pytest.fixture
def embedder() -> MagicMock:
    embedder = create_autospec(TextEmbedder, instance=True)
    embedder.embed.return_value = [QUERY_VECTOR]
    return embedder


@pytest.fixture
def identify(repository: MagicMock, embedder: MagicMock) -> IdentifyPokemon:
    return IdentifyPokemon(pokemon=repository, embedder=embedder)


def names(results: list[PokemonIdentification]) -> list[str]:
    return [r.name for r in results]


def test_returns_closest_pokemon_with_what_is_needed_to_recognize_it(
    identify: IdentifyPokemon,
) -> None:
    [first, *_] = identify.execute(IdentifyPokemonQuery("small yellow mouse"))

    assert first == PokemonIdentification(
        id=25,
        name="pikachu",
        display_name="Pikachu",
        sprite=POKEMON[25].images.sprite,
        types=POKEMON[25].types,
        genus=POKEMON[25].species.genus,
        score=pytest.approx(0.995, abs=1e-3),
    )


def test_results_are_ordered_closest_first(identify: IdentifyPokemon) -> None:
    results = identify.execute(IdentifyPokemonQuery("small yellow mouse"))

    assert names(results) == ["pikachu", "mr-mime", "bulbasaur"]
    assert [r.score for r in results] == sorted(
        (r.score for r in results), reverse=True
    )


def test_display_name_is_used(identify: IdentifyPokemon) -> None:
    results = identify.execute(IdentifyPokemonQuery("clown"))
    assert "Mr. Mime" in [r.display_name for r in results]


def test_the_cleaned_description_is_embedded(
    identify: IdentifyPokemon, embedder: MagicMock
) -> None:
    identify.execute(IdentifyPokemonQuery("  small   yellow\nmouse "))

    embedder.embed.assert_called_once_with(["small yellow mouse"])


def test_only_the_kept_pokemon_are_loaded(
    identify: IdentifyPokemon, repository: MagicMock
) -> None:
    identify.execute(IdentifyPokemonQuery("small yellow mouse", limit=2))

    repository.get_many.assert_called_once_with([25, 122])


def test_ranking_order_is_kept_whatever_the_repository_order(
    identify: IdentifyPokemon, repository: MagicMock
) -> None:
    repository.get_many.side_effect = lambda ids: [POKEMON[i] for i in reversed(ids)]

    results = identify.execute(IdentifyPokemonQuery("small yellow mouse"))

    assert names(results) == ["pikachu", "mr-mime", "bulbasaur"]


def test_default_limit() -> None:
    assert IdentifyPokemonQuery("x").limit == DEFAULT_LIMIT


@pytest.mark.parametrize("text", ["", "   ", "!!!"])
def test_invalid_description_is_rejected_before_any_work(
    identify: IdentifyPokemon, repository: MagicMock, embedder: MagicMock, text: str
) -> None:
    with pytest.raises(InvalidSearchQueryError):
        identify.execute(IdentifyPokemonQuery(text))

    embedder.embed.assert_not_called()
    repository.list_appearance_candidates.assert_not_called()


@pytest.mark.parametrize("limit", [MIN_LIMIT - 1, MAX_LIMIT + 1])
def test_out_of_bounds_limit_is_rejected_before_any_work(
    identify: IdentifyPokemon, embedder: MagicMock, limit: int
) -> None:
    with pytest.raises(InvalidSearchQueryError, match="limit"):
        identify.execute(IdentifyPokemonQuery("yellow mouse", limit=limit))

    embedder.embed.assert_not_called()


def test_no_index_gives_no_result_without_loading(
    identify: IdentifyPokemon, repository: MagicMock
) -> None:
    repository.list_appearance_candidates.return_value = []

    assert identify.execute(IdentifyPokemonQuery("yellow mouse")) == []
    repository.get_many.assert_not_called()


def test_pokemon_missing_from_get_many_is_skipped(
    identify: IdentifyPokemon, repository: MagicMock
) -> None:
    repository.get_many.side_effect = lambda ids: [POKEMON[1]]

    assert names(identify.execute(IdentifyPokemonQuery("yellow mouse"))) == [
        "bulbasaur"
    ]
