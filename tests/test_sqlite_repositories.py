import sqlite3
from pathlib import Path

import pytest

from fullstack_pokedex.domain.appearance import AppearanceDescription
from fullstack_pokedex.domain.effects import PokemonEffect, SourceKind
from fullstack_pokedex.domain.entities import DamageClass, PokemonType
from fullstack_pokedex.domain.name_search import MatchKind, NameCandidate
from fullstack_pokedex.domain.repositories import (
    AbilityRepository,
    EffectRepository,
    FeedbackRepository,
    MoveCriteria,
    MoveRepository,
    PokemonCriteria,
    PokemonRepository,
)
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex
from fullstack_pokedex.infrastructure.sqlite.feedback import SqliteFeedbackRepository
from fullstack_pokedex.infrastructure.sqlite.repositories import (
    SqliteAbilityRepository,
    SqliteEffectRepository,
    SqliteMoveRepository,
    SqlitePokemonRepository,
    connect,
    decode_vector,
    encode_vector,
)
from fullstack_pokedex.use_cases.suggest_pokemon import (
    SuggestPokemon,
    SuggestPokemonQuery,
)
from tests.factories import FakeEmbedder


@pytest.mark.parametrize(
    "port, implementation",
    [
        (PokemonRepository, SqlitePokemonRepository),
        (MoveRepository, SqliteMoveRepository),
        (AbilityRepository, SqliteAbilityRepository),
        (EffectRepository, SqliteEffectRepository),
        (FeedbackRepository, SqliteFeedbackRepository),
    ],
)
def test_implementation_provides_every_port_method(
    port: type, implementation: type
) -> None:
    """No type checker runs on the project: catch a port method left
    unimplemented (it would only fail at runtime, on the route using it)."""
    port_methods = {name for name in vars(port) if not name.startswith("_")}
    missing = {name for name in port_methods if not hasattr(implementation, name)}
    assert not missing


@pytest.fixture
def pokemon_repo(conn: sqlite3.Connection) -> SqlitePokemonRepository:
    return SqlitePokemonRepository(conn)


@pytest.fixture
def move_repo(conn: sqlite3.Connection) -> SqliteMoveRepository:
    return SqliteMoveRepository(conn)


@pytest.fixture
def ability_repo(conn: sqlite3.Connection) -> SqliteAbilityRepository:
    return SqliteAbilityRepository(conn)


# --- Round trip: what is imported is read back identically -------------------


def test_pokemon_round_trip(
    pokedex: Pokedex, pokemon_repo: SqlitePokemonRepository
) -> None:
    for pokemon in pokedex.pokemon:
        assert pokemon_repo.get_by_id(pokemon.id) == pokemon
        assert pokemon_repo.get_by_name(pokemon.name) == pokemon


def test_move_round_trip(pokedex: Pokedex, move_repo: SqliteMoveRepository) -> None:
    for move in pokedex.moves:
        assert move_repo.get_by_id(move.id) == move
        assert move_repo.get_by_name(move.name) == move


def test_ability_round_trip(
    pokedex: Pokedex, ability_repo: SqliteAbilityRepository
) -> None:
    for ability in pokedex.abilities:
        assert ability_repo.get_by_id(ability.id) == ability
        assert ability_repo.get_by_name(ability.name) == ability


def test_unknown_entities_return_none(
    pokemon_repo: SqlitePokemonRepository,
    move_repo: SqliteMoveRepository,
    ability_repo: SqliteAbilityRepository,
) -> None:
    assert pokemon_repo.get_by_id(999) is None
    assert pokemon_repo.get_by_name("missingno") is None
    assert move_repo.get_by_id(999) is None
    assert move_repo.get_by_name("nope") is None
    assert ability_repo.get_by_id(999) is None
    assert ability_repo.get_by_name("nope") is None


# --- Pokémon search -------------------------------------------------------------


