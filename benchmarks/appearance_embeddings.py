"""Benchmark: identify a Pokémon from a free-text appearance description.

Compares embedding models (model2vec, sentence-transformers) and ways of
combining the 3 reference descriptions of each Pokémon, on the evaluation set
benchmarks/appearance_queries.json, against a no-AI word-overlap baseline.

Its dependencies are NOT project dependencies (that is what it helps decide):
run it in a separate environment, e.g.
    uv venv /tmp/emb && uv pip install --python /tmp/emb/bin/python \
        model2vec sentence-transformers
    (CPU-only torch: add `torch --index-url https://download.pytorch.org/whl/cpu`)
    /tmp/emb/bin/python benchmarks/appearance_embeddings.py [out.json]
Models are downloaded from Hugging Face on first run.
"""

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]
DESCRIPTIONS = ROOT / "data" / "pokemon_descriptions.json"
QUERIES = ROOT / "benchmarks" / "appearance_queries.json"
FIELDS = ("glance", "detailed", "everyday")
KS = (1, 3, 5)

# name -> (library, model id, prefix added to queries only)
MODELS = {
    "potion-base-8M": ("model2vec", "minishlab/potion-base-8M", ""),
    "potion-base-32M": ("model2vec", "minishlab/potion-base-32M", ""),
    "potion-retrieval-32M": ("model2vec", "minishlab/potion-retrieval-32M", ""),
    "all-MiniLM-L6-v2": ("st", "sentence-transformers/all-MiniLM-L6-v2", ""),
    "bge-small-en-v1.5": (
        "st",
        "BAAI/bge-small-en-v1.5",
        "Represent this sentence for searching relevant passages: ",
    ),
    "all-mpnet-base-v2": ("st", "sentence-transformers/all-mpnet-base-v2", ""),
}


def load_encoder(library: str, model_id: str):
    if library == "model2vec":
        from model2vec import StaticModel

        model = StaticModel.from_pretrained(model_id)
        return lambda texts: np.asarray(model.encode(texts))
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_id, device="cpu")
    return lambda texts: np.asarray(model.encode(texts, batch_size=64))


def normalize(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def model_size_mb(model_id: str) -> float | None:
    cache = Path.home() / ".cache" / "huggingface" / "hub"
    folder = cache / ("models--" + model_id.replace("/", "--"))
    if not folder.exists():
        return None
    blobs = folder / "blobs"
    return sum(f.stat().st_size for f in blobs.iterdir()) / 1e6


def rank(scores: np.ndarray) -> np.ndarray:
    """Indexes of candidates, best first (ties by Pokédex order)."""
    return np.lexsort((np.arange(len(scores)), -scores))


def evaluate(rankings: list[np.ndarray], expected: list[int]) -> dict[int, float]:
    return {
        k: round(100 * np.mean([e in r[:k] for r, e in zip(rankings, expected)]), 1)
        for k in KS
    }


WORD = re.compile(r"[a-z]+")
STOP = {
    "a",
    "an",
    "the",
    "and",
    "with",
    "on",
    "its",
    "of",
    "in",
    "to",
    "like",
    "or",
    "looks",
    "is",
    "it",
    "that",
    "has",
    "for",
    "at",
    "by",
}


def words(text: str) -> set[str]:
    return {w.rstrip("s") for w in WORD.findall(text.lower())} - STOP


def main() -> None:
    entries = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))["queries"]
    names = [e["name"] for e in entries]
    expected = [names.index(q["expected"]) for q in queries]
    categories = [q["category"] for q in queries]
    texts = [q["query"] for q in queries]
    results = {}

    def by_category(rankings):
        groups = defaultdict(list)
        for r, e, c in zip(rankings, expected, categories):
            groups[c].append((r, e))
        return {
            c: evaluate([r for r, _ in g], [e for _, e in g])[1]
            for c, g in groups.items()
        }

    # Baseline without AI: share of query words found in the descriptions.
    refs = [set().union(*(words(e[f]) for f in FIELDS)) for e in entries]
    rankings = [
        rank(np.array([len(words(q) & r) / max(len(words(q)), 1) for r in refs]))
        for q in texts
    ]
    results["word-overlap (no AI)"] = {
        "max-of-3": evaluate(rankings, expected),
        "categories@1": by_category(rankings),
    }

    for name, (library, model_id, prefix) in MODELS.items():
        try:
            t0 = time.perf_counter()
            encode = load_encoder(library, model_id)
            load_s = time.perf_counter() - t0
        except Exception as error:  # noqa: BLE001 - report and go on
            results[name] = {"error": str(error)[:200]}
            print(f"{name}: unavailable ({error})", file=sys.stderr)
            continue

        refs = {f: normalize(encode([e[f] for e in entries])) for f in FIELDS}
        joined = normalize(encode([". ".join(e[f] for f in FIELDS) for e in entries]))
        t0 = time.perf_counter()
        q = normalize(encode([prefix + t for t in texts]))
        query_ms = (time.perf_counter() - t0) / len(texts) * 1000

        per_field = np.stack([q @ refs[f].T for f in FIELDS])  # (3, queries, 151)
        strategies = {
            "max-of-3": per_field.max(axis=0),
            "mean-of-3": per_field.mean(axis=0),
            "joined": q @ joined.T,
            **{f"only-{f}": per_field[i] for i, f in enumerate(FIELDS)},
        }
        entry = {
            s: evaluate([rank(row) for row in m], expected)
            for s, m in strategies.items()
        }
        best = [rank(row) for row in strategies["max-of-3"]]
        entry["categories@1"] = by_category(best)
        entry["misses@3"] = [
            {"query": t, "expected": names[e], "got": [names[i] for i in r[:3]]}
            for t, e, r in zip(texts, expected, best)
            if e not in r[:3]
        ]
        entry["load_s"] = round(load_s, 2)
        entry["query_ms"] = round(query_ms, 2)
        entry["size_mb"] = model_size_mb(model_id)
        results[name] = entry
        print(f"done {name}", file=sys.stderr)

    out = sys.argv[1] if len(sys.argv) > 1 else "appearance_embeddings_results.json"
    Path(out).write_text(json.dumps(results, indent=1), encoding="utf-8")
    for name, r in results.items():
        if "error" in r:
            print(f"{name:24} ERROR {r['error'][:80]}")
            continue
        m = r["max-of-3"]
        print(
            f"{name:24} hit@1 {m[1]:5} hit@3 {m[3]:5} hit@5 {m[5]:5}"
            f" | {r.get('size_mb') or 0:7.1f} MB | {r.get('query_ms', 0):6.2f} ms/query"
        )


if __name__ == "__main__":
    main()
