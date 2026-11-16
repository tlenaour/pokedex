"""Application wiring: settings, real SQLite dependencies, entry point."""

import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import fullstack_pokedex
from fullstack_pokedex.api.app import create_app
from fullstack_pokedex.api.routes import get_text_embedder
from fullstack_pokedex.domain.appearance import AppearanceDescription
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex
from fullstack_pokedex.infrastructure.sqlite.importer import (
    import_appearance,
    import_pokedex,
)
from tests.factories import FakeEmbedder


@pytest.fixture
def db_file(tmp_path: Path, conn: sqlite3.Connection) -> Path:
    """Copy of the in-memory mini pokedex to a file."""
    db = tmp_path / "pokedex.db"
    with sqlite3.connect(db) as target:
        conn.backup(target)
    target.close()
    return db


@pytest.fixture
def appearance_db_file(tmp_path: Path, appearance_conn: sqlite3.Connection) -> Path:
    """Mini pokedex with its appearance index (built with FakeEmbedder)."""
    db = tmp_path / "pokedex-appearance.db"
    with sqlite3.connect(db) as target:
        appearance_conn.backup(target)
    target.close()
    return db


def identify_client(db: Path) -> TestClient:
    app = create_app(db)
    # The fake embedder that built the test index: no model download.
    app.dependency_overrides[get_text_embedder] = FakeEmbedder
    return TestClient(app)


def test_create_app_fails_without_database(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="pokedex-import"):
        create_app(tmp_path / "missing.db")


def test_create_app_reads_db_path_from_env(
    db_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_DB", str(db_file))
    assert create_app().state.db_path == db_file


def test_feedback_db_is_created_next_to_the_pokedex(db_file: Path) -> None:
    app = create_app(db_file)

    assert app.state.feedback_db_path == db_file.with_name("feedback.db")
    assert app.state.feedback_db_path.is_file()


def test_feedback_db_path_from_env(
    db_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_FEEDBACK_DB", str(tmp_path / "elsewhere.db"))
    assert create_app(db_file).state.feedback_db_path == tmp_path / "elsewhere.db"


def test_trainer_reports_a_missing_pokemon(db_file: Path) -> None:
    """End to end: route, use case, both databases, no mock."""
    with TestClient(create_app(db_file)) as client:
        created = client.post(
            "/feedback/missing-result",
            json={"kind": "name", "query": "  bulbi ", "shown_ids": [1, 2]},
        )
        unknown = client.post(
            "/feedback/missing-result",
            json={"kind": "name", "query": "x", "shown_ids": [999]},
        )

    assert created.status_code == 201
    assert unknown.status_code == 422
    with sqlite3.connect(db_file.with_name("feedback.db")) as check:
        saved = check.execute(
            "SELECT id, kind, query, shown_ids FROM missing_result_report"
        ).fetchall()
    check.close()
    assert saved == [(created.json()["id"], "name", "bulbi", "[1, 2]")]


def test_reports_survive_a_pokedex_reimport(
    db_file: Path, pokedex: Pokedex, tmp_path: Path
) -> None:
    """pokedex-import rebuilds pokedex.db: feedback is in another file."""
    with TestClient(create_app(db_file)) as client:
        client.post(
            "/feedback/missing-result",
            json={"kind": "appearance", "query": "blue noodles", "shown_ids": []},
        )
    with closing(sqlite3.connect(db_file)) as target:
        import_pokedex(pokedex, target)

    with closing(sqlite3.connect(db_file.with_name("feedback.db"))) as check:
        count = check.execute("SELECT count(*) FROM missing_result_report").fetchone()
    assert count == (1,)


def test_catalog_lists_the_whole_pokedex_in_order(db_file: Path) -> None:
    with TestClient(create_app(db_file)) as client:
        response = client.get("/pokemon")

    assert response.status_code == 200
    catalog = response.json()
    assert [p["id"] for p in catalog] == [1, 2, 25, 150]
    assert catalog[0] == {
        "id": 1,
        "name": "bulbasaur",
        "display_name": "Bulbasaur",
        "types": ["grass", "poison"],
        "sprite": catalog[0]["sprite"],
        "genus": "Seed Pokémon",
    }
    assert catalog[0]["sprite"].endswith("/1.png")


def test_trainer_prepares_a_fight_against_pikachu(db_file: Path) -> None:
    with TestClient(create_app(db_file)) as client:
        response = client.get("/pokemon/pikachu/matchup")

    assert response.status_code == 200
    matchup = response.json()
    assert matchup["weaknesses"] == [{"type": "ground", "multiplier": 2}]
    # Lightning Rod is one of Pikachu's abilities (effect tags of the mini pokedex).
    assert {"type": "electric", "ability": "lightning-rod"} in matchup["immunities"]


def test_routes_are_wired_to_sqlite(db_file: Path) -> None:
    """Smoke test without mocks: the real dependencies reach the database."""
    with TestClient(create_app(db_file)) as client:
        response = client.get("/pokemon/pikachu")

    assert response.status_code == 200
    assert response.json()["id"] == 25


def test_new_trainer_finds_bulbasaur_from_bulba(db_file: Path) -> None:
    """Acceptance test of the feature, end to end and without mocks:
    a trainer remembers that the name began with "bulba"."""
    with TestClient(create_app(db_file)) as client:
        response = client.get("/pokemon/suggest", params={"q": "Bulba"})

    assert response.status_code == 200
    first = response.json()[0]
    assert first["name"] == "bulbasaur"
    assert first["display_name"] == "Bulbasaur"
    # What lets them confirm it is the one they saw:
    assert first["sprite"].endswith("/1.png")
    assert first["types"] == ["grass", "poison"]
    assert first["genus"] == "Seed Pokémon"
    # What lets the UI show "**Bulba**saur":
    assert first["match"]["segments"] == [
        {"text": "Bulba", "matched": True},
        {"text": "saur", "matched": False},
    ]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("bulbsaur", "bulbasaur"),  # typo in the full name
        ("bulbs", "bulbasaur"),  # partially remembered AND mistyped
        ("pikachoo", "pikachu"),  # written as it sounds
    ],
)
def test_trainer_finds_the_pokemon_despite_a_typo(
    db_file: Path, query: str, expected: str
) -> None:
    """End to end with the real Jaro-Winkler scorer: typo tolerance is wired."""
    with TestClient(create_app(db_file)) as client:
        suggestions = client.get("/pokemon/suggest", params={"q": query}).json()

    assert [s["name"] for s in suggestions] == [expected]
    assert suggestions[0]["match"]["kind"] == "fuzzy"
    assert [s["matched"] for s in suggestions[0]["match"]["segments"]] == [False]


