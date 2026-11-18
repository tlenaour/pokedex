"""Use cases: one Pokémon's details, and the moves it can learn."""

from dataclasses import dataclass

from fullstack_pokedex.domain.entities import Ability, Move, Pokemon
from fullstack_pokedex.domain.repositories import (
    AbilityRepository,
    MoveRepository,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.lookup import find_by_ref


@dataclass(frozen=True)
class PokemonDetail:
    pokemon: Pokemon
    abilities: tuple[Ability, ...]
    # Every Pokémon of the same evolution chain, the Pokémon itself included.
    evolution_family: tuple[Pokemon, ...]


@dataclass(frozen=True)
class GetPokemonDetail:
    pokemon: PokemonRepository
    abilities: AbilityRepository

    def execute(self, ref: int | str) -> PokemonDetail:
        pokemon = find_by_ref(self.pokemon, ref, "Pokemon")
        return PokemonDetail(
            pokemon=pokemon,
            abilities=tuple(self.abilities.get_many(pokemon.ability_ids)),
            evolution_family=tuple(
                self.pokemon.list_by_evolution_chain(pokemon.species.evolution_chain_id)
            ),
        )


@dataclass(frozen=True)
class GetPokemonMoves:
    pokemon: PokemonRepository
    moves: MoveRepository

    def execute(self, ref: int | str) -> list[Move]:
        return self.moves.get_many(find_by_ref(self.pokemon, ref, "Pokemon").move_ids)
