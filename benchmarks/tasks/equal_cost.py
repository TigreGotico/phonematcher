"""Equal costs: the feature baselines at the shipped costs of phonematcher, on the dev split.

    python benchmarks/run.py --task equal-cost --system equal-cost --split dev

The test run gave the feature baselines a gap of 1 and linear substitutions, and gave only
phonematcher the candidates with a gap of 0.5 and a square-root substitution. This task runs
``panphon-weighted`` and ``soundvectors`` beside ``panphon-weighted-p5`` and ``soundvectors-p5``,
which take the shipped costs, and beside ``pm-C0`` and ``phonematcher``, the table at the two cost
rules. Cognates, alignment and retrieval run on the dev split. Retrieval scores every system by
brute force on the fixed sample of 500 queries per language pair, as the ablations do.
"""
from pathlib import Path
from typing import List

from systems import System
from tasks import alignment, cognates, retrieval

SPLITS = ("dev",)
#: the systems of the comparison, in the order of the table
SYSTEMS = ["levenshtein", "pm-C0", "phonematcher", "panphon-weighted", "panphon-weighted-p5", "soundvectors", "soundvectors-p5"]


def run(systems: List[System], split: str, cache: Path) -> dict:
    names = [system.name for system in systems]
    for system in systems:
        for pair in retrieval.PAIRS:
            retrieval.run_pair(system, pair, cache, split, retrieval.SAMPLE_SIZE)
    tasks = {
        "cognates": cognates.run(systems, split, cache),
        "alignment": alignment.run(names, cache, split),
        "retrieval": retrieval.aggregate(cache, split, names),
    }
    return {"systems": names, "tasks": tasks}


def lines(payload: dict) -> List[str]:
    out = []
    for name, entry in payload["tasks"]["cognates"]["systems"].items():
        out.append(f"[cognates] {name}: AP all words {entry['unread_at_1']['average_precision']['mean']:.4f} "
                   f"AP common words {entry['common']['average_precision']['mean']:.4f}")
    for name, row in payload["tasks"]["alignment"]["all"]["systems"].items():
        out.append(f"[alignment] {name}: scored={row['n_scored']} common PAS={row['common_pas']:.4f} CS={row['common_cs']:.4f}")
    out += [f"[retrieval] {line}" for line in retrieval.lines(payload["tasks"]["retrieval"])]
    return out
