"""Quality guard with the REAL embedding model, on the full evaluation set.

Fails if a change to the reference descriptions (data/pokemon_descriptions.json)
or to the model lowers identification quality below the measured baseline
(potion-base-32M, "joined" strategy, 95.6 % first / 100 % top 3 on the
68 queries of fixtures/appearance_queries.json).

Skipped when the model is not already on this machine: tests never download it.
Get it once with `uv run pokedex-import` (or any first use of the model).
"""

import json
from pathlib import Path

import huggingface_hub
import pytest

from fullstack_pokedex.domain.appearance import AppearanceCandidate, rank_by_appearance
from fullstack_pokedex.infrastructure.appearance_descriptions import (
    load_appearance_descriptions,
)
from fullstack_pokedex.infrastructure.embeddings import (
    Model2VecEmbedder,
    configured_model,
)
from tests.factories import DESCRIPTIONS

QUERIES = Path(__file__).parent / "fixtures" / "appearance_queries.json"

# Measured baseline minus a small margin (1 query = 1.5 points).
MIN_HIT_AT_1 = 0.92
MIN_HIT_AT_3 = 0.97


def model_is_available() -> bool:
    model = configured_model()
    if Path(model).is_dir():  # local folder (offline setup)
        return True
    cached = huggingface_hub.try_to_load_from_cache(model, "config.json")
    return isinstance(cached, str)


pytestmark = pytest.mark.skipif(
    not model_is_available(),
    reason=f"embedding model {configured_model()!r} not downloaded on this machine",
)


@pytest.fixture(scope="module")
def embedder() -> Model2VecEmbedder:
    # Cached locally: never reach the network from the test suite.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(huggingface_hub.constants, "HF_HUB_OFFLINE", True)
        return Model2VecEmbedder()


def test_embeddings_are_vectors_of_floats(embedder: Model2VecEmbedder) -> None:
    vectors = embedder.embed(["small yellow mouse", "giant blue sea serpent"])

    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1]) > 0
    assert all(isinstance(x, float) for x in vectors[0])


def test_identification_quality_on_the_evaluation_set(
    embedder: Model2VecEmbedder,
) -> None:
    descriptions = load_appearance_descriptions(DESCRIPTIONS)
    names = {e["id"]: e["name"] for e in json.loads(DESCRIPTIONS.read_text("utf-8"))}
    vectors = embedder.embed([d.reference_text for d in descriptions])
    candidates = [
        AppearanceCandidate(d.pokemon_id, v)
        for d, v in zip(descriptions, vectors, strict=True)
    ]
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))["queries"]
    query_vectors = embedder.embed([q["query"] for q in queries])

    hits_1 = hits_3 = 0
    misses = []
    for query, vector in zip(queries, query_vectors, strict=True):
        top = [names[m.pokemon_id] for m in rank_by_appearance(vector, candidates, 3)]
        hits_1 += top[0] == query["expected"]
        hits_3 += query["expected"] in top
        if top[0] != query["expected"]:
            misses.append(
                f"{query['query']!r}: expected {query['expected']}, got {top}"
            )

    report = "\n".join(misses)
    assert hits_1 / len(queries) >= MIN_HIT_AT_1, f"hit@1 too low, misses:\n{report}"
    assert hits_3 / len(queries) >= MIN_HIT_AT_3, f"hit@3 too low, misses:\n{report}"
