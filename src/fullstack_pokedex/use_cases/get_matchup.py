"""Use case: prepare a fight against a Pokémon.

Its weaknesses, resistances and immunities, the types it hits super
effectively, what it can do (threats), what it can avoid or heal
(protections) and what must not be done to it (pitfalls).
"""

from dataclasses import dataclass

from fullstack_pokedex.domain.effects import (
    Pitfall,
    Protection,
    Threat,
    drop_universal_moves,
    pitfalls,
    protections,
    threats,
)
from fullstack_pokedex.domain.entities import Pokemon, PokemonType
from fullstack_pokedex.domain.matchup import (
    DefensiveProfile,
    blocked_types,
    defensive_profile,
    strong_against,
)
from fullstack_pokedex.domain.repositories import (
    EffectRepository,
    PokemonCriteria,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.list_pokemon import PokemonListItem


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

    def execute(self, target: Pokemon) -> Matchup:
        pokemon_count = len(self.pokemon.search(PokemonCriteria()))
        effects = drop_universal_moves(
            self.effects.list_pokemon_effects(), pokemon_count
        )
        target_effects = effects.get(target.id, ())
        return Matchup(
            pokemon=PokemonListItem.from_entity(target),
            defense=defensive_profile(target.types, blocked_types(target_effects)),
            strong_against=strong_against(target.types),
            threats=threats(target_effects),
            protections=protections(target_effects),
            pitfalls=pitfalls(target_effects),
        )
