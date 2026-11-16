import sqlite3
from collections.abc import Iterator
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from fullstack_pokedex.api.schemas import (
    AbilityDetailOut,
    AbilitySummary,
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
from fullstack_pokedex.domain.entities import (
    Ability,
    DamageClass,
    Move,
    Pokemon,
    PokemonType,
)
from fullstack_pokedex.domain.errors import NotFoundError
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
from fullstack_pokedex.use_cases.get_matchup import GetMatchup
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


def get_suggest_pokemon(pokemons: Pokemons) -> SuggestPokemon:
    return SuggestPokemon(pokemon=pokemons, scorer=JaroWinklerScorer())


class AppearanceIndexUnavailableError(Exception):
    """The appearance search index is missing or built with another model."""


@cache
def get_text_embedder() -> TextEmbedder:
    """Loaded once per process, on first use (loading takes a moment)."""
    return Model2VecEmbedder()


def get_identify_pokemon(
    pokemons: Pokemons,
    conn: Connection,
    embedder: Annotated[TextEmbedder, Depends(get_text_embedder)],
) -> IdentifyPokemon:
    # Vectors from different models are not comparable: refuse rather than
    # return meaningless results.
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


def _parse_ref(ref: str) -> int | str:
    """`/pokemon/25` and `/pokemon/pikachu` both work."""
    return int(ref) if ref.isdigit() else ref.lower()


def _find_pokemon(repo: PokemonRepository, ref: str) -> Pokemon:
    key = _parse_ref(ref)
    pokemon = repo.get_by_id(key) if isinstance(key, int) else repo.get_by_name(key)
    if pokemon is None:
        raise NotFoundError("Pokemon", ref)
    return pokemon


# --- Pokémon ----------------------------------------------------------------


@router.get("/pokemon", tags=["pokemon"])
def search_pokemon(
    list_pokemon: Annotated[ListPokemon, Depends(get_list_pokemon)],
    q: Annotated[str | None, Query(description="Part of the name")] = None,
    type: PokemonType | None = None,
    habitat: str | None = None,
    legendary: bool | None = None,
) -> list[PokemonSummary]:
    criteria = PokemonCriteria(
        name_contains=q, type=type, habitat=habitat, is_legendary=legendary
    )
    """All the Pokémon in Pokédex order (the catalog), optionally filtered."""
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
@router.get("/pokemon/identify", tags=["pokemon"])
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


@router.get("/pokemon/{ref}", tags=["pokemon"])
def get_pokemon(ref: str, pokemons: Pokemons, abilities: Abilities) -> PokemonOut:
    pokemon = _find_pokemon(pokemons, ref)
    family = pokemons.list_by_evolution_chain(pokemon.species.evolution_chain_id)
    return PokemonOut(
        id=pokemon.id,
        name=pokemon.name,
        height_m=pokemon.height_m,
        weight_kg=pokemon.weight_kg,
        base_experience=pokemon.base_experience,
        types=list(pokemon.types),
        stats=pokemon.stats,
        species=pokemon.species,
        images=pokemon.images,
        abilities=[
            AbilitySummary(id=a.id, name=a.name, short_effect=a.short_effect)
            for a in abilities.get_many(pokemon.ability_ids)
        ],
        evolution_family=[PokemonSummary.from_entity(p) for p in family],
    )


@router.get("/pokemon/{ref}/matchup", tags=["pokemon"])
def get_pokemon_matchup(
    ref: str,
    pokemons: Pokemons,
    get_matchup: Annotated[GetMatchup, Depends(get_get_matchup)],
) -> MatchupOut:
    """Prepare a fight: the Pokémon's weaknesses and strengths, and the
    Pokémon to send against it (best first)."""
    return MatchupOut.from_matchup(get_matchup.execute(_find_pokemon(pokemons, ref)))


@router.get("/pokemon/{ref}/moves", tags=["pokemon"])
def get_pokemon_moves(ref: str, pokemons: Pokemons, moves: Moves) -> list[Move]:
    return moves.get_many(_find_pokemon(pokemons, ref).move_ids)


# --- Moves ------------------------------------------------------------------


@router.get("/moves", tags=["moves"])
def search_moves(
    moves: Moves,
    type: PokemonType | None = None,
    damage_class: DamageClass | None = None,
) -> list[Move]:
    return moves.search(MoveCriteria(type=type, damage_class=damage_class))


@router.get("/moves/{ref}", tags=["moves"])
def get_move(ref: str, moves: Moves, pokemons: Pokemons) -> MoveDetailOut:
    key = _parse_ref(ref)
    move = moves.get_by_id(key) if isinstance(key, int) else moves.get_by_name(key)
    if move is None:
        raise NotFoundError("Move", ref)
    return MoveDetailOut(
        **move.model_dump(),
        learned_by=[
            PokemonSummary.from_entity(p) for p in pokemons.list_by_move(move.id)
        ],
    )


# --- Abilities --------------------------------------------------------------


@router.get("/abilities", tags=["abilities"])
def list_abilities(abilities: Abilities) -> list[Ability]:
    return abilities.list_all()


@router.get("/abilities/{ref}", tags=["abilities"])
def get_ability(ref: str, abilities: Abilities, pokemons: Pokemons) -> AbilityDetailOut:
    key = _parse_ref(ref)
    ability = (
        abilities.get_by_id(key) if isinstance(key, int) else abilities.get_by_name(key)
    )
    if ability is None:
        raise NotFoundError("Ability", ref)
    return AbilityDetailOut(
        **ability.model_dump(),
        pokemon=[
            PokemonSummary.from_entity(p) for p in pokemons.list_by_ability(ability.id)
        ],
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
