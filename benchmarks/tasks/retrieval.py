"""Task C6, variant retrieval: find a word from its pronunciation in another dialect.

WikiPron lists one broad transcription set per dialect. For a language with two dialect files the
index holds every pronunciation of dialect A and each query is a dialect B pronunciation of a word
that both files list. The gold answer is the same word.

    python benchmarks/run.py --task retrieval --system all --split dev

A run stores one rank record per system and pair, and one record per slice of the fuzzy search, in
the cache. A later run reuses a record made by the same code, so the slices can be computed in
parallel first:

    python benchmarks/tasks/retrieval.py run --system sca --pair en-US-UK --sample 500
    python benchmarks/tasks/retrieval.py fuzzy --pair en-US-UK --sensitivity 0.1 --part 0 --parts 5
"""
import argparse
import csv
import hashlib
import json
import random
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from split import is_test  # noqa: E402
from systems import NAMES, PhoneMatcher, downey  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
WIKIPRON_REPO = "https://github.com/CUNY-CL/wikipron"
WIKIPRON_SHA = "d282e848a211ea31cfd730f0ced8bc8cdab9e83d"
WIKIPRON_RAW = f"https://raw.githubusercontent.com/CUNY-CL/wikipron/{WIKIPRON_SHA}/data/scrape/tsv/"

#: language pair -> (dialect A file for the index, dialect B file for the queries)
PAIRS: Dict[str, Tuple[str, str]] = {
    "en-US-UK": ("eng_latn_us_broad", "eng_latn_uk_broad"),
    "pt-PT-BR": ("por_latn_po_broad", "por_latn_bz_broad"),
    "es-ES-LA": ("spa_latn_ca_broad", "spa_latn_la_broad"),
    "hy-E-W": ("hye_armn_e_broad", "hye_armn_w_broad"),
}
INDEX_CAP = 20000
SAMPLE_SIZE = 500
#: systems that score a fixed random sample of the queries, with its size, because a full run takes hours
SLOW: Dict[str, int] = {"aline": 100, "sca": SAMPLE_SIZE}
FUZZY_PARTS = 5
SAMPLE_SEED = 0
SENSITIVITIES = (0.01, 0.02, 0.03, 0.05, 0.08, 0.12)
TIE_EPSILON = 1e-9
#: systems whose word distance is an edit distance with one cost per segment pair and a constant
#: indel cost, so the distance to the whole index is computed as one vectorised table
BATCHED = ("phonematcher", "levenshtein", "panphon-weighted", "panphon-hamming", "soundvectors")

SPLITS = ("dev",)

Pron = Tuple[str, ...]


def stamp() -> str:
    """Hash of the code a stored record depends on: a record made by other code is not reused."""
    digest = hashlib.sha1()
    files = [ROOT / "benchmarks" / "systems.py", ROOT / "benchmarks" / "variants.py"]
    files += sorted((ROOT / "phonematcher").rglob("*.py")) + sorted((ROOT / "phonematcher").rglob("*.json"))
    for path in files:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def download(cache: Path) -> Path:
    """Fetch the broad WikiPron files at the pinned commit into ``cache/C6``."""
    folder = Path(cache) / "C6"
    folder.mkdir(parents=True, exist_ok=True)
    for name in {n for pair in PAIRS.values() for n in pair}:
        target = folder / f"{name}.tsv"
        if not target.exists():
            with urllib.request.urlopen(WIKIPRON_RAW + f"{name}.tsv") as response:
                target.write_bytes(response.read())
    return folder


