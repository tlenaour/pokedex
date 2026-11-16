"""Benchmark of similarity measures for typo-tolerant Pokémon name search.

Every case runs through the real domain `rank_candidates` (strict tiers first,
fuzzy only to fill the limit), with limit=5 like the API default.
Documentation: docs/benchmark-fuzzy-name-matching.md

Usage (from the project root, ~4 min):
    uv run python benchmarks/fuzzy_name_matching.py \
        [pokedex.json] [benchmarks/results/fuzzy_name_matching.json]
"""

import json
import random
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import OSA, Indel, JaroWinkler, Levenshtein

from fullstack_pokedex.domain.name_search import (
    NameCandidate,
    normalize_name,
    rank_candidates,
)

LIMIT = 5
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
SEED = 20261110

# ----------------------------------------------------------------- scorers


def trigrams(s: str) -> set[str]:
    padded = f"  {s} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def prefix_osa(q: str, n: str) -> float:
    """Compare the query to the beginning of the name (same length +/- 1)."""
    best = 0.0
    for length in (len(q) - 1, len(q), len(q) + 1):
        if 1 <= length <= len(n):
            best = max(best, OSA.normalized_similarity(q, n[:length]))
    if len(n) < len(q) - 1:  # name shorter than the query: compare whole
        best = max(best, OSA.normalized_similarity(q, n))
    return best


SCORERS = {
    "levenshtein": lambda q, n: Levenshtein.normalized_similarity(q, n),
    "damerau_osa": lambda q, n: OSA.normalized_similarity(q, n),
    "indel_ratio": lambda q, n: Indel.normalized_similarity(q, n),
    "jaro_winkler": lambda q, n: JaroWinkler.similarity(q, n),
    "partial_ratio": lambda q, n: fuzz.partial_ratio(q, n) / 100,
    "wratio": lambda q, n: fuzz.WRatio(q, n) / 100,
    "prefix_osa": prefix_osa,
    "hybrid_osa": lambda q, n: max(OSA.normalized_similarity(q, n), prefix_osa(q, n)),
    "trigram_jaccard": lambda q, n: (
        len(trigrams(q) & trigrams(n)) / len(trigrams(q) | trigrams(n))
    ),
    # Combinations of the two complementary measures.
    "jw_prefix_max": lambda q, n: max(JaroWinkler.similarity(q, n), prefix_osa(q, n)),
    # OR rule with two thresholds, expressed as one score: at threshold t it
    # accepts JW >= t OR prefix_osa >= t - 0.10 (t=0.80: JW>=0.80 OR pfx>=0.70).
    "jw_or_prefix": lambda q, n: min(
        1.0, max(JaroWinkler.similarity(q, n), prefix_osa(q, n) + 0.10)
    ),
}


@dataclass
class CachedScorer:
    """Implements the SimilarityScorer port; caches scores across thresholds."""

    fn: object
    cache: dict

    def score(self, query: str, name: str) -> float:
        key = (query, name)
        if key not in self.cache:
            self.cache[key] = self.fn(query, name)
        return self.cache[key]


# ------------------------------------------------------------------- cases

QWERTY = [
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
]
NEIGHBORS: dict[str, str] = {}
for r, row in enumerate(QWERTY):
    for c, ch in enumerate(row):
        near = []
        for dr in (-1, 0, 1):
            rr = r + dr
            if 0 <= rr < len(QWERTY):
                for dc in (-1, 0, 1):
                    cc = c + dc
                    if (dr, dc) != (0, 0) and 0 <= cc < len(QWERTY[rr]):
                        near.append(QWERTY[rr][cc])
        NEIGHBORS[ch] = "".join(near)


def typo(name: str, kind: str, rng: random.Random) -> str:
    """One realistic typo, never on the first letter (see edge cases)."""
    s = list(name)
    if kind == "deletion":
        i = rng.randrange(1, len(s))
        del s[i]
    elif kind == "insertion":
        i = rng.randrange(1, len(s) + 1)
        prev = s[i - 1]
        s.insert(i, rng.choice([prev, *NEIGHBORS.get(prev, prev)]))
    elif kind == "substitution":
        i = rng.randrange(1, len(s))
        s[i] = rng.choice(NEIGHBORS.get(s[i], "e"))
    elif kind == "transposition":
        i = rng.randrange(1, len(s) - 1)
        s[i], s[i + 1] = s[i + 1], s[i]
    elif kind == "prefix_with_typo":
        length = max(4, round(len(s) * 0.6))
        s = s[:length]
        i = rng.randrange(1, len(s))
        s[i] = rng.choice(NEIGHBORS.get(s[i], "e"))
    return "".join(s)


