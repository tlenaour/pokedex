"""API tests: repositories and use cases are replaced by mocks, no database."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from fullstack_pokedex.api.app import create_app
from fullstack_pokedex.api.routes import (
    get_ability_repository,
    get_get_matchup,
    get_identify_pokemon,
    get_list_pokemon,
    get_move_repository,
    get_pokemon_repository,
    get_report_missing_result,
    get_suggest_pokemon,
    get_text_embedder,
)
from fullstack_pokedex.domain.effects import (
    Effect,
    Pitfall,
    PitfallKind,
    Protection,
    ProtectionKind,
    Threat,
)
from fullstack_pokedex.domain.entities import DamageClass, PokemonType
from fullstack_pokedex.domain.errors import (
    InvalidReportError,
    InvalidSearchQueryError,
    NotFoundError,
)
from fullstack_pokedex.domain.feedback import MissingResultReport, SearchKind
from fullstack_pokedex.domain.matchup import (
    DefensiveProfile,
    TypeImmunity,
    TypeMultiplier,
)
from fullstack_pokedex.domain.name_search import MatchKind, NameSegment
from fullstack_pokedex.domain.repositories import (
    AbilityRepository,
    MoveCriteria,
    MoveRepository,
    PokemonCriteria,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.get_matchup import GetMatchup, Matchup
from fullstack_pokedex.use_cases.identify_pokemon import (
    IdentifyPokemon,
    IdentifyPokemonQuery,
    PokemonIdentification,
)
from fullstack_pokedex.use_cases.list_pokemon import ListPokemon, PokemonListItem
from fullstack_pokedex.use_cases.report_missing_result import ReportMissingResult
from fullstack_pokedex.use_cases.suggest_pokemon import (
    DEFAULT_LIMIT,
    PokemonSuggestion,
    SuggestPokemon,
    SuggestPokemonQuery,
)
from tests.factories import FakeEmbedder, make_ability, make_move, make_pokemon


@dataclass
class Mocks:
    pokemon: MagicMock
    moves: MagicMock
    abilities: MagicMock
    suggest: MagicMock
    identify: MagicMock
    report: MagicMock
    list: MagicMock
    matchup: MagicMock


@pytest.fixture
def mocks() -> Mocks:
    # autospec: calling a method that does not exist fails the test.
    return Mocks(
        pokemon=create_autospec(PokemonRepository, instance=True),
        moves=create_autospec(MoveRepository, instance=True),
        abilities=create_autospec(AbilityRepository, instance=True),
        suggest=create_autospec(SuggestPokemon, instance=True),
        identify=create_autospec(IdentifyPokemon, instance=True),
        report=create_autospec(ReportMissingResult, instance=True),
        list=create_autospec(ListPokemon, instance=True),
        matchup=create_autospec(GetMatchup, instance=True),
    )


@pytest.fixture
def client(tmp_path: Path, mocks: Mocks) -> Iterator[TestClient]:
    db = tmp_path / "unused.db"
    db.touch()  # create_app checks that the file exists
    app = create_app(db)
    app.dependency_overrides = {
        get_pokemon_repository: lambda: mocks.pokemon,
        get_move_repository: lambda: mocks.moves,
        get_ability_repository: lambda: mocks.abilities,
        get_suggest_pokemon: lambda: mocks.suggest,
        get_identify_pokemon: lambda: mocks.identify,
        get_report_missing_result: lambda: mocks.report,
        get_list_pokemon: lambda: mocks.list,
        get_get_matchup: lambda: mocks.matchup,
        # Never load the real model in API tests.
        get_text_embedder: FakeEmbedder,
    }
    with TestClient(app) as client:
        yield client


# --- GET /pokemon/suggest ----------------------------------------------------

BULBASAUR_SUGGESTION = PokemonSuggestion(
    id=1,
    name="bulbasaur",
    display_name="Bulbasaur",
    sprite="https://example.com/1.png",  # type: ignore[arg-type]
    types=(PokemonType.GRASS, PokemonType.POISON),
    genus="Seed Pokémon",
    match_kind=MatchKind.PREFIX,
    score=1.0,
    segments=(NameSegment("Bulba", True), NameSegment("saur", False)),
)


def test_suggest_returns_what_is_needed_to_recognize_the_pokemon(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.suggest.execute.return_value = [BULBASAUR_SUGGESTION]

    response = client.get("/pokemon/suggest?q=bulba")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "bulbasaur",
            "display_name": "Bulbasaur",
            "sprite": "https://example.com/1.png",
            "types": ["grass", "poison"],
            "genus": "Seed Pokémon",
            "match": {
                "kind": "prefix",
                "score": 1.0,
                "segments": [
                    {"text": "Bulba", "matched": True},
                    {"text": "saur", "matched": False},
                ],
            },
        }
    ]


def test_suggest_forwards_the_query_to_the_use_case(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.suggest.execute.return_value = []

    client.get("/pokemon/suggest?q=Bulba&limit=3")

    # The raw text is forwarded: normalizing it is the use case's job.
    mocks.suggest.execute.assert_called_once_with(
        SuggestPokemonQuery(text="Bulba", limit=3)
    )


def test_suggest_uses_the_default_limit(client: TestClient, mocks: Mocks) -> None:
    mocks.suggest.execute.return_value = []

    client.get("/pokemon/suggest?q=bulba")

    mocks.suggest.execute.assert_called_once_with(
        SuggestPokemonQuery(text="bulba", limit=DEFAULT_LIMIT)
    )


def test_suggest_without_match_returns_an_empty_list(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.suggest.execute.return_value = []

    response = client.get("/pokemon/suggest?q=xyz")

    assert response.status_code == 200
    assert response.json() == []


def test_fuzzy_suggestion_is_one_unmatched_segment(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.suggest.execute.return_value = [
        PokemonSuggestion(
            **{
                **vars(BULBASAUR_SUGGESTION),
                "match_kind": MatchKind.FUZZY,
                "score": 0.9,
                "segments": (NameSegment("Bulbasaur", False),),
            }
        )
    ]

    match = client.get("/pokemon/suggest?q=bulbsaur").json()[0]["match"]

    assert match == {
        "kind": "fuzzy",
        "score": 0.9,
        "segments": [{"text": "Bulbasaur", "matched": False}],
    }


@pytest.mark.parametrize(
    "query",
    ["", "?q=", "?q=bulba&limit=0", "?q=bulba&limit=11", "?q=" + "a" * 101],
)
def test_suggest_rejects_invalid_parameters(
    client: TestClient, mocks: Mocks, query: str
) -> None:
    assert client.get(f"/pokemon/suggest{query}").status_code == 422
    mocks.suggest.execute.assert_not_called()


def test_business_validation_error_returns_422(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.suggest.execute.side_effect = InvalidSearchQueryError(
        "!!!", "no letter or digit"
    )

    response = client.get("/pokemon/suggest?q=!!!")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": [],
                "msg": "Invalid search query '!!!': no letter or digit",
                "type": "value_error",
            }
        ]
    }


def test_suggest_is_not_captured_by_the_pokemon_detail_route(
    client: TestClient, mocks: Mocks
) -> None:
    """/pokemon/{ref} must not treat "suggest" as a Pokémon name."""
    mocks.suggest.execute.return_value = []

    client.get("/pokemon/suggest?q=bulba")

    mocks.suggest.execute.assert_called_once()
    mocks.pokemon.get_by_name.assert_not_called()


# --- GET /pokemon/identify ---------------------------------------------------

PIKACHU_IDENTIFICATION = PokemonIdentification(
    id=25,
    name="pikachu",
    display_name="Pikachu",
    sprite="https://example.com/25.png",  # type: ignore[arg-type]
    types=(PokemonType.ELECTRIC,),
    genus="Mouse Pokémon",
    score=0.87,
)


def test_identify_returns_what_is_needed_to_recognize_the_pokemon(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.identify.execute.return_value = [PIKACHU_IDENTIFICATION]

    response = client.get(
        "/pokemon/identify", params={"description": "small yellow mouse"}
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 25,
            "name": "pikachu",
            "display_name": "Pikachu",
            "sprite": "https://example.com/25.png",
            "types": ["electric"],
            "genus": "Mouse Pokémon",
            "score": 0.87,
        }
    ]


def test_identify_forwards_the_query(client: TestClient, mocks: Mocks) -> None:
    mocks.identify.execute.return_value = []

    client.get("/pokemon/identify", params={"description": "yellow mouse", "limit": 3})

    mocks.identify.execute.assert_called_once_with(
        IdentifyPokemonQuery(description="yellow mouse", limit=3)
    )


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"description": ""},
        {"description": "a" * 1001},
        {"description": "x", "limit": 0},
    ],
)
def test_identify_rejects_invalid_parameters(
    client: TestClient, mocks: Mocks, params: dict
) -> None:
    assert client.get("/pokemon/identify", params=params).status_code == 422
    mocks.identify.execute.assert_not_called()


def test_identify_business_error_returns_422(client: TestClient, mocks: Mocks) -> None:
    mocks.identify.execute.side_effect = InvalidSearchQueryError("!!!", "no letter")

    assert (
        client.get("/pokemon/identify", params={"description": "!!!"}).status_code
        == 422
    )


def test_identify_is_not_captured_by_the_pokemon_detail_route(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.identify.execute.return_value = []

    client.get("/pokemon/identify", params={"description": "yellow mouse"})

    mocks.identify.execute.assert_called_once()
    mocks.pokemon.get_by_name.assert_not_called()


def test_identify_without_index_returns_503(client: TestClient) -> None:
    """Real wiring (not mocked): the test database has no appearance index."""
    del client.app.dependency_overrides[get_identify_pokemon]

    response = client.get("/pokemon/identify", params={"description": "yellow mouse"})

    assert response.status_code == 503
    assert "pokedex-import" in response.json()["detail"]
    assert "cache-control" not in response.headers


# --- GET /pokemon/{ref} ------------------------------------------------------


def test_get_pokemon_by_id(client: TestClient, mocks: Mocks) -> None:
    pikachu = make_pokemon()
    mocks.pokemon.get_by_id.return_value = pikachu
    mocks.pokemon.list_by_evolution_chain.return_value = [pikachu]
    mocks.abilities.get_many.return_value = [make_ability()]

    response = client.get("/pokemon/25")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "pikachu"
    assert body["display_name"] == "Pikachu"
    assert body["types"] == ["electric"]
    assert body["height_m"] == 0.4
    assert body["weight_kg"] == 6.0
    assert body["stats"]["total"] == 320
    assert body["abilities"] == [
        {
            "id": 9,
            "name": "static",
            "short_effect": "Has a 30% chance of paralyzing attacking Pokémon.",
        }
    ]
    assert [p["name"] for p in body["evolution_family"]] == ["pikachu"]
    mocks.pokemon.get_by_id.assert_called_once_with(25)
    mocks.pokemon.list_by_evolution_chain.assert_called_once_with(10)
    mocks.abilities.get_many.assert_called_once_with(frozenset({9}))


def test_get_pokemon_by_name_is_case_insensitive(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.pokemon.get_by_name.return_value = make_pokemon()
    mocks.pokemon.list_by_evolution_chain.return_value = []
    mocks.abilities.get_many.return_value = []

    assert client.get("/pokemon/PikaChu").status_code == 200
    mocks.pokemon.get_by_name.assert_called_once_with("pikachu")
    mocks.pokemon.get_by_id.assert_not_called()


@pytest.mark.parametrize("ref", ["999", "missingno"])
def test_get_unknown_pokemon_returns_404(
    client: TestClient, mocks: Mocks, ref: str
) -> None:
    mocks.pokemon.get_by_id.return_value = None
    mocks.pokemon.get_by_name.return_value = None

    response = client.get(f"/pokemon/{ref}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Pokemon '{ref}' not found"}


def test_get_pokemon_matchup(client: TestClient, mocks: Mocks) -> None:
    pikachu = make_pokemon()
    mocks.matchup.execute.return_value = Matchup(
        pokemon=PokemonListItem.from_entity(pikachu),
        defense=DefensiveProfile(
            weaknesses=(TypeMultiplier(PokemonType.GROUND, 2),),
            resistances=(TypeMultiplier(PokemonType.STEEL, 0.5),),
            immunities=(TypeImmunity(PokemonType.ELECTRIC, "lightning-rod"),),
        ),
        strong_against=(PokemonType.WATER, PokemonType.FLYING),
        threats=(Threat(Effect.PARALYSIS, ("thunder-wave",)),),
        protections=(Protection(ProtectionKind.PREVENTS, Effect.SLEEP, ("insomnia",)),),
        pitfalls=(Pitfall(PitfallKind.REFLECTS, Effect.PARALYSIS, "synchronize"),),
    )

    response = client.get("/pokemon/Pikachu/matchup")

    assert response.status_code == 200
    # The route only reads the reference; the use case looks the Pokémon up.
    mocks.matchup.execute.assert_called_once_with("pikachu")
    body = response.json()
    assert body["pokemon"]["display_name"] == "Pikachu"
    assert body["weaknesses"] == [{"type": "ground", "multiplier": 2}]
    assert body["resistances"] == [{"type": "steel", "multiplier": 0.5}]
    assert body["immunities"] == [{"type": "electric", "ability": "lightning-rod"}]
    assert body["strong_against"] == ["water", "flying"]
    assert body["threats"] == [{"effect": "paralysis", "sources": ["thunder-wave"]}]
    assert body["protections"] == [
        {"kind": "prevents", "effect": "sleep", "sources": ["insomnia"]}
    ]
    assert body["pitfalls"] == [
        {"kind": "reflects", "effect": "paralysis", "ability": "synchronize"}
    ]


def test_matchup_of_an_unknown_pokemon_returns_404(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.matchup.execute.side_effect = NotFoundError("Pokemon", 0)

    assert client.get("/pokemon/0/matchup").status_code == 404
    mocks.matchup.execute.assert_called_once_with(0)


def test_get_pokemon_moves(client: TestClient, mocks: Mocks) -> None:
    mocks.pokemon.get_by_id.return_value = make_pokemon()
    mocks.moves.get_many.return_value = [make_move()]

    response = client.get("/pokemon/25/moves")

    assert response.status_code == 200
    assert [m["name"] for m in response.json()] == ["thunderbolt"]
    mocks.moves.get_many.assert_called_once_with(frozenset({85}))


# --- GET /pokemon ------------------------------------------------------------


def test_list_pokemon_without_filters_is_the_catalog(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.list.execute.return_value = [
        PokemonListItem.from_entity(make_pokemon(id=122, name="mr-mime"))
    ]

    response = client.get("/pokemon")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 122,
            "name": "mr-mime",
            "display_name": "Mr. Mime",
            "types": ["electric"],
            "sprite": "https://example.com/25.png",
            "genus": "Mouse Pokémon",
        }
    ]
    assert response.headers["cache-control"].startswith("public")
    mocks.list.execute.assert_called_once_with(PokemonCriteria())


def test_list_pokemon_forwards_filters(client: TestClient, mocks: Mocks) -> None:
    mocks.list.execute.return_value = []

    client.get("/pokemon?q=chu&type=electric&habitat=forest&legendary=false")

    mocks.list.execute.assert_called_once_with(
        PokemonCriteria(
            name_contains="chu",
            type=PokemonType.ELECTRIC,
            habitat="forest",
            is_legendary=False,
        )
    )


@pytest.mark.parametrize("query", ["type=banana", "legendary=maybe"])
def test_list_pokemon_rejects_invalid_filters(
    client: TestClient, mocks: Mocks, query: str
) -> None:
    assert client.get(f"/pokemon?{query}").status_code == 422
    mocks.list.execute.assert_not_called()


# --- Moves -------------------------------------------------------------------


def test_search_moves_forwards_filters(client: TestClient, mocks: Mocks) -> None:
    mocks.moves.search.return_value = [make_move()]

    response = client.get("/moves?type=electric&damage_class=special")

    assert response.status_code == 200
    assert [m["name"] for m in response.json()] == ["thunderbolt"]
    mocks.moves.search.assert_called_once_with(
        MoveCriteria(type=PokemonType.ELECTRIC, damage_class=DamageClass.SPECIAL)
    )


def test_get_move_with_learners(client: TestClient, mocks: Mocks) -> None:
    mocks.moves.get_by_name.return_value = make_move()
    mocks.pokemon.list_by_move.return_value = [make_pokemon()]

    response = client.get("/moves/thunderbolt")

    assert response.status_code == 200
    body = response.json()
    assert body["power"] == 90
    assert [p["name"] for p in body["learned_by"]] == ["pikachu"]
    mocks.pokemon.list_by_move.assert_called_once_with(85)


def test_get_move_by_id(client: TestClient, mocks: Mocks) -> None:
    mocks.moves.get_by_id.return_value = make_move()
    mocks.pokemon.list_by_move.return_value = []

    assert client.get("/moves/85").status_code == 200
    mocks.moves.get_by_id.assert_called_once_with(85)


def test_get_unknown_move_returns_404(client: TestClient, mocks: Mocks) -> None:
    mocks.moves.get_by_name.return_value = None

    response = client.get("/moves/nope")

    assert response.status_code == 404
    mocks.pokemon.list_by_move.assert_not_called()


# --- Abilities ---------------------------------------------------------------


def test_list_abilities(client: TestClient, mocks: Mocks) -> None:
    mocks.abilities.list_all.return_value = [make_ability()]

    response = client.get("/abilities")

    assert response.status_code == 200
    assert [a["name"] for a in response.json()] == ["static"]


def test_get_ability_with_pokemon(client: TestClient, mocks: Mocks) -> None:
    mocks.abilities.get_by_name.return_value = make_ability()
    mocks.pokemon.list_by_ability.return_value = [make_pokemon()]

    response = client.get("/abilities/static")

    assert response.status_code == 200
    assert [p["name"] for p in response.json()["pokemon"]] == ["pikachu"]
    mocks.pokemon.list_by_ability.assert_called_once_with(9)


def test_get_ability_by_id(client: TestClient, mocks: Mocks) -> None:
    mocks.abilities.get_by_id.return_value = make_ability()
    mocks.pokemon.list_by_ability.return_value = []

    assert client.get("/abilities/9").status_code == 200
    mocks.abilities.get_by_id.assert_called_once_with(9)


def test_get_unknown_ability_returns_404(client: TestClient, mocks: Mocks) -> None:
    mocks.abilities.get_by_id.return_value = None

    assert client.get("/abilities/0").status_code == 404


# --- Types -------------------------------------------------------------------


def test_list_types(client: TestClient) -> None:
    response = client.get("/types")

    assert response.status_code == 200
    assert len(response.json()) == 18
    assert "fire" in response.json()


# --- POST /feedback/missing-result ---------------------------------------------

REPORT_BODY = {"kind": "name", "query": "char", "shown_ids": [4, 5, 113]}


def test_report_missing_result_returns_201_with_the_id(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.report.execute.return_value = 42

    response = client.post("/feedback/missing-result", json=REPORT_BODY)

    assert response.status_code == 201
    assert response.json() == {"id": 42}
    assert "cache-control" not in response.headers
    mocks.report.execute.assert_called_once_with(
        MissingResultReport(SearchKind.NAME, "char", (4, 5, 113))
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {**REPORT_BODY, "kind": "other"},
        {**REPORT_BODY, "query": ""},
        {**REPORT_BODY, "query": "a" * 1001},
        {**REPORT_BODY, "shown_ids": list(range(11))},
        {**REPORT_BODY, "shown_ids": ["pikachu"]},
        {"kind": "name", "query": "char"},
    ],
)
def test_report_missing_result_rejects_invalid_bodies(
    client: TestClient, mocks: Mocks, body: dict
) -> None:
    assert client.post("/feedback/missing-result", json=body).status_code == 422
    mocks.report.execute.assert_not_called()


def test_report_missing_result_business_error_returns_422(
    client: TestClient, mocks: Mocks
) -> None:
    mocks.report.execute.side_effect = InvalidReportError("unknown Pokémon ids: [999]")

    response = client.post("/feedback/missing-result", json=REPORT_BODY)

    assert response.status_code == 422
    assert "999" in response.json()["detail"][0]["msg"]
