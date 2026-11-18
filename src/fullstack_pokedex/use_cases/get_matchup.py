"""Use case: prepare a fight against a Pokémon.

Its weaknesses, resistances and immunities, the types it hits super
effectively, what it can do (threats), what it can avoid or heal
(protections) and what must not be done to it (pitfalls).
"""

from dataclasses import dataclass

from fullstack_pokedex.domain.effects import (
    Pitfall,
    Protection,
    SourceKind,
    Threat,
    drop_universal_moves,
    pitfalls,
    protections,
    threats,
)
from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.domain.matchup import (
    DefensiveProfile,
    blocked_types,
    defensive_profile,
    strong_against,
)
from fullstack_pokedex.domain.repositories import (
    EffectRepository,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.list_pokemon import PokemonListItem
from fullstack_pokedex.use_cases.lookup import find_by_ref


@dataclass(frozen=True)
class Matchup:
    pokemon: PokemonListItem
    defense: DefensiveProfile
    strong_against: tuple[PokemonType, ...]
    threats: tuple[Threat, ...]
    protections: tuple[Protection, ...]
    pitfalls: tuple[Pitfall, ...]


@dataclass(frozen=True)
class GetMatchup:
    pokemon: PokemonRepository
    effects: EffectRepository

    def execute(self, ref: int | str) -> Matchup:
        target = find_by_ref(self.pokemon, ref, "Pokemon")
        # Only the target's data: its effects, and how many Pokémon learn each
        # of its moves (to drop the moves almost everyone learns).
        own = self.effects.list_effects(target.id)
        moves = {e.source for e in own if e.source_kind is SourceKind.MOVE}
        target_effects = drop_universal_moves(
            own, self.effects.count_learners(moves), self.pokemon.count()
        )
        return Matchup(
            pokemon=PokemonListItem.from_entity(target),
            defense=defensive_profile(target.types, blocked_types(target_effects)),
            strong_against=strong_against(target.types),
            threats=threats(target_effects),
            protections=protections(target_effects),
            pitfalls=pitfalls(target_effects),
        )