# Realistic misspellings: phonetic, how people actually spell names.
HANDWRITTEN = {
    "bulbasaur": ["bulbasore", "bulbasor", "bulbasaurus"],
    "charmander": ["charmandar", "charmender", "charmandor"],
    "squirtle": ["squirtel", "squirtl", "squirtul"],
    "pikachu": ["pikachoo", "pickachu", "pikatchu", "peekachu"],
    "jigglypuff": ["jigglypuf", "jiggly puf", "jigglipuff"],
    "charizard": ["charizad", "charizerd", "charrizard"],
    "gyarados": ["gyrados", "garados", "gyaradose"],
    "alakazam": ["alakazm", "alakazaam", "allakazam"],
    "kadabra": ["kadabara", "kedabra", "kadabbra"],
    "geodude": ["geodood", "jeodude", "geodud"],
    "magikarp": ["magicarp", "magikarpe", "majikarp"],
    "snorlax": ["snorelax", "snorlacks", "snorlaks"],
    "eevee": ["evee", "eevie", "eevy"],
    "mewtwo": ["mewto", "mewtoo", "mewtow"],
    "psyduck": ["psiduck", "sykduck", "psyduk"],
    "farfetchd": ["farfetched", "farfechd", "farfeched"],
    "mr-mime": ["mr mine", "mrmim", "mr myme"],
    "nidoqueen": ["nidoqeen", "nidoquen", "nidoqueene"],
    "butterfree": ["buterfree", "butterfre", "butterfry"],
    "dragonite": ["dragonight", "dragonit", "draggonite"],
    "venusaur": ["venasaur", "venusar", "venosaur"],
    "blastoise": ["blastoys", "blastois", "blastoyse"],
    "golem": ["golum", "gollem"],
    "exeggutor": ["exegutor", "exeggutr", "exegguter"],
    "hitmonchan": ["hitmonchun", "hitmonshan", "hitmonchann"],
    "onix": ["onyx", "oniks"],
    "ditto": ["dito", "dittoo"],
    "vulpix": ["vulpicks", "volpix", "vulpiks"],
    "ninetales": ["ninetails", "ninetail", "ninetayles"],
    "arcanine": ["arkanine", "arcanin", "arcanien"],
    "machamp": ["machomp", "machampe", "matchamp"],
    "tentacruel": ["tentacrule", "tentacrool"],
    "rhydon": ["ridon", "rhaidon", "rydon"],
    "kangaskhan": ["kangaskan", "kangaskhann", "kangasken"],
    "starmie": ["starme", "starmy", "starmee"],
    "scyther": ["sycther", "scither", "sythe"],
    "jynx": ["jinx", "jynks"],
    "electabuzz": ["electrabuzz", "electabuz", "elektabuzz"],
    "lapras": ["lapris", "laprass", "lappras"],
    "porygon": ["porigon", "poligon", "porygone"],
    "articuno": ["articuna", "arcticuno", "articono"],
    "zapdos": ["zapdoss", "zabdos", "zapdose"],
    "moltres": ["moltress", "moltris", "moltras"],
    "dratini": ["dratiny", "dratinni", "dratine"],
    "weedle": ["weedel", "wedle", "weedl"],
    "pidgey": ["pidgy", "pidgie", "pigey"],
    "rattata": ["ratata", "rattatta", "rattatah"],
    "caterpie": ["caterpy", "caterpi", "caterpee"],
    "diglett": ["diglet", "digglet", "dyglett"],
    "meowth": ["meowt", "meouth", "miowth"],
    "slowpoke": ["slowpok", "slopoke", "slowpoak"],
    "gengar": ["genger", "gangar", "gengur"],
    "cubone": ["cubon", "cuebone", "kubone"],
    "marowak": ["marowack", "marowac", "marrowak"],
    "koffing": ["kofing", "koffin", "coffing"],
    "voltorb": ["voltorbe", "voltrob", "voltorp"],
    "chansey": ["chancey", "chansy", "chancy"],
    "tangela": ["tangella", "tanjela"],
    "ponyta": ["ponita", "poneyta", "ponytah"],
    "seadra": ["seedra", "sedra"],
    "goldeen": ["goldin", "goldene", "goldean"],
    "staryu": ["stariu", "staryou"],
    "aerodactyl": ["aerodactil", "areodactyl", "aerodactile"],
    "omanyte": ["omanite", "omanyt", "ommanyte"],
    "kabutops": ["kabutop", "kabootops", "kabutobs"],
    "zubat": ["zoubat", "zubbat", "zubatt"],
    "golbat": ["golbatt", "golbet"],
    "oddish": ["odish", "oddisch", "oddich"],
    "vileplume": ["vileplum", "vilplume", "vileplume e"],
    "bellsprout": ["belsprout", "bellsprot", "bellspout"],
    "tentacool": ["tentacoul", "tentakool"],
    "machop": ["matchop", "machopp"],
    "abra": ["abbra", "abrah"],
    "haunter": ["hauntr", "hawnter", "haunteur"],
    "hypno": ["hipno", "hypnoh"],
    "krabby": ["craby", "krabbi", "crabby"],
    "electrode": ["electrod", "elecktrode"],
    "lickitung": ["lickytung", "likitung", "lickitang"],
    "rhyhorn": ["ryhorn", "rhihorn", "rhyhorne"],
    "horsea": ["horsee", "horsia"],
    "magmar": ["magmer", "magmarr"],
    "pinsir": ["pinser", "pincir", "pinsyr"],
    "tauros": ["taurus", "toros", "tauross"],
    "vaporeon": ["vaporion", "vaporeonn", "vaperon"],
    "jolteon": ["joltion", "jolteonn", "joltean"],
    "flareon": ["flarion", "flaireon"],
}

