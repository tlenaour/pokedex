"""Use case: list the Pokémon, e.g. to present the Pokédex as a catalog.

Optional criteria filter the list (type, habitat, ...); without criteria,
the whole Pokédex is returned, in Pokédex order.
"""

from dataclasses import dataclass

from pydantic import HttpUrl

from fullstack_pokedex.domain.display_name import display_name
from fullstack_pokedex.domain.entities import Pokemon, PokemonType
from fullstack_pokedex.domain.repositories import PokemonCriteria, PokemonRepository


@dataclass(frozen=True)
class PokemonListItem:
    """What a list or a catalog shows about a Pokémon."""

    id: int
    name: str
    display_name: str
    sprite: HttpUrl
    types: tuple[PokemonType, ...]
    genus: str

    @classmethod
    def from_entity(cls, pokemon: Pokemon) -> "PokemonListItem":
        return cls(
            id=pokemon.id,
            name=pokemon.name,
            display_name=display_name(pokemon.name),
            sprite=pokemon.images.sprite,
            types=pokemon.types,
            genus=pokemon.species.genus,
        )


@dataclass(frozen=True)
class ListPokemon:
    pokemon: PokemonRepository

    def execute(self, criteria: PokemonCriteria) -> list[PokemonListItem]:
        # Pokédex order, whatever order the repository returns.
        found = sorted(self.pokemon.search(criteria), key=lambda p: p.id)
        return [PokemonListItem.from_entity(p) for p in found]
