import pytest

from fullstack_pokedex.domain.entities import PokemonType as T
from fullstack_pokedex.domain.type_chart import CHART, effectiveness


@pytest.mark.parametrize(
    ("attack", "defender", "expected"),
    [
        (T.FIRE, (T.GRASS,), 2),
        (T.WATER, (T.FIRE,), 2),
        (T.NORMAL, (T.NORMAL,), 1),
        (T.FIRE, (T.WATER,), 0.5),
        (T.ELECTRIC, (T.GROUND,), 0),
        (T.FIGHTING, (T.GHOST,), 0),
        (T.DRAGON, (T.FAIRY,), 0),
        (T.GROUND, (T.FLYING,), 0),
        # Two types: the multipliers are multiplied.
        (T.FIRE, (T.GRASS, T.BUG), 4),
        (T.ROCK, (T.FIRE, T.FLYING), 4),
        (T.FIRE, (T.FIRE, T.WATER), 0.25),
        (T.ELECTRIC, (T.WATER, T.GROUND), 0),
        (T.GRASS, (T.GRASS, T.POISON), 0.25),
        (T.WATER, (T.GRASS, T.GROUND), 1),
    ],
)
def test_effectiveness(attack: T, defender: tuple[T, ...], expected: float) -> None:
    assert effectiveness(attack, defender) == expected


def test_every_type_attacks() -> None:
    assert set(CHART) == set(T)


def test_only_game_multipliers_are_listed() -> None:
    # ×1 is the default: it is never written.
    assert {m for row in CHART.values() for m in row.values()} == {0, 0.5, 2}
