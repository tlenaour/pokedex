"""Use case: identify a Pokémon from a description of its appearance.

A trainer types what they saw ("small yellow mouse with red cheeks"); they get
a short, ranked list of Pokémon with what they need to recognize the one they
saw (picture, types, genus).
"""

from dataclasses import dataclass

from pydantic import HttpUrl

from fullstack_pokedex.domain.appearance import (
    TextEmbedder,
    rank_by_appearance,
    validate_description,
)
from fullstack_pokedex.domain.display_name import display_name
from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.domain.errors import InvalidSearchQueryError
from fullstack_pokedex.domain.repositories import PokemonRepository

MIN_LIMIT = 1
MAX_LIMIT = 10
DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class IdentifyPokemonQuery:
    description: str
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class PokemonIdentification:
    id: int
    name: str
    display_name: str
    sprite: HttpUrl
    types: tuple[PokemonType, ...]
    genus: str
    score: float
    """Similarity with the description, from -1 to 1 (higher is closer).
    Comparable between results of one query, not across queries."""


@dataclass(frozen=True)
class IdentifyPokemon:
    pokemon: PokemonRepository
    embedder: TextEmbedder

    def execute(self, query: IdentifyPokemonQuery) -> list[PokemonIdentification]:
        # 1. Validate before computing anything.
        if not MIN_LIMIT <= query.limit <= MAX_LIMIT:
            raise InvalidSearchQueryError(
                query.description,
                f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}",
            )
        description = validate_description(query.description)

        # 2. Embed the description and rank the Pokémon (domain rule).
        [vector] = self.embedder.embed([description])
        candidates = self.pokemon.list_appearance_candidates()
        if not candidates:
            return []
        matches = rank_by_appearance(vector, candidates, query.limit)

        # 3. Load only the kept Pokémon, then restore the ranking order:
        #    the repository does not guarantee any order.
        by_id = {
            p.id: p for p in self.pokemon.get_many([m.pokemon_id for m in matches])
        }
        return [
            PokemonIdentification(
                id=pokemon.id,
                name=pokemon.name,
                display_name=display_name(pokemon.name),
                sprite=pokemon.images.sprite,
                types=pokemon.types,
                genus=pokemon.species.genus,
                score=match.score,
            )
            for match in matches
            if (pokemon := by_id.get(match.pokemon_id)) is not None
        ]
