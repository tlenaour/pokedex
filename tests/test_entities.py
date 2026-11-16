import pytest
from pydantic import ValidationError

from fullstack_pokedex.domain.entities import PokemonType, Stats
from tests.factories import make_ability, make_move, make_pokemon


def test_stats_total_is_the_sum_of_the_six_stats() -> None:
    stats = Stats(
        hp=1, attack=2, defense=3, special_attack=4, special_defense=5, speed=6
    )
    assert stats.total == 21


def test_stats_total_is_serialized() -> None:
    assert make_pokemon().stats.model_dump()["total"] == 320


def test_height_and_weight_are_converted_to_metric_units() -> None:
    pokemon = make_pokemon(height_decimetres=17, weight_hectograms=905)
    assert pokemon.height_m == 1.7
    assert pokemon.weight_kg == 90.5


@pytest.mark.parametrize(
    "types",
    [
        (PokemonType.FIRE,),
        (PokemonType.FIRE, PokemonType.FLYING),
    ],
)
def test_pokemon_has_one_or_two_types(types: tuple[PokemonType, ...]) -> None:
    assert make_pokemon(types=types).types == types


@pytest.mark.parametrize(
    "types",
    [
        (),
        (PokemonType.FIRE, PokemonType.FLYING, PokemonType.DRAGON),
        ("banana",),
    ],
)
def test_pokemon_rejects_invalid_types(types: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        make_pokemon(types=types)


def test_domain_models_are_immutable() -> None:
    pokemon = make_pokemon()
    with pytest.raises(ValidationError):
        pokemon.name = "raichu"  # type: ignore[misc]


def test_domain_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_ability(unexpected="field")


def test_move_power_and_accuracy_are_optional() -> None:
    move = make_move(power=None, accuracy=None, effect_chance=None)
    assert move.power is None
    assert move.accuracy is None


@pytest.mark.parametrize(
    "field, value",
    [("accuracy", 101), ("accuracy", -1), ("pp", 0), ("effect_chance", 101)],
)
def test_move_rejects_out_of_range_values(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        make_move(**{field: value})


def test_stats_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Stats(hp=0, attack=1, defense=1, special_attack=1, special_defense=1, speed=1)
