"""Tone weights: the cognate task on the dev split with the weights of the four tone features set to each pair of a grid.

    python benchmarks/run.py --task tone-weights --system tone-weights --split dev

The systems are ``pm-p5-tone-standalone`` (a tone is a segment of its own) and ``pm-p5-tone-W-P``
(``tone_is`` weighs W and each of the three pitches P), all on the shipped P5 costs. The result keeps,
for each system, the mean average precision and mean B-cubed F over the six training word lists, and the
average precision of the Chinese list.
"""
from pathlib import Path
from typing import List

from systems import System
from tasks import cognates

SPLITS = ("dev",)
CHINESE = "Chinese-140-15"


def run(systems: List[System], split: str, cache: Path) -> dict:
    payload = cognates.run(systems, split, cache)
    rows = {}
    for name, entry in payload["systems"].items():
        scored = entry["unread_at_1"]
        rows[name] = {
            "average_precision": scored["average_precision"]["mean"],
            "bcubed_f": scored["bcubed_f"]["mean"],
            "chinese_average_precision": scored["average_precision"][CHINESE],
        }
    return {"source": payload["source"], "datasets": payload["datasets"], "systems": rows}


def lines(payload: dict) -> List[str]:
    return [f"{name}: AP {row['average_precision']:.4f} F {row['bcubed_f']:.4f} Chinese AP {row['chinese_average_precision']:.4f}"
            for name, row in payload["systems"].items()]
