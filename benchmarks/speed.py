"""Task C8, speed: segment distances, ``ipa_distance`` and the fuzzy search, timed.

    python benchmarks/speed.py --cache ~/.cache/phonematcher-bench --runs 3 --out benchmarks/results/speed.json

The segment set is the letters and tied affricates that ``phone_clusters`` clusters. The distance
of every ordered pair of them, diagonal included, is timed once per run, and the ``repr`` of every
float is hashed, so a later change can show that the matrix is bit-identical. WikiPron pairs and
index terms come from the broad files that task C6 downloads into ``CACHE/C6``.
"""
import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from phonematcher import PhoneticFuzzySearch, ipa_distance, phonetic_distance  # noqa: E402
from phonematcher.clustering import phone_clusters  # noqa: E402
from phonematcher.features import vectorize_phones  # noqa: E402

SEED = 0
IPA_PAIRS = 10000
INDEX_TERMS = 100000
QUERIES = 1000
SENSITIVITIES = (0.05, 0.1)
INDEX_FILE = "eng_latn_us_broad"
QUERY_FILE = "eng_latn_uk_broad"


def letters() -> List[str]:
    """The letters and tied affricates of the phone table, sorted."""
    return sorted(phone_clusters(0.1))


def matrix_hash(segments: Sequence[str], distance: Callable[[str, str], float]) -> str:
    """SHA-256 of ``a TAB b TAB repr(distance(a, b))`` for every ordered pair, one per line."""
    digest = hashlib.sha256()
    for a in segments:
        for b in segments:
            digest.update(f"{a}\t{b}\t{distance(a, b)!r}\n".encode("utf8"))
    return digest.hexdigest()


def time_pairs(segments: Sequence[str], distance: Callable[[str, str], float]) -> Tuple[int, float]:
    """The pair count and the seconds one pass over every ordered pair takes."""
    start = time.perf_counter()
    for a in segments:
        for b in segments:
            distance(a, b)
    return len(segments) ** 2, time.perf_counter() - start


def read_prons(path: Path) -> List[str]:
    """Column 2 of a WikiPron file with the spaces removed, in file order, rows without a pronunciation skipped."""
    out = []
    with open(path, encoding="utf8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 2 and parts[1].strip():
                out.append(parts[1].replace(" ", ""))
    return out


def pick_pairs(pool: Sequence[str], count: int, seed: int = SEED) -> List[Tuple[str, str]]:
    """*count* pairs of two distinct positions of *pool*, drawn with ``random.Random(seed)``."""
    rng = random.Random(seed)
    return [tuple(pool[i] for i in rng.sample(range(len(pool)), 2)) for _ in range(count)]


def time_search(terms: Sequence[str], queries: Sequence[str], sensitivity: float) -> Dict[str, float]:
    """Index build seconds for *terms* and queries per second for *queries* (10 results each)."""
    start = time.perf_counter()
    index = PhoneticFuzzySearch(sensitivity)
    for i, term in enumerate(terms):
        index.add_term(term, i)
    build = time.perf_counter() - start
    start = time.perf_counter()
    for query in queries:
        index.search(query)
    return {"build_seconds": build, "queries_per_second": len(queries) / (time.perf_counter() - start)}


def machine() -> Dict[str, object]:
    model = next((l.split(":", 1)[1].strip() for l in subprocess.run(
        ["lscpu"], capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"}).stdout.splitlines() if l.startswith("Model name")), "?")
    return {"cpu": model, "cores": os.cpu_count(), "python": platform.python_version()}


def load_average() -> str:
    return Path("/proc/loadavg").read_text().split()[0]


def one_run(cache: Path) -> Dict[str, object]:
    folder = cache / "C6"
    segs = letters()
    for seg in segs:
        vectorize_phones(seg)
    record: Dict[str, object] = {"load_at_start": load_average()}
    pairs, seconds = time_pairs(segs, phonetic_distance)
    record["segment"] = {"pairs": pairs, "seconds": seconds, "per_second": pairs / seconds}

    pool: List[str] = []
    for path in sorted(folder.glob("*_broad.tsv")):
        pool += read_prons(path)
    ipa = pick_pairs(pool, IPA_PAIRS)
    start = time.perf_counter()
    for a, b in ipa:
        ipa_distance(a, b)
    seconds = time.perf_counter() - start
    record["ipa_distance"] = {"pairs": len(ipa), "seconds": seconds, "per_second": len(ipa) / seconds}

    terms = read_prons(folder / f"{INDEX_FILE}.tsv")[:INDEX_TERMS]
    queries = random.Random(SEED).sample(read_prons(folder / f"{QUERY_FILE}.tsv"), QUERIES)
    record["search"] = {"terms": len(terms), "queries": len(queries)}
    for sensitivity in SENSITIVITIES:
        record["search"][str(sensitivity)] = time_search(terms, queries, sensitivity)
    return record


def median_of(runs: List[Dict[str, object]]) -> Dict[str, object]:
    def med(*path: str) -> float:
        values = []
        for run in runs:
            node = run
            for key in path:
                node = node[key]
            values.append(node)
        return statistics.median(values)

    summary = {
        "segment_per_second": med("segment", "per_second"),
        "ipa_distance_per_second": med("ipa_distance", "per_second"),
    }
    for sensitivity in SENSITIVITIES:
        s = str(sensitivity)
        summary[f"build_seconds_{s}"] = med("search", s, "build_seconds")
        summary[f"queries_per_second_{s}"] = med("search", s, "queries_per_second")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "phonematcher-bench")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "results" / "speed.json")
    args = parser.parse_args()

    segs = letters()
    runs = [one_run(args.cache) for _ in range(args.runs)]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    payload = {
        "task": "speed",
        "head": head,
        "machine": machine(),
        "segments": len(segs),
        "pair_count": len(segs) ** 2,
        "matrix_sha256": matrix_hash(segs, phonetic_distance),
        "method": {
            "ipa_pairs": f"{IPA_PAIRS} pairs of two distinct rows drawn with random.Random({SEED}).sample from all "
                         "broad WikiPron files in the cache, sorted by file name, spaces removed",
            "index_terms": f"the first {INDEX_TERMS} rows of {INDEX_FILE}, one term per row, spaces removed",
            "queries": f"{QUERIES} rows of {QUERY_FILE} drawn with random.Random({SEED}).sample, search(n_results=10)",
            "segments": "letters and tied affricates of phone_clusters; every ordered pair, diagonal included; "
                        "vectors warmed before timing",
        },
        "runs": runs,
        "median": median_of(runs),
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"segments {len(segs)}, pairs {payload['pair_count']}, matrix sha256 {payload['matrix_sha256']}")
    print(json.dumps(payload["median"], indent=1))


if __name__ == "__main__":
    main()
