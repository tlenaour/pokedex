"""Test data: the mini JSON fixture, and factories building valid domain
objects where tests override only the fields they care about."""

import re
import zlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fullstack_pokedex.domain.entities import (
    Ability,
    DamageClass,
    Images,
    Move,
    Pokemon,
    PokemonType,
    Species,
    Stats,
)

MINI_POKEDEX = Path(__file__).parent / "fixtures" / "mini_pokedex.json"
DESCRIPTIONS = Path(__file__).parents[1] / "data" / "pokemon_descriptions.json"
EFFECT_TAGS = Path(__file__).parents[1] / "data" / "tags_llm.json"
"""4 Pokémon (bulbasaur, ivysaur, pikachu, mewtwo), 6 moves, 6 abilities."""


def make_pokemon(**overrides: Any) -> Pokemon:
    fields: dict[str, Any] = {
        "id": 25,
        "name": "pikachu",
        "height_decimetres": 4,
        "weight_hectograms": 60,
        "base_experience": 112,
        "types": (PokemonType.ELECTRIC,),
        "stats": Stats(
            hp=35,
            attack=55,
            defense=40,
            special_attack=50,
            special_defense=50,
            speed=90,
        ),
        "species": Species(
            genus="Mouse Pokémon",
            description="An electric mouse.",
            generation="generation-i",
            color="yellow",
            shape="quadruped",
            habitat="forest",
            is_legendary=False,
            is_mythical=False,
            evolution_chain_id=10,
        ),
        "images": Images(
            sprite="https://example.com/25.png",
            official_artwork="https://example.com/25-art.png",
        ),
        "ability_ids": frozenset({9}),
        "move_ids": frozenset({85}),
    }
    return Pokemon(**(fields | overrides))


def make_move(**overrides: Any) -> Move:
    fields: dict[str, Any] = {
        "id": 85,
        "name": "thunderbolt",
        "type": PokemonType.ELECTRIC,
        "damage_class": DamageClass.SPECIAL,
        "power": 90,
        "accuracy": 100,
        "pp": 15,
        "priority": 0,
        "effect_chance": 10,
        "effect": "Inflicts regular damage.",
        "short_effect": "Has a chance to paralyze.",
        "generation": "generation-i",
    }
    return Move(**(fields | overrides))


def make_ability(**overrides: Any) -> Ability:
    fields: dict[str, Any] = {
        "id": 9,
        "name": "static",
        "effect": "May paralyze on contact.",
        "short_effect": "Has a 30% chance of paralyzing attacking Pokémon.",
        "generation": "generation-iii",
        "is_main_series": True,
    }
    return Ability(**(fields | overrides))


class FakeEmbedder:
    """Deterministic TextEmbedder for tests: a bag of words hashed into a few
    dimensions, so texts sharing words get close vectors. No model, no download."""

    model_name = "fake-embedder"
    DIMENSIONS = 32

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.DIMENSIONS
            for word in re.findall(r"[a-z]+", text.lower()):
                vector[zlib.crc32(word.encode()) % self.DIMENSIONS] += 1.0
            vectors.append(vector)
        return vectors
