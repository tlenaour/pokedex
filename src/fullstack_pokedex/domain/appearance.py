"""Business rules for identifying a Pokémon from a description of its appearance.

Each Pokémon has reference descriptions (data/pokemon_descriptions.json). They
are turned into vectors by a TextEmbedder (a port: the embedding model is an
infrastructure concern); a user's description is embedded the same way, and
Pokémon are ranked by cosine similarity between the two vectors.

Choices measured in benchmarks/appearance_embeddings.py: joining the three
reference texts into one ("joined") beats keeping the best of three.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from fullstack_pokedex.domain.errors import InvalidSearchQueryError

MAX_DESCRIPTION_LENGTH = 300
"""Characters. A useful description is a sentence or two; longer input only
dilutes its meaning (and guards against abuse)."""

type Vector = Sequence[float]


@dataclass(frozen=True)
class AppearanceDescription:
    """Reference descriptions of one Pokémon (see data/README.md)."""

    pokemon_id: int
    glance: str
    detailed: str
    everyday: str

    @property
    def reference_text(self) -> str:
        """The text embedded for this Pokémon: the three descriptions joined."""
        return f"{self.glance}. {self.detailed}. {self.everyday}"


@dataclass(frozen=True)
class AppearanceCandidate:
    """A Pokémon with the vector of its reference text."""

    pokemon_id: int
    vector: Vector


@dataclass(frozen=True)
class AppearanceMatch:
    pokemon_id: int
    score: float
    """Cosine similarity, from -1 to 1 (higher is closer)."""


class TextEmbedder(Protocol):
    """Port: turns texts into vectors whose closeness reflects their meaning."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def validate_description(text: str) -> str:
    description = " ".join(text.split())
    if not any(c.isalnum() for c in description):
        raise InvalidSearchQueryError(text, "no letter or digit")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise InvalidSearchQueryError(
            text, f"longer than {MAX_DESCRIPTION_LENGTH} characters"
        )
    return description


def cosine_similarity(a: Vector, b: Vector) -> float:
    if len(a) != len(b):
        raise ValueError(f"vectors of different sizes: {len(a)} != {len(b)}")
    norm = math.hypot(*a) * math.hypot(*b)
    if norm == 0:
        return 0.0
    return math.sumprod(a, b) / norm


def rank_by_appearance(
    query: Vector, candidates: Sequence[AppearanceCandidate], limit: int
) -> list[AppearanceMatch]:
    """The `limit` Pokémon whose reference vector is closest to `query`,
    closest first; ties broken by Pokédex number."""
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")
    matches = [
        AppearanceMatch(c.pokemon_id, cosine_similarity(query, c.vector))
        for c in candidates
    ]
    matches.sort(key=lambda m: (-m.score, m.pokemon_id))
    return matches[:limit]
