"""GetMove: the repositories are mocked."""

from unittest.mock import create_autospec

import pytest

from fullstack_pokedex.domain.errors import NotFoundError
from fullstack_pokedex.domain.repositories import MoveRepository, PokemonRepository
from fullstack_pokedex.use_cases.get_move import GetMove
from tests.factories import make_move, make_pokemon


def test_a_move_and_the_pokemon_that_learn_it() -> None:
    moves = create_autospec(MoveRepository, instance=True)
    moves.get_by_name.return_value = make_move()
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.list_by_move.return_value = [make_pokemon()]

    detail = GetMove(moves, pokemon).execute("thunderbolt")

    assert detail.move.id == 85
    assert [p.name for p in detail.learned_by] == ["pikachu"]
    pokemon.list_by_move.assert_called_once_with(85)


def test_an_unknown_move() -> None:
    moves = create_autospec(MoveRepository, instance=True)
    moves.get_by_id.return_value = None
    pokemon = create_autospec(PokemonRepository, instance=True)

    with pytest.raises(NotFoundError, match="Move '999' not found"):
        GetMove(moves, pokemon).execute(999)
    pokemon.list_by_move.assert_not_called()
