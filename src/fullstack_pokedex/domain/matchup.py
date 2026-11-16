"""Matchup: a Pokémon's weaknesses and strengths.

Pure functions over the type chart, plus the `immune:<type>` effect tags of
abilities (see domain/effects.py), e.g. Levitate makes the holder immune to
Ground moves.

A Pokémon has only one of its abilities at a time: an immunity given by an
ability is therefore only *possible*.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from fullstack_pokedex.domain.effects import PokemonEffect, SourceKind
from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.domain.type_chart import effectiveness


def immune_type(tag: str) -> PokemonType | None:
    """The type of an `immune:<source>` effect tag; None for any other tag, and
    for sources that are not a type (`sound`, `weather`, `recoil`, ...)."""
    relation, _, source = tag.partition(":")
    if relation != "immune":
        return None
    try:
        return PokemonType(source)
    except ValueError:
        return None


def blocked_types(effects: Iterable[PokemonEffect]) -> dict[PokemonType, str]:
    """Types a Pokémon may be immune to thanks to one of its abilities, with
    the name of that ability (the first by name if several)."""
    blocked: dict[PokemonType, str] = {}
    for e in sorted(effects, key=lambda e: e.source):
        if e.source_kind is SourceKind.ABILITY and (t := immune_type(e.tag)):
            blocked.setdefault(t, e.source)
    return blocked


@dataclass(frozen=True)
class TypeMultiplier:
    type: PokemonType
    multiplier: float


@dataclass(frozen=True)
class TypeImmunity:
    type: PokemonType
    ability: str | None
    """None when the types alone give the immunity; otherwise the ability
    that may give it."""


@dataclass(frozen=True)
class DefensiveProfile:
    weaknesses: tuple[TypeMultiplier, ...]
    """Most damaging first."""
    resistances: tuple[TypeMultiplier, ...]
    """Least damaging first."""
    immunities: tuple[TypeImmunity, ...]


def defensive_profile(
    types: Iterable[PokemonType], blocked: Mapping[PokemonType, str]
) -> DefensiveProfile:
    """What the moves of each type do to a Pokémon of these types."""
    types = tuple(types)
    weaknesses, resistances, immunities = [], [], []
    for attack in PokemonType:
        multiplier = effectiveness(attack, types)
        if multiplier == 0:
            immunities.append(TypeImmunity(attack, None))
        elif attack in blocked:
            immunities.append(TypeImmunity(attack, blocked[attack]))
        elif multiplier > 1:
            weaknesses.append(TypeMultiplier(attack, multiplier))
        elif multiplier < 1:
            resistances.append(TypeMultiplier(attack, multiplier))
    # Stable sorts: equal multipliers keep the order of PokemonType.
    return DefensiveProfile(
        weaknesses=tuple(sorted(weaknesses, key=lambda w: -w.multiplier)),
        resistances=tuple(sorted(resistances, key=lambda r: r.multiplier)),
        immunities=tuple(immunities),
    )


def strong_against(types: Iterable[PokemonType]) -> tuple[PokemonType, ...]:
    """Defending types that at least one of these types hits super effectively."""
    types = tuple(types)
    return tuple(
        defender
        for defender in PokemonType
        if any(effectiveness(attack, (defender,)) > 1 for attack in types)
    )
