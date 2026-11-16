"""Integrity of data/pokemon_descriptions.json, the reference appearance
descriptions used to identify a Pokémon from a free-text description.

The file was generated once by an LLM, then reviewed and edited by hand: these
tests keep the rules of its generation prompt true after every manual edit.
Each test collects every violation, so one run shows everything to fix.
"""

import json
import re
from pathlib import Path

import pytest

from tests.factories import MINI_POKEDEX

DESCRIPTIONS = Path(__file__).parents[1] / "data" / "pokemon_descriptions.json"

FIELDS = {"id", "name", "glance", "detailed", "everyday", "confidence", "notes"}
TEXT_FIELDS = ("glance", "detailed", "everyday")
WORD_LIMITS = {"glance": (5, 10), "detailed": (12, 25), "everyday": (8, 20)}

# Appearance only: no game vocabulary in the descriptions.
GAME_WORDS = re.compile(
    r"\b(types?|evolv\w*|pok[eé]mon|attack\w*|abilit\w*|moves?|trainer|battle"
    r"|level|generation)\b",
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def entries() -> list[dict]:
    return json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))


def name_words(slug: str) -> set[str]:
    """Words that would reveal a Pokémon's name: "mr-mime" -> {"mr-mime",
    "mr mime"}, "nidoran-f" -> {"nidoran-f", "nidoran f", "nidoran"}."""
    words = {slug, slug.replace("-", " ")}
    first = slug.split("-")[0]
    if len(first) > 2:  # skip "mr" from "mr-mime"
        words.add(first)
    return words


def assert_no_violation(violations: list[str]) -> None:
    assert not violations, f"{len(violations)} violation(s):\n" + "\n".join(violations)


# --- Structure ---------------------------------------------------------------


def test_covers_the_151_pokemon_once_in_order(entries: list[dict]) -> None:
    assert [e["id"] for e in entries] == list(range(1, 152))


def test_names_are_unique(entries: list[dict]) -> None:
    names = [e["name"] for e in entries]
    assert len(set(names)) == len(names)


def test_every_entry_has_exactly_the_expected_fields(entries: list[dict]) -> None:
    assert_no_violation(
        [
            f"#{e.get('id')}: fields {sorted(set(e) ^ FIELDS)}"
            for e in entries
            if set(e) != FIELDS
        ]
    )


def test_field_types_and_confidence(entries: list[dict]) -> None:
    violations = []
    for e in entries:
        if not isinstance(e["id"], int):
            violations.append(f"#{e['id']}: id is not an integer")
        for field in ("name", *TEXT_FIELDS, "notes"):
            if not isinstance(e[field], str):
                violations.append(f"#{e['id']}: {field} is not a string")
        if e["confidence"] not in ("high", "medium", "low"):
            violations.append(f"#{e['id']}: confidence {e['confidence']!r}")
    assert_no_violation(violations)


def test_ids_and_names_match_the_dataset(entries: list[dict]) -> None:
    """Checked against the versioned mini fixture (pokedex.json is not)."""
    dataset = json.loads(MINI_POKEDEX.read_text(encoding="utf-8"))["pokemon"]
    by_id = {e["id"]: e["name"] for e in entries}
    assert_no_violation(
        [
            f"#{p['id']}: {by_id.get(p['id'])!r} != dataset {p['name']!r}"
            for p in dataset
            if by_id.get(p["id"]) != p["name"]
        ]
    )


# --- Content rules (from the generation prompt) ------------------------------


def test_descriptions_are_not_empty(entries: list[dict]) -> None:
    assert_no_violation(
        [
            f"#{e['id']} {e['name']}: {field} is empty"
            for e in entries
            for field in TEXT_FIELDS
            if not e[field].strip()
        ]
    )


def test_word_counts_stay_within_limits(entries: list[dict]) -> None:
    """Short texts: a long one dilutes its embedding (and may be truncated)."""
    violations = []
    for e in entries:
        for field, (low, high) in WORD_LIMITS.items():
            count = len(e[field].split())
            if not low <= count <= high:
                violations.append(
                    f"#{e['id']} {e['name']}: {field} has {count} words "
                    f"(expected {low}-{high})"
                )
    assert_no_violation(violations)


def test_no_pokemon_name_in_descriptions(entries: list[dict]) -> None:
    """Neither its own name nor another one: matching must rely on appearance."""
    patterns = {
        e["name"]: re.compile(
            r"\b(" + "|".join(re.escape(w) for w in name_words(e["name"])) + r")\b"
        )
        for e in entries
    }
    violations = []
    for e in entries:
        for field in TEXT_FIELDS:
            text = e[field].lower()
            for name, pattern in patterns.items():
                if pattern.search(text):
                    violations.append(
                        f"#{e['id']} {e['name']}: {field} mentions {name!r}"
                    )
    assert_no_violation(violations)


def test_no_game_vocabulary(entries: list[dict]) -> None:
    assert_no_violation(
        [
            f"#{e['id']} {e['name']}: {field} contains {match.group(0)!r}"
            for e in entries
            for field in TEXT_FIELDS
            if (match := GAME_WORDS.search(e[field]))
        ]
    )


def test_single_line_without_trailing_period(entries: list[dict]) -> None:
    violations = []
    for e in entries:
        for field in TEXT_FIELDS:
            text = e[field]
            if "\n" in text:
                violations.append(f"#{e['id']} {e['name']}: {field} spans lines")
            if text.rstrip().endswith("."):
                violations.append(f"#{e['id']} {e['name']}: {field} ends with '.'")
            if text != text.strip():
                violations.append(f"#{e['id']} {e['name']}: {field} has outer spaces")
    assert_no_violation(violations)


def test_descriptions_of_a_pokemon_differ(entries: list[dict]) -> None:
    """The 3 texts are 3 phrasings: identical ones add nothing to matching."""
    assert_no_violation(
        [
            f"#{e['id']} {e['name']}: two identical descriptions"
            for e in entries
            if len({e[field] for field in TEXT_FIELDS}) < len(TEXT_FIELDS)
        ]
    )


def test_glance_descriptions_are_unique(entries: list[dict]) -> None:
    """Two Pokémon with the same glance text could never be told apart."""
    seen: dict[str, str] = {}
    violations = []
    for e in entries:
        if (other := seen.setdefault(e["glance"], e["name"])) != e["name"]:
            violations.append(f"{e['name']} and {other}: same glance {e['glance']!r}")
    assert_no_violation(violations)
