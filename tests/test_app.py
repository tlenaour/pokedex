"""Application wiring: settings, real SQLite dependencies, entry point."""

import json
import sqlite3
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import fullstack_pokedex
from fullstack_pokedex.api.app import (
    OPENAPI_FILE,
    create_app,
    create_server,
    export_openapi,
    openapi_schema,
    repository_root,
)
from fullstack_pokedex.api.routes import _load_text_embedder, get_text_embedder
from fullstack_pokedex.api.schemas import ErrorOut
from fullstack_pokedex.domain.appearance import AppearanceDescription
from fullstack_pokedex.domain.errors import DomainError
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


def test_reports_survive_a_pokedex_reimport(db_file: Path, pokedex: Pokedex) -> None:
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


def test_health_is_ok_and_never_cached(db_file: Path) -> None:
    with TestClient(create_app(db_file)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("damage", ["removed", "not a database"])
def test_health_is_unavailable_when_the_database_cannot_be_read(
    db_file: Path, damage: str
) -> None:
    with TestClient(create_app(db_file)) as client:
        if damage == "removed":
            db_file.unlink()
        else:
            db_file.write_text("not a database")
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/pokemon/²",  # str.isdigit() is True, int() raises
        "/pokemon/²/matchup",
        "/moves/¹",
        "/abilities/³",
        "/pokemon/٣",  # another script's digit: not an id
        "/pokemon/99999999999999999999",  # would overflow SQLite's INTEGER
        "/moves/99999999999999999999",
    ],
)
def test_odd_references_are_not_found_rather_than_crashing(
    db_file: Path, path: str
) -> None:
    with TestClient(create_app(db_file)) as client:
        assert client.get(path).status_code == 404


def test_a_reference_with_leading_zeros_is_still_an_id(db_file: Path) -> None:
    with TestClient(create_app(db_file)) as client:
        assert client.get("/pokemon/025").json()["name"] == "pikachu"


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


@pytest.mark.parametrize("model", [None, "another/model"])
def test_identify_checks_the_index_before_loading_the_model(
    tmp_path: Path,
    appearance_conn: sqlite3.Connection,
    mini_descriptions: list[AppearanceDescription],
    model: str | None,
) -> None:
    """A missing or stale index answers 503 without loading the model (slow,
    and it may not even be available: the user would get a 500)."""
    if model is None:
        # Committed: backup() waits forever on a source with a pending write.
        with appearance_conn:
            appearance_conn.execute("DELETE FROM appearance_index")
    else:
        import_appearance(mini_descriptions, FakeEmbedder(), model, appearance_conn)
    db = tmp_path / "pokedex.db"
    with sqlite3.connect(db) as target:
        appearance_conn.backup(target)
    target.close()

    def must_not_load() -> FakeEmbedder:
        raise AssertionError("the model was loaded before checking the index")

    app = create_app(db)
    app.dependency_overrides[get_text_embedder] = must_not_load
    with TestClient(app) as client:
        response = client.get("/pokemon/identify", params={"description": "mouse"})

    assert response.status_code == 503


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


def test_main_starts_the_server_on_localhost() -> None:
    with patch("fullstack_pokedex.uvicorn.run") as run:
        fullstack_pokedex.main()

    run.assert_called_once_with(
        "fullstack_pokedex.api.app:create_server",
        factory=True,
        host="127.0.0.1",
        port=8000,
    )


def test_main_reads_host_and_port_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POKEDEX_HOST", "0.0.0.0")
    monkeypatch.setenv("POKEDEX_PORT", "9000")
    with patch("fullstack_pokedex.uvicorn.run") as run:
        fullstack_pokedex.main()

    assert run.call_args.kwargs["host"] == "0.0.0.0"
    assert run.call_args.kwargs["port"] == 9000


# The server: what runs in production (API under /api, frontend build at /).


@pytest.fixture
def frontend_build(tmp_path: Path) -> Path:
    build = tmp_path / "dist"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text("<title>Pokédex</title>")
    (build / "assets" / "app.js").write_text("console.log('pokedex')")
    return build


