"""Repository interfaces, implemented in the infrastructure layer (SQLite, ...)."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from fullstack_pokedex.domain.appearance import AppearanceCandidate
from fullstack_pokedex.domain.effects import PokemonEffect
from fullstack_pokedex.domain.entities import (
    Ability,
    DamageClass,
    Move,
    Pokemon,
    PokemonType,
)
from fullstack_pokedex.domain.feedback import MissingResultReport
from fullstack_pokedex.domain.name_search import NameCandidate


@dataclass(frozen=True)
class PokemonCriteria:
    name_contains: str | None = None
    type: PokemonType | None = None
    habitat: str | None = None
    is_legendary: bool | None = None


@dataclass(frozen=True)
class MoveCriteria:
    type: PokemonType | None = None
    damage_class: DamageClass | None = None


class PokemonRepository(Protocol):
    def get_by_id(self, pokemon_id: int) -> Pokemon | None: ...
    def get_by_name(self, name: str) -> Pokemon | None: ...
    def get_many(self, pokemon_ids: Iterable[int]) -> list[Pokemon]:
        """No ordering guarantee: callers needing an order must apply it."""
        ...

    def search(self, criteria: PokemonCriteria) -> list[Pokemon]: ...
    def list_name_candidates(self) -> list[NameCandidate]:
        """Every Pokémon, reduced to what name search needs."""
        ...

    def list_appearance_candidates(self) -> list[AppearanceCandidate]:
        """Every Pokémon having a reference vector of its appearance."""
        ...

    def list_by_evolution_chain(self, chain_id: int) -> list[Pokemon]: ...
    def list_by_move(self, move_id: int) -> list[Pokemon]: ...
    def list_by_ability(self, ability_id: int) -> list[Pokemon]: ...


class MoveRepository(Protocol):
    def get_by_id(self, move_id: int) -> Move | None: ...
    def get_by_name(self, name: str) -> Move | None: ...
    def get_many(self, move_ids: Iterable[int]) -> list[Move]: ...
    def search(self, criteria: MoveCriteria) -> list[Move]: ...


class AbilityRepository(Protocol):
    def get_by_id(self, ability_id: int) -> Ability | None: ...
    def get_by_name(self, name: str) -> Ability | None: ...
    def get_many(self, ability_ids: Iterable[int]) -> list[Ability]: ...
    def list_all(self) -> list[Ability]: ...


class EffectRepository(Protocol):
    def list_pokemon_effects(self) -> dict[int, list[PokemonEffect]]:
        """Effect tags of every Pokémon, by id, from its moves and abilities.
        Pokémon without any tag are absent."""
        ...


class FeedbackRepository(Protocol):
    def add(self, report: MissingResultReport) -> int:
        """Save the report; returns its id."""
        ...
