"""ListPokemon use case (the catalog): the repository is mocked."""

from unittest.mock import create_autospec

from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.domain.repositories import PokemonCriteria, PokemonRepository
from fullstack_pokedex.use_cases.list_pokemon import ListPokemon, PokemonListItem
from tests.factories import make_pokemon


def test_lists_what_a_catalog_shows_in_pokedex_order() -> None:
    repository = create_autospec(PokemonRepository, instance=True)
    # Not in Pokédex order: the use case must not rely on the repository order.
    repository.search.return_value = [
        make_pokemon(id=122, name="mr-mime", types=(PokemonType.PSYCHIC,)),
        make_pokemon(id=25, name="pikachu"),
    ]

    items = ListPokemon(pokemon=repository).execute(PokemonCriteria())

    assert [i.id for i in items] == [25, 122]
    assert items[1] == PokemonListItem(
        id=122,
        name="mr-mime",
        display_name="Mr. Mime",
        sprite=items[1].sprite,
        types=(PokemonType.PSYCHIC,),
        genus="Mouse Pokémon",
    )
    assert str(items[1].sprite) == "https://example.com/25.png"


def test_forwards_the_criteria() -> None:
    repository = create_autospec(PokemonRepository, instance=True)
    repository.search.return_value = []
    criteria = PokemonCriteria(type=PokemonType.FIRE)

    assert ListPokemon(pokemon=repository).execute(criteria) == []
    repository.search.assert_called_once_with(criteria)
