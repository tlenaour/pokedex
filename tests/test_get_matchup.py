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
    PokemonCriteria,
    PokemonRepository,
)
from fullstack_pokedex.use_cases.get_matchup import GetMatchup
from tests.factories import make_pokemon


def test_matchup_of_pikachu() -> None:
    pikachu = make_pokemon()
    sandshrew = make_pokemon(id=27, name="sandshrew", types=(T.GROUND,))
    squirtle = make_pokemon(id=7, name="squirtle", types=(T.WATER,))
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.search.return_value = [squirtle, pikachu, sandshrew]
    effects = create_autospec(EffectRepository, instance=True)
    effects.list_pokemon_effects.return_value = {
        25: [
            PokemonEffect("immune:electric", SourceKind.ABILITY, "lightning-rod", None),
            PokemonEffect(
                "reflects:paralysis", SourceKind.ABILITY, "synchronize", None
            ),
            PokemonEffect("inflicts:paralysis", SourceKind.MOVE, "thunder-wave", 100),
            PokemonEffect("prevents:paralysis", SourceKind.ABILITY, "limber", None),
        ],
    }

    matchup = GetMatchup(pokemon, effects).execute(pikachu)

    pokemon.search.assert_called_once_with(PokemonCriteria())
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
    others = [make_pokemon(id=i, name=f"p{i}") for i in range(1, 6)]
    pokemon = create_autospec(PokemonRepository, instance=True)
    pokemon.search.return_value = [target, *others]
    effects = create_autospec(EffectRepository, instance=True)
    toxic = PokemonEffect("inflicts:poison", SourceKind.MOVE, "toxic", 100)
    effects.list_pokemon_effects.return_value = {
        p.id: [toxic] for p in [target, *others]
    }

    matchup = GetMatchup(pokemon, effects).execute(target)

    assert matchup.threats == ()
