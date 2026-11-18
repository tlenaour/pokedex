from unittest.mock import create_autospec

from fullstack_pokedex.domain.effects import (
    Effect,
    Pitfall,
    PitfallKind,
    PokemonEffect,
    Protection,
    ProtectionKind,
    SourceKind,
)
from fullstack_pokedex.domain.entities import PokemonType as T
from fullstack_pokedex.domain.matchup import TypeImmunity
from fullstack_pokedex.domain.repositories import (
    EffectRepository,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.get_matchup import GetMatchup
from tests.factories import make_pokemon


def test_matchup_of_pikachu() -> None:
    pikachu = make_pokemon()
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.get_by_name.return_value = pikachu
    pokemon.count.return_value = 3
    effects = create_autospec(EffectRepository, instance=True)
    effects.list_effects.return_value = [
        PokemonEffect("immune:electric", SourceKind.ABILITY, "lightning-rod", None),
        PokemonEffect("reflects:paralysis", SourceKind.ABILITY, "synchronize", None),
        PokemonEffect("inflicts:paralysis", SourceKind.MOVE, "thunder-wave", 100),
        PokemonEffect("prevents:paralysis", SourceKind.ABILITY, "limber", None),
    ]
    effects.count_learners.return_value = {"thunder-wave": 1}

    matchup = GetMatchup(pokemon, effects).execute("pikachu")

    pokemon.get_by_name.assert_called_once_with("pikachu")
    effects.list_effects.assert_called_once_with(25)
    effects.count_learners.assert_called_once_with({"thunder-wave"})
    # Only the target's data: never every Pokémon.
    pokemon.search.assert_not_called()
    assert matchup.pokemon.display_name == "Pikachu"
    assert [w.type for w in matchup.defense.weaknesses] == [T.GROUND]
    assert TypeImmunity(T.ELECTRIC, "lightning-rod") in matchup.defense.immunities
    assert matchup.strong_against == (T.WATER, T.FLYING)
    assert [t.effect for t in matchup.threats] == [Effect.PARALYSIS]
    assert matchup.protections == (
        Protection(ProtectionKind.PREVENTS, Effect.PARALYSIS, ("limber",)),
    )
    assert matchup.pitfalls == (
        Pitfall(PitfallKind.REFLECTS, Effect.PARALYSIS, "synchronize"),
    )


def test_moves_almost_everyone_learns_are_ignored() -> None:
    target = make_pokemon()
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.get_by_id.return_value = target
    pokemon.count.return_value = 6
    effects = create_autospec(EffectRepository, instance=True)
    toxic = PokemonEffect("inflicts:poison", SourceKind.MOVE, "toxic", 100)
    effects.list_effects.return_value = [toxic]
    effects.count_learners.return_value = {"toxic": 6}

    matchup = GetMatchup(pokemon, effects).execute(target.id)

    assert matchup.threats == ()