def load_tsv(path: Path) -> Dict[str, List[Pron]]:
    """``word -> pronunciations`` in file order, each a tuple of space-separated segments."""
    words: Dict[str, List[Pron]] = {}
    with open(path, encoding="utf8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) != 2:
                continue
            pron = tuple(row[1].split())
            if pron and pron not in words.setdefault(row[0], []):
                words[row[0]].append(pron)
    return words


@dataclass
class Pair:
    """The index and the dev queries of one language pair, with the counts of every step."""

    name: str
    words: List[str]
    prons: List[Pron]
    owner: List[int]
    queries: List[Tuple[str, Pron]]
    counts: Dict[str, int] = field(default_factory=dict)


def build_pair(
    name: str, a: Dict[str, List[Pron]], b: Dict[str, List[Pron]], split: str = "dev", cap: int = INDEX_CAP
) -> Pair:
    """Index the first *cap* words of dialect A in sorted order; query with the B pronunciations
    of shared words that A does not list for the same word. Keys for the split: ``<name>:<word>``
    with the language code taken from the pair name."""
    language = name.split("-")[0]
    index_words = sorted(a)[:cap]
    in_index = set(index_words)
    shared = sorted(set(a) & set(b))
    counts = {"a_words": len(a), "b_words": len(b), "shared_words": len(shared), "index_words": len(index_words)}
    counts["index_prons"] = sum(len(a[w]) for w in index_words)
    differ = [w for w in shared if [p for p in b[w] if p not in a[w]]]
    counts["same_pronunciations"] = sum(1 for w in shared if set(a[w]) == set(b[w]))
    counts["b_within_a"] = len(shared) - len(differ) - counts["same_pronunciations"]
    counts["item_words"] = len(differ)
    counts["items_outside_index_cap"] = sum(1 for w in differ if w not in in_index)
    inside = [w for w in differ if w in in_index]
    wanted_test = split == "test"
    kept = [w for w in inside if is_test(f"{language}:{w}") == wanted_test]
    counts["items_in_other_split"] = len(inside) - len(kept)
    counts["item_words_in_split"] = len(kept)
    queries = [(w, p) for w in kept for p in b[w] if p not in a[w]]
    counts["queries"] = len(queries)
    prons = [p for w in index_words for p in a[w]]
    owner = [i for i, w in enumerate(index_words) for _ in a[w]]
    return Pair(name, index_words, prons, owner, queries, counts)


def sample_queries(queries: Sequence, size: int = SAMPLE_SIZE, seed: int = SAMPLE_SEED) -> List[int]:
    """Sorted indices of a fixed random sample; all indices when there are fewer than *size*.
    A smaller *size* takes the first draws of the larger sample, so the samples are nested.
    Raises ``ValueError`` when *size* is above ``SAMPLE_SIZE``, the size of the larger sample."""
    if size > SAMPLE_SIZE:
        raise ValueError(f"a sample holds at most {SAMPLE_SIZE} queries, not {size}")
    if len(queries) <= size:
        return list(range(len(queries)))
    draw = random.Random(seed).sample(range(len(queries)), min(len(queries), SAMPLE_SIZE))
    return sorted(draw[:size])


def tie_rank(distances: np.ndarray, gold: int) -> Tuple[int, int]:
    """``(s, t)``: how many terms are strictly closer than the gold term, and how many are as
    close, the gold term included."""
    g = distances[gold]
    return int((distances < g - TIE_EPSILON).sum()), int((np.abs(distances - g) <= TIE_EPSILON).sum())


def recall_at(k: int, s: int, t: int) -> float:
    """Chance that the gold term is in the top *k* when the tied terms are in random order."""
    return min(1.0, max(0.0, (k - s) / t))


def reciprocal_rank(s: int, t: int) -> float:
    """Mean of ``1/rank`` over the *t* places the gold term can take among its ties."""
    return sum(1.0 / (s + i) for i in range(1, t + 1)) / t


def retrieval_scores(ranks: Sequence[Tuple[int, int]]) -> Dict[str, float]:
    n = len(ranks)
    if not n:
        return {"n": 0, "recall@1": None, "recall@10": None, "mrr": None}
    return {
        "n": n,
        "recall@1": sum(recall_at(1, s, t) for s, t in ranks) / n,
        "recall@10": sum(recall_at(10, s, t) for s, t in ranks) / n,
        "mrr": sum(reciprocal_rank(s, t) for s, t in ranks) / n,
    }


class Batched:
    """Distances from one query to every index pronunciation, from the system's own segment
    distances. Equal to ``system.word_distance_or_one(..., normalized=True)``; ``check`` proves it."""

    def __init__(self, system, pair: Pair):
        self.system = system
        # PhoneMatcher splits a segment such as a diphthong into the parts the library reads
        self.parts = system._parts if isinstance(system, PhoneMatcher) else lambda segment: [segment]
        prons = [self.expand(p) for p in pair.prons]
        segments = sorted({s for p in prons for s in p} | {s for _, q in pair.queries for s in self.expand(q)})
        self.id = {s: i for i, s in enumerate(segments)}
        self.read = np.array([system.reads(s) for s in segments] + [True])
        size = len(segments) + 1
        self.sub = np.zeros((size, size))
        for x, a in enumerate(segments):
            if not self.read[x]:
                continue
            for y, b in enumerate(segments):
                if self.read[y]:
                    self.sub[x, y] = system.segment_distance(a, b)
        self.indel = float(system.word_distance(["a"], [], False))
        self.lengths = np.array([len(p) for p in prons])
        self.unread = np.array([not all(self.read[self.id[s]] for s in p) for p in prons])
        self.owner = np.array(pair.owner)
        self.starts = np.flatnonzero(np.r_[True, self.owner[1:] != self.owner[:-1]])
        self.buckets = []
        order = np.argsort(self.lengths, kind="stable")
        limits = [6, 9, 12, 16, int(self.lengths.max())]
        low = 0
        for limit in limits:
            members = order[(self.lengths[order] > low) & (self.lengths[order] <= limit)]
            low = limit
            if len(members):
                width = int(self.lengths[members].max())
                table = np.full((width, len(members)), size - 1, dtype=np.int64)
                for col, k in enumerate(members):
                    table[: self.lengths[k], col] = [self.id[s] for s in prons[k]]
                self.buckets.append((members, table, self.lengths[members]))

    def expand(self, word: Pron) -> List[str]:
        return [part for segment in word for part in self.parts(segment)]

    def query_unread(self, query: Pron) -> bool:
        return not all(self.read[self.id[s]] for s in self.expand(query))

    def prons_distance(self, query: Pron) -> np.ndarray:
        """Normalized distance from *query* to every index pronunciation, unread ones at 1.0."""
        unread = self.query_unread(query)
        query = self.expand(query)
        out = np.empty(len(self.lengths))
        ids = [self.id[s] for s in query]
        for members, table, lengths in self.buckets:
            width = table.shape[0]
            prev = self.indel * np.arange(width + 1, dtype=float)[:, None] * np.ones((1, len(members)))
            for i, q in enumerate(ids, start=1):
                sub = self.sub[q][table]
                cur = np.empty_like(prev)
                cur[0] = i * self.indel
                for j in range(1, width + 1):
                    np.minimum(prev[j] + self.indel, cur[j - 1] + self.indel, out=cur[j])
                    np.minimum(cur[j], prev[j - 1] + sub[j - 1], out=cur[j])
                prev = cur
            raw = prev[lengths, np.arange(len(members))]
            out[members] = raw / np.maximum(lengths, len(query))
        if unread:
            out[:] = 1.0
        out[self.unread] = 1.0
        return out

    def word_distances(self, query: Pron) -> np.ndarray:
        return np.minimum.reduceat(self.prons_distance(query), self.starts)

    def check(self, pair: Pair, count: int = 300) -> int:
        """Assert equality with the system's own word distance on a fixed sample of pairs."""
        rng = random.Random(1)
        checked = 0
        for _, query in rng.sample(pair.queries, min(count, len(pair.queries))):
            distances = self.prons_distance(query)
            for k in rng.sample(range(len(pair.prons)), min(5, len(pair.prons))):
                expected = self.system.word_distance_or_one(list(query), list(pair.prons[k]), True)
                assert abs(distances[k] - expected) < 1e-9, (query, pair.prons[k], distances[k], expected)
                checked += 1
        return checked


class Sequential:
    """The same distances for an alignment system (ALINE, SCA), one pair at a time, with the
    self-similarity of every word computed once."""

    def __init__(self, system, pair: Pair):
        self.system = system
        self.pair = pair
        self.self_similarity: Dict[Pron, float] = {}
        self.unread_cache: Dict[Pron, bool] = {}
        self.owner = np.array(pair.owner)
        self.starts = np.flatnonzero(np.r_[True, self.owner[1:] != self.owner[:-1]])

    def unread(self, word: Pron) -> bool:
        if word not in self.unread_cache:
            self.unread_cache[word] = not all(self.system.reads(s) for s in word)
        return self.unread_cache[word]

    def own(self, word: Pron) -> float:
        if word not in self.self_similarity:
            self.self_similarity[word] = self.system.similarity(word, word)
        return self.self_similarity[word]

    def distance(self, a: Pron, b: Pron) -> float:
        if self.unread(a) or self.unread(b):
            return 1.0
        return downey(self.system.similarity(a, b), self.own(a), self.own(b), True)

    def query_unread(self, query: Pron) -> bool:
        return self.unread(query)

    def prons_distance(self, query: Pron) -> np.ndarray:
        return np.array([self.distance(query, p) for p in self.pair.prons])

    def word_distances(self, query: Pron) -> np.ndarray:
        return np.minimum.reduceat(self.prons_distance(query), self.starts)

    def check(self, pair: Pair, count: int = 20) -> int:
        rng = random.Random(1)
        checked = 0
        for _, query in rng.sample(pair.queries, min(count, len(pair.queries))):
            for k in rng.sample(range(len(pair.prons)), min(5, len(pair.prons))):
                expected = self.system.word_distance_or_one(list(query), list(pair.prons[k]), True)
                assert abs(self.distance(query, pair.prons[k]) - expected) < 1e-9
                checked += 1
        return checked


def brute_force(system, pair: Pair, indices: Sequence[int]) -> dict:
    """Rank record of every chosen query: ``s``, ``t`` and whether the item is unscorable
    (the query or every reading of the gold word holds a segment the system cannot read)."""
    engine = (Batched if system.name in BATCHED or isinstance(system, PhoneMatcher) else Sequential)(system, pair)
    checked = engine.check(pair)
    gold_of = {w: i for i, w in enumerate(pair.words)}
    readings: Dict[int, List[Pron]] = {}
    for pron, o in zip(pair.prons, pair.owner):
        readings.setdefault(o, []).append(pron)
    reads: Dict[str, bool] = {}

    def unread(word: Pron) -> bool:
        for segment in word:
            if segment not in reads:
                reads[segment] = system.reads(segment)
        return not all(reads[segment] for segment in word)

    record = {"index": list(indices), "s": [], "t": [], "unread": [], "pairs_checked": checked}
    memo: Dict[Pron, np.ndarray] = {}
    for k in indices:
        word, query = pair.queries[k]
        if query not in memo:
            if len(memo) > 2000:
                memo.pop(next(iter(memo)))
            memo[query] = engine.word_distances(query)
        g = gold_of[word]
        s, t = tie_rank(memo[query], g)
        record["s"].append(s)
        record["t"].append(t)
        record["unread"].append(unread(query) or all(unread(p) for p in readings[g]))
    return record


def fuzzy_search(pair: Pair, indices: Sequence[int], sensitivity: float) -> dict:
    """``PhoneticFuzzySearch`` over the index: candidate hits, candidate count, recall@1 credit
    and the time of the searches. Ties at the best score share the credit, as in ``tie_rank``."""
    from phonematcher import PhoneticFuzzySearch

    search = PhoneticFuzzySearch(sensitivity)
    by_word: Dict[int, List[str]] = {}
    for pron, o in zip(pair.prons, pair.owner):
        by_word.setdefault(o, []).append("".join(pron))
    for o, word in enumerate(pair.words):
        search.add_term(by_word[o], word)
    hits, candidates, top1, seconds = 0, 0, 0.0, 0.0
    for k in indices:
        word, query = pair.queries[k]
        begin = time.perf_counter()
        matches = search.search("".join(query), n_results=len(pair.words))
        seconds += time.perf_counter() - begin
        candidates += len(matches)
        gold = next((m.score for m in matches if m.id == word), None)
        if gold is None:
            continue
        hits += 1
        s = sum(m.score < gold - TIE_EPSILON for m in matches)
        t = sum(abs(m.score - gold) <= TIE_EPSILON for m in matches)
        top1 += recall_at(1, s, t)
    return {"sensitivity": sensitivity, "n": len(indices), "candidate_hits": hits,
            "candidates": candidates, "top1": top1, "seconds": seconds}


def record_path(cache: Path, split: str, system: str, pair: str) -> Path:
    return Path(cache) / "C6" / f"ranks-{split}-{system}-{pair}.json"


def load_pair(pair_name: str, cache: Path, split: str) -> Pair:
    folder = download(cache)
    a_file, b_file = PAIRS[pair_name]
    return build_pair(pair_name, load_tsv(folder / f"{a_file}.tsv"), load_tsv(folder / f"{b_file}.tsv"), split)


def run_pair(system, pair_name: str, cache: Path, split: str, sample: int = 0) -> dict:
    """Score one system on one language pair and store the record in the cache."""
    path = record_path(cache, split, system.name, pair_name)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf8"))
        if stored.get("stamp") == stamp() and stored["sample"] == (sample or None):
            return stored
    pair = load_pair(pair_name, cache, split)
    indices = sample_queries(pair.queries, sample) if sample else list(range(len(pair.queries)))
    begin = time.perf_counter()
    record = {"stamp": stamp(), "pair": pair_name, "system": system.name, "counts": pair.counts,
              "sample": sample or None, "queries_in": len(pair.queries)}
    record["brute"] = brute_force(system, pair, indices)
    record["brute_seconds"] = time.perf_counter() - begin
    assert len(record["brute"]["s"]) == len(indices)
    path.write_text(json.dumps(record), encoding="utf8")
    return record


def fuzzy_path(cache: Path, split: str, pair: str, sensitivity: float, part: int) -> Path:
    return Path(cache) / "C6" / f"fuzzy-{split}-{pair}-{sensitivity}-{part}.json"


def run_fuzzy(pair_name: str, sensitivity: float, part: int, parts: int, cache: Path, split: str, sample: int) -> dict:
    """One slice of the fixed query sample, searched at one sensitivity; stored in the cache.
    The sample is cut into *parts* consecutive slices so that a slice finishes in minutes."""
    path = fuzzy_path(cache, split, pair_name, sensitivity, part)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf8"))
        if stored.get("stamp") == stamp() and stored["parts"] == parts and stored["sample"] == min(sample, stored["queries_in"]):
            return stored
    pair = load_pair(pair_name, cache, split)
    chosen = sample_queries(pair.queries, sample)
    size = -(-len(chosen) // parts)
    indices = chosen[part * size:(part + 1) * size]
    row = fuzzy_search(pair, indices, sensitivity)
    row.update(stamp=stamp(), pair=pair_name, part=part, parts=parts, sample=len(chosen), queries_in=len(pair.queries))
    assert row["top1"] <= row["candidate_hits"] + 1e-9, row
    path.write_text(json.dumps(row), encoding="utf8")
    return row


def run(systems: list, split: str, cache: Path) -> dict:
    """The ``run.py`` entry: every system and every language pair, then the fuzzy search of
    phonematcher in slices of the fixed sample. Stored records of the same code are reused."""
    for system in systems:
        for name in PAIRS:
            run_pair(system, name, cache, split, SLOW.get(system.name, 0))
    if any(system.name == "phonematcher" for system in systems):
        for name in PAIRS:
            for x in SENSITIVITIES:
                for part in range(FUZZY_PARTS):
                    run_fuzzy(name, x, part, FUZZY_PARTS, cache, split, SAMPLE_SIZE)
    return aggregate(cache, split, [system.name for system in systems])


def lines(payload: dict) -> List[str]:
    out = []
    for name, pair in payload["pairs"].items():
        for system, row in pair["systems"].items():
            score = row["all_items_unread_at_1"]
            out.append(f"{name} {system}: n={score['n']} recall@1={score['recall@1']:.3f} "
                       f"recall@10={score['recall@10']:.3f} mrr={score['mrr']:.3f}")
        for row in pair["fuzzy_search"] or []:
            out.append(f"{name} fuzzy {row['sensitivity']}: candidate recall={row['candidate_recall']:.3f} "
                       f"candidates={row['mean_candidates']:.1f} recall@1={row['recall@1']:.3f} "
                       f"qps={row['queries_per_second']:.2f}")
    return out


def aggregate(cache: Path, split: str, names: Sequence[str] = NAMES) -> dict:
    """Combine the stored records into the result file."""
    pairs: Dict[str, dict] = {}
    for name in PAIRS:
        records = {}
        for system in names:
            path = record_path(cache, split, system, name)
            if path.exists():
                records[system] = json.loads(path.read_text(encoding="utf8"))
        if not records:
            continue
        counts = next(iter(records.values()))["counts"]
        queries_in = next(iter(records.values()))["queries_in"]
        by_index = {system: {i: (s, t, u) for i, s, t, u in zip(r["brute"]["index"], r["brute"]["s"],
                                                           r["brute"]["t"], r["brute"]["unread"])}
                    for system, r in records.items()}
        common = sorted(set.intersection(*(set(m) for m in by_index.values()))
                        - {i for m in by_index.values() for i, (_, _, u) in m.items() if u})
        sampled = sorted(set.intersection(*(set(m) for m in by_index.values())))
        full = [system for system, r in records.items() if r["sample"] is None]
        common_full = sorted(set.intersection(*(set(by_index[system]) for system in full))
                             - {i for system in full for i, (_, _, u) in by_index[system].items() if u}) if full else []
        systems = {}
        for system, r in records.items():
            m = by_index[system]
            systems[system] = {
                "queries_scored": len(m),
                "sample": r["sample"],
                "skipped_unread": sum(u for _, _, u in m.values()),
                "all_items_unread_at_1": retrieval_scores([m[i][:2] for i in sorted(m)]),
                "common_subset": retrieval_scores([m[i][:2] for i in common]),
                "common_full_run_subset": retrieval_scores([m[i][:2] for i in common_full if i in m]),
                "on_shared_queries": retrieval_scores([m[i][:2] for i in sampled]),
                "seconds": round(r["brute_seconds"], 1),
                "batched_equals_system_on_pairs": r["brute"]["pairs_checked"],
            }
        fuzzy = []
        for x in SENSITIVITIES:
            rows = [json.loads(f.read_text(encoding="utf8")) for f in sorted(
                (Path(cache) / "C6").glob(f"fuzzy-{split}-{name}-{x}-*.json"))]
            if not rows:
                continue
            n = sum(r["n"] for r in rows)
            assert n == rows[0]["sample"], (name, x, n, rows[0]["sample"])
            seconds = sum(r["seconds"] for r in rows)
            fuzzy.append({
                "sensitivity": x, "queries": n,
                "candidate_recall": sum(r["candidate_hits"] for r in rows) / n,
                "mean_candidates": sum(r["candidates"] for r in rows) / n,
                "recall@1": sum(r["top1"] for r in rows) / n,
                "queries_per_second": n / seconds,
            })
            assert fuzzy[-1]["recall@1"] <= fuzzy[-1]["candidate_recall"] + 1e-9
        pairs[name] = {"files": PAIRS[name], "counts": counts, "queries_in": queries_in,
                       "common_queries": len(common), "common_full_run_queries": len(common_full), "shared_sampled_queries": len(sampled),
                       "systems": systems, "fuzzy_search": fuzzy or None}
    return {
        "task": "retrieval", "split": split,
        "source": {"url": WIKIPRON_REPO, "sha": WIKIPRON_SHA, "licence": "Apache-2.0",
                   "path": "data/scrape/tsv", "transcription": "broad, unfiltered"},
        "index_cap": INDEX_CAP, "index_order": "sorted word order, first terms",
        "tie_rule": "tied terms in random order: recall@k is the expected share, MRR the mean 1/rank",
        "pairs": pairs,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["run", "fuzzy"])
    parser.add_argument("--system", help="one system name")
    parser.add_argument("--pair", choices=sorted(PAIRS))
    parser.add_argument("--split", default="dev", choices=["dev"])
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "phonematcher-bench")
    parser.add_argument("--sample", type=int, default=0, help="score a fixed random sample of this many queries")
    parser.add_argument("--sensitivity", type=float, choices=SENSITIVITIES)
    parser.add_argument("--part", type=int, default=0)
    parser.add_argument("--parts", type=int, default=1)
    parser.add_argument("--fuzzy-sample", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args(argv)
    if args.command == "fuzzy":
        row = run_fuzzy(args.pair, args.sensitivity, args.part, args.parts, args.cache, args.split, args.fuzzy_sample)
        print(row, flush=True)
        return 0
    from systems import build

    system = build(args.system, args.cache)
    for name in [args.pair] if args.pair else PAIRS:
        record = run_pair(system, name, args.cache, args.split, args.sample)
        scores = retrieval_scores(list(zip(record["brute"]["s"], record["brute"]["t"])))
        print(f"{system.name} {name}: in={record['queries_in']} out={scores['n']} {scores} "
              f"{record['brute_seconds']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