# Semantic / very distant spellings: no string measure is expected to catch them.
HARD = {
    "butterfree": ["butterfly"],
    "mr-mime": ["mister mime"],
    "exeggutor": ["eggsecutor"],
    "koffing": ["coughing"],
    "kangaskhan": ["kangaroo"],
}

EDGE_SHOULD_FIND = [
    ("vulbasaur", "bulbasaur", "first letter wrong"),
    ("ublbasaur", "bulbasaur", "transposition at start"),
    ("bulbsor", "bulbasaur", "two typos"),
    ("bulbs", "bulbasaur", "short prefix + typo"),
    ("pikc", "pikachu", "short prefix + transposition"),
    ("charmad", "charmander", "prefix + typo"),
    ("bulbasaurr", "bulbasaur", "extra letter at the end"),
    ("pikachuu", "pikachu", "extra letter at the end"),
    ("mrmine", "mr-mime", "hyphenated name + typo"),
    ("nidorna", "nidorina", "close siblings (nidorina/nidorino)"),
    ("nidokng", "nidoking", "close siblings (nidoking/nidoqueen)"),
    ("mwe", "mew", "3-letter name, transposition"),
    ("mewtow", "mewtwo", "transposition at end"),
    ("onyx", "onix", "4-letter name, substitution"),
    ("jinx", "jynx", "4-letter name, substitution"),
    ("eve", "eevee", "very short, deletion"),
    ("pikachuuuu", "pikachu", "many repeated letters"),
    ("charzard", "charizard", "deletion in the middle"),
    ("charmeleom", "charmeleon", "last letter adjacent key"),
    ("raichu pikachu", "raichu", "two names typed"),
]

EDGE_REPORT_ONLY = ["bu", "pk", "mw", "ch", "sq", "zz", "a"]

NEGATIVES_WORDS = [
    "pokemon",
    "qwerty",
    "abcdef",
    "hello",
    "table",
    "computer",
    "zzzzzzzz",
    "aaaa",
    "test",
    "lorem",
    "ipsum",
    "banana",
    "kitchen",
    "monday",
    "office",
    "window",
    "python",
    "france",
    "wxyz",
    "xkcd",
    "keyboard",
    "summer",
    "yellow",
    "trainer",
    "battle",
    "garden",
    "music",
    "planet",
    "silver",
    "tomato",
]


def random_negatives(rng: random.Random, n: int) -> list[str]:
    letters = "abcdefghijklmnopqrstuvwxyz"
    return [
        "".join(rng.choice(letters) for _ in range(rng.randint(4, 9))) for _ in range(n)
    ]


# --------------------------------------------------------------- evaluation


