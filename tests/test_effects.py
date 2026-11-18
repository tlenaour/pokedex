from fullstack_pokedex.domain.effects import (
    Effect,
    Pitfall,
    PitfallKind,
    PokemonEffect,
    Protection,
    ProtectionKind,
    SourceKind,
    drop_universal_moves,
    pitfalls,
    protections,
    threats,
)


def ability(name: str, tag: str) -> PokemonEffect:
    return PokemonEffect(tag, SourceKind.ABILITY, name, None)


def move(name: str, tag: str, chance: float | None = None) -> PokemonEffect:
    return PokemonEffect(tag, SourceKind.MOVE, name, chance)


# --- Noise ------------------------------------------------------------------------


def test_moves_learned_by_almost_everyone_are_dropped() -> None:
    toxic = move("toxic", "inflicts:poison", 100)
    sting = move("poison-sting", "inflicts:poison", 30)
    learners = {"toxic": 5, "poison-sting": 1}

    kept = drop_universal_moves([toxic, sting], learners, pokemon_count=5)

    assert kept == (sting,)


def test_a_move_at_the_threshold_is_kept() -> None:
    body_slam = move("body-slam", "inflicts:paralysis", 30)

    kept = drop_universal_moves([body_slam], {"body-slam": 4}, pokemon_count=5)

    assert kept == (body_slam,)


def test_abilities_are_always_kept() -> None:
    hydration = ability("hydration", "cures:any")

    assert drop_universal_moves([hydration], {}, pokemon_count=1) == (hydration,)


# --- The target -------------------------------------------------------------------


def test_threats_are_what_the_target_inflicts() -> None:
    effects = [
        move("sludge", "inflicts:poison", 30),
        ability("poison-point", "inflicts:poison"),
        move("hypnosis", "inflicts:sleep", 100),
        move("wrap", "inflicts:trap"),  # nothing prevents it
        move("leer", "lowers:defense", 100),  # not an inflicted effect
    ]

    assert [(t.effect, t.sources) for t in threats(effects)] == [
        (Effect.SLEEP, ("hypnosis",)),
        (Effect.POISON, ("poison-point", "sludge")),
    ]


def test_pitfalls_come_from_abilities() -> None:
    effects = [
        ability("synchronize", "reflects:poison"),
        ability("guts", "requires:any"),
        ability("steadfast", "requires:flinch"),
        move("dream-eater", "requires:sleep"),  # about the target of the move
    ]

    assert pitfalls(effects) == (
        Pitfall(PitfallKind.REFLECTS, Effect.POISON, "synchronize"),
        Pitfall(PitfallKind.BOOSTS, Effect.FLINCH, "steadfast"),
        Pitfall(PitfallKind.BOOSTS, Effect.ANY, "guts"),
    )


def test_protections_are_what_the_target_prevents_or_cures() -> None:
    effects = [
        ability("shed-skin", "cures:any"),
        ability("natural-cure", "cures:any"),
        ability("insomnia", "prevents:sleep"),
        ability("leaf-guard", "prevents:any"),
        ability("clear-body", "prevents:stat-drop"),  # not a status-like effect
        move("haze", "cures:stat-change", 100),  # same
        move("hypnosis", "inflicts:sleep", 100),  # a threat, not a protection
    ]

    assert protections(effects) == (
        Protection(ProtectionKind.PREVENTS, Effect.SLEEP, ("insomnia",)),
        Protection(ProtectionKind.PREVENTS, Effect.ANY, ("leaf-guard",)),
        Protection(ProtectionKind.CURES, Effect.ANY, ("natural-cure", "shed-skin")),
    )
