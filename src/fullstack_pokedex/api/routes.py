import logging
import re
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing
from functools import cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response

from fullstack_pokedex.api.schemas import (
    AbilityDetailOut,
    AbilitySummary,
    ErrorOut,
    HealthOut,
    MatchupOut,
    MissingResultReportIn,
    MoveDetailOut,
    PokemonIdentificationOut,
    PokemonOut,
    PokemonSuggestionOut,
    PokemonSummary,
    ReportCreatedOut,
)
from fullstack_pokedex.domain.appearance import TextEmbedder
from fullstack_pokedex.domain.display_name import display_name
from fullstack_pokedex.domain.entities import (
    Ability,
    DamageClass,
    Move,
    PokemonType,
)
from fullstack_pokedex.domain.repositories import (
    AbilityRepository,
    EffectRepository,
    FeedbackRepository,
    MoveCriteria,
    MoveRepository,
    PokemonCriteria,
    PokemonRepository,
)
from fullstack_pokedex.infrastructure.embeddings import (
    Model2VecEmbedder,
    configured_model,
)
from fullstack_pokedex.infrastructure.similarity import JaroWinklerScorer
from fullstack_pokedex.infrastructure.sqlite.feedback import (
    SqliteFeedbackRepository,
    connect_feedback_db,
)
from fullstack_pokedex.infrastructure.sqlite.repositories import (
    SqliteAbilityRepository,
    SqliteEffectRepository,
    SqliteMoveRepository,
    SqlitePokemonRepository,
    connect,
    read_appearance_model,
)
from fullstack_pokedex.use_cases import identify_pokemon
from fullstack_pokedex.use_cases.get_ability import GetAbility
from fullstack_pokedex.use_cases.get_matchup import GetMatchup
from fullstack_pokedex.use_cases.get_move import GetMove
from fullstack_pokedex.use_cases.get_pokemon_detail import (
    GetPokemonDetail,
    GetPokemonMoves,
)
from fullstack_pokedex.use_cases.identify_pokemon import (
    IdentifyPokemon,
    IdentifyPokemonQuery,
)
from fullstack_pokedex.use_cases.list_pokemon import ListPokemon
from fullstack_pokedex.use_cases.report_missing_result import ReportMissingResult
from fullstack_pokedex.use_cases.suggest_pokemon import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_LIMIT,
    SuggestPokemon,
    SuggestPokemonQuery,
)

router = APIRouter()
_log = logging.getLogger(__name__)


# --- Dependencies: the only place where SQLite is wired to the domain ------


