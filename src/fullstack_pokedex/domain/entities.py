"""Domain entities of the Pokédex.

Pure business model: no dependency on storage (SQLite) nor on the source
format (pokedex.json). Other aggregates are referenced by id.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field


class _DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PokemonType(StrEnum):
    NORMAL = "normal"
    FIRE = "fire"
    WATER = "water"
    ELECTRIC = "electric"
    GRASS = "grass"
    ICE = "ice"
    FIGHTING = "fighting"
    POISON = "poison"
    GROUND = "ground"
    FLYING = "flying"
    PSYCHIC = "psychic"
    BUG = "bug"
    ROCK = "rock"
    GHOST = "ghost"
    DRAGON = "dragon"
    DARK = "dark"
    STEEL = "steel"
    FAIRY = "fairy"


class DamageClass(StrEnum):
    PHYSICAL = "physical"
    SPECIAL = "special"
    STATUS = "status"


class Stats(_DomainModel):
    hp: int = Field(ge=1)
    attack: int = Field(ge=1)
    defense: int = Field(ge=1)
    special_attack: int = Field(ge=1)
    special_defense: int = Field(ge=1)
    speed: int = Field(ge=1)

    @computed_field
    @property
    def total(self) -> int:
        return (
            self.hp
            + self.attack
            + self.defense
            + self.special_attack
            + self.special_defense
            + self.speed
        )


class Species(_DomainModel):
    genus: str
    description: str
    generation: str
    color: str
    shape: str
    habitat: str
    is_legendary: bool
    is_mythical: bool
    evolution_chain_id: int = Field(ge=1)


class Images(_DomainModel):
    sprite: HttpUrl
    official_artwork: HttpUrl


class Pokemon(_DomainModel):
    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    height_decimetres: int = Field(ge=0)
    weight_hectograms: int = Field(ge=0)
    base_experience: int = Field(ge=0)
    types: tuple[PokemonType] | tuple[PokemonType, PokemonType]
    """Ordered: the first one is the primary type."""
    stats: Stats
    species: Species
    images: Images
    ability_ids: frozenset[int]
    move_ids: frozenset[int]

    @property
    def height_m(self) -> float:
        return self.height_decimetres / 10

    @property
    def weight_kg(self) -> float:
        return self.weight_hectograms / 10


class Move(_DomainModel):
    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    type: PokemonType
    damage_class: DamageClass
    power: int | None = Field(default=None, ge=0)
    """None for moves that deal no direct damage."""
    accuracy: int | None = Field(default=None, ge=0, le=100)
    """None for moves that never miss."""
    pp: int = Field(ge=1)
    priority: int
    effect_chance: int | None = Field(default=None, ge=0, le=100)
    effect: str
    short_effect: str
    generation: str


class Ability(_DomainModel):
    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    effect: str
    short_effect: str
    generation: str
    is_main_series: bool
