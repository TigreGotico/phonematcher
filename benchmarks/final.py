"""The single pre-registered test run: bootstrap, candidates, decision rules.

``benchmarks/prereg-2.md`` fixes the systems, metrics and rules. ``run.py --final`` calls
:func:`run_final` for the cognate, alignment and retrieval tasks. ``--dry-run`` walks the same path
on the dev split, with a cap on the units, and writes nothing to ``benchmarks/results``.

    python benchmarks/final.py decide        # rules 1 to 5 on the three test result files
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import variants  # noqa: E402
from systems import NAMES, System, build  # noqa: E402
from tasks import alignment, cognates, retrieval  # noqa: E402

HERE = Path(__file__).resolve().parent
PREREG = HERE / "prereg-2.md"
PREREG_SHA256 = "29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c"
#: the system every candidate is paired with. The test result files were written when the
#: library used the C0 costs, so their baseline row is named ``phonematcher``.
BASELINE = variants.C0
RESAMPLES = 1000
SEED = 0
TASKS = ("cognates", "alignment", "retrieval")
#: the main metric and the bootstrap unit of each task, as ``prereg-2.md`` states them
MAIN = {
    "cognates": ("mean average precision over the test sets, tones kept, unread pairs at distance 1", "concept"),
    "alignment": ("perfect-alignment score on the pairs every aligning system reads", "pair"),
    "retrieval": ("mean over the dialect pairs of brute-force recall@1, unread at distance 1", "query"),
}

Metric = Callable[[np.ndarray], float]


def prereg_sha256() -> str:
    """The sha256 of ``prereg-2.md``. Raises ``SystemExit`` when it is not the registered value."""
    found = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    if found != PREREG_SHA256:
        raise SystemExit(f"{PREREG} has sha256 {found}, not the registered {PREREG_SHA256}")
    return found


def final_names() -> List[str]:
    """Every system of the test run: the seven systems, C0, the C10 variants and the candidates."""
    return [*NAMES, variants.C0, *variants.NAMES, *variants.CANDIDATES]


def interval(values: np.ndarray) -> Dict[str, float]:
    low, high = np.percentile(values, [2.5, 97.5])
    return {"low": float(low), "high": float(high)}


def paired_bootstrap(
    metrics: Dict[str, Metric],
    strata: Sequence[int],
    baseline: Optional[str] = None,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> dict:
    """Bootstrap intervals of several systems scored on the same units.

    The units are numbered 0 to ``sum(strata) - 1``; stratum k holds ``strata[k]`` consecutive
    units, and each resample draws ``strata[k]`` units with replacement from stratum k. Every system
    sees the same draws. A metric takes the drawn unit numbers, stratum by stratum, and returns
    the score. Returns ``systems`` (the score on all units and its 95% interval) and, when a
    *baseline* is given, ``paired``: each other system's score minus the baseline's, with its interval.
    """
    rng = np.random.default_rng(seed)
    offsets = np.cumsum([0, *strata[:-1]])
    draws = [np.concatenate([o + rng.integers(0, n, n) for o, n in zip(offsets, strata)]) for _ in range(resamples)]
    everything = np.arange(sum(strata))
    estimate = {name: float(metric(everything)) for name, metric in metrics.items()}
    resampled = {name: np.array([metric(d) for d in draws]) for name, metric in metrics.items()}
    out = {"systems": {name: {"estimate": estimate[name], **interval(resampled[name])} for name in metrics}}
    if baseline is not None:
        out["paired"] = {
            name: {"diff": estimate[name] - estimate[baseline], **interval(resampled[name] - resampled[baseline])}
            for name in metrics
            if name != baseline
        }
    return out


def stratified_mean(values: Sequence[np.ndarray]) -> Metric:
    """The mean over strata of the mean of each stratum's drawn units; *values* holds one array of
    per-unit scores for each stratum."""
    sizes = np.cumsum([len(v) for v in values])[:-1]

    def metric(picks: np.ndarray) -> float:
        parts = np.split(picks, sizes)
        return float(np.mean([v[p - start].mean() for v, p, start in zip(values, parts, [0, *sizes])]))

    return metric


def cognate_metric(sets: Sequence[Sequence[Tuple[np.ndarray, np.ndarray]]]) -> Metric:
    """Mean over data sets of the average precision of the pairs of the drawn concepts; *sets* holds,
    for each data set, the ``(scores, same-cognate labels)`` of every concept."""
    sizes = np.cumsum([len(s) for s in sets])[:-1]

    def metric(picks: np.ndarray) -> float:
        parts = np.split(picks, sizes)
        aps = []
        for concepts, p, start in zip(sets, parts, [0, *sizes]):
            chosen = [concepts[i - start] for i in p]
            aps.append(cognates.average_precision(np.concatenate([s for s, _ in chosen]), np.concatenate([l for _, l in chosen])))
        return float(np.mean(aps))

    return metric


def candidate_table() -> Dict[str, dict]:
    """Per candidate id (``C1`` to ``P5``): its system name and whether it passes K1 (rule 1)."""
    table = {name.removeprefix("pm-"): {"system": name, "k1": variants.k1(variants.build_variant(name))} for name in variants.CANDIDATES}
    table["C3"]["major_class_weight"] = variants.c3_weight()
    return table


def decide(results: Dict[str, dict]) -> dict:
    """Rules 1 to 5 of ``prereg-2.md``.

    *results* maps a candidate id to ``{"k1": bool, "cognates": d, "alignment": d, "retrieval": d}``
    where each ``d`` holds ``diff``, ``low`` and ``high`` of the paired difference to C0 on that
    task's main metric. Returns the ``winner`` (a candidate id or ``C0``), the candidates that
    ``beating`` C0, and the ``reasons`` as one line per candidate and one for the outcome.
    """
    beating, reasons = [], []
    for name, r in results.items():
        if not r["k1"]:
            reasons.append(f"{name}: out by rule 1, K1 fails")
            continue
        c4, c5, c6 = r["cognates"], r["alignment"], r["retrieval"]
        faults = []
        if not c4["low"] > 0:
            faults.append(f"C4 lower bound {c4['low']:.4f} is not above 0")
        if not c6["low"] > 0:
            faults.append(f"C6 lower bound {c6['low']:.4f} is not above 0")
        if c5["high"] < 0:
            faults.append(f"C5 upper bound {c5['high']:.4f} is below 0")
        if faults:
            reasons.append(f"{name}: does not beat C0 (rule 3): " + "; ".join(faults))
        else:
            beating.append(name)
            reasons.append(f"{name}: beats C0 (C4 {c4['diff']:+.4f}, C5 {c5['diff']:+.4f}, C6 {c6['diff']:+.4f})")
    if not beating:
        reasons.append("no candidate beats C0 (rule 5): the weights and the gap cost stay")
        return {"winner": "C0", "beating": [], "reasons": reasons}
    best = max(round(results[n]["cognates"]["diff"], 4) for n in beating)
    tied = [n for n in beating if round(results[n]["cognates"]["diff"], 4) == best]
    winner = max(tied, key=lambda n: results[n]["retrieval"]["diff"])
    if len(beating) == 1:
        reasons.append(f"{winner} is the only candidate that beats C0")
    elif len(tied) == 1:
        reasons.append(f"{winner} has the largest C4 difference of {len(beating)} candidates that beat C0 (rule 4)")
    else:
        reasons.append(f"{' and '.join(tied)} tie on C4 at four decimals; {winner} has the larger C6 difference (rule 4)")
    return {"winner": winner, "beating": beating, "reasons": reasons}


def decision_input(directory: Path) -> Dict[str, dict]:
    """The input of :func:`decide` from the three test result files in *directory*."""
    files = {task: json.loads((directory / f"{task}-test.json").read_text(encoding="utf8")) for task in TASKS}
    out = {}
    for name, row in files["cognates"]["candidates"].items():
        out[name] = {"k1": row["k1"], **{task: files[task]["paired"][row["system"]] for task in TASKS}}
    return out


def _bootstrap_groups(groups: Dict[object, Tuple[List[str], Dict[str, Metric], Sequence[int]]]) -> Tuple[dict, dict]:
    """Run :func:`paired_bootstrap` once per group of systems that share units; the baseline pairs
    with the systems of its own group."""
    intervals: dict = {}
    paired: dict = {}
    for _, metrics, strata in groups.values():
        out = paired_bootstrap(metrics, strata, BASELINE if BASELINE in metrics else None)
        intervals.update(out["systems"])
        paired.update(out.get("paired", {}))
    return intervals, paired


def cognates_final(systems: List[System], split: str, cache: Path, limit: int) -> Tuple[dict, dict, dict]:
    payload, sets = cognates.score(systems, split, cache, final=True, limit=limit)
    names = payload["datasets"]
    metrics, strata = {}, None
    for system in systems:
        per_set = [[cognates.pair_scores([c], skip_unread=False)[:2] for c in sets[system.name][n]] for n in names]
        shape = [len(s) for s in per_set]
        assert strata in (None, shape), f"{system.name} has other concepts than the first system"
        strata = shape
        metrics[system.name] = cognate_metric(per_set)
    return payload, {"all": (list(metrics), metrics, strata)}, {n: payload["systems"][n]["unread_at_1"]["average_precision"]["mean"] for n in metrics}


def alignment_final(systems: List[System], split: str, cache: Path, limit: int) -> Tuple[dict, dict, dict]:
    names = [s.name for s in systems if type(s)._align is not System._align]
    payload, per_system = alignment.score(names, cache, split, limit)
    keys = [k for k in next(iter(per_system.values())) if all(per_system[n][k] is not None for n in names)]
    metrics = {n: stratified_mean([np.array([per_system[n][k][0] for k in keys])]) for n in names}
    return payload, {"all": (names, metrics, [len(keys)])}, {n: payload["all"]["systems"][n]["common_pas"] for n in names}


def retrieval_final(systems: List[System], split: str, cache: Path, limit: int) -> Tuple[dict, dict, dict]:
    """Full query sets for the systems of the decision, the fixed samples of ``retrieval.SLOW`` for
    ALINE and SCA, and the ablation sample for the C10 variants."""
    records = {}
    for system in systems:
        size = limit or retrieval.SLOW.get(system.name) or (retrieval.SAMPLE_SIZE if system.name in variants.NAMES else 0)
        for pair in retrieval.PAIRS:
            records[system.name, pair] = retrieval.run_pair(system, pair, cache, split, size)
    payload = retrieval.aggregate(cache, split, [s.name for s in systems])
    groups: dict = {}
    for system in systems:
        rows = [records[system.name, pair]["brute"] for pair in retrieval.PAIRS]
        values = [np.array([retrieval.recall_at(1, s, t) for s, t in zip(r["s"], r["t"])]) for r in rows]
        key = tuple(tuple(r["index"]) for r in rows)
        names, metrics, strata = groups.setdefault(key, ([], {}, [len(v) for v in values]))
        names.append(system.name)
        metrics[system.name] = stratified_mean(values)
    expected = {
        n: float(np.mean([payload["pairs"][p]["systems"][n]["all_items_unread_at_1"]["recall@1"] for p in retrieval.PAIRS]))
        for n in (s.name for s in systems)
    }
    return payload, groups, expected


ADAPTERS = {"cognates": cognates_final, "alignment": alignment_final, "retrieval": retrieval_final}


def run_final(task: str, cache: Path, split: str, limit: int = 0) -> dict:
    """Score every system and candidate on one task and bootstrap the main metric. Returns the
    result record; the caller writes it. *limit* caps the units, for the dry run on dev."""
    sha = prereg_sha256()
    systems = [build(name, cache) for name in final_names()]
    payload, groups, expected = ADAPTERS[task](systems, split, cache, limit)
    intervals, paired = _bootstrap_groups(groups)
    for name, value in expected.items():
        assert abs(intervals[name]["estimate"] - value) < 1e-9, (name, intervals[name]["estimate"], value)
    metric, unit = MAIN[task]
    return {
        **payload,
        "prereg_sha256": sha,
        "main_metric": metric,
        "unit": unit,
        "units_by_stratum": next(strata for _, metrics, strata in groups.values() if BASELINE in metrics),
        "resamples": RESAMPLES,
        "seed": SEED,
        "candidates": candidate_table(),
        "intervals": intervals,
        "paired": paired,
        "systems_in": len(systems),
    }


def report(task: str, split: str, record: dict) -> List[str]:
    """The printed summary of a result record: one line per system and per paired difference."""
    lines = [f"{task} {split}: {record['main_metric']}; {record['systems_in']} systems in, {len(record['intervals'])} scored"]
    lines += [f"{n}: {i['estimate']:.4f} [{i['low']:.4f}, {i['high']:.4f}]" for n, i in record["intervals"].items()]
    lines += [f"{n} - {BASELINE}: {p['diff']:+.4f} [{p['low']:+.4f}, {p['high']:+.4f}]" for n, p in record["paired"].items()]
    lines.append(f"units per stratum {record['units_by_stratum']}; prereg sha256 {record['prereg_sha256']}")
    lines.append("candidates " + json.dumps(record["candidates"], ensure_ascii=False))
    return lines


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["decide"])
    parser.add_argument("--results", type=Path, default=HERE / "results")
    args = parser.parse_args(argv)
    outcome = decide(decision_input(args.results))
    print("\n".join(outcome["reasons"]))
    print(f"winner: {outcome['winner']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
