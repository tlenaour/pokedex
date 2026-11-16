from fullstack_pokedex.domain.effects import PokemonEffect, SourceKind
from fullstack_pokedex.domain.entities import PokemonType as T
from fullstack_pokedex.domain.matchup import (
    TypeImmunity,
    TypeMultiplier,
    blocked_types,
    defensive_profile,
    immune_type,
    strong_against,
)


def ability(name: str, tag: str) -> PokemonEffect:
    return PokemonEffect(tag, SourceKind.ABILITY, name, None)


def move(name: str, tag: str, chance: float | None = None) -> PokemonEffect:
    return PokemonEffect(tag, SourceKind.MOVE, name, chance)


LEVITATE = ability("levitate", "immune:ground")


def test_immune_type_reads_only_type_immunities() -> None:
    assert immune_type("immune:ground") is T.GROUND
    assert immune_type("immune:sound") is None
    assert immune_type("immune:weather") is None
    assert immune_type("inflicts:burn") is None


def test_blocked_types_come_from_abilities_only() -> None:
    # Dig makes the user immune to moves for one turn: not a type immunity.
    effects = [LEVITATE, move("dig", "immune:moves"), ability("x", "immune:sound")]

    assert blocked_types(effects) == {T.GROUND: "levitate"}


def test_blocked_types_name_the_first_ability_by_name() -> None:
    effects = [
        ability("volt-absorb", "immune:electric"),
        ability("lightning-rod", "immune:electric"),
    ]
    assert blocked_types(effects) == {T.ELECTRIC: "lightning-rod"}


def test_charizard_fears_rock_and_ignores_ground() -> None:
    profile = defensive_profile((T.FIRE, T.FLYING), {})

    assert profile.weaknesses == (
        TypeMultiplier(T.ROCK, 4),
        TypeMultiplier(T.WATER, 2),
        TypeMultiplier(T.ELECTRIC, 2),
    )
    assert profile.resistances[:2] == (
        TypeMultiplier(T.GRASS, 0.25),
        TypeMultiplier(T.BUG, 0.25),
    )
    assert profile.immunities == (TypeImmunity(T.GROUND, None),)


def test_an_ability_turns_a_weakness_into_a_possible_immunity() -> None:
    # Gastly (Ghost/Poison) is weak to Ground, unless it has Levitate.
    profile = defensive_profile((T.GHOST, T.POISON), {T.GROUND: "levitate"})

    assert T.GROUND not in [w.type for w in profile.weaknesses]
    assert TypeImmunity(T.GROUND, "levitate") in profile.immunities
    assert TypeImmunity(T.NORMAL, None) in profile.immunities


def test_strong_against_uses_the_pokemon_types() -> None:
    assert strong_against((T.ELECTRIC,)) == (T.WATER, T.FLYING)
    assert strong_against((T.NORMAL,)) == ()
