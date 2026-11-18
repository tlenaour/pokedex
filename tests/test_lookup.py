"""find_by_ref: one lookup by id or name for every entity."""

from unittest.mock import create_autospec

import pytest

from fullstack_pokedex.domain.errors import NotFoundError
from fullstack_pokedex.domain.repositories import MoveRepository, PokemonRepository
from fullstack_pokedex.use_cases.lookup import find_by_ref
from tests.factories import make_move, make_pokemon


def test_an_int_is_looked_up_as_an_id() -> None:
    repository = create_autospec(PokemonRepository, instance=True)
    repository.get_by_id.return_value = make_pokemon()

    assert find_by_ref(repository, 25, "Pokemon").name == "pikachu"
    repository.get_by_id.assert_called_once_with(25)
    repository.get_by_name.assert_not_called()


def test_a_str_is_looked_up_as_a_name() -> None:
    repository = create_autospec(MoveRepository, instance=True)
    repository.get_by_name.return_value = make_move()

    assert find_by_ref(repository, "thunderbolt", "Move").id == 85
    repository.get_by_name.assert_called_once_with("thunderbolt")
    repository.get_by_id.assert_not_called()


@pytest.mark.parametrize("ref", [999, "missingno"])
def test_nothing_found_raises_not_found(ref: int | str) -> None:
    repository = create_autospec(PokemonRepository, instance=True)
    repository.get_by_id.return_value = None
    repository.get_by_name.return_value = None

    with pytest.raises(NotFoundError, match=f"Pokemon '{ref}' not found"):
        find_by_ref(repository, ref, "Pokemon")