def test_server_serves_the_api_under_the_prefix_only(
    db_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_DB", str(db_file))
    client = TestClient(create_server())

    assert client.get("/api/pokemon/pikachu").json()["name"] == "pikachu"
    assert client.get("/api/pokemon/9999").status_code == 404
    assert client.get("/api/docs").status_code == 200
    assert "/pokemon/suggest" in client.get("/api/openapi.json").json()["paths"]
    # Without a frontend build, nothing else is served.
    assert client.get("/pokemon/pikachu").status_code == 404
    assert client.get("/").status_code == 404


def test_server_serves_the_frontend_build(
    db_file: Path, frontend_build: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_DB", str(db_file))
    client = TestClient(create_server(frontend_build))

    assert "Pokédex" in client.get("/").text
    assert "pokedex" in client.get("/assets/app.js").text
    # The API keeps the priority over the files.
    assert client.get("/api/pokemon/pikachu").json()["name"] == "pikachu"
    assert client.get("/api/unknown").headers["content-type"] == "application/json"


def test_server_reads_the_frontend_build_from_env(
    db_file: Path, frontend_build: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_DB", str(db_file))
    monkeypatch.setenv("POKEDEX_STATIC_DIR", str(frontend_build))

    assert "Pokédex" in TestClient(create_server()).get("/").text


def test_server_fails_without_the_frontend_build(
    db_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POKEDEX_DB", str(db_file))

    with pytest.raises(RuntimeError, match="pnpm build"):
        create_server(tmp_path / "missing")


# The API's contract with the frontend (frontend/openapi.json).

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_contract_matches_the_api() -> None:
    """Fails as soon as the API changes without the frontend's contract.

    The frontend's types are generated from this file: if it is stale, the
    frontend compiles against an API that no longer exists.
    """
    contract = REPO_ROOT / OPENAPI_FILE
    fix = (
        "The API changed: run `uv run pokedex-openapi`, then `cd frontend && "
        "pnpm build` (it regenerates the types) and fix what it reports."
    )
    assert contract.is_file(), fix
    assert json.loads(contract.read_text(encoding="utf-8")) == openapi_schema(), fix


def test_contract_is_the_schema_the_app_serves(db_file: Path) -> None:
    assert create_app(db_file).openapi() == openapi_schema()


def test_export_openapi_writes_the_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "openapi.json"
    monkeypatch.setattr("sys.argv", ["pokedex-openapi", "--out", str(out)])

    export_openapi()

    assert json.loads(out.read_text(encoding="utf-8")) == openapi_schema()


# Loading the embedding model (never the real one here).


@pytest.fixture
def fresh_model_cache() -> Iterator[None]:
    """No model loaded before, and no fake one leaking into other tests."""
    _load_text_embedder.cache_clear()
    yield
    _load_text_embedder.cache_clear()


@pytest.mark.usefixtures("fresh_model_cache")
def test_a_model_that_cannot_be_loaded_answers_503(
    appearance_db_file: Path, caplog: pytest.LogCaptureFixture
) -> None:
    internal = "/root/.cache/huggingface: snapshot not found (offline)"
    with (
        patch(
            "fullstack_pokedex.api.routes.Model2VecEmbedder",
            side_effect=OSError(internal),
        ),
        TestClient(create_app(appearance_db_file)) as client,
    ):
        response = client.get("/pokemon/identify", params={"description": "mouse"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The embedding model could not be loaded. Run `uv run "
        "pokedex-import` once with network access to cache it."
    }
    # The technical cause stays on the server: logged, never sent.
    assert internal not in response.text
    assert internal in caplog.text


@pytest.mark.usefixtures("fresh_model_cache")
def test_the_next_search_tries_to_load_the_model_again(
    appearance_db_file: Path,
) -> None:
    with (
        patch(
            "fullstack_pokedex.api.routes.Model2VecEmbedder",
            side_effect=[OSError("offline"), FakeEmbedder()],
        ),
        TestClient(create_app(appearance_db_file)) as client,
    ):
        first = client.get("/pokemon/identify", params={"description": "mouse"})
        second = client.get("/pokemon/identify", params={"description": "mouse"})

    assert (first.status_code, second.status_code) == (503, 200)


@pytest.mark.usefixtures("fresh_model_cache")
def test_concurrent_first_searches_load_the_model_once() -> None:
    loads: list[FakeEmbedder] = []

    def slow_load() -> FakeEmbedder:
        time.sleep(0.2)  # long enough for every thread to arrive meanwhile
        loads.append(FakeEmbedder())
        return loads[-1]

    with (
        patch("fullstack_pokedex.api.routes.Model2VecEmbedder", side_effect=slow_load),
        ThreadPoolExecutor(max_workers=8) as pool,
    ):
        embedders = list(pool.map(lambda _: get_text_embedder(), range(8)))

    assert len(loads) == 1
    assert all(embedder is loads[0] for embedder in embedders)


# Error format.


def test_any_business_error_is_a_422_not_a_500(db_file: Path) -> None:
    class SomeRuleError(DomainError):
        """A business error added later, without its own handler."""

    app = create_app(db_file)

    @app.get("/broken-rule")
    def broken_rule() -> None:
        raise SomeRuleError("this rule is broken")

    with TestClient(app) as client:
        response = client.get("/broken-rule")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [{"loc": [], "msg": "this rule is broken", "type": "value_error"}]
    }


@pytest.mark.parametrize(
    "path",
    [
        "/pokemon/suggest?q=!!!",  # business rule (domain)
        "/pokemon/suggest",  # missing parameter (FastAPI)
        "/pokemon/suggest?q=bulba&limit=99",  # out of range (FastAPI)
    ],
)
def test_every_422_has_the_same_shape(db_file: Path, path: str) -> None:
    """The shape the OpenAPI declares, so the frontend's types are true."""
    with TestClient(create_app(db_file)) as client:
        response = client.get(path)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail
    assert all({"loc", "msg", "type"} <= set(error) for error in detail)


def test_not_found_stays_a_plain_message(db_file: Path) -> None:
    with TestClient(create_app(db_file)) as client:
        response = client.get("/pokemon/missingno")

    assert response.status_code == 404
    assert response.json() == {"detail": "Pokemon 'missingno' not found"}


# Error responses declared in the contract.

REF_ROUTES_WITH_UNKNOWN_REF = [
    "/pokemon/missingno",
    "/pokemon/missingno/matchup",
    "/pokemon/missingno/moves",
    "/moves/missingno",
    "/abilities/missingno",
]


def test_every_ref_route_declares_its_404() -> None:
    paths = openapi_schema()["paths"]
    ref_routes = [path for path in paths if "{ref}" in path]

    assert len(ref_routes) == len(REF_ROUTES_WITH_UNKNOWN_REF)
    for path in ref_routes:
        response = paths[path]["get"]["responses"].get("404")
        assert response, f"{path} answers 404 but does not declare it"
        schema = response["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/ErrorOut"}


def test_routes_that_can_be_unavailable_declare_their_503() -> None:
    paths = openapi_schema()["paths"]

    assert "503" in paths["/pokemon/identify"]["get"]["responses"]
    assert "503" in paths["/health"]["get"]["responses"]


@pytest.mark.parametrize("path", REF_ROUTES_WITH_UNKNOWN_REF)
def test_the_declared_404_is_what_is_sent(db_file: Path, path: str) -> None:
    with TestClient(create_app(db_file)) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert ErrorOut.model_validate(response.json()).detail.endswith("not found")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A folder shaped like the repository: pyproject.toml and frontend/."""
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "frontend" / "src").mkdir(parents=True)
    return tmp_path


@pytest.mark.parametrize("cwd", ["", "frontend", "frontend/src"])
def test_export_openapi_writes_the_same_file_from_anywhere_in_the_repository(
    repository: Path, cwd: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repository / cwd)
    monkeypatch.setattr("sys.argv", ["pokedex-openapi"])

    export_openapi()

    written = repository / "frontend" / "openapi.json"
    assert json.loads(written.read_text(encoding="utf-8")) == openapi_schema()
    # And nowhere else (e.g. not frontend/frontend/openapi.json).
    assert list(repository.rglob("openapi.json")) == [written]


def test_export_openapi_refuses_to_guess_outside_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["pokedex-openapi"])

    with pytest.raises(SystemExit, match="not inside the Pokédex repository"):
        export_openapi()


def test_the_real_repository_root_is_found_from_a_subfolder() -> None:
    assert repository_root(REPO_ROOT / "frontend" / "src") == REPO_ROOT
