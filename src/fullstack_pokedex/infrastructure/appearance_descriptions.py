"""Reads data/pokemon_descriptions.json (format documented in data/README.md)."""

import json
from pathlib import Path

from fullstack_pokedex.domain.appearance import AppearanceDescription

DEFAULT_PATH = Path("data/pokemon_descriptions.json")


def load_appearance_descriptions(path: Path) -> list[AppearanceDescription]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    return [
        AppearanceDescription(
            pokemon_id=entry["id"],
            glance=entry["glance"],
            detailed=entry["detailed"],
            everyday=entry["everyday"],
        )
        for entry in entries
    ]