def get_connection(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


Connection = Annotated[sqlite3.Connection, Depends(get_connection)]


def get_pokemon_repository(conn: Connection) -> PokemonRepository:
    return SqlitePokemonRepository(conn)


def get_move_repository(conn: Connection) -> MoveRepository:
    return SqliteMoveRepository(conn)


def get_ability_repository(conn: Connection) -> AbilityRepository:
    return SqliteAbilityRepository(conn)


Pokemons = Annotated[PokemonRepository, Depends(get_pokemon_repository)]
Moves = Annotated[MoveRepository, Depends(get_move_repository)]
Abilities = Annotated[AbilityRepository, Depends(get_ability_repository)]


def get_list_pokemon(pokemons: Pokemons) -> ListPokemon:
    return ListPokemon(pokemon=pokemons)


def get_effect_repository(conn: Connection) -> EffectRepository:
    return SqliteEffectRepository(conn)


def get_get_matchup(
    pokemons: Pokemons,
    effects: Annotated[EffectRepository, Depends(get_effect_repository)],
) -> GetMatchup:
    return GetMatchup(pokemons, effects)


def get_get_pokemon_detail(
    pokemons: Pokemons, abilities: Abilities
) -> GetPokemonDetail:
    return GetPokemonDetail(pokemons, abilities)


def get_get_pokemon_moves(pokemons: Pokemons, moves: Moves) -> GetPokemonMoves:
    return GetPokemonMoves(pokemons, moves)


def get_get_move(moves: Moves, pokemons: Pokemons) -> GetMove:
    return GetMove(moves, pokemons)


def get_get_ability(abilities: Abilities, pokemons: Pokemons) -> GetAbility:
    return GetAbility(abilities, pokemons)


def get_suggest_pokemon(pokemons: Pokemons) -> SuggestPokemon:
    return SuggestPokemon(pokemon=pokemons, scorer=JaroWinklerScorer())


class AppearanceIndexUnavailableError(Exception):
    """The search by appearance cannot run: index missing or stale, or model
    not loadable."""


_embedder_lock = threading.Lock()


def get_text_embedder() -> TextEmbedder:
    """Loaded once per process, on first use (loading takes a moment).

    The lock: FastAPI runs this in a thread pool, and two first searches at
    the same time would otherwise load the model twice (≈ 290 MB each at peak).
    """
    with _embedder_lock:
        return _load_text_embedder()


@cache
def _load_text_embedder() -> TextEmbedder:
    # Not cached on failure: the next search tries again (e.g. once cached).
    try:
        return Model2VecEmbedder()
    except Exception as error:  # model2vec / huggingface_hub raise many types
        # The cause goes to the server's log, not to the client: it may hold
        # paths, URLs or library internals.
        _log.exception("Embedding model %r could not be loaded", configured_model())
        raise AppearanceIndexUnavailableError(
            "The embedding model could not be loaded. Run `uv run pokedex-import` "
            "once with network access to cache it."
        ) from error


def require_appearance_index(conn: Connection) -> None:
    """The appearance index exists and was built with the configured model.

    Vectors from different models are not comparable: refuse rather than
    return meaningless results.
    """
    stored = read_appearance_model(conn)
    if stored is None:
        raise AppearanceIndexUnavailableError(
            "Appearance search index not built: run `uv run pokedex-import`."
        )
    if stored != configured_model():
        raise AppearanceIndexUnavailableError(
            f"Appearance index built with {stored!r}, but the configured model is "
            f"{configured_model()!r}: run `uv run pokedex-import` again."
        )


def get_identify_pokemon(
    pokemons: Pokemons,
    # Before `embedder`: FastAPI resolves dependencies in parameter order, so a
    # missing or stale index answers 503 without loading the model first.
    _index: Annotated[None, Depends(require_appearance_index)],
    embedder: Annotated[TextEmbedder, Depends(get_text_embedder)],
) -> IdentifyPokemon:
    return IdentifyPokemon(pokemon=pokemons, embedder=embedder)


def get_feedback_connection(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect_feedback_db(request.app.state.feedback_db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_feedback_repository(
    conn: Annotated[sqlite3.Connection, Depends(get_feedback_connection)],
) -> FeedbackRepository:
    return SqliteFeedbackRepository(conn)


def get_report_missing_result(
    feedback: Annotated[FeedbackRepository, Depends(get_feedback_repository)],
    pokemons: Pokemons,
) -> ReportMissingResult:
    return ReportMissingResult(feedback=feedback, pokemon=pokemons)


# An id is 1 to 9 ASCII digits. Not `str.isdigit()`: it accepts "²" (which
# `int()` rejects) and other scripts' digits; and an unbounded number
# overflows SQLite's INTEGER. Anything else is looked up as a name (404).
_ID = re.compile(r"[0-9]{1,9}")


def _parse_ref(ref: str) -> int | str:
    """`/pokemon/25` and `/pokemon/pikachu` both work: an id or a name.

    Only the URL convention lives here; the use cases do the lookup.
    """
    return int(ref) if _ID.fullmatch(ref) else ref.lower()


# Error responses a route can send besides 200/422, declared so that they show
# in /api/docs and in the frontend's generated types. A test checks that every
# `{ref}` route declares NOT_FOUND.
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {
        "model": ErrorOut,
        "description": "No Pokémon, move or ability with this name or id",
    }
}
UNAVAILABLE: dict[int | str, dict[str, Any]] = {
    503: {
        "model": ErrorOut,
        "description": "Search by appearance unavailable: index missing or stale, "
        "or model not loadable",
    }
}


# --- Pokémon ----------------------------------------------------------------


@router.get("/pokemon", tags=["pokemon"])
def search_pokemon(
    list_pokemon: Annotated[ListPokemon, Depends(get_list_pokemon)],
    q: Annotated[str | None, Query(description="Part of the name")] = None,
    type: PokemonType | None = None,
    habitat: str | None = None,
    legendary: bool | None = None,
) -> list[PokemonSummary]:
    """All the Pokémon in Pokédex order (the catalog), optionally filtered."""
    criteria = PokemonCriteria(
        name_contains=q, type=type, habitat=habitat, is_legendary=legendary
    )
    return [PokemonSummary.from_item(p) for p in list_pokemon.execute(criteria)]


# Must be declared before /pokemon/{ref}, which would otherwise capture
# "suggest" as a Pokémon name.
@router.get("/pokemon/suggest", tags=["pokemon"])
def suggest_pokemon(
    suggest: Annotated[SuggestPokemon, Depends(get_suggest_pokemon)],
    q: Annotated[
        str,
        Query(
            min_length=1,
            # Guards against huge inputs; the business limit is checked on the
            # normalized query by the use case.
            max_length=100,
            description="Beginning (or part) of the name, e.g. `bulba`",
        ),
    ],
    limit: Annotated[int, Query(ge=MIN_LIMIT, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> list[PokemonSuggestionOut]:
    """Find a Pokémon from a partially remembered name, best matches first."""
    suggestions = suggest.execute(SuggestPokemonQuery(text=q, limit=limit))
    return [PokemonSuggestionOut.from_suggestion(s) for s in suggestions]


# Also before /pokemon/{ref}, for the same reason.
@router.get("/pokemon/identify", tags=["pokemon"], responses=UNAVAILABLE)
def identify(
    identify_use_case: Annotated[IdentifyPokemon, Depends(get_identify_pokemon)],
    description: Annotated[
        str,
        Query(
            min_length=1,
            # Guards against huge inputs; the business limit is checked by the
            # use case on the cleaned-up text.
            max_length=1000,
            description="What the Pokémon looks like, e.g. "
            "`small yellow mouse with red cheeks`",
        ),
    ],
    limit: Annotated[
        int,
        Query(ge=identify_pokemon.MIN_LIMIT, le=identify_pokemon.MAX_LIMIT),
    ] = identify_pokemon.DEFAULT_LIMIT,
) -> list[PokemonIdentificationOut]:
    """Identify a Pokémon from a description of its appearance, closest first."""
    results = identify_use_case.execute(
        IdentifyPokemonQuery(description=description, limit=limit)
    )
    return [PokemonIdentificationOut.from_identification(r) for r in results]


@router.get("/pokemon/{ref}", tags=["pokemon"], responses=NOT_FOUND)
def get_pokemon(
    ref: str,
    get_detail: Annotated[GetPokemonDetail, Depends(get_get_pokemon_detail)],
) -> PokemonOut:
    detail = get_detail.execute(_parse_ref(ref))
    pokemon = detail.pokemon
    return PokemonOut(
        id=pokemon.id,
        name=pokemon.name,
        display_name=display_name(pokemon.name),
        height_m=pokemon.height_m,
        weight_kg=pokemon.weight_kg,
        base_experience=pokemon.base_experience,
        types=list(pokemon.types),
        stats=pokemon.stats,
        species=pokemon.species,
        images=pokemon.images,
        abilities=[
            AbilitySummary(id=a.id, name=a.name, short_effect=a.short_effect)
            for a in detail.abilities
        ],
        evolution_family=[
            PokemonSummary.from_entity(p) for p in detail.evolution_family
        ],
    )


@router.get("/pokemon/{ref}/matchup", tags=["pokemon"], responses=NOT_FOUND)
def get_pokemon_matchup(
    ref: str,
    get_matchup: Annotated[GetMatchup, Depends(get_get_matchup)],
) -> MatchupOut:
    """How to beat a Pokémon: its weaknesses, resistances and immunities, the
    types it hits hard, what it can inflict, avoid or cure, and what not to do
    to it."""
    return MatchupOut.from_matchup(get_matchup.execute(_parse_ref(ref)))


@router.get("/pokemon/{ref}/moves", tags=["pokemon"], responses=NOT_FOUND)
def get_pokemon_moves(
    ref: str,
    get_moves: Annotated[GetPokemonMoves, Depends(get_get_pokemon_moves)],
) -> list[Move]:
    return get_moves.execute(_parse_ref(ref))


# --- Moves ------------------------------------------------------------------


@router.get("/moves", tags=["moves"])
def search_moves(
    moves: Moves,
    type: PokemonType | None = None,
    damage_class: DamageClass | None = None,
) -> list[Move]:
    return moves.search(MoveCriteria(type=type, damage_class=damage_class))


@router.get("/moves/{ref}", tags=["moves"], responses=NOT_FOUND)
def get_move(
    ref: str, get_move_use_case: Annotated[GetMove, Depends(get_get_move)]
) -> MoveDetailOut:
    detail = get_move_use_case.execute(_parse_ref(ref))
    return MoveDetailOut(
        **detail.move.model_dump(),
        learned_by=[PokemonSummary.from_entity(p) for p in detail.learned_by],
    )


# --- Abilities --------------------------------------------------------------


@router.get("/abilities", tags=["abilities"])
def list_abilities(abilities: Abilities) -> list[Ability]:
    return abilities.list_all()


@router.get("/abilities/{ref}", tags=["abilities"], responses=NOT_FOUND)
def get_ability(
    ref: str, get_ability_use_case: Annotated[GetAbility, Depends(get_get_ability)]
) -> AbilityDetailOut:
    detail = get_ability_use_case.execute(_parse_ref(ref))
    return AbilityDetailOut(
        **detail.ability.model_dump(),
        pokemon=[PokemonSummary.from_entity(p) for p in detail.pokemon],
    )


# --- Types ------------------------------------------------------------------


@router.get("/types", tags=["types"])
def list_types() -> list[PokemonType]:
    return list(PokemonType)


# --- Feedback ----------------------------------------------------------------


@router.post("/feedback/missing-result", status_code=201, tags=["feedback"])
def report_missing_result(
    report_use_case: Annotated[ReportMissingResult, Depends(get_report_missing_result)],
    body: MissingResultReportIn,
) -> ReportCreatedOut:
    """'I did not find my Pokémon': save a search that did not show it."""
    return ReportCreatedOut(id=report_use_case.execute(body.to_report()))


# --- Health ------------------------------------------------------------------


@router.get(
    "/health",
    tags=["health"],
    responses={503: {"model": HealthOut, "description": "pokedex.db cannot be read"}},
)
def health(request: Request, response: Response) -> HealthOut:
    """Is this process able to serve? For the container's health check.

    Minimal on purpose: it fails if the process no longer answers or if
    pokedex.db cannot be read. The appearance model and feedback.db are left
    out: without them most of the site still works, and restarting the
    container in a loop would turn a partial problem into a full outage.
    """
    # Never cached: a proxy must not answer "ok" in place of a dead container.
    response.headers["Cache-Control"] = "no-store"
    try:
        # Not the `Connection` dependency: a failure to open must be caught here.
        # A real read: `SELECT 1` alone would not touch the file.
        with closing(connect(request.app.state.db_path)) as conn:
            conn.execute("SELECT 1 FROM pokemon LIMIT 1").fetchone()
    except sqlite3.Error:
        response.status_code = 503
        return HealthOut(status="unavailable")
    return HealthOut(status="ok")
