"""Ablations: the variants of ``benchmarks/variants.py`` and phonematcher on the seen or dev tasks.

    python benchmarks/run.py --task ablations --system variants --split seen
    python benchmarks/run.py --task ablations --system variants --split dev

The ``seen`` split holds coverage, allophones and confusions, with the control of ``pm-panphon22``
against ``panphon-weighted``. The ``dev`` split holds cognates, toneless cognates, alignment and
retrieval. Retrieval scores every system by brute force on the fixed sample of 500 queries per
language pair that the SCA row uses, and does not run the fuzzy search.
"""
from pathlib import Path
from typing import List

from systems import System
from tasks import alignment, allophones, cognates, cognates_toneless, confusions, coverage, retrieval

SPLITS = ("seen", "dev")
SAMPLE = retrieval.SAMPLE_SIZE


def retrieval_payload(systems: List[System], split: str, cache: Path) -> dict:
    for system in systems:
        for name in retrieval.PAIRS:
            retrieval.run_pair(system, name, cache, split, SAMPLE)
    return retrieval.aggregate(cache, split, [system.name for system in systems])


def run(systems: List[System], split: str, cache: Path) -> dict:
    import variants

    names = [system.name for system in systems]
    if split == "seen":
        tasks = {
            "coverage": coverage.run(systems, split, cache),
            "allophones": allophones.run(systems, split, cache),
            "confusions": confusions.run(systems, split, cache),
        }
        extra = {"control": variants.control(cache)}
    else:
        tasks = {
            "cognates": cognates.run(systems, split, cache),
            "cognates-toneless": cognates_toneless.run(systems, split, cache),
            "alignment": alignment.run(names, cache, split),
            "retrieval": retrieval_payload(systems, split, cache),
        }
        extra = {}
    return {"systems": names, "tasks": tasks, **extra}


def lines(payload: dict) -> List[str]:
    out = []
    for task, module in (("coverage", coverage), ("allophones", allophones), ("confusions", confusions),
                         ("cognates", cognates), ("cognates-toneless", cognates_toneless), ("retrieval", retrieval)):
        if task in payload["tasks"]:
            out += [f"[{task}] {line}" for line in module.lines(payload["tasks"][task])]
    if "alignment" in payload["tasks"]:
        for name, row in payload["tasks"]["alignment"]["all"]["systems"].items():
            out.append(f"[alignment] {name}: n_in={row['n_in']} scored={row['n_scored']} "
                       f"common PAS={row['common_pas']:.4f} CS={row['common_cs']:.4f}")
    if "control" in payload:
        c = payload["control"]
        out.append(f"[control] pairs={c['pairs_compared']} differing={c['pairs_differing']} "
                   f"identical-vector pairs={c['identical_vector_pairs']} differing={c['identical_vector_pairs_differing']}")
    return out
