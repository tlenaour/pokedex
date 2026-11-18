"""GetAbility: the repositories are mocked."""

from unittest.mock import create_autospec

import pytest

from fullstack_pokedex.domain.errors import NotFoundError
from fullstack_pokedex.domain.repositories import AbilityRepository, PokemonRepository
from fullstack_pokedex.use_cases.get_ability import GetAbility
from tests.factories import make_ability, make_pokemon


def test_an_ability_and_the_pokemon_that_have_it() -> None:
    abilities = create_autospec(AbilityRepository, instance=True)
    abilities.get_by_id.return_value = make_ability()
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.list_by_ability.return_value = [make_pokemon()]

    detail = GetAbility(abilities, pokemon).execute(9)

    assert detail.ability.name == "static"
    assert [p.name for p in detail.pokemon] == ["pikachu"]
    pokemon.list_by_ability.assert_called_once_with(9)


def test_an_unknown_ability() -> None:
    abilities = create_autospec(AbilityRepository, instance=True)
    abilities.get_by_name.return_value = None
    pokemon = create_autospec(PokemonRepository, instance=True)

    with pytest.raises(NotFoundError, match="Ability 'nothing' not found"):
        GetAbility(abilities, pokemon).execute("nothing")
    pokemon.list_by_ability.assert_not_called()
