"""What the effect tags of moves and abilities (data/tags_llm.json) say about
a fight.

- Threats: what the target can inflict (`inflicts:poison`, ...).
- Protections: what it can avoid or heal (`prevents:sleep`, `cures:any`, ...).
- Pitfalls: what must not be done to the target (its ability reflects the
  status, or the status makes it stronger).

A Pokémon has only one of its abilities at a time: what an ability gives is
only *possible*.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

UNIVERSAL_MOVE_SHARE = 0.8
"""A move learned by more than this share of the Pokémon (Toxic, Rest,
Substitute, ...) says nothing about one of them: its tags are ignored."""


class SourceKind(StrEnum):
    ABILITY = "ability"
    MOVE = "move"


@dataclass(frozen=True)
class PokemonEffect:
    """An effect tag that a Pokémon gets from one of its moves or abilities."""

    tag: str
    """`relation:effect`, e.g. `inflicts:poison`."""
    source_kind: SourceKind
    source: str
    """Name of the move or ability."""
    chance: float | None

    @property
    def relation(self) -> str:
        return self.tag.partition(":")[0]

    @property
    def effect(self) -> str:
        return self.tag.partition(":")[2]


class Effect(StrEnum):
    """Effects of the tag vocabulary that something can prevent."""

    SLEEP = "sleep"
    POISON = "poison"
    PARALYSIS = "paralysis"
    BURN = "burn"
    FREEZE = "freeze"
    CONFUSION = "confusion"
    FLINCH = "flinch"
    INFATUATION = "infatuation"
    ONE_HIT_KO = "one-hit-ko"
    ANY = "any"
    """Any major status, as in the tags."""


def drop_universal_moves(
    effects: Mapping[int, Sequence[PokemonEffect]], pokemon_count: int
) -> dict[int, tuple[PokemonEffect, ...]]:
    """The effects without those of the moves almost every Pokémon learns."""
    learners: defaultdict[str, set[int]] = defaultdict(set)
    for pokemon_id, pokemon_effects in effects.items():
        for e in pokemon_effects:
            if e.source_kind is SourceKind.MOVE:
                learners[e.source].add(pokemon_id)
    limit = UNIVERSAL_MOVE_SHARE * pokemon_count

    def kept(e: PokemonEffect) -> bool:
        return e.source_kind is not SourceKind.MOVE or len(learners[e.source]) <= limit

    return {
        pokemon_id: tuple(e for e in pokemon_effects if kept(e))
        for pokemon_id, pokemon_effects in effects.items()
    }


# --- The target -------------------------------------------------------------------


@dataclass(frozen=True)
class Threat:
    effect: Effect
    sources: tuple[str, ...]
    """Moves and abilities that inflict it, by name."""


def threats(effects: Iterable[PokemonEffect]) -> tuple[Threat, ...]:
    """What the target can inflict, among what something can prevent."""
    sources: defaultdict[Effect, set[str]] = defaultdict(set)
    for e in effects:
        if e.relation == "inflicts" and e.effect in Effect:
            sources[Effect(e.effect)].add(e.source)
    return tuple(
        Threat(effect, tuple(sorted(sources[effect])))
        for effect in Effect
        if effect in sources
    )


class PitfallKind(StrEnum):
    REFLECTS = "reflects"
    """Its ability gives the status back to the one who inflicted it."""
    BOOSTS = "boosts"
    """The effect makes it stronger."""


@dataclass(frozen=True)
class Pitfall:
    kind: PitfallKind
    effect: Effect
    ability: str


def pitfalls(effects: Iterable[PokemonEffect]) -> tuple[Pitfall, ...]:
    """What not to do to the target, from its abilities' `reflects:` and
    `requires:` tags."""
    kinds = {"reflects": PitfallKind.REFLECTS, "requires": PitfallKind.BOOSTS}
    found = {
        Pitfall(kinds[e.relation], Effect(e.effect), e.source)
        for e in effects
        if e.source_kind is SourceKind.ABILITY
        and e.relation in kinds
        and e.effect in Effect
    }
    order = list(Effect)
    return tuple(
        sorted(found, key=lambda p: (order.index(p.effect), p.kind, p.ability))
    )


class ProtectionKind(StrEnum):
    PREVENTS = "prevents"
    CURES = "cures"


@dataclass(frozen=True)
class Protection:
    kind: ProtectionKind
    effect: Effect
    sources: tuple[str, ...]
    """Moves and abilities that give it, by name."""


def protections(effects: Iterable[PokemonEffect]) -> tuple[Protection, ...]:
    """What the target can avoid or heal, from its `prevents:` and `cures:` tags."""
    sources: defaultdict[tuple[Effect, ProtectionKind], set[str]] = defaultdict(set)
    for e in effects:
        if e.relation in ProtectionKind and e.effect in Effect:
            sources[Effect(e.effect), ProtectionKind(e.relation)].add(e.source)
    return tuple(
        Protection(kind, effect, tuple(sorted(sources[effect, kind])))
        for effect in Effect
        for kind in ProtectionKind
        if (effect, kind) in sources
    )