def build_cases(names: dict[str, int], rng: random.Random) -> list[dict]:
    normalized_names = {normalize_name(n) for n in names}
    cases = []
    for name, pid in names.items():
        base = normalize_name(name)
        for kind in (
            "deletion",
            "insertion",
            "substitution",
            "transposition",
            "prefix_with_typo",
        ):
            for _ in range(10):  # retry until the typo is not another real name
                q = typo(base, kind, rng)
                if q not in normalized_names and q != base:
                    break
            cases.append({"query": q, "target": pid, "group": "standard", "kind": kind})
    for name, queries in HANDWRITTEN.items():
        for q in queries:
            cases.append(
                {
                    "query": q,
                    "target": names[name],
                    "group": "handwritten",
                    "kind": "phonetic",
                }
            )
    for name, queries in HARD.items():
        for q in queries:
            cases.append(
                {"query": q, "target": names[name], "group": "hard", "kind": "semantic"}
            )
    for q, name, label in EDGE_SHOULD_FIND:
        cases.append(
            {"query": q, "target": names[name], "group": "edge", "kind": label}
        )
    for q in NEGATIVES_WORDS:
        cases.append({"query": q, "target": None, "group": "negative", "kind": "word"})
    for q in random_negatives(rng, 40):
        cases.append(
            {"query": q, "target": None, "group": "negative", "kind": "random"}
        )
    return cases


def evaluate(cases, candidates, scorer, threshold):
    rows = []
    for case in cases:
        ranked = rank_candidates(
            case["query"], candidates, LIMIT, scorer=scorer, fuzzy_threshold=threshold
        )
        ids = [m.pokemon_id for m in ranked]
        fuzzy = [m for m in ranked if m.kind.value == "fuzzy"]
        rows.append(
            {
                **case,
                "hit1": case["target"] is not None and ids[:1] == [case["target"]],
                "hit5": case["target"] is not None and case["target"] in ids,
                "n_fuzzy": len(fuzzy),
                "n_results": len(ranked),
                "noise": sum(1 for m in fuzzy if m.pokemon_id != case["target"]),
                "top": [m.name for m in ranked[:3]],
            }
        )
    return rows


def summarize(rows):
    def rate(rs, key):
        return round(100 * sum(r[key] for r in rs) / len(rs), 1) if rs else None

    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)
    positives = [r for r in rows if r["target"] is not None and r["group"] != "hard"]
    negatives = by_group["negative"]
    return {
        "positives_hit1": rate(positives, "hit1"),
        "positives_hit5": rate(positives, "hit5"),
        "standard_hit1": rate(by_group["standard"], "hit1"),
        "standard_hit5": rate(by_group["standard"], "hit5"),
        "handwritten_hit1": rate(by_group["handwritten"], "hit1"),
        "handwritten_hit5": rate(by_group["handwritten"], "hit5"),
        "edge_hit1": rate(by_group["edge"], "hit1"),
        "edge_hit5": rate(by_group["edge"], "hit5"),
        "hard_hit5": rate(by_group["hard"], "hit5"),
        "negatives_false_positive": round(
            100 * sum(r["n_fuzzy"] > 0 for r in negatives) / len(negatives), 1
        ),
        "negatives_avg_fuzzy": round(
            statistics.mean(r["n_fuzzy"] for r in negatives), 2
        ),
        "positives_avg_noise": round(statistics.mean(r["noise"] for r in positives), 2),
    }


def raw_discrimination(cases, names_norm, fn):
    """Threshold-free: is the target the single best-scored name? And the
    score distributions of the target vs. the best score on negatives."""
    target_scores, best_wrong, top1 = [], [], 0
    pos = [c for c in cases if c["target"] is not None and c["group"] != "hard"]
    for c in pos:
        q = normalize_name(c["query"])
        scores = {pid: fn(q, n) for pid, n in names_norm.items()}
        target_scores.append(scores[c["target"]])
        top1 += max(scores, key=lambda p: (scores[p], -p)) == c["target"]
    for c in cases:
        if c["target"] is None:
            q = normalize_name(c["query"])
            best_wrong.append(max(fn(q, n) for n in names_norm.values()))
    q = statistics.quantiles
    return {
        "raw_top1": round(100 * top1 / len(pos), 1),
        "target_score_p10": round(q(target_scores, n=10)[0], 3),
        "target_score_median": round(statistics.median(target_scores), 3),
        "negative_best_median": round(statistics.median(best_wrong), 3),
        "negative_best_p90": round(q(best_wrong, n=10)[-1], 3),
        "negative_best_max": round(max(best_wrong), 3),
    }


