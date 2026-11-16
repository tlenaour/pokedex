import json
import sqlite3
from pathlib import Path

import pytest

from fullstack_pokedex.domain.appearance import AppearanceDescription
from fullstack_pokedex.infrastructure import embeddings
from fullstack_pokedex.infrastructure.effect_tags import EffectTag
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex
from fullstack_pokedex.infrastructure.sqlite import importer
from fullstack_pokedex.infrastructure.sqlite.importer import (
    import_appearance,
    import_effect_tags,
    import_pokedex,
)
from fullstack_pokedex.infrastructure.sqlite.repositories import (
    decode_vector,
    read_appearance_model,
)
from tests.factories import MINI_POKEDEX, FakeEmbedder


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_imports_every_table(conn: sqlite3.Connection) -> None:
    assert _count(conn, "pokemon") == 4
    assert _count(conn, "move") == 6
    assert _count(conn, "ability") == 6
    assert _count(conn, "type") == 18
    assert _count(conn, "pokemon_type") == 6  # bulbasaur & ivysaur have 2 types
    assert _count(conn, "pokemon_move") == 14
    assert _count(conn, "pokemon_ability") == 8


def test_foreign_keys_are_consistent(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_type_order_is_kept_in_slots(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT slot, type FROM pokemon_type WHERE pokemon_id = 1 ORDER BY slot"
    ).fetchall()
    assert [tuple(r) for r in rows] == [(1, "grass"), (2, "poison")]


def test_import_can_be_run_twice(conn: sqlite3.Connection, pokedex: Pokedex) -> None:
    import_pokedex(pokedex, conn)
    assert _count(conn, "pokemon") == 4


def test_cli_creates_the_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "pokedex.db"
    monkeypatch.setattr(
        "sys.argv",
        [
            "pokedex-import",
            *("--json", str(MINI_POKEDEX), "--db", str(db)),
            *("--tags", str(tmp_path / "missing.json")),
            *("--descriptions", str(tmp_path / "missing.json")),
        ],
    )

    importer.main()

    out = capsys.readouterr().out
    assert "Imported 4 pokemon, 6 moves, 6 abilities" in out
    assert "effect tags not imported" in out
    assert "appearance search index not built" in out
    with sqlite3.connect(db) as check:
        assert _count(check, "pokemon") == 4
        assert _count(check, "pokemon_appearance") == 0
    check.close()


def test_cli_builds_the_appearance_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mini_descriptions: list[AppearanceDescription],
) -> None:
    descriptions = tmp_path / "descriptions.json"
    descriptions.write_text(
        json.dumps(
            [
                {
                    "id": d.pokemon_id,
                    "glance": d.glance,
                    "detailed": d.detailed,
                    "everyday": d.everyday,
                }
                for d in mini_descriptions
            ]
        ),
        encoding="utf-8",
    )
    db = tmp_path / "pokedex.db"
    # The real model would be downloaded: replace it with the fake one.
    monkeypatch.setattr(embeddings, "Model2VecEmbedder", FakeEmbedder)
    monkeypatch.setattr(
        "sys.argv",
        [
            "pokedex-import",
            *("--json", str(MINI_POKEDEX), "--db", str(db)),
            *("--tags", str(tmp_path / "missing.json")),
            *("--descriptions", str(descriptions)),
        ],
    )

    importer.main()

    assert "Built the appearance index: 4 pokemon, model fake-embedder" in (
        capsys.readouterr().out
    )
    with sqlite3.connect(db) as check:
        assert _count(check, "pokemon_appearance") == 4
        assert read_appearance_model(check) == "fake-embedder"
    check.close()


# --- Effect tags ----------------------------------------------------------------


def _tags_json(tags: list[EffectTag]) -> str:
    return json.dumps(
        [
            {
                "entity_type": t.entity_type,
                "name": t.entity_name,
                "tags": [
                    {
                        "tag": t.tag,
                        "chance": t.chance,
                        "trigger": t.trigger,
                        "evidence": t.evidence,
                    }
                ],
                "comment": None,
                "confidence": "high",
            }
            for t in tags
        ]
    )