@pytest.mark.parametrize(
    "criteria, expected",
    [
        (PokemonCriteria(), ["bulbasaur", "ivysaur", "pikachu", "mewtwo"]),
        (PokemonCriteria(name_contains="SAUR"), ["bulbasaur", "ivysaur"]),
        (PokemonCriteria(type=PokemonType.POISON), ["bulbasaur", "ivysaur"]),
        (PokemonCriteria(habitat="forest"), ["pikachu"]),
        (PokemonCriteria(is_legendary=True), ["mewtwo"]),
        (
            PokemonCriteria(is_legendary=False),
            ["bulbasaur", "ivysaur", "pikachu"],
        ),
        (PokemonCriteria(type=PokemonType.GRASS, name_contains="ivy"), ["ivysaur"]),
        (PokemonCriteria(type=PokemonType.FIRE), []),
        # LIKE wildcards are escaped: they match literally, not "anything".
        (PokemonCriteria(name_contains="%"), []),
        (PokemonCriteria(name_contains="_"), []),
    ],
)
def test_search_pokemon(
    pokemon_repo: SqlitePokemonRepository,
    criteria: PokemonCriteria,
    expected: list[str],
) -> None:
    assert [p.name for p in pokemon_repo.search(criteria)] == expected


def test_list_by_evolution_chain(pokemon_repo: SqlitePokemonRepository) -> None:
    assert [p.name for p in pokemon_repo.list_by_evolution_chain(1)] == [
        "bulbasaur",
        "ivysaur",
    ]


def test_list_by_move(pokemon_repo: SqlitePokemonRepository) -> None:
    thunderbolt = 85
    assert [p.name for p in pokemon_repo.list_by_move(thunderbolt)] == [
        "pikachu",
        "mewtwo",
    ]


def test_list_by_ability(pokemon_repo: SqlitePokemonRepository) -> None:
    chlorophyll = 34
    assert [p.name for p in pokemon_repo.list_by_ability(chlorophyll)] == [
        "bulbasaur",
        "ivysaur",
    ]


# --- Name search support ----------------------------------------------------------


def test_list_name_candidates(pokemon_repo: SqlitePokemonRepository) -> None:
    assert pokemon_repo.list_name_candidates() == [
        NameCandidate(1, "bulbasaur"),
        NameCandidate(2, "ivysaur"),
        NameCandidate(25, "pikachu"),
        NameCandidate(150, "mewtwo"),
    ]


def test_get_many_pokemon_returns_complete_entities(
    pokedex: Pokedex, pokemon_repo: SqlitePokemonRepository
) -> None:
    expected = {p.id: p for p in pokedex.pokemon}

    loaded = pokemon_repo.get_many([150, 1])

    assert {p.id: p for p in loaded} == {1: expected[1], 150: expected[150]}


@pytest.mark.parametrize(
    "ids, expected",
    [
        ([], set()),
        ([999], set()),  # unknown ids are ignored
        ([25, 999], {25}),
        ([25, 25], {25}),  # duplicates are loaded once
        (iter([1, 2]), {1, 2}),  # any iterable, not only lists
    ],
)
def test_get_many_pokemon_edge_cases(
    pokemon_repo: SqlitePokemonRepository, ids: object, expected: set[int]
) -> None:
    loaded = pokemon_repo.get_many(ids)  # type: ignore[arg-type]
    assert [p.id for p in loaded] == sorted(expected)


def test_suggest_pokemon_on_sqlite(pokemon_repo: SqlitePokemonRepository) -> None:
    """Integration: the use case with the real repository, no mock."""
    suggest = SuggestPokemon(pokemon=pokemon_repo)

    [suggestion] = suggest.execute(SuggestPokemonQuery("bulba"))

    assert suggestion.name == "bulbasaur"
    assert suggestion.genus == "Seed Pokémon"
    assert suggestion.match_kind is MatchKind.PREFIX
    assert str(suggestion.sprite).endswith("/1.png")


# --- Moves & abilities ----------------------------------------------------------


