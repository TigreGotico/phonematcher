"""Score the pre-registered weight candidates once on the Spanish word-in-noise confusions.

Data: Tóth, García Lecumberri, Tang and Cooke (2015), "A corpus of noise-induced word
misperceptions for Spanish", JASA 137(2), EL184-EL189; Zenodo 3521449, CC BY 4.0. Pass the path
of its ``confusionsCorpus.csv``.

Each row gives a target word and the word listeners reported, in IPA, and how many listeners
reported it (the Consistency column). The two are aligned by an edit distance with unit costs,
which does not depend on any candidate. The corpus writes ASCII g, an untied tʃ and the ligature ʤ;
these read as ɡ, t͡ʃ and d͡ʒ. Every aligned substitution adds the listener count to its pair of segments. A candidate
scores the Spearman correlation between the negative distance of a pair and its count, over all
pairs of segments in the targets.

The candidates and the constraints were fixed before the data was read: C0 the table's weights,
C1 equal weights, C2 equal weights with each multi-feature scale at one unit, C3 C2 with the
major-class features at the least weight that passes K1. K1: two chart vowels are nearer each other
than a chart vowel and an obstruent. K2: at sensitivity 0.1, i is clustered with neither a nor u.

    python scripts/score_candidates.py confusionsCorpus.csv
"""
import csv
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import phonematcher.features as features  # noqa: E402
from phonematcher.clustering import phone_clusters, upgma  # noqa: E402

CHART = Path(__file__).resolve().parent / "sources" / "ipa-vowel-chart.csv"
OBSTRUENTS = "pbtdkɡqʔfvszʃʒxχh"
SPELLING = {"g": "ɡ", "tʃ": "t͡ʃ", "ʤ": "d͡ʒ"}


def substitutions(path: Path) -> tuple:
    """Listener-weighted substitution counts per unordered segment pair, and the segments."""
    counts: Counter = Counter()
    inventory = set()
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            target = [SPELLING.get(s, s) for s in row["Target-IPA"].split() if s not in "!."]
            heard = [SPELLING.get(s, s) for s in row["Confusion-IPA"].split() if s not in "!."]
            inventory.update(target)
            for a, b in align(target, heard):
                if a != b:
                    counts[min(a, b), max(a, b)] += int(row["Consistency"])
    return counts, sorted(inventory)


def align(a, b):
    """The substitutions of one unit-cost alignment of *a* and *b*, chosen deterministically."""
    rows = [[max(i, j) if not i * j else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1,
                             rows[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    pairs, i, j = [], len(a), len(b)
    while i and j:
        if rows[i][j] == rows[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            pairs.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif rows[i][j] == rows[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return pairs


def with_weights(weights, fn):
    saved = features.WEIGHTS
    features.WEIGHTS = tuple(weights)
    try:
        return fn()
    finally:
        features.WEIGHTS = saved


def passes_k1() -> bool:
    vowels = [r["symbol"] for r in csv.DictReader(open(CHART, encoding="utf-8"))]
    widest = max(features.phonetic_distance(a, b) for a, b in combinations(vowels, 2))
    return widest < min(features.phonetic_distance(v, o) for v in vowels for o in OBSTRUENTS)


def passes_k2() -> bool:
    clusters = upgma(sorted(phone_clusters(0.1)), 0.1)
    return clusters["i"] != clusters["a"] and clusters["i"] != clusters["u"]


def main(path: Path) -> None:
    counts, inventory = substitutions(path)
    pairs = [p for p in combinations(inventory, 2)]
    print(f"{len(inventory)} segments, {len(pairs)} pairs, "
          f"{sum(1 for p in pairs if counts[p])} with a substitution")
    names = features.FEATURES
    scale = {"h1", "h2", "h3", "h4", "h5", "h6"}
    halves = {"front", "back", "round", "lab"}
    c2 = [1 / 6 if f in scale else 0.5 if f in halves else 1.0 for f in names]

    def c3_weight() -> float:
        low, high = 1.0, 10.0
        while high - low > 0.01:
            mid = (low + high) / 2
            w = [mid if f in ("syl", "son", "cons") else x for f, x in zip(names, c2)]
            low, high = (low, mid) if with_weights(w, passes_k1) else (mid, high)
        return round(high, 2)

    major = c3_weight()
    candidates = {"C0": features.WEIGHTS, "C1": [1.0] * len(names), "C2": c2,
                  "C3": [major if f in ("syl", "son", "cons") else x for f, x in zip(names, c2)]}
    print(f"C3 major-class weight: {major}")
    for name, weights in candidates.items():
        def run():
            distances = [-features.phonetic_distance(a, b) for a, b in pairs]
            return spearmanr(distances, [counts[p] for p in pairs]).statistic, passes_k1(), \
                passes_k2()
        rho, k1, k2 = with_weights(weights, run)
        print(f"{name}: Spanish {rho:.4f}  K1 {k1}  K2 {k2}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
