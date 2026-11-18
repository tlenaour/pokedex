"""Response models of the HTTP API.

Domain entities are reused as-is when their shape fits; dedicated models
are only defined where the API returns a different shape.
"""

from typing import Literal, Self

from pydantic import BaseModel, Field, HttpUrl

from fullstack_pokedex.domain.effects import Effect, PitfallKind, ProtectionKind
from fullstack_pokedex.domain.entities import (
    Ability,
    Images,
    Move,
    Pokemon,
    PokemonType,
    Species,
    Stats,
)
from fullstack_pokedex.domain.feedback import (
    MAX_SHOWN_POKEMON,
    MissingResultReport,
    SearchKind,
)
from fullstack_pokedex.domain.name_search import MatchKind
from fullstack_pokedex.use_cases.get_matchup import Matchup
from fullstack_pokedex.use_cases.identify_pokemon import PokemonIdentification
from fullstack_pokedex.use_cases.list_pokemon import PokemonListItem
from fullstack_pokedex.use_cases.suggest_pokemon import PokemonSuggestion


class PokemonSummary(BaseModel):
    id: int
    name: str
    display_name: str
    types: list[PokemonType]
    sprite: HttpUrl
    genus: str

    @classmethod
    def from_item(cls, item: PokemonListItem) -> Self:
        return cls(
            id=item.id,
            name=item.name,
            display_name=item.display_name,
            types=list(item.types),
            sprite=item.sprite,
            genus=item.genus,
        )

    @classmethod
    def from_entity(cls, pokemon: Pokemon) -> Self:
        return cls.from_item(PokemonListItem.from_entity(pokemon))


class AbilitySummary(BaseModel):
    id: int
    name: str
    short_effect: str


class PokemonOut(BaseModel):
    id: int
    name: str
    display_name: str
    height_m: float
    weight_kg: float
    base_experience: int
    types: list[PokemonType]
    stats: Stats
    species: Species
    images: Images
    abilities: list[AbilitySummary]
    evolution_family: list[PokemonSummary]


class MoveDetailOut(Move):
    learned_by: list[PokemonSummary]


class AbilityDetailOut(Ability):
    pokemon: list[PokemonSummary]


class NameSegmentOut(BaseModel):
    text: str
    matched: bool


class MatchOut(BaseModel):
    kind: MatchKind
    score: float
    segments: list[NameSegmentOut]
    """`display_name` cut into parts; show the `matched` ones in bold.
    Concatenating every `text` gives `display_name`. A fuzzy match is a single
    unmatched part."""


class PokemonSuggestionOut(BaseModel):
    id: int
    name: str
    display_name: str
    sprite: HttpUrl
    types: list[PokemonType]
    genus: str
    match: MatchOut

    @classmethod
    def from_suggestion(cls, suggestion: PokemonSuggestion) -> Self:
        return cls(
            id=suggestion.id,
            name=suggestion.name,
            display_name=suggestion.display_name,
            sprite=suggestion.sprite,
            types=list(suggestion.types),
            genus=suggestion.genus,
            match=MatchOut(
                kind=suggestion.match_kind,
                score=suggestion.score,
                segments=[
                    NameSegmentOut(text=s.text, matched=s.matched)
                    for s in suggestion.segments
                ],
            ),
        )


class PokemonIdentificationOut(BaseModel):
    id: int
    name: str
    display_name: str
    sprite: HttpUrl
    types: list[PokemonType]
    genus: str
    score: float
    """Similarity with the description (higher is closer); only meaningful to
    compare results of the same query."""

    @classmethod
    def from_identification(cls, identification: PokemonIdentification) -> Self:
        return cls(
            id=identification.id,
            name=identification.name,
            display_name=identification.display_name,
            sprite=identification.sprite,
            types=list(identification.types),
            genus=identification.genus,
            score=identification.score,
        )


class MissingResultReportIn(BaseModel):
    """'I did not find my Pokémon', sent from the results of a search."""

    kind: SearchKind
    query: str = Field(
        min_length=1,
        # Guards against huge inputs; the business limit is checked by the
        # use case on the cleaned-up text.
        max_length=1000,
        description="The search text that produced the results",
    )
    shown_ids: list[int] = Field(
        max_length=MAX_SHOWN_POKEMON,
        description="Ids of the Pokémon shown, in display order (may be empty)",
    )

    def to_report(self) -> MissingResultReport:
        return MissingResultReport(self.kind, self.query, tuple(self.shown_ids))


class ReportCreatedOut(BaseModel):
    id: int


class ErrorOut(BaseModel):
    """A 404 or 503: what went wrong, in one sentence."""

    detail: str


class HealthOut(BaseModel):
    status: Literal["ok", "unavailable"]


class TypeMultiplierOut(BaseModel):
    type: PokemonType
    multiplier: float


class TypeImmunityOut(BaseModel):
    type: PokemonType
    ability: str | None
    """None when its types give the immunity; otherwise the ability that may
    give it (a Pokémon has only one of its abilities at a time)."""


class ThreatOut(BaseModel):
    effect: Effect
    sources: list[str]
    """Moves and abilities that give it."""


class ProtectionOut(BaseModel):
    kind: ProtectionKind
    effect: Effect
    sources: list[str]
    """Moves and abilities that give it."""


class PitfallOut(BaseModel):
    kind: PitfallKind
    effect: Effect
    ability: str
    """A possible ability of the target."""


class MatchupOut(BaseModel):
    pokemon: PokemonSummary
    weaknesses: list[TypeMultiplierOut]
    """Most damaging first."""
    resistances: list[TypeMultiplierOut]
    """Least damaging first."""
    immunities: list[TypeImmunityOut]
    strong_against: list[PokemonType]
    threats: list[ThreatOut]
    """What it can inflict."""
    protections: list[ProtectionOut]
    """What it can avoid or heal."""
    pitfalls: list[PitfallOut]
    """What not to do to it."""

    @classmethod
    def from_matchup(cls, matchup: Matchup) -> Self:
        defense = matchup.defense
        return cls(
            pokemon=PokemonSummary.from_item(matchup.pokemon),
            weaknesses=[
                TypeMultiplierOut(type=w.type, multiplier=w.multiplier)
                for w in defense.weaknesses
            ],
            resistances=[
                TypeMultiplierOut(type=r.type, multiplier=r.multiplier)
                for r in defense.resistances
            ],
            immunities=[
                TypeImmunityOut(type=i.type, ability=i.ability)
                for i in defense.immunities
            ],
            strong_against=list(matchup.strong_against),
            threats=[
                ThreatOut(effect=t.effect, sources=list(t.sources))
                for t in matchup.threats
            ],
            protections=[
                ProtectionOut(kind=p.kind, effect=p.effect, sources=list(p.sources))
                for p in matchup.protections
            ],
            pitfalls=[
                PitfallOut(kind=p.kind, effect=p.effect, ability=p.ability)
                for p in matchup.pitfalls
            ],
        )
