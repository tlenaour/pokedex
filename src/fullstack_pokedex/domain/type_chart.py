"""Type effectiveness: how much damage a move of one type does to a Pokémon.

These are rules of the game, not data: they never change, so they live in the
domain as code. This is the current chart (18 types, with Steel, Dark and Fairy),
consistent with the types of the data (e.g. Clefairy is Fairy). Source: PokéAPI,
`damage_relations` of /type/{name}.
"""

from collections.abc import Iterable

from fullstack_pokedex.domain.entities import PokemonType as T

CHART: dict[T, dict[T, float]] = {
    T.NORMAL: {T.ROCK: 0.5, T.GHOST: 0, T.STEEL: 0.5},
    T.FIRE: {
        T.FIRE: 0.5, T.WATER: 0.5, T.GRASS: 2, T.ICE: 2,
        T.BUG: 2, T.ROCK: 0.5, T.DRAGON: 0.5, T.STEEL: 2,
    },
    T.WATER: {
        T.FIRE: 2, T.WATER: 0.5, T.GRASS: 0.5, T.GROUND: 2,
        T.ROCK: 2, T.DRAGON: 0.5,
    },
    T.ELECTRIC: {
        T.WATER: 2, T.ELECTRIC: 0.5, T.GRASS: 0.5, T.GROUND: 0,
        T.FLYING: 2, T.DRAGON: 0.5,
    },
    T.GRASS: {
        T.FIRE: 0.5, T.WATER: 2, T.GRASS: 0.5, T.POISON: 0.5, T.GROUND: 2,
        T.FLYING: 0.5, T.BUG: 0.5, T.ROCK: 2, T.DRAGON: 0.5, T.STEEL: 0.5,
    },
    T.ICE: {
        T.FIRE: 0.5, T.WATER: 0.5, T.GRASS: 2, T.ICE: 0.5,
        T.GROUND: 2, T.FLYING: 2, T.DRAGON: 2, T.STEEL: 0.5,
    },
    T.FIGHTING: {
        T.NORMAL: 2, T.ICE: 2, T.POISON: 0.5, T.FLYING: 0.5, T.PSYCHIC: 0.5,
        T.BUG: 0.5, T.ROCK: 2, T.GHOST: 0, T.DARK: 2, T.STEEL: 2, T.FAIRY: 0.5,
    },
    T.POISON: {
        T.GRASS: 2, T.POISON: 0.5, T.GROUND: 0.5, T.ROCK: 0.5,
        T.GHOST: 0.5, T.STEEL: 0, T.FAIRY: 2,
    },
    T.GROUND: {
        T.FIRE: 2, T.ELECTRIC: 2, T.GRASS: 0.5, T.POISON: 2,
        T.FLYING: 0, T.BUG: 0.5, T.ROCK: 2, T.STEEL: 2,
    },
    T.FLYING: {
        T.ELECTRIC: 0.5, T.GRASS: 2, T.FIGHTING: 2, T.BUG: 2,
        T.ROCK: 0.5, T.STEEL: 0.5,
    },
    T.PSYCHIC: {
        T.FIGHTING: 2, T.POISON: 2, T.PSYCHIC: 0.5, T.DARK: 0, T.STEEL: 0.5,
    },
    T.BUG: {
        T.FIRE: 0.5, T.GRASS: 2, T.FIGHTING: 0.5, T.POISON: 0.5, T.FLYING: 0.5,
        T.PSYCHIC: 2, T.GHOST: 0.5, T.DARK: 2, T.STEEL: 0.5, T.FAIRY: 0.5,
    },
    T.ROCK: {
        T.FIRE: 2, T.ICE: 2, T.FIGHTING: 0.5, T.GROUND: 0.5,
        T.FLYING: 2, T.BUG: 2, T.STEEL: 0.5,
    },
    T.GHOST: {T.NORMAL: 0, T.PSYCHIC: 2, T.GHOST: 2, T.DARK: 0.5},
    T.DRAGON: {T.DRAGON: 2, T.STEEL: 0.5, T.FAIRY: 0},
    T.DARK: {
        T.FIGHTING: 0.5, T.PSYCHIC: 2, T.GHOST: 2, T.DARK: 0.5, T.FAIRY: 0.5,
    },
    T.STEEL: {
        T.FIRE: 0.5, T.WATER: 0.5, T.ELECTRIC: 0.5, T.ICE: 2,
        T.ROCK: 2, T.STEEL: 0.5, T.FAIRY: 2,
    },
    T.FAIRY: {
        T.FIRE: 0.5, T.FIGHTING: 2, T.POISON: 0.5, T.DRAGON: 2,
        T.DARK: 2, T.STEEL: 0.5,
    },
}  # fmt: skip
"""Attacking type -> defending type -> multiplier; absent means ×1."""


def effectiveness(attack: T, defender_types: Iterable[T]) -> float:
    """Multiplier of a move of type `attack` against a Pokémon of these types:
    the product over its types, so ×4, ×2, ×1, ×0.5, ×0.25 or ×0."""
    multiplier = 1.0
    for defender in defender_types:
        multiplier *= CHART[attack].get(defender, 1)
    return multiplier
