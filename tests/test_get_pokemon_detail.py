"""GetPokemonDetail and GetPokemonMoves: the repositories are mocked."""

from unittest.mock import create_autospec

import pytest

from fullstack_pokedex.domain.errors import NotFoundError
from fullstack_pokedex.domain.repositories import (
    AbilityRepository,
    MoveRepository,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.get_pokemon_detail import (
    GetPokemonDetail,
    GetPokemonMoves,
)
from tests.factories import make_ability, make_move, make_pokemon


def test_details_of_a_pokemon_with_its_abilities_and_family() -> None:
    pikachu = make_pokemon()
    raichu = make_pokemon(id=26, name="raichu")
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.get_by_name.return_value = pikachu
    pokemon.list_by_evolution_chain.return_value = [pikachu, raichu]
    abilities = create_autospec(AbilityRepository, instance=True)
    abilities.get_many.return_value = [make_ability()]

    detail = GetPokemonDetail(pokemon, abilities).execute("pikachu")

    assert detail.pokemon is pikachu
    assert [a.name for a in detail.abilities] == ["static"]
    assert detail.evolution_family == (pikachu, raichu)
    abilities.get_many.assert_called_once_with(pikachu.ability_ids)
    pokemon.list_by_evolution_chain.assert_called_once_with(10)


def test_details_of_an_unknown_pokemon() -> None:
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.get_by_id.return_value = None
    abilities = create_autospec(AbilityRepository, instance=True)

    with pytest.raises(NotFoundError):
        GetPokemonDetail(pokemon, abilities).execute(999)
    abilities.get_many.assert_not_called()


def test_moves_of_a_pokemon() -> None:
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.get_by_id.return_value = make_pokemon()
    moves = create_autospec(MoveRepository, instance=True)
    moves.get_many.return_value = [make_move()]

    assert [m.name for m in GetPokemonMoves(pokemon, moves).execute(25)] == [
        "thunderbolt"
    ]
    moves.get_many.assert_called_once_with(frozenset({85}))
