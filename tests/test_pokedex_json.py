import json
from pathlib import Path

import pytest

from fullstack_pokedex.domain.entities import PokemonType
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex, load_pokedex
from tests.factories import MINI_POKEDEX


def test_loads_every_entity(pokedex: Pokedex) -> None:
    assert [p.name for p in pokedex.pokemon] == [
        "bulbasaur",
        "ivysaur",
        "pikachu",
        "mewtwo",
    ]
    assert len(pokedex.moves) == 6
    assert len(pokedex.abilities) == 6


def test_maps_pokemon_fields(pokedex: Pokedex) -> None:
    bulbasaur = pokedex.pokemon[0]

    assert bulbasaur.types == (PokemonType.GRASS, PokemonType.POISON)
    # "special-attack" in the JSON becomes special_attack in the domain.
    assert bulbasaur.stats.special_attack == 65
    assert bulbasaur.stats.special_defense == 65
    assert bulbasaur.species.evolution_chain_id == 1
    assert str(bulbasaur.images.sprite).endswith("/1.png")


def test_resolves_move_and_ability_names_to_ids(pokedex: Pokedex) -> None:
    pikachu = pokedex.pokemon[2]
    move_ids = {m.name: m.id for m in pokedex.moves}
    ability_ids = {a.name: a.id for a in pokedex.abilities}

    assert pikachu.move_ids == {
        move_ids[name] for name in ("body-slam", "growl", "swift", "thunderbolt")
    }
    assert pikachu.ability_ids == {ability_ids["static"], ability_ids["lightning-rod"]}


def test_keeps_null_power_and_accuracy(pokedex: Pokedex) -> None:
    moves = {m.name: m for m in pokedex.moves}
    assert moves["growl"].power is None
    assert moves["swift"].accuracy is None


def test_fails_on_unknown_move_reference(tmp_path: Path) -> None:
    raw = json.loads(MINI_POKEDEX.read_text(encoding="utf-8"))
    raw["pokemon"][0]["moves"].append("does-not-exist")
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(KeyError, match="does-not-exist"):
        load_pokedex(broken)