def test_unrelated_query_suggests_nothing(db_file: Path) -> None:
    with TestClient(create_app(db_file)) as client:
        response = client.get("/pokemon/suggest", params={"q": "xyz"})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "path, status, cached",
    [
        ("/pokemon/suggest?q=bulba", 200, True),
        ("/pokemon/pikachu", 200, True),
        ("/pokemon/9999", 404, False),  # NotFoundError handler
        ("/pokemon/suggest?q=!!!", 422, False),  # InvalidSearchQueryError handler
        ("/pokemon/suggest", 422, False),  # FastAPI parameter validation
    ],
)
def test_only_successful_responses_are_cacheable(
    db_file: Path, path: str, status: int, cached: bool
) -> None:
    with TestClient(create_app(db_file, cache_max_age=120)) as client:
        response = client.get(path)

    assert response.status_code == status
    assert response.headers.get("cache-control") == (
        "public, max-age=120" if cached else None
    )


def test_trainer_identifies_pikachu_from_its_appearance(
    appearance_db_file: Path,
) -> None:
    """End to end: route, use case, SQLite index, domain ranking (fake embedder)."""
    with identify_client(appearance_db_file) as client:
        response = client.get(
            "/pokemon/identify",
            params={"description": "small yellow mouse with red cheeks"},
        )

    assert response.status_code == 200
    first = response.json()[0]
    assert first["name"] == "pikachu"
    assert first["display_name"] == "Pikachu"
    assert first["genus"] == "Mouse Pokémon"


def test_identify_refuses_an_index_built_with_another_model(
    tmp_path: Path,
    appearance_conn: sqlite3.Connection,
    mini_descriptions: list[AppearanceDescription],
) -> None:
    import_appearance(
        mini_descriptions, FakeEmbedder(), "another/model", appearance_conn
    )
    db = tmp_path / "other-model.db"
    with sqlite3.connect(db) as target:
        appearance_conn.backup(target)
    target.close()

    with identify_client(db) as client:
        response = client.get("/pokemon/identify", params={"description": "mouse"})

    assert response.status_code == 503
    assert "another/model" in response.json()["detail"]


def test_main_starts_uvicorn() -> None:
    with patch("fullstack_pokedex.uvicorn.run") as run:
        fullstack_pokedex.main()

    run.assert_called_once_with("fullstack_pokedex.api.app:create_app", factory=True)