def timing(candidates, names_norm, fn):
    # Worst case: no strict match, so all 151 names are fuzzy-scored.
    queries = ["zxqwvbnm", "bulbsor", "qqqqq", "vulbasaur"]
    raw_n = 300
    t0 = time.perf_counter()
    for _ in range(raw_n):
        for n in names_norm.values():
            fn("vulbasaur", n)
    per_151 = (time.perf_counter() - t0) / raw_n * 1000

    class NoCache:
        def score(self, q, n):
            return fn(q, n)

    t0 = time.perf_counter()
    for _ in range(100):
        for q in queries:
            rank_candidates(
                q, candidates, LIMIT, scorer=NoCache(), fuzzy_threshold=0.85
            )
    per_rank = (time.perf_counter() - t0) / (100 * len(queries)) * 1000
    return {
        "ms_151_scores": round(per_151, 3),
        "ms_rank_worst_case": round(per_rank, 3),
    }


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else "pokedex.json"
    output = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "benchmarks/results/fuzzy_name_matching.json"
    )
    with open(source, encoding="utf-8") as f:
        data = json.load(f)
    names = {p["name"]: p["id"] for p in data["pokemon"]}
    candidates = [NameCandidate(pid, name) for name, pid in names.items()]
    names_norm = {pid: normalize_name(name) for name, pid in names.items()}
    rng = random.Random(SEED)
    cases = build_cases(names, rng)

    counts = defaultdict(int)
    for c in cases:
        counts[c["group"]] += 1
    print("cases:", dict(counts), "total", len(cases))

    # Baseline: no scorer at all (strict tiers only).
    baseline = summarize(evaluate(cases, candidates, None, 1.0))
    print("baseline (no fuzzy):", baseline)

    results = {"cases": dict(counts), "baseline": baseline, "methods": {}}
    for method, fn in SCORERS.items():
        scorer = CachedScorer(fn, {})
        sweep = {}
        for t in THRESHOLDS:
            sweep[t] = summarize(evaluate(cases, candidates, scorer, t))
        results["methods"][method] = {
            "sweep": sweep,
            "raw": raw_discrimination(cases, names_norm, fn),
            "timing": timing(candidates, names_norm, fn),
        }
        print("done", method, file=sys.stderr)

    # Per-case detail at each method's chosen threshold, kept for the report.
    results["detail"] = {}
    for method, fn in SCORERS.items():
        sweep = results["methods"][method]["sweep"]
        # Best positives_hit5 with <= 5% false positives on negatives.
        ok = [t for t in THRESHOLDS if sweep[t]["negatives_false_positive"] <= 5.0]
        best_t = (
            max(
                ok,
                key=lambda t: (
                    sweep[t]["positives_hit5"],
                    sweep[t]["positives_hit1"],
                    -t,
                ),
            )
            if ok
            else 0.95
        )
        results["methods"][method]["chosen_threshold"] = best_t
        rows = evaluate(cases, candidates, CachedScorer(fn, {}), best_t)
        by_kind = defaultdict(list)
        for r in rows:
            by_kind[(r["group"], r["kind"])].append(r)
        results["detail"][method] = {
            "by_kind": {
                f"{g}/{k}": {
                    "n": len(rs),
                    "hit1": round(100 * sum(r["hit1"] for r in rs) / len(rs), 1),
                    "hit5": round(100 * sum(r["hit5"] for r in rs) / len(rs), 1),
                    "fp": round(100 * sum(r["n_fuzzy"] > 0 for r in rs) / len(rs), 1),
                }
                for (g, k), rs in sorted(by_kind.items())
            },
            "edge": [
                {
                    "query": r["query"],
                    "kind": r["kind"],
                    "hit1": r["hit1"],
                    "hit5": r["hit5"],
                    "top": r["top"],
                }
                for r in rows
                if r["group"] == "edge"
            ],
            "short": {
                q: [
                    m.name
                    for m in rank_candidates(
                        q,
                        candidates,
                        LIMIT,
                        scorer=CachedScorer(fn, {}),
                        fuzzy_threshold=best_t,
                    )
                ]
                for q in EDGE_REPORT_ONLY
            },
            "negatives_hit": [
                {"query": r["query"], "top": r["top"]}
                for r in rows
                if r["group"] == "negative" and r["n_fuzzy"] > 0
            ],
            "misses": [
                {
                    "query": r["query"],
                    "group": r["group"],
                    "kind": r["kind"],
                    "top": r["top"],
                }
                for r in rows
                if r["target"] is not None
                and not r["hit5"]
                and r["group"] in ("handwritten", "edge")
            ],
        }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, default=str, ensure_ascii=False)
    print("results written to", output)


if __name__ == "__main__":
    main()