def test_get_many_moves_is_sorted_by_name(move_repo: SqliteMoveRepository) -> None:
    moves = move_repo.get_many([85, 22, 45])
    assert [m.name for m in moves] == ["growl", "thunderbolt", "vine-whip"]


def test_get_many_with_no_ids(
    move_repo: SqliteMoveRepository, ability_repo: SqliteAbilityRepository
) -> None:
    assert move_repo.get_many([]) == []
    assert ability_repo.get_many([]) == []


@pytest.mark.parametrize(
    "criteria, expected",
    [
        (MoveCriteria(), 6),
        (MoveCriteria(type=PokemonType.NORMAL), 3),
        (MoveCriteria(damage_class=DamageClass.SPECIAL), 3),
        (MoveCriteria(type=PokemonType.NORMAL, damage_class=DamageClass.STATUS), 1),
    ],
)
def test_search_moves(
    move_repo: SqliteMoveRepository, criteria: MoveCriteria, expected: int
) -> None:
    assert len(move_repo.search(criteria)) == expected


def test_list_all_abilities_is_sorted_by_id(
    ability_repo: SqliteAbilityRepository,
) -> None:
    ids = [a.id for a in ability_repo.list_all()]
    assert ids == sorted(ids)
    assert len(ids) == 6


def test_get_many_abilities_is_sorted_by_name(
    ability_repo: SqliteAbilityRepository,
) -> None:
    abilities = ability_repo.get_many([65, 34])
    assert [a.name for a in abilities] == ["chlorophyll", "overgrow"]


# --- Connection -----------------------------------------------------------------


def test_connect_is_read_only(tmp_path: Path, conn: sqlite3.Connection) -> None:
    db = tmp_path / "pokedex.db"
    with sqlite3.connect(db) as target:
        conn.backup(target)
    target.close()

    ro = connect(db)
    assert ro.execute("SELECT name FROM pokemon WHERE id = 25").fetchone()["name"] == (
        "pikachu"
    )
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        ro.execute("DELETE FROM pokemon")
    ro.close()


def test_connect_fails_on_missing_database(tmp_path: Path) -> None:
    with pytest.raises(sqlite3.OperationalError):
        connect(tmp_path / "missing.db")


# --- Appearance index -----------------------------------------------------------------


def test_list_appearance_candidates(
    appearance_conn: sqlite3.Connection,
    mini_descriptions: list[AppearanceDescription],
) -> None:
    candidates = SqlitePokemonRepository(appearance_conn).list_appearance_candidates()
    expected = FakeEmbedder().embed([d.reference_text for d in mini_descriptions])

    assert [c.pokemon_id for c in candidates] == [1, 2, 25, 150]
    assert [list(c.vector) for c in candidates] == expected


def test_no_appearance_candidates_without_index(
    pokemon_repo: SqlitePokemonRepository,
) -> None:
    assert pokemon_repo.list_appearance_candidates() == []


@pytest.mark.parametrize("vector", [[], [0.0], [1.0, -2.5, 3.25], [0.1] * 512])
def test_vector_storage_round_trip(vector: list[float]) -> None:
    decoded = decode_vector(encode_vector(vector))
    assert decoded == pytest.approx(vector)  # float32 precision
    assert len(encode_vector(vector)) == 4 * len(vector)


def test_pokemon_effects_come_from_moves_and_abilities(
    conn: sqlite3.Connection,
) -> None:
    effects = SqliteEffectRepository(conn).list_pokemon_effects()

    assert set(effects) <= {1, 2, 25, 150}
    assert (
        PokemonEffect("immune:electric", SourceKind.ABILITY, "lightning-rod", None)
        in effects[25]
    )
    assert (
        PokemonEffect("inflicts:paralysis", SourceKind.MOVE, "thunderbolt", 10)
        in effects[25]
    )
    # Only Pikachu learns Thunderbolt in the mini pokedex.
    assert all(e.source != "thunderbolt" for e in effects.get(1, []))
