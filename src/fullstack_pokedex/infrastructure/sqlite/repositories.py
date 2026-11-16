"""SQLite implementations of the domain repositories."""

import sqlite3
from array import array
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from fullstack_pokedex.domain.appearance import AppearanceCandidate
from fullstack_pokedex.domain.effects import PokemonEffect, SourceKind
from fullstack_pokedex.domain.entities import (
    Ability,
    Images,
    Move,
    Pokemon,
    Species,
    Stats,
)
from fullstack_pokedex.domain.name_search import NameCandidate
from fullstack_pokedex.domain.repositories import MoveCriteria, PokemonCriteria


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a read-only connection. Raises if the database does not exist."""
    conn = sqlite3.connect(
        f"file:{db_path}?mode=ro",
        uri=True,
        # FastAPI may create the connection and use it in different threads
        # (one connection per request, never used concurrently).
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def encode_vector(vector: Sequence[float]) -> bytes:
    """Store a vector compactly: float32 values (4 bytes each)."""
    return array("f", vector).tobytes()


def decode_vector(blob: bytes) -> list[float]:
    vector = array("f")
    vector.frombytes(blob)
    return vector.tolist()


def read_appearance_model(conn: sqlite3.Connection) -> str | None:
    """Embedding model that produced the stored vectors (None if not built)."""
    try:
        row = conn.execute("SELECT model FROM appearance_index").fetchone()
    except sqlite3.OperationalError:  # database imported before this feature
        return None
    return row[0] if row else None


def _placeholders(values: Sequence[Any]) -> str:
    return ", ".join("?" * len(values))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlitePokemonRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, pokemon_id: int) -> Pokemon | None:
        return next(iter(self._select("WHERE id = ?", [pokemon_id])), None)

    def get_by_name(self, name: str) -> Pokemon | None:
        return next(iter(self._select("WHERE name = ?", [name])), None)

    def get_many(self, pokemon_ids: Iterable[int]) -> list[Pokemon]:
        """Ordered by id (the port guarantees no order: do not rely on it)."""
        ids = list(pokemon_ids)
        if not ids:
            return []
        return self._select(f"WHERE id IN ({_placeholders(ids)})", ids)

    def list_name_candidates(self) -> list[NameCandidate]:
        rows = self._conn.execute("SELECT id, name FROM pokemon ORDER BY id")
        return [NameCandidate(pokemon_id=row["id"], name=row["name"]) for row in rows]

    def list_appearance_candidates(self) -> list[AppearanceCandidate]:
        rows = self._conn.execute(
            "SELECT pokemon_id, embedding FROM pokemon_appearance ORDER BY pokemon_id"
        )
        return [
            AppearanceCandidate(pokemon_id=row[0], vector=decode_vector(row[1]))
            for row in rows
        ]

    def search(self, criteria: PokemonCriteria) -> list[Pokemon]:
        clauses: list[str] = []
        params: list[Any] = []
        if criteria.name_contains:
            clauses.append("name LIKE ? ESCAPE '\\'")
            params.append(f"%{_escape_like(criteria.name_contains.lower())}%")
        if criteria.type is not None:
            clauses.append("id IN (SELECT pokemon_id FROM pokemon_type WHERE type = ?)")
            params.append(criteria.type.value)
        if criteria.habitat is not None:
            clauses.append("habitat = ?")
            params.append(criteria.habitat)
        if criteria.is_legendary is not None:
            clauses.append("is_legendary = ?")
            params.append(int(criteria.is_legendary))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._select(where, params)

    def list_by_evolution_chain(self, chain_id: int) -> list[Pokemon]:
        return self._select("WHERE evolution_chain_id = ?", [chain_id])

    def list_by_move(self, move_id: int) -> list[Pokemon]:
        return self._select(
            "WHERE id IN (SELECT pokemon_id FROM pokemon_move WHERE move_id = ?)",
            [move_id],
        )

    def list_by_ability(self, ability_id: int) -> list[Pokemon]:
        return self._select(
            "WHERE id IN (SELECT pokemon_id FROM pokemon_ability WHERE ability_id = ?)",
            [ability_id],
        )

    def _select(self, where: str, params: Sequence[Any]) -> list[Pokemon]:
        """Load Pokémon rows, then their types/moves/abilities in 3 queries."""
        rows = self._conn.execute(
            f"SELECT * FROM pokemon {where} ORDER BY id", params
        ).fetchall()
        if not rows:
            return []

        ids = [row["id"] for row in rows]
        in_ids = f"pokemon_id IN ({_placeholders(ids)})"
        types = self._group(
            f"SELECT pokemon_id, type FROM pokemon_type WHERE {in_ids} ORDER BY slot",
            ids,
        )
        moves = self._group(
            f"SELECT pokemon_id, move_id FROM pokemon_move WHERE {in_ids}", ids
        )
        abilities = self._group(
            f"SELECT pokemon_id, ability_id FROM pokemon_ability WHERE {in_ids}", ids
        )
        return [
            _to_pokemon(row, types[row["id"]], moves[row["id"]], abilities[row["id"]])
            for row in rows
        ]

    def _group(self, sql: str, ids: Sequence[int]) -> dict[int, list[Any]]:
        grouped: dict[int, list[Any]] = defaultdict(list)
        for pokemon_id, value in self._conn.execute(sql, ids):
            grouped[pokemon_id].append(value)
        return grouped


class SqliteMoveRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, move_id: int) -> Move | None:
        row = self._conn.execute(
            "SELECT * FROM move WHERE id = ?", [move_id]
        ).fetchone()
        return Move(**row) if row else None

    def get_by_name(self, name: str) -> Move | None:
        row = self._conn.execute("SELECT * FROM move WHERE name = ?", [name]).fetchone()
        return Move(**row) if row else None

    def get_many(self, move_ids: Iterable[int]) -> list[Move]:
        ids = list(move_ids)
        rows = self._conn.execute(
            f"SELECT * FROM move WHERE id IN ({_placeholders(ids)}) ORDER BY name", ids
        )
        return [Move(**row) for row in rows]

    def search(self, criteria: MoveCriteria) -> list[Move]:
        clauses: list[str] = []
        params: list[Any] = []
        if criteria.type is not None:
            clauses.append("type = ?")
            params.append(criteria.type.value)
        if criteria.damage_class is not None:
            clauses.append("damage_class = ?")
            params.append(criteria.damage_class.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(f"SELECT * FROM move {where} ORDER BY id", params)
        return [Move(**row) for row in rows]


class SqliteAbilityRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, ability_id: int) -> Ability | None:
        row = self._conn.execute(
            "SELECT * FROM ability WHERE id = ?", [ability_id]
        ).fetchone()
        return Ability(**row) if row else None

    def get_by_name(self, name: str) -> Ability | None:
        row = self._conn.execute(
            "SELECT * FROM ability WHERE name = ?", [name]
        ).fetchone()
        return Ability(**row) if row else None

    def get_many(self, ability_ids: Iterable[int]) -> list[Ability]:
        ids = list(ability_ids)
        rows = self._conn.execute(
            f"SELECT * FROM ability WHERE id IN ({_placeholders(ids)}) ORDER BY name",
            ids,
        )
        return [Ability(**row) for row in rows]

    def list_all(self) -> list[Ability]:
        rows = self._conn.execute("SELECT * FROM ability ORDER BY id")
        return [Ability(**row) for row in rows]


class SqliteEffectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_pokemon_effects(self) -> dict[int, list[PokemonEffect]]:
        rows = self._conn.execute(
            """SELECT pm.pokemon_id, 'move' AS kind, m.name, t.tag, t.chance
            FROM pokemon_move pm
            JOIN move m ON m.id = pm.move_id
            JOIN effect_tag t ON t.entity_type = 'move' AND t.entity_id = m.id
            UNION ALL
            SELECT pa.pokemon_id, 'ability', a.name, t.tag, t.chance
            FROM pokemon_ability pa
            JOIN ability a ON a.id = pa.ability_id
            JOIN effect_tag t ON t.entity_type = 'ability' AND t.entity_id = a.id
            ORDER BY 1, 2, 3, 4"""
        )
        effects: defaultdict[int, list[PokemonEffect]] = defaultdict(list)
        for pokemon_id, kind, source, tag, chance in rows:
            effects[pokemon_id].append(
                PokemonEffect(tag, SourceKind(kind), source, chance)
            )
        return dict(effects)


def _to_pokemon(
    row: sqlite3.Row, types: list[str], move_ids: list[int], ability_ids: list[int]
) -> Pokemon:
    return Pokemon(
        id=row["id"],
        name=row["name"],
        height_decimetres=row["height_decimetres"],
        weight_hectograms=row["weight_hectograms"],
        base_experience=row["base_experience"],
        types=tuple(types),
        stats=Stats(**{field: row[field] for field in Stats.model_fields}),
        species=Species(**{field: row[field] for field in Species.model_fields}),
        images=Images(
            sprite=row["sprite_url"], official_artwork=row["official_artwork_url"]
        ),
        move_ids=frozenset(move_ids),
        ability_ids=frozenset(ability_ids),
    )
