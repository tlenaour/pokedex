"""Business rules for finding a Pokémon from a partially remembered name.

Normalization makes what a trainer types comparable with the dataset names,
which are slugs ("bulbasaur", "mr-mime", "nidoran-f", "farfetchd"):

    "  Mr. Mime " -> "mrmime"       "mr-mime"   -> "mrmime"
    "Farfetch'd"  -> "farfetchd"    "Nidoran♀"  -> "nidoranf"
    "BÜLBA"       -> "bulba"        "ｂｕｌｂａ" -> "bulba"

Invariant: normalize_name(text) == "".join(split_words(text)).

Ranking then orders the candidates by match kind, from the most to the least
reliable (see MatchKind), and keeps the best `limit` ones.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from fullstack_pokedex.domain.errors import InvalidSearchQueryError

MAX_QUERY_LENGTH = 30
"""Longest normalized query accepted (the longest Pokémon name is 10 chars)."""

FUZZY_THRESHOLD = 0.80
"""Minimum similarity for a fuzzy match: below, the name is considered unrelated.

Tuned for Jaro-Winkler, see docs/decisions/fuzzy-name-matching-benchmark.md: 0.80 finds
95% of typos with 1.4% false positives; 0.75 jumps to 14% false positives,
0.85 drops to 86% of typos found."""

# Symbols spelled out the way the dataset slugs them ("nidoran-f").
_SYMBOLS = {"♀": " f ", "♂": " m "}

# Apostrophes are dropped without splitting: "farfetch'd" is one word.
_APOSTROPHES = re.compile(r"['’ʼ`´]")

# A word is a run of letters or digits (any script); everything else separates.
_WORD = re.compile(r"[^\W_]+")


def split_words(text: str) -> list[str]:
    """Normalized words of `text`: "Mr. Mime" -> ["mr", "mime"]."""
    for symbol, replacement in _SYMBOLS.items():
        text = text.replace(symbol, replacement)
    # NFKD splits accented letters into base letter + combining mark (dropped
    # below) and maps compatibility forms (full-width, ligatures) to plain ones.
    # It runs before casefold so that "İ" becomes "i", not "i" + a dot.
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _WORD.findall(_APOSTROPHES.sub("", without_marks.casefold()))


def normalize_name(text: str) -> str:
    """Comparable form of a name: lowercase, no accents, no separators.

    Returns "" when nothing meaningful is left (blank or punctuation only);
    deciding whether that is an error is up to the caller.
    """
    return "".join(split_words(text))


def normalize_query(text: str) -> str:
    """Normalize what a trainer typed, rejecting queries that cannot match."""
    query = normalize_name(text)
    if not query:
        raise InvalidSearchQueryError(text, "no letter or digit")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidSearchQueryError(
            text, f"longer than {MAX_QUERY_LENGTH} characters"
        )
    return query


# --- Ranking -------------------------------------------------------------------


class MatchKind(StrEnum):
    """How a name matches the query. Declaration order is the priority order."""

    EXACT = "exact"  # "bulbasaur" -> bulbasaur
    PREFIX = "prefix"  # "bulba" -> bulbasaur
    WORD_PREFIX = "word_prefix"  # "mime" -> mr-mime
    SUBSTRING = "substring"  # "saur" -> ivysaur
    FUZZY = "fuzzy"  # "bulbsaur" -> bulbasaur (typo)

    @property
    def priority(self) -> int:
        return list(MatchKind).index(self)


@dataclass(frozen=True)
class NameCandidate:
    """The minimal view of a Pokémon needed to search it by name."""

    pokemon_id: int
    name: str


@dataclass(frozen=True)
class NameMatch:
    pokemon_id: int
    name: str
    kind: MatchKind
    score: float
    """1.0 for exact/prefix/word-prefix/substring, the similarity for fuzzy."""
    span: tuple[int, int] | None
    """[start, end) of the matched part in the *normalized* name ("mime" in
    "mr-mime" -> (2, 6) in "mrmime"); None for a fuzzy match.

    Normalized coordinates fit every spelling of the name ("mr-mime",
    "Mr. Mime"): use `split_by_span` to highlight the one being displayed."""


class SimilarityScorer(Protocol):
    """Port: similarity between two normalized names, from 0.0 to 1.0."""

    def score(self, query: str, name: str) -> float: ...


def rank_candidates(
    query: str,
    candidates: Sequence[NameCandidate],
    limit: int,
    scorer: SimilarityScorer | None = None,
    fuzzy_threshold: float = FUZZY_THRESHOLD,
) -> list[NameMatch]:
    """Best `limit` matches for `query`, most relevant first.

    Order: match kind (exact > prefix > word prefix > substring > fuzzy), then
    score, then closest length to the query, then Pokédex number.
    Fuzzy matching only runs when the other kinds found fewer than `limit`
    names, and only with a `scorer`.
    """
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")
    normalized_query = normalize_query(query)

    strict: list[NameMatch] = []
    unmatched: list[NameCandidate] = []
    for candidate in candidates:
        match = _strict_match(normalized_query, candidate)
        if match is None:
            unmatched.append(candidate)
        else:
            strict.append(match)

    fuzzy: list[NameMatch] = []
    if scorer is not None and len(strict) < limit:
        for candidate in unmatched:
            score = scorer.score(normalized_query, normalize_name(candidate.name))
            if score >= fuzzy_threshold:
                fuzzy.append(
                    NameMatch(
                        candidate.pokemon_id,
                        candidate.name,
                        MatchKind.FUZZY,
                        score,
                        span=None,
                    )
                )

    def sort_key(match: NameMatch) -> tuple[int, float, int, int]:
        length_gap = abs(len(normalize_name(match.name)) - len(normalized_query))
        return (match.kind.priority, -match.score, length_gap, match.pokemon_id)

    return sorted(strict + fuzzy, key=sort_key)[:limit]


def _strict_match(query: str, candidate: NameCandidate) -> NameMatch | None:
    normalized = normalize_name(candidate.name)

    if normalized == query:
        kind, start = MatchKind.EXACT, 0
    elif normalized.startswith(query):
        kind, start = MatchKind.PREFIX, 0
    elif (word_start := _word_prefix_start(query, candidate.name)) is not None:
        kind, start = MatchKind.WORD_PREFIX, word_start
    elif (index := normalized.find(query)) != -1:
        kind, start = MatchKind.SUBSTRING, index
    else:
        return None

    span = (start, start + len(query))
    return NameMatch(candidate.pokemon_id, candidate.name, kind, 1.0, span)


def _word_prefix_start(query: str, name: str) -> int | None:
    """Start, in the normalized name, of the first non-first word starting
    with `query` ("mime" in "mr-mime" -> 2)."""
    words = split_words(name)
    offset = len(words[0]) if words else 0
    for word in words[1:]:
        if word.startswith(query):
            return offset
        offset += len(word)
    return None


def _normalize_with_positions(name: str) -> tuple[str, list[int]]:
    """Normalized name, and for each of its characters the index of the
    original character it comes from ("mr-mime" -> "mrmime", [0,1,3,4,5,6])."""
    chars: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(name):
        for normalized_char in normalize_name(char):
            chars.append(normalized_char)
            positions.append(index)
    return "".join(chars), positions


# --- Highlighting -----------------------------------------------------------------


@dataclass(frozen=True)
class NameSegment:
    text: str
    matched: bool


def split_by_span(text: str, span: tuple[int, int] | None) -> list[NameSegment]:
    """Cut `text` (any spelling of the name: slug or display name) into the
    parts matching the query and the others, for display.

    `span` is in normalized coordinates (see NameMatch.span), so the same span
    works for "mr-mime" and "Mr. Mime":
        split_by_span("Mr. Mime", (2, 6)) -> [("Mr. ", False), ("Mime", True)]
    Characters ignored by normalization inside the matched part (spaces, dots,
    hyphens) belong to it: "mrmi" -> [("Mr. Mi", True), ("me", False)].
    """
    if span is None:
        return [NameSegment(text, matched=False)]
    normalized, positions = _normalize_with_positions(text)
    start, end = span
    if not 0 <= start < end <= len(normalized):
        raise ValueError(f"span {span} out of range for {text!r} ({normalized!r})")

    first, last = positions[start], positions[end - 1] + 1
    parts = [
        NameSegment(text[:first], matched=False),
        NameSegment(text[first:last], matched=True),
        NameSegment(text[last:], matched=False),
    ]
    return [part for part in parts if part.text]
