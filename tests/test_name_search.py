import pytest

from fullstack_pokedex.domain.name_search import normalize_name, split_words
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex

# --- What a trainer types vs. how the dataset spells it ----------------------


@pytest.mark.parametrize(
    "typed, slug",
    [
        # The feature's case: a prefix, whatever the case or surrounding spaces.
        ("bulba", "bulba"),
        ("BULBA", "bulba"),
        ("  Bulba\t", "bulba"),
        # Separators: spaces, dots, hyphens, underscores all disappear.
        ("Mr. Mime", "mr-mime"),
        ("mr mime", "mr-mime"),
        ("MR-MIME", "mr-mime"),
        ("mr_mime", "mr-mime"),
        ("mr.mime", "mr-mime"),
        # Apostrophes (straight or typographic) are dropped.
        ("Farfetch'd", "farfetchd"),
        ("Farfetch’d", "farfetchd"),
        # Gender symbols are spelled like in the slugs.
        ("Nidoran♀", "nidoran-f"),
        ("Nidoran ♂", "nidoran-m"),
        # Accents and compatibility forms.
        ("Bülbasaur", "bulbasaur"),
        ("ＢＵＬＢＡ", "bulba"),
        ("Pokémon", "pokemon"),
        # Digits are kept.
        ("Porygon2", "porygon2"),
    ],
)
def test_typed_text_matches_the_dataset_slug(typed: str, slug: str) -> None:
    assert normalize_name(typed) == normalize_name(slug)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("bulbasaur", "bulbasaur"),
        ("Mr. Mime", "mrmime"),
        ("Nidoran♀", "nidoranf"),
        ("İvysaur", "ivysaur"),  # no stray combining dot after casefold
        ("Straße", "strasse"),  # casefold, not lower()
    ],
)
def test_normalize_name(text: str, expected: str) -> None:
    assert normalize_name(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "!!!", "%_", "-.-", "''"])
def test_nothing_meaningful_normalizes_to_empty(text: str) -> None:
    assert normalize_name(text) == ""
    assert split_words(text) == []


@pytest.mark.parametrize(
    "text, words",
    [
        ("bulbasaur", ["bulbasaur"]),
        ("mr-mime", ["mr", "mime"]),
        ("Mr. Mime", ["mr", "mime"]),
        ("nidoran-f", ["nidoran", "f"]),
        ("Nidoran♀", ["nidoran", "f"]),
        ("Farfetch'd", ["farfetchd"]),
        ("  several   spaces  ", ["several", "spaces"]),
    ],
)
def test_split_words(text: str, words: list[str]) -> None:
    assert split_words(text) == words


# --- Invariants ----------------------------------------------------------------

SAMPLES = [
    "bulba",
    "  Mr. Mime ",
    "Farfetch’d",
    "Nidoran♀",
    "ＢＵＬＢＡ",
    "İvysaur",
    "%_!",
    "",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_normalize_is_the_concatenation_of_words(text: str) -> None:
    assert normalize_name(text) == "".join(split_words(text))


@pytest.mark.parametrize("text", SAMPLES)
def test_normalize_is_idempotent(text: str) -> None:
    once = normalize_name(text)
    assert normalize_name(once) == once


@pytest.mark.parametrize("text", SAMPLES)
def test_normalized_form_is_lowercase_alphanumeric(text: str) -> None:
    normalized = normalize_name(text)
    assert normalized == normalized.casefold()
    assert all(c.isalnum() for c in normalized)


def test_dataset_names_stay_distinct(pokedex: Pokedex) -> None:
    """Normalization must never merge two different Pokémon."""
    names = [p.name for p in pokedex.pokemon]
    assert len({normalize_name(n) for n in names}) == len(names)
