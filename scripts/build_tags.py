"""Build and validate `data/tags_llm.json` (effect tags of moves and abilities).

The labels below were written by an LLM following `src/fullstack_pokedex/prompts/tag_effects.md`.
This script only assembles them into the output format and checks them against `pokedex.json`:
closed vocabulary, `evidence` is an exact substring of the texts, triggers, 278 objects, and
the examples of the prompt are identical to the generated objects.

To change a label, edit it here and re-run: `data/tags_llm.json` is overwritten on each run.

Usage (from anywhere): uv run python scripts/build_tags.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "src" / "fullstack_pokedex" / "prompts" / "tag_effects.md"
d = json.loads((ROOT / "pokedex.json").read_text(encoding="utf-8"))
ITEMS = {("move", x["name"]): x for x in d["moves"]} | {
    ("ability", x["name"]): x for x in d["abilities"]
}
EC = {x["name"]: x["effect_chance"] for x in d["moves"]}

LABELS = {}  # (entity_type, name) -> (tags, comment, confidence)


def tag(tag, chance=None, evidence=None, trigger=None):
    """One tag. `evidence=None` means the whole `short_effect`; `trigger=None` means the default."""
    return {"tag": tag, "chance": chance, "trigger": trigger, "evidence": evidence}


def label(entity_type, name, *tags, comment=None, confidence="high"):
    key = (entity_type, name)
    assert key in ITEMS, f"unknown item {key}"
    assert key not in LABELS, f"labeled twice {key}"
    default_trigger = "move_hit" if entity_type == "move" else "other"
    done = []
    for t in tags:
        t = dict(t)
        t["trigger"] = t["trigger"] or default_trigger
        t["evidence"] = t["evidence"] or ITEMS[key]["short_effect"]
        done.append(t)
    LABELS[key] = (done, comment, confidence)


def move(name, *tags, **kw):
    label("move", name, *tags, **kw)


def ability(name, *tags, **kw):
    label("ability", name, *tags, **kw)


# ----------------------------------------------------------------------------- moves
# Secondary effect: "Has a chance to ..." -> chance = effect_chance
CHANCE_SENTENCE = {
    "inflicts:burn": "Has a chance to burn the target.",
    "inflicts:freeze": "Has a chance to freeze the target.",
    "inflicts:paralysis": "Has a chance to paralyze the target.",
    "inflicts:poison": "Has a chance to poison the target.",
    "inflicts:confusion": "Has a chance to confuse the target.",
    "inflicts:flinch": "Has a chance to make the target flinch.",
    "lowers:attack": "Has a chance to lower the target’s Attack by one stage.",
    "lowers:special-defense": "Has a chance to lower the target’s Special Defense by one stage.",
    "lowers:speed": "Has a chance to lower the target’s Speed by one stage.",
}
SECONDARY = {
    "inflicts:burn": ["fire-punch", "ember", "flamethrower", "fire-blast"],
    "inflicts:freeze": ["ice-punch", "ice-beam", "blizzard"],
    "inflicts:paralysis": [
        "thunder-punch",
        "body-slam",
        "thunder-shock",
        "thunderbolt",
        "thunder",
        "lick",
    ],
    "inflicts:poison": ["poison-sting", "twineedle", "smog", "sludge"],
    "inflicts:confusion": ["psybeam", "confusion", "dizzy-punch"],
    "inflicts:flinch": [
        "stomp",
        "rolling-kick",
        "headbutt",
        "bite",
        "bone-club",
        "waterfall",
        "rock-slide",
        "hyper-fang",
    ],
    "lowers:attack": ["aurora-beam"],
    "lowers:special-defense": ["acid", "psychic"],
    "lowers:speed": ["bubble-beam", "constrict", "bubble"],
}
for t, names in SECONDARY.items():
    for n in names:
        move(n, tag(t, EC[n], CHANCE_SENTENCE[t]))
move(
    "tri-attack",
    *[
        tag(
            f"inflicts:{s}",
            6.7,
            "Has a chance to burn, freeze, or paralyze the target.",
        )
        for s in ("burn", "freeze", "paralysis")
    ],
    comment="one 20% roll (effect_chance) split across three statuses",
)
move(
    "sky-attack",
    tag("inflicts:flinch", EC["sky-attack"], CHANCE_SENTENCE["inflicts:flinch"]),
    tag(
        "raises:critical", None, "Critical hit chance is one level higher than normal."
    ),
)

# Main effect of a status move -> chance 100, evidence = whole short_effect
MAIN = {
    "inflicts:sleep": ["sing", "sleep-powder", "hypnosis", "lovely-kiss", "spore"],
    "inflicts:confusion": ["supersonic", "confuse-ray"],
    "inflicts:poison": ["poison-powder", "poison-gas"],
    "inflicts:paralysis": ["stun-spore", "thunder-wave", "glare"],
    "lowers:accuracy": ["sand-attack", "smokescreen", "kinesis", "flash"],
    "lowers:defense": ["tail-whip", "leer", "screech"],
    "lowers:attack": ["growl"],
    "lowers:speed": ["string-shot"],
    "raises:attack": ["swords-dance", "meditate", "sharpen"],
    "raises:speed": ["agility"],
    "raises:evasion": ["double-team", "minimize"],
    "raises:defense": ["harden", "withdraw", "defense-curl", "barrier", "acid-armor"],
    "raises:special-defense": ["amnesia"],
    "raises:critical": ["focus-energy"],
    "self:heal": ["recover", "soft-boiled"],
    "prevents:stat-drop": ["mist"],
    "cures:stat-change": ["haze"],
}
for t, names in MAIN.items():
    for n in names:
        move(n, tag(t, 100))
move("toxic", tag("inflicts:poison", 100, "Badly poisons the target"))
move("disable", tag("inflicts:disable", 100))
for n in ("whirlwind", "roar"):
    move(
        n,
        tag("inflicts:switch", 100, "Forces trainers to switch Pokémon."),
        comment="in wild battles, ends the battle instead",
    )
move(
    "growth",
    tag(
        "raises:attack",
        100,
        "Raises the user’s Attack and Special Attack by one stage.",
    ),
    tag(
        "raises:special-attack",
        100,
        "Raises the user’s Attack and Special Attack by one stage.",
    ),
)
move(
    "light-screen",
    tag("reduces:damage", 100),
    comment="special attacks only, for five turns",
)
move(
    "reflect",
    tag("reduces:damage", 100),
    comment="physical attacks only, for five turns",
)
move("leech-seed", tag("self:heal", 100, "heals the user for the amount taken"))
move(
    "rest",
    tag("self:sleep", 100, "User sleeps for two turns"),
    tag("self:heal", 100, "completely healing itself"),
    comment="effect also says sleep replaces another major status effect; replacement is not a cure, not tagged",
)
SUBSTITUTE = "The doll will block major status effects, confusion, and flinching."
move(
    "substitute",
    tag("prevents:any", None, SUBSTITUTE),
    tag("prevents:confusion", None, SUBSTITUTE),
    tag("prevents:flinch", None, SUBSTITUTE),
    comment="protection lasts only while the doll stands; some sources still get through (e.g. a Yawn already in effect)",
    confidence="low",
)

# Effects of damaging moves stated without a chance -> chance null
for n in ("thrash", "petal-dance"):
    move(n, tag("self:confusion", None, "then confuses the user"))
move(
    "dream-eater",
    tag("requires:sleep", None, "Only works on sleeping Pokémon."),
    tag("self:heal", None, "Drains half the damage inflicted to heal the user."),
)
for n in ("absorb", "mega-drain", "leech-life"):
    move(n, tag("self:heal"))
for n in ("karate-chop", "razor-leaf", "crabhammer", "slash"):
    move(n, tag("raises:critical"))
move(
    "razor-wind",
    tag(
        "raises:critical",
        None,
        "User’s critical hit rate is one level higher when using this move.",
    ),
)
for n in ("guillotine", "horn-drill", "fissure"):
    move(n, tag("inflicts:one-hit-ko"))
for n in ("bind", "wrap", "fire-spin", "clamp"):
    move(n, tag("inflicts:trap", None, "Prevents the target from fleeing"))
for n in (
    "double-slap",
    "comet-punch",
    "fury-attack",
    "pin-missile",
    "spike-cannon",
    "barrage",
    "fury-swipes",
    "double-kick",
    "bonemerang",
):
    move(n, tag("inflicts:multi-hit"))
move(
    "skull-bash", tag("raises:defense", None, "Raises the user’s Defense by one stage.")
)
move(
    "rage",
    tag("raises:attack"),
    comment="only when the user is hit after using this move",
)
move(
    "fly",
    tag(
        "immune:moves",
        None,
        "User flies high into the air for one turn, becoming immune to attack",
    ),
    comment="for one turn only (the turn before it hits); some moves still hit the user (e.g. Gust, Thunder)",
)
move(
    "dig",
    tag(
        "immune:moves",
        None,
        "User digs underground for one turn, becoming immune to attack",
    ),
    comment="for one turn only (the turn before it hits); some moves still hit the user (e.g. Earthquake, Fissure)",
)

# ----------------------------------------------------------------------------- abilities
for n in ("limber", "insomnia", "immunity", "own-tempo", "water-veil", "vital-spirit"):
    status = {
        "limber": "paralysis",
        "insomnia": "sleep",
        "immunity": "poison",
        "own-tempo": "confusion",
        "water-veil": "burn",
        "vital-spirit": "sleep",
    }[n]
    ability(n, tag(f"prevents:{status}"))
ability("leaf-guard", tag("prevents:any"), comment="only during strong sunlight")
ability("inner-focus", tag("prevents:flinch"))
ability(
    "sturdy",
    tag(
        "prevents:one-hit-ko",
        None,
        "Protects against the one-hit KO moves regardless of HP.",
    ),
)
ability("clear-body", tag("prevents:stat-drop"))
ability("hyper-cutter", tag("prevents:stat-drop"), comment="Attack only")
ability("keen-eye", tag("prevents:stat-drop"), comment="accuracy only")
ability("big-pecks", tag("prevents:stat-drop"), comment="Defense only")

ability("static", tag("inflicts:paralysis", 30, trigger="on_contact"))
ability("poison-point", tag("inflicts:poison", 30, trigger="on_contact"))
ability("flame-body", tag("inflicts:burn", 30, trigger="on_contact"))
ability(
    "effect-spore",
    *[
        tag(
            f"inflicts:{s}",
            10,
            "Has a 30% chance of inflcting either paralysis, poison, or sleep",
            "on_contact",
        )
        for s in ("paralysis", "poison", "sleep")
    ],
    comment="one 30% roll split across three statuses",
)
ability(
    "poison-touch",
    tag("inflicts:poison", 30),
    comment="the holder's own contact moves poison the target; not a Pokémon touching the holder, so trigger is other",
)
ability("stench", tag("inflicts:flinch", 10))
ability(
    "arena-trap",
    tag("inflicts:trap", None, "Prevents opponents from fleeing or switching out."),
    comment="does not affect Flying-types and Pokémon in the air",
)
ability("magnet-pull", tag("inflicts:trap"), comment="Steel-type opponents only")
ability("intimidate", tag("lowers:attack"), comment="upon entering battle")
ability(
    "cursed-body",
    tag("inflicts:disable", 30),
    comment="disables any move that hits the holder, contact or not",
)

ability("natural-cure", tag("cures:any"), comment="upon switching out")
ability("shed-skin", tag("cures:any", 33))
ability("hydration", tag("cures:any"), comment="only during rain")
ability("healer", tag("cures:any", 30), comment="cures adjacent allies, not the holder")

ability(
    "guts",
    tag("requires:any", None, "with a major status ailment"),
    tag("raises:attack", None, "Increases Attack to 1.5×"),
)
ability(
    "marvel-scale",
    tag("requires:any", None, "with a major status ailment"),
    tag("raises:defense", None, "Increases Defense to 1.5×"),
)
ability(
    "quick-feet",
    tag("requires:any", None, "with a major status ailment"),
    tag("raises:speed", None, "Increases Speed to 1.5×"),
)
ability("tangled-feet", tag("requires:confusion"), tag("raises:evasion"))
ability("steadfast", tag("requires:flinch"), tag("raises:speed"))

ability(
    "sand-veil",
    tag("raises:evasion", None, "Increases evasion to 1.25× during a sandstorm."),
    tag("immune:weather", None, "Protects against sandstorm damage."),
    comment="evasion bonus only during a sandstorm; immune to sandstorm damage only",
)
ability(
    "snow-cloak",
    tag("raises:evasion", None, "Increases evasion to 1.25× during hail."),
    tag("immune:weather", None, "Protects against hail damage."),
    comment="evasion bonus only during hail; immune to hail damage only",
)
ability("swift-swim", tag("raises:speed"), comment="only during rain")
ability("chlorophyll", tag("raises:speed"), comment="only during strong sunlight")
ability(
    "sand-rush",
    tag("raises:speed", None, "Doubles Speed during a sandstorm."),
    tag("immune:weather", None, "Protects against sandstorm damage."),
    comment="Speed bonus only during a sandstorm; immune to sandstorm damage only",
)
ability(
    "sand-force",
    tag("immune:weather", None, "Protects against sandstorm damage."),
    comment="sandstorm damage only",
)
ability("overcoat", tag("immune:weather"))
ability(
    "rock-head",
    tag("immune:recoil"),
    comment="not Struggle's recoil, nor crash damage from missing Jump Kick or High Jump Kick",
)
ability("battle-armor", tag("immune:critical"))
ability("shell-armor", tag("immune:critical"))
ability("soundproof", tag("immune:sound"))
ability(
    "flash-fire",
    tag("immune:fire", None, "Protects against Fire moves."),
    comment="has no effect while the holder is frozen",
)
ability(
    "levitate",
    tag("immune:ground", None, "This Pokémon is immune to Ground-type moves"),
    comment="disabled during Gravity or Ingrain, or while holding an Iron Ball",
)
ability(
    "magic-guard",
    tag(
        "immune:weather",
        None,
        "this Pokémon takes no damage from from weather, recoil, status ailments, or Spikes",
    ),
    tag(
        "immune:recoil",
        None,
        "this Pokémon takes no damage from from weather, recoil, status ailments, or Spikes",
    ),
    comment="immune to all damage not directly caused by a move, e.g. also damage from status ailments and Spikes; "
    "the ailments themselves are not prevented",
)
ability(
    "synchronize",
    *[tag(f"reflects:{s}") for s in ("burn", "paralysis", "poison")],
    comment="only statuses received directly from another Pokémon",
)
ability("cute-charm", tag("inflicts:infatuation", 30, trigger="on_contact"))
ability("oblivious", tag("prevents:infatuation", None, "Prevents infatuation"))
ability(
    "solar-power",
    tag("raises:special-attack", None, "Increases Special Attack to 1.5×"),
    comment="only during strong sunlight, and costs HP each turn",
)
ability("unburden", tag("raises:speed"), comment="upon using or losing a held item")
ability(
    "lightning-rod",
    tag(
        "raises:special-attack",
        None,
        "Absorbs Electric moves, raising Special Attack one stage.",
    ),
    tag("immune:electric", None, "Absorbs Electric moves"),
    comment="Special Attack rises when hit by an Electric move",
)
ability("anger-point", tag("raises:attack"), comment="upon receiving a critical hit")
ability(
    "download",
    tag("raises:attack"),
    tag("raises:special-attack"),
    comment="raises only one of the two, depending on the opponents' weaker defense",
)
ability("defiant", tag("raises:attack"), comment="upon having any stat lowered")
ability(
    "competitive", tag("raises:special-attack"), comment="upon having any stat lowered"
)
ability("moxie", tag("raises:attack"), comment="upon KOing a Pokémon")
ability("justified", tag("raises:attack"), comment="upon being hit by a Dark move")
ability(
    "rattled",
    tag("raises:speed"),
    comment="upon being hit by a Dark, Ghost, or Bug move",
)
ability(
    "weak-armor",
    tag("raises:speed"),
    comment="upon being hit by a physical move; also lowers the holder's own Defense, which `lowers` (target only) does not cover",
)
ability(
    "compound-eyes",
    tag("raises:accuracy"),
    comment="raises the accuracy of the holder's moves, not the accuracy stat itself",
    confidence="low",
)

ability(
    "volt-absorb",
    tag("self:heal"),
    tag("immune:electric", None, "Absorbs Electric moves"),
    comment="heals when hit by an Electric move",
)
ability(
    "water-absorb",
    tag("self:heal"),
    tag("immune:water", None, "Absorbs Water moves"),
    comment="heals when hit by a Water move",
)
ability("rain-dish", tag("self:heal"), comment="only during rain")
ability(
    "ice-body",
    tag("self:heal", None, "Heals for 1/16 max HP after each turn during hail."),
    tag("immune:weather", None, "Protects against hail damage."),
    comment="heals only during hail; immune to hail damage only",
)
ability(
    "dry-skin",
    tag("self:heal", None, "heals for 1/8 max HP during rain"),
    tag("immune:water", None, "absorbs Water moves"),
    comment="during rain or when hit by a Water move; also takes damage in strong sunlight and extra Fire damage",
)
ability("regenerator", tag("self:heal"), comment="upon switching out")

ability("thick-fat", tag("reduces:damage"), comment="Fire and Ice moves only")
ability("filter", tag("reduces:damage"), comment="super-effective moves only")
ability("multiscale", tag("reduces:damage"), comment="only at full HP")
ability(
    "friend-guard", tag("reduces:damage"), comment="protects allies, not the holder"
)

# An effect of the vocabulary is mentioned but does not fit it -> no tag, comment (rule 6)
ability(
    "early-bird",
    comment="shortens sleep duration; neither prevents nor cures it",
    confidence="low",
)
ability(
    "shield-dust",
    comment="blocks moves' extra effects (status ailments, stat changes, flinching) but not main effects; not a plain prevention",
    confidence="low",
)
ability(
    "serene-grace",
    comment="doubles the chance of moves' extra effects (status ailments, stat changes, flinching); does not fit the vocabulary",
    confidence="low",
)
ability(
    "sheer-force",
    comment="removes the extra effects of the holder's own moves; does not fit the vocabulary",
    confidence="low",
)
ability(
    "hustle",
    comment="lowers the accuracy of the holder's own physical moves; `lowers` is for the target's stats",
    confidence="low",
)
ability(
    "liquid-ooze",
    comment="turns the healing of opponents' leeching moves into damage; does not fit the vocabulary",
    confidence="low",
)
ability(
    "run-away",
    comment="lets the holder flee wild battles even when trapped; `trap` can only be inflicted in the vocabulary",
    confidence="low",
)

# ----------------------------------------------------------------------------- build + validate
STATUSES = {"sleep", "poison", "paralysis", "burn", "freeze", "confusion", "any"}
STATS = {
    "attack",
    "defense",
    "special-attack",
    "special-defense",
    "speed",
    "accuracy",
    "evasion",
}
ALLOWED = {
    "inflicts": STATUSES
    | {"flinch", "trap", "one-hit-ko", "infatuation", "multi-hit", "disable", "switch"},
    "self": STATUSES | {"heal"},
    "prevents": STATUSES | {"flinch", "one-hit-ko", "stat-drop", "infatuation"},
    "cures": STATUSES | {"stat-change"},
    "requires": STATUSES | {"flinch"},
    "lowers": STATS,
    "raises": STATS | {"critical"},
    "reduces": {"damage"},
    "reflects": STATUSES,
    "immune": {
        "fire",
        "ground",
        "electric",
        "water",
        "sound",
        "moves",
        "weather",
        "recoil",
        "critical",
    },
}

out, errors = [], []
for key, item in ITEMS.items():  # file order: moves first, then abilities
    entity_type, name = key
    tags, comment, confidence = LABELS.get(key, ([], None, "high"))
    seen = set()
    for t in tags:
        relation, _, effect = t["tag"].partition(":")
        if effect not in ALLOWED.get(relation, ()):
            errors.append(("vocabulary", key, t["tag"]))
        if t["tag"] in seen:
            errors.append(("duplicate tag", key, t["tag"]))
        seen.add(t["tag"])
        if t["evidence"] not in (item["short_effect"] or "") and t["evidence"] not in (
            item["effect"] or ""
        ):
            errors.append(("evidence", key, t["evidence"]))
        if t["chance"] is not None and not 0 <= t["chance"] <= 100:
            errors.append(("chance", key, t["chance"]))
        if (entity_type == "move") != (t["trigger"] == "move_hit") or t[
            "trigger"
        ] not in ("move_hit", "on_contact", "other"):
            errors.append(("trigger", key, t["trigger"]))
    out.append(
        {
            "entity_type": entity_type,
            "name": name,
            "tags": tags,
            "comment": comment,
            "confidence": confidence,
        }
    )

if len(out) != 278 or len({o["name"] for o in out}) != 278:
    errors.append(("count", len(out)))

# The examples of the prompt must be real inputs and match the generated objects exactly.
by_key = {(o["entity_type"], o["name"]): o for o in out}
lines = PROMPT.read_text(encoding="utf-8").splitlines()
examples_in = [
    json.loads(line[len("Input: ") :]) for line in lines if line.startswith("Input: {")
]
examples_out = [
    json.loads(line[len("Output: ") :])
    for line in lines
    if line.startswith("Output: {")
]
for example in examples_in:
    item = ITEMS[(example["entity_type"], example["name"])]
    for field in ("short_effect", "damage_class", "effect_chance"):
        if field in example and example[field] != item[field]:
            errors.append(("prompt example input", example["name"], field))
for example in examples_out:
    if example != by_key[(example["entity_type"], example["name"])]:
        errors.append(("prompt example output", example["name"]))

if errors:
    for e in errors:
        print("ERROR", e)
    sys.exit(1)

(ROOT / "data" / "tags_llm.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)

per_tag = {}
for o in out:
    for t in o["tags"]:
        per_tag[t["tag"]] = per_tag.get(t["tag"], 0) + 1
print(
    f"objects {len(out)} | with tags {sum(bool(o['tags']) for o in out)} | tags {sum(per_tag.values())}"
    f" | comment only {sum(1 for o in out if not o['tags'] and o['comment'])}"
    f" | low {sum(o['confidence'] == 'low' for o in out)} | prompt examples checked {len(examples_out)}"
)
for t in sorted(per_tag):
    print(f"  {t}: {per_tag[t]}")
