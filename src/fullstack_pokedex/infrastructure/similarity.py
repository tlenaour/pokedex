"""Implementations of the SimilarityScorer port (typo tolerance).

The only module depending on rapidfuzz. The choice of Jaro-Winkler is
documented in docs/decisions/fuzzy-name-matching-benchmark.md.
"""

from rapidfuzz.distance import JaroWinkler


class JaroWinklerScorer:
    """Jaro-Winkler similarity: shared letters close to each other, with a
    bonus when the beginnings match (fits a partially remembered name)."""

    def score(self, query: str, name: str) -> float:
        return JaroWinkler.similarity(query, name)
