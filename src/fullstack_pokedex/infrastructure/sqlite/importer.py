"""Import pokedex.json into a SQLite database (recreates the schema), then the
effect tags from data/tags_llm.json, then build the appearance search index
from data/pokemon_descriptions.json.

Usage: uv run pokedex-import [--json pokedex.json] [--db pokedex.db]
                             [--tags data/tags_llm.json]
                             [--descriptions data/pokemon_descriptions.json]
"""

import argparse
import sqlite3
from contextlib import closing
from importlib.resources import files
from pathlib import Path

from fullstack_pokedex.domain.appearance import AppearanceDescription, TextEmbedder
from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.infrastructure import appearance_descriptions, effect_tags
from fullstack_pokedex.infrastructure.effect_tags import EffectTag
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex, load_pokedex
from fullstack_pokedex.infrastructure.sqlite.repositories import encode_vector

SCHEMA = files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")


def import_pokedex(pokedex: Pokedex, conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    with conn:  # single transaction
        conn.executemany(
            "INSERT INTO type (name) VALUES (?)", [(t.value,) for t in PokemonType]
        )
        conn.executemany(
            """INSERT INTO ability (id, name, effect, short_effect, generation, is_main_series)
            VALUES (:id, :name, :effect, :short_effect, :generation, :is_main_series)""",
            [a.model_dump() for a in pokedex.abilities],
        )
        conn.executemany(
            """INSERT INTO move (id, name, type, damage_class, power, accuracy, pp,
                                 priority, effect_chance, effect, short_effect, generation)
            VALUES (:id, :name, :type, :damage_class, :power, :accuracy, :pp,
                    :priority, :effect_chance, :effect, :short_effect, :generation)""",
            [m.model_dump(mode="json") for m in pokedex.moves],
        )
        conn.executemany(
            """INSERT INTO pokemon (id, name, height_decimetres, weight_hectograms,
                base_experience, hp, attack, defense, special_attack, special_defense,
                speed, genus, description, generation, color, shape, habitat,
                is_legendary, is_mythical, evolution_chain_id, sprite_url,
                official_artwork_url)
            VALUES (:id, :name, :height_decimetres, :weight_hectograms,
                :base_experience, :hp, :attack, :defense, :special_attack,
                :special_defense, :speed, :genus, :description, :generation, :color,
                :shape, :habitat, :is_legendary, :is_mythical, :evolution_chain_id,
                :sprite_url, :official_artwork_url)""",
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "height_decimetres": p.height_decimetres,
                    "weight_hectograms": p.weight_hectograms,
                    "base_experience": p.base_experience,
                    **p.stats.model_dump(),
                    **p.species.model_dump(),
                    "sprite_url": str(p.images.sprite),
                    "official_artwork_url": str(p.images.official_artwork),
                }
                for p in pokedex.pokemon
            ],
        )
        conn.executemany(
            "INSERT INTO pokemon_type (pokemon_id, slot, type) VALUES (?, ?, ?)",
            [
                (p.id, slot, t.value)
                for p in pokedex.pokemon
                for slot, t in enumerate(p.types, start=1)
            ],
        )
        conn.executemany(
            "INSERT INTO pokemon_move (pokemon_id, move_id) VALUES (?, ?)",
            [(p.id, m) for p in pokedex.pokemon for m in sorted(p.move_ids)],
        )
        conn.executemany(
            "INSERT INTO pokemon_ability (pokemon_id, ability_id) VALUES (?, ?)",
            [(p.id, a) for p in pokedex.pokemon for a in sorted(p.ability_ids)],
        )


def import_effect_tags(tags: list[EffectTag], conn: sqlite3.Connection) -> None:
    """Store the effect tags, each linked to its move or ability by name.

    Must run after import_pokedex: every name must match a move or an ability.
    """
    ids = {
        (entity_type, name): entity_id
        for entity_type in ("move", "ability")
        for entity_id, name in conn.execute(f"SELECT id, name FROM {entity_type}")
    }
    if unknown := sorted(
        {f"{t.entity_type} {t.entity_name}" for t in tags}
        - {f"{entity_type} {name}" for entity_type, name in ids}
    ):
        raise ValueError(f"Effect tags for unknown moves or abilities: {unknown}")

    with conn:  # single transaction
        conn.execute("DELETE FROM effect_tag")
        conn.executemany(
            """INSERT INTO effect_tag (entity_type, entity_id, tag, chance, trigger,
                                       evidence)
            VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    t.entity_type,
                    ids[(t.entity_type, t.entity_name)],
                    t.tag,
                    t.chance,
                    t.trigger,
                    t.evidence,
                )
                for t in tags
            ],
        )


def import_appearance(
    descriptions: list[AppearanceDescription],
    embedder: TextEmbedder,
    model_name: str,
    conn: sqlite3.Connection,
) -> None:
    """Embed each Pokémon's reference text and store the vectors.

    Must run after import_pokedex: every description must match a Pokémon
    (enforced by a foreign key).
    """
    known = {row[0] for row in conn.execute("SELECT id FROM pokemon")}
    if unknown := sorted({d.pokemon_id for d in descriptions} - known):
        raise ValueError(f"Descriptions for unknown Pokémon ids: {unknown}")

    vectors = embedder.embed([d.reference_text for d in descriptions])
    conn.execute("PRAGMA foreign_keys = ON")
    with conn:  # single transaction
        conn.execute("DELETE FROM pokemon_appearance")
        conn.execute("DELETE FROM appearance_index")
        conn.executemany(
            """INSERT INTO pokemon_appearance (pokemon_id, reference_text, embedding)
            VALUES (?, ?, ?)""",
            [
                (d.pokemon_id, d.reference_text, encode_vector(v))
                for d, v in zip(descriptions, vectors, strict=True)
            ],
        )
        conn.execute(
            "INSERT INTO appearance_index (model, dimensions) VALUES (?, ?)",
            (model_name, len(vectors[0]) if vectors else 0),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=Path("pokedex.json"))
    parser.add_argument("--db", type=Path, default=Path("pokedex.db"))
    parser.add_argument("--tags", type=Path, default=effect_tags.DEFAULT_PATH)
    parser.add_argument(
        "--descriptions", type=Path, default=appearance_descriptions.DEFAULT_PATH
    )
    args = parser.parse_args()

    pokedex = load_pokedex(args.json)
    # closing(): `with sqlite3.connect()` commits but never closes the connection.
    with closing(sqlite3.connect(args.db)) as conn:
        import_pokedex(pokedex, conn)
        print(
            f"Imported {len(pokedex.pokemon)} pokemon, {len(pokedex.moves)} moves, "
            f"{len(pokedex.abilities)} abilities into {args.db}"
        )

        if not args.tags.is_file():
            print(f"No {args.tags}: effect tags not imported.")
        else:
            tags = effect_tags.load_effect_tags(args.tags)
            import_effect_tags(tags, conn)
            print(f"Imported {len(tags)} effect tags")

        if not args.descriptions.is_file():
            print(f"No {args.descriptions}: appearance search index not built.")
        else:
            # Imported here: loading the model is slow and only needed for this.
            from fullstack_pokedex.infrastructure.embeddings import Model2VecEmbedder

            descriptions = appearance_descriptions.load_appearance_descriptions(
                args.descriptions
            )
            embedder = Model2VecEmbedder()
            import_appearance(descriptions, embedder, embedder.model_name, conn)
            print(
                f"Built the appearance index: {len(descriptions)} pokemon, "
                f"model {embedder.model_name}"
            )


if __name__ == "__main__":
    main()
