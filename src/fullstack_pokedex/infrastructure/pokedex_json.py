"""Adapter reading the pokedex.json file and turning it into domain entities."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fullstack_pokedex.domain.entities import (
    Ability,
    Images,
    Move,
    Pokemon,
    Species,
    Stats,
)


@dataclass(frozen=True)
class Pokedex:
    pokemon: list[Pokemon]
    moves: list[Move]
    abilities: list[Ability]


def load_pokedex(path: Path) -> Pokedex:
    raw = json.loads(path.read_text(encoding="utf-8"))

    moves = [_to_move(m) for m in raw["moves"]]
    abilities = [_to_ability(a) for a in raw["abilities"]]

    # The file links entities by name: resolve them to ids.
    move_ids = {m.name: m.id for m in moves}
    ability_ids = {a.name: a.id for a in abilities}
    pokemon = [_to_pokemon(p, move_ids, ability_ids) for p in raw["pokemon"]]

    return Pokedex(pokemon=pokemon, moves=moves, abilities=abilities)


def _to_pokemon(
    raw: dict[str, Any], move_ids: dict[str, int], ability_ids: dict[str, int]
) -> Pokemon:
    stats = raw["stats"]
    return Pokemon(
        id=raw["id"],
        name=raw["name"],
        height_decimetres=raw["height_decimetres"],
        weight_hectograms=raw["weight_hectograms"],
        base_experience=raw["base_experience"],
        types=tuple(raw["types"]),
        stats=Stats(
            hp=stats["hp"],
            attack=stats["attack"],
            defense=stats["defense"],
            special_attack=stats["special-attack"],
            special_defense=stats["special-defense"],
            speed=stats["speed"],
        ),
        species=Species(**raw["species"]),
        images=Images(**raw["images"]),
        move_ids=frozenset(move_ids[name] for name in raw["moves"]),
        ability_ids=frozenset(ability_ids[name] for name in raw["abilities"]),
    )


def _to_move(raw: dict[str, Any]) -> Move:
    # learned_by_pokemon is the inverse of Pokemon.move_ids: redundant.
    return Move(**{k: v for k, v in raw.items() if k != "learned_by_pokemon"})


def _to_ability(raw: dict[str, Any]) -> Ability:
    # pokemon is the inverse of Pokemon.ability_ids: redundant.
    return Ability(**{k: v for k, v in raw.items() if k != "pokemon"})
