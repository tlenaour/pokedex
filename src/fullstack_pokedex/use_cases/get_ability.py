"""Use case: one ability, and the Pokémon that can have it."""

from dataclasses import dataclass

from fullstack_pokedex.domain.entities import Ability, Pokemon
from fullstack_pokedex.domain.repositories import AbilityRepository, PokemonRepository
from fullstack_pokedex.use_cases.lookup import find_by_ref


@dataclass(frozen=True)
class AbilityDetail:
    ability: Ability
    pokemon: tuple[Pokemon, ...]


@dataclass(frozen=True)
class GetAbility:
    abilities: AbilityRepository
    pokemon: PokemonRepository

    def execute(self, ref: int | str) -> AbilityDetail:
        ability = find_by_ref(self.abilities, ref, "Ability")
        return AbilityDetail(ability, tuple(self.pokemon.list_by_ability(ability.id)))
