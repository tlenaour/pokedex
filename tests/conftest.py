import sqlite3
from collections.abc import Iterator

import pytest

from fullstack_pokedex.domain.appearance import AppearanceDescription
from fullstack_pokedex.infrastructure.appearance_descriptions import (
    load_appearance_descriptions,
)
from fullstack_pokedex.infrastructure.effect_tags import EffectTag, load_effect_tags
from fullstack_pokedex.infrastructure.embeddings import configured_model
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex, load_pokedex
from fullstack_pokedex.infrastructure.sqlite.importer import (
    import_appearance,
    import_effect_tags,
    import_pokedex,
)
from tests.factories import DESCRIPTIONS, EFFECT_TAGS, MINI_POKEDEX, FakeEmbedder


@pytest.fixture
def pokedex() -> Pokedex:
    return load_pokedex(MINI_POKEDEX)


@pytest.fixture
def mini_tags(pokedex: Pokedex) -> list[EffectTag]:
    """The real effect tags of the mini pokedex's moves and abilities."""
    names = {("move", m.name) for m in pokedex.moves} | {
        ("ability", a.name) for a in pokedex.abilities
    }
    return [
        t
        for t in load_effect_tags(EFFECT_TAGS)
        if (t.entity_type, t.entity_name) in names
    ]


@pytest.fixture
def conn(pokedex: Pokedex, mini_tags: list[EffectTag]) -> Iterator[sqlite3.Connection]:
    """In-memory SQLite database filled with the mini pokedex and its effect tags."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    import_pokedex(pokedex, conn)
    import_effect_tags(mini_tags, conn)
    yield conn
    conn.close()


@pytest.fixture
def mini_descriptions(pokedex: Pokedex) -> list[AppearanceDescription]:
    """The real reference descriptions of the mini pokedex's 4 Pokémon."""
    ids = {p.id for p in pokedex.pokemon}
    return [
        d for d in load_appearance_descriptions(DESCRIPTIONS) if d.pokemon_id in ids
    ]


@pytest.fixture
def appearance_conn(
    conn: sqlite3.Connection, mini_descriptions: list[AppearanceDescription]
) -> sqlite3.Connection:
    """The mini pokedex plus its appearance index, built with FakeEmbedder but
    recorded under the configured model name (as the API expects)."""
    import_appearance(mini_descriptions, FakeEmbedder(), configured_model(), conn)
    return conn
