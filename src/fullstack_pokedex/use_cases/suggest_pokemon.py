"""Use case: find a Pokémon from a partially remembered name.

A trainer types the beginning of a name ("bulba"); they get a short, ranked
list of Pokémon with what they need to recognize the one they saw (picture,
types, genus).
"""

from dataclasses import dataclass

from pydantic import HttpUrl

from fullstack_pokedex.domain.display_name import display_name
from fullstack_pokedex.domain.entities import Pokemon, PokemonType
from fullstack_pokedex.domain.errors import InvalidSearchQueryError
from fullstack_pokedex.domain.name_search import (
    MatchKind,
    NameMatch,
    NameSegment,
    SimilarityScorer,
    normalize_query,
    rank_candidates,
    split_by_span,
)
from fullstack_pokedex.domain.repositories import PokemonRepository

MIN_LIMIT = 1
MAX_LIMIT = 10
DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class SuggestPokemonQuery:
    text: str
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class PokemonSuggestion:
    id: int
    name: str
    """Dataset slug ("mr-mime"): stable identifier."""
    display_name: str
    """Spelling for people ("Mr. Mime")."""
    sprite: HttpUrl
    types: tuple[PokemonType, ...]
    genus: str
    match_kind: MatchKind
    score: float
    segments: tuple[NameSegment, ...]
    """`display_name` cut into matched / unmatched parts, ready to highlight:
    "mime" -> ("Mr. ", False), ("Mime", True). A single unmatched part for a
    fuzzy match (no exact letters to point at)."""


@dataclass(frozen=True)
class SuggestPokemon:
    pokemon: PokemonRepository
    scorer: SimilarityScorer | None = None
    """Enables typo tolerance; without it, only exact/prefix/substring matches."""

    def execute(self, query: SuggestPokemonQuery) -> list[PokemonSuggestion]:
        # 1. Validate before touching any data.
        if not MIN_LIMIT <= query.limit <= MAX_LIMIT:
            raise InvalidSearchQueryError(
                query.text, f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}"
            )
        normalized = normalize_query(query.text)

        # 2. Rank every name (domain rule), keep the best ones.
        candidates = self.pokemon.list_name_candidates()
        matches = rank_candidates(normalized, candidates, query.limit, self.scorer)
        if not matches:
            return []

        # 3. Load only the kept Pokémon, then restore the ranking order:
        #    the repository does not guarantee any order.
        loaded = self.pokemon.get_many([m.pokemon_id for m in matches])
        by_id = {p.id: p for p in loaded}
        return [
            _to_suggestion(match, by_id[match.pokemon_id])
            for match in matches
            # A candidate missing from get_many (data changed in between) is
            # skipped rather than failing the whole search.
            if match.pokemon_id in by_id
        ]


def _to_suggestion(match: NameMatch, pokemon: Pokemon) -> PokemonSuggestion:
    shown = display_name(pokemon.name)
    return PokemonSuggestion(
        id=pokemon.id,
        name=pokemon.name,
        display_name=shown,
        sprite=pokemon.images.sprite,
        types=pokemon.types,
        genus=pokemon.species.genus,
        match_kind=match.kind,
        score=match.score,
        segments=tuple(split_by_span(shown, match.span)),
    )
