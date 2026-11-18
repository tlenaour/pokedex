"""Use case: one move, and the Pokémon that can learn it."""

from dataclasses import dataclass

from fullstack_pokedex.domain.entities import Move, Pokemon
from fullstack_pokedex.domain.repositories import MoveRepository, PokemonRepository
from fullstack_pokedex.use_cases.lookup import find_by_ref


@dataclass(frozen=True)
class MoveDetail:
    move: Move
    learned_by: tuple[Pokemon, ...]


@dataclass(frozen=True)
class GetMove:
    moves: MoveRepository
    pokemon: PokemonRepository

    def execute(self, ref: int | str) -> MoveDetail:
        move = find_by_ref(self.moves, ref, "Move")
        return MoveDetail(move, tuple(self.pokemon.list_by_move(move.id)))
