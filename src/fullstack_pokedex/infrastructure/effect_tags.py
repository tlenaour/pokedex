"""Reads data/tags_llm.json (format documented in data/README.md)."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DEFAULT_PATH = Path("data/tags_llm.json")


@dataclass(frozen=True)
class EffectTag:
    """One effect of a move or an ability, e.g. Levitate -> `immune:ground`."""

    entity_type: Literal["move", "ability"]
    entity_name: str
    tag: str
    chance: float | None
    trigger: Literal["move_hit", "on_contact", "other"]
    evidence: str


def load_effect_tags(path: Path) -> list[EffectTag]:
    """One EffectTag per tag; entries without tags produce nothing."""
    entries = json.loads(path.read_text(encoding="utf-8"))
    return [
        EffectTag(
            entity_type=entry["entity_type"],
            entity_name=entry["name"],
            tag=tag["tag"],
            chance=tag["chance"],
            trigger=tag["trigger"],
            evidence=tag["evidence"],
        )
        for entry in entries
        for tag in entry["tags"]
    ]
