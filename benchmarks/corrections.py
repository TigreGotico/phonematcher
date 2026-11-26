"""Paired dev scores of the shipped library against an earlier library, unit by unit.

    python benchmarks/corrections.py --out benchmarks/results/ablations/corrections-dev.json

The "before" library is the package at ``BEFORE_LIBRARY`` with the benchmark code of
``BEFORE_BENCHMARKS``. Both are unpacked from git into a scratch directory. The "after" library is
this tree. Each library scores the same units on the dev split: the concepts of the six cognate
training word lists, the alignment pairs that both libraries read, and the sample of 500 queries of
each retrieval pair. The paired bootstrap uses 1,000 resamples with seed 0, as ``final.py`` does.

    python benchmarks/corrections.py units ROOT OUT.pkl

writes the per-unit scores of the library and the benchmark code in ROOT.
"""
import argparse
import json
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_CACHE = Path.home() / ".cache" / "phonematcher-bench"
BEFORE_LIBRARY = "cd2996a"
BEFORE_BENCHMARKS = "100ff08"
RULE = "adopt unless a dev paired 95% interval (1,000 resamples, seed 0) lies wholly below 0"
TASKS = {"cognates": "cognates_ap", "alignment": "alignment_pas", "retrieval": "retrieval_recall@1"}


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def units(root: Path, cache: Path) -> dict:
    """Per-unit dev scores of phonematcher as the library and the benchmark code in *root* give them."""
    sys.path[:0] = [str(root), str(root / "benchmarks")]
    import phonematcher

    assert phonematcher.__file__.startswith(str(root)), phonematcher.__file__
    from systems import build
    from tasks import alignment, cognates, retrieval

    system = build("phonematcher", cache)
    out = {"library": phonematcher.__file__}
    payload, sets = cognates.score([system], "dev", cache, final=True, limit=0)
    out["cognates"] = {n: [cognates.pair_scores([c], skip_unread=False)[:2] for c in sets["phonematcher"][n]] for n in payload["datasets"]}
    _, per = alignment.score(["phonematcher"], cache, "dev", 0)
    out["alignment"] = {k: v[0] if v is not None else None for k, v in per["phonematcher"].items()}
    rows = {p: retrieval.run_pair(system, p, cache, "dev", retrieval.SAMPLE_SIZE)["brute"] for p in retrieval.PAIRS}
    out["retrieval"] = {p: (list(r["index"]), [retrieval.recall_at(1, s, t) for s, t in zip(r["s"], r["t"])]) for p, r in rows.items()}
    return out


def paired(before: dict, after: dict) -> dict:
    """The paired bootstrap of the three tasks; "after" minus "before" on the same units."""
    import final

    def bootstrap(metrics: dict, strata: List[int]) -> dict:
        res = final.paired_bootstrap(metrics, strata, "before")
        return {"estimates": res["systems"], "paired": res["paired"]}

    out = {}
    names = list(after["cognates"])
    assert list(before["cognates"]) == names
    assert all(len(before["cognates"][n]) == len(after["cognates"][n]) for n in names)
    strata = [len(after["cognates"][n]) for n in names]
    metrics = {s: final.cognate_metric([d["cognates"][n] for n in names]) for s, d in (("before", before), ("after", after))}
    out["cognates"] = {"unit": "concept", "units": sum(strata), **bootstrap(metrics, strata)}

    keys = [k for k, v in after["alignment"].items() if v is not None and before["alignment"].get(k) is not None]
    metrics = {s: final.stratified_mean([np.array([d["alignment"][k] for k in keys])]) for s, d in (("before", before), ("after", after))}
    out["alignment"] = {"unit": "pair both read", "units": len(keys), **bootstrap(metrics, [len(keys)])}

    pairs = list(after["retrieval"])
    assert all(before["retrieval"][p][0] == after["retrieval"][p][0] for p in pairs)
    strata = [len(after["retrieval"][p][1]) for p in pairs]
    metrics = {s: final.stratified_mean([np.array(d["retrieval"][p][1]) for p in pairs]) for s, d in (("before", before), ("after", after))}
    out["retrieval"] = {"unit": "query", "units": sum(strata), **bootstrap(metrics, strata)}
    return out


def record(before: dict, after: dict) -> dict:
    result = paired(before, after)
    return {
        "about": "phonematcher on dev, the library of 'before' against the shipped library of 'after', scored unit by unit on the same units. "
        "Each 'before' and 'after' value is the mean of the units of its task, as 'paired' lists them.",
        "before": {"library": BEFORE_LIBRARY, "benchmarks": BEFORE_BENCHMARKS,
                   **{key: result[task]["estimates"]["before"]["estimate"] for task, key in TASKS.items()}},
        "after": {"head": git("rev-parse", "HEAD"), "tree_dirty": bool(git("status", "--porcelain")),
                  **{key: result[task]["estimates"]["after"]["estimate"] for task, key in TASKS.items()}},
        "paired": result,
        "rule": RULE,
        "adopted": all(result[task]["paired"]["after"]["high"] >= 0 for task in TASKS),
    }


def score_before_and_after(cache: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="pm-corrections-") as scratch:
        old = Path(scratch) / "before"
        old.mkdir()
        for commit, path in ((BEFORE_LIBRARY, "phonematcher"), (BEFORE_BENCHMARKS, "benchmarks")):
            archive = subprocess.run(["git", "archive", commit, path], cwd=ROOT, capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(old)], input=archive, check=True)
        found = {}
        for label, root in (("before", old), ("after", ROOT)):
            out = Path(scratch) / f"{label}.pkl"
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "units", str(root), str(out), "--cache", str(cache)], check=True)
            found[label] = pickle.loads(out.read_bytes())
    return found


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", nargs="?", choices=["units"])
    parser.add_argument("args", nargs="*")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.command == "units":
        root, out = Path(args.args[0]).resolve(), Path(args.args[1])
        result = units(root, args.cache)
        out.write_bytes(pickle.dumps(result))
        print({k: len(v) for k, v in result.items() if k != "library"})
        return 0
    found = score_before_and_after(args.cache)
    text = json.dumps(record(found["before"], found["after"]), indent=1) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf8")
        print(f"wrote {args.out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