def test_effect_tags_are_linked_to_their_move_or_ability(
    conn: sqlite3.Connection,
) -> None:
    rows = conn.execute(
        """SELECT a.name, t.tag, t.trigger FROM effect_tag t
        JOIN ability a ON a.id = t.entity_id WHERE t.entity_type = 'ability'
        ORDER BY a.name, t.tag"""
    ).fetchall()
    assert ("lightning-rod", "immune:electric", "other") in [tuple(r) for r in rows]
    thunderbolt = conn.execute(
        """SELECT t.tag, t.chance FROM effect_tag t JOIN move m ON m.id = t.entity_id
        WHERE t.entity_type = 'move' AND m.name = 'thunderbolt'"""
    ).fetchall()
    assert [tuple(r) for r in thunderbolt] == [("inflicts:paralysis", 10)]


def test_effect_tags_can_be_imported_twice(
    conn: sqlite3.Connection, mini_tags: list[EffectTag]
) -> None:
    import_effect_tags(mini_tags, conn)
    assert _count(conn, "effect_tag") == len(mini_tags)


def test_effect_tags_of_an_unknown_ability_are_refused(
    conn: sqlite3.Connection, mini_tags: list[EffectTag]
) -> None:
    unknown = EffectTag("ability", "levitate", "immune:ground", None, "other", "x")

    with pytest.raises(ValueError, match="ability levitate"):
        import_effect_tags([*mini_tags, unknown], conn)
    assert _count(conn, "effect_tag") == len(mini_tags)  # nothing changed


def test_cli_imports_the_effect_tags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mini_tags: list[EffectTag],
) -> None:
    tags = tmp_path / "tags.json"
    tags.write_text(_tags_json(mini_tags), encoding="utf-8")
    db = tmp_path / "pokedex.db"
    monkeypatch.setattr(
        "sys.argv",
        [
            "pokedex-import",
            *("--json", str(MINI_POKEDEX), "--db", str(db)),
            *("--tags", str(tags)),
            *("--descriptions", str(tmp_path / "missing.json")),
        ],
    )

    importer.main()

    assert f"Imported {len(mini_tags)} effect tags" in capsys.readouterr().out
    with sqlite3.connect(db) as check:
        assert _count(check, "effect_tag") == len(mini_tags)
    check.close()


# --- Appearance index ---------------------------------------------------------------


def test_appearance_index_stores_one_vector_per_pokemon(
    appearance_conn: sqlite3.Connection,
    mini_descriptions: list[AppearanceDescription],
) -> None:
    rows = appearance_conn.execute(
        "SELECT pokemon_id, reference_text, embedding FROM pokemon_appearance"
        " ORDER BY pokemon_id"
    ).fetchall()
    expected_vectors = FakeEmbedder().embed(
        [d.reference_text for d in mini_descriptions]
    )

    assert [r[0] for r in rows] == [d.pokemon_id for d in mini_descriptions]
    assert [r[1] for r in rows] == [d.reference_text for d in mini_descriptions]
    assert [decode_vector(r[2]) for r in rows] == expected_vectors


def test_appearance_index_records_the_model(
    appearance_conn: sqlite3.Connection,
) -> None:
    row = appearance_conn.execute(
        "SELECT model, dimensions FROM appearance_index"
    ).fetchall()
    assert [tuple(r) for r in row] == [
        (embeddings.configured_model(), FakeEmbedder.DIMENSIONS)
    ]


def test_appearance_import_replaces_the_previous_index(
    appearance_conn: sqlite3.Connection,
    mini_descriptions: list[AppearanceDescription],
) -> None:
    import_appearance(
        mini_descriptions[:1], FakeEmbedder(), "other-model", appearance_conn
    )

    assert _count(appearance_conn, "pokemon_appearance") == 1
    assert read_appearance_model(appearance_conn) == "other-model"


def test_appearance_import_rejects_unknown_pokemon(conn: sqlite3.Connection) -> None:
    unknown = AppearanceDescription(999, "a", "b", "c")

    with pytest.raises(ValueError, match=r"unknown Pokémon ids: \[999\]"):
        import_appearance([unknown], FakeEmbedder(), "model", conn)
    assert _count(conn, "pokemon_appearance") == 0


def test_no_appearance_model_before_the_index_is_built(
    conn: sqlite3.Connection,
) -> None:
    assert read_appearance_model(conn) is None


def test_no_appearance_model_on_a_database_without_the_table() -> None:
    """A database imported before this feature existed."""
    with sqlite3.connect(":memory:") as old:
        assert read_appearance_model(old) is None
    old.close()
