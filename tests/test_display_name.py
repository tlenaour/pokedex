"""display_name and split_by_span: how a match is shown to people."""

import pytest

from fullstack_pokedex.domain.display_name import display_name
from fullstack_pokedex.domain.name_search import (
    NameCandidate,
    NameSegment,
    normalize_name,
    rank_candidates,
    split_by_span,
)
from fullstack_pokedex.infrastructure.pokedex_json import Pokedex

SPECIAL_SLUGS = ["mr-mime", "nidoran-f", "nidoran-m", "farfetchd"]

# --- display_name ----------------------------------------------------------------


@pytest.mark.parametrize(
    "slug, expected",
    [
        ("bulbasaur", "Bulbasaur"),
        ("mew", "Mew"),
        # Official spellings no rule can guess.
        ("mr-mime", "Mr. Mime"),
        ("nidoran-f", "Nidoran♀"),
        ("nidoran-m", "Nidoran♂"),
        ("farfetchd", "Farfetch'd"),
        # General rule for hyphenated names of later generations.
        ("ho-oh", "Ho-Oh"),
        ("porygon-z", "Porygon-Z"),
    ],
)
def test_display_name(slug: str, expected: str) -> None:
    assert display_name(slug) == expected


@pytest.mark.parametrize("slug", [*SPECIAL_SLUGS, "bulbasaur", "ho-oh"])
def test_display_name_normalizes_like_the_slug(slug: str) -> None:
    """The invariant that lets a span computed on the slug highlight the
    display name."""
    assert normalize_name(display_name(slug)) == normalize_name(slug)


def test_every_dataset_name_keeps_the_invariant(pokedex: Pokedex) -> None:
    for pokemon in pokedex.pokemon:
        assert normalize_name(display_name(pokemon.name)) == normalize_name(
            pokemon.name
        )


# --- split_by_span ---------------------------------------------------------------


def segments(*parts: tuple[str, bool]) -> list[NameSegment]:
    return [NameSegment(text, matched) for text, matched in parts]


@pytest.mark.parametrize(
    "text, span, expected",
    [
        ("Bulbasaur", (0, 5), segments(("Bulba", True), ("saur", False))),
        ("Bulbasaur", (0, 9), segments(("Bulbasaur", True))),
        ("Ivysaur", (3, 7), segments(("Ivy", False), ("saur", True))),
        (
            "Farfetch'd",
            (2, 5),
            segments(("Fa", False), ("rfe", True), ("tch'd", False)),
        ),
        # Same normalized span (2, 6), two spellings of the same name.
        ("mr-mime", (2, 6), segments(("mr-", False), ("mime", True))),
        ("Mr. Mime", (2, 6), segments(("Mr. ", False), ("Mime", True))),
        # Ignored characters inside the matched part belong to it.
        ("Mr. Mime", (0, 4), segments(("Mr. Mi", True), ("me", False))),
        # The gender symbol is the normalized "f".
        ("Nidoran♀", (0, 8), segments(("Nidoran♀", True))),
        ("Nidoran♀", (0, 4), segments(("Nido", True), ("ran♀", False))),
        # The apostrophe inside a match stays in it.
        ("Farfetch'd", (5, 9), segments(("Farfe", False), ("tch'd", True))),
    ],
)
def test_split_by_span(
    text: str, span: tuple[int, int], expected: list[NameSegment]
) -> None:
    assert split_by_span(text, span) == expected


def test_no_span_gives_a_single_unmatched_segment() -> None:
    assert split_by_span("Bulbasaur", None) == segments(("Bulbasaur", False))


@pytest.mark.parametrize("span", [(0, 0), (5, 3), (-1, 2), (0, 10)])
def test_span_out_of_range_is_rejected(span: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="out of range"):
        split_by_span("Bulbasaur", span)


@pytest.mark.parametrize(
    "query, slug",
    [
        ("bulba", "bulbasaur"),
        ("mime", "mr-mime"),
        ("Mr. Mi", "mr-mime"),
        ("nido", "nidoran-f"),
        ("Nidoran♀", "nidoran-f"),
        ("farf", "farfetchd"),
        ("tchd", "farfetchd"),
    ],
)
def test_segments_always_rebuild_the_display_name(query: str, slug: str) -> None:
    """End to end in the domain: rank, then cut the display name."""
    [match] = rank_candidates(query, [NameCandidate(1, slug)], limit=1)
    shown = display_name(slug)

    parts = split_by_span(shown, match.span)

    assert "".join(p.text for p in parts) == shown
    assert any(p.matched for p in parts)
    matched = "".join(p.text for p in parts if p.matched)
    assert normalize_name(matched) == normalize_name(query)
