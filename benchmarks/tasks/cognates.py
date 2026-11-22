"""Cognate detection on the benchmark data of List, Greenhill and Gray (2017).

Data: Zenodo record 192607 (CC BY 4.0), https://doi.org/10.5281/zenodo.192607. The training sets
are the dev split. The test sets load only when ``final`` is set; ``run.py`` refuses them otherwise.

Words are the dataset's own ``TOKENS`` column, which is what LingPy's edit-distance clustering
reads. Metric 1 is the average precision of ``-distance`` for "same cognate set" over all word
pairs of one concept. Metric 2 is the B-cubed F-score of a flat UPGMA cut per concept, at the
threshold with the best mean F-score over the dev sets (List et al. 2017, Table 6).
"""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Sequence, Tuple

import numpy as np

from systems import System, UnreadSegment

URL = "https://zenodo.org/api/records/192607/files/glottobank/potential-of-cognate-detection-v1.0.zip/content"
MD5 = "d270e3803e5be2f018c9a2975b750ce8"
SOURCE = "https://doi.org/10.5281/zenodo.192607 (v1.0, glottobank/potential-of-cognate-detection-v1.0.zip, md5 " + MD5 + ")"

TRAINING = ["Austronesian-210-20", "Bai-110-09", "Chinese-140-15", "IndoEuropean-207-20", "Japanese-200-10", "ObUgrian-110-21"]
TEST = ["Bahnaric-200-24", "Chinese-180-18", "Huon-140-14", "Romance-110-43", "Tujia-109-5", "Uralic-173-8"]

#: The edit-distance thresholds of the paper: 0.10 to 0.90 in steps of 0.05.
PAPER_GRID = [round(0.05 * i, 2) for i in range(2, 19)]


class Word(NamedTuple):
    concept: str
    language: str
    tokens: Tuple[str, ...]
    cogid: str


def fetch(cache: Path) -> Path:
    """Download and unpack the Zenodo archive into ``cache/cognates``; return the data directory."""
    root = Path(cache) / "cognates"
    code = next(root.glob("x/*/code"), None) if root.exists() else None
    if code is not None:
        return code
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "pkg.zip"
    urllib.request.urlretrieve(URL, archive)
    if hashlib.md5(archive.read_bytes()).hexdigest() != MD5:
        raise SystemExit(f"{archive} does not match md5 {MD5}")
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(root / "x")
    return next(root.glob("x/*/code"))


TONE_MARKS = set("⁰¹²³⁴⁵⁶⁷⁸⁹˥˦˧˨˩")


def load(path: Path, drop_tones: bool = False) -> List[Word]:
    """Read one ``D_*.tsv`` word list: ``#`` lines and blank lines are skipped.

    With ``drop_tones`` a token made only of superscript digits or Chao tone letters is removed."""
    rows = [
        line.rstrip("\n").split("\t")
        for line in Path(path).read_text(encoding="utf8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    head = rows[0]
    concept, language, tokens, cogid = (head.index(name) for name in ("CONCEPT", "DOCULECT", "TOKENS", "COGID"))
    def segments(cell: str) -> Tuple[str, ...]:
        return tuple(t for t in cell.split(" ") if not (drop_tones and set(t) <= TONE_MARKS))

    return [Word(r[concept], r[language], segments(r[tokens]), r[cogid]) for r in rows[1:]]


def average_precision(scores: Sequence[float], labels: Sequence[bool]) -> float:
    """Average precision with tied scores taken as one threshold: the sum over distinct score
    values of the recall gained times the precision there."""
    scores, labels = np.asarray(scores, dtype=float), np.asarray(labels, dtype=bool)
    positives = labels.sum()
    if positives == 0:
        return 0.0
    order = np.argsort(-scores, kind="stable")
    scores, labels = scores[order], labels[order]
    last = np.r_[np.flatnonzero(np.diff(scores)), len(scores) - 1]
    hits = np.cumsum(labels)[last]
    seen = last + 1
    gained = np.diff(np.r_[0, hits])
    return float((gained / positives * (hits / seen)).sum())


def flat_upgma(matrix: np.ndarray, thresholds: Sequence[float]) -> List[np.ndarray]:
    """Flat UPGMA clusters of one distance matrix at each threshold.

    Two clusters merge while the smallest mean distance between clusters is at most the threshold.
    This is LingPy's ``flat_upgma``, including its choice among equal distances: the first pair in
    cluster order wins and the second cluster joins the first. Edit distances tie often, so another
    rule gives other clusters.
    """
    n = len(matrix)
    rows = np.asarray(matrix).tolist()
    clusters: Dict[int, List[int]] = {i: [i] for i in range(n)}
    heights: List[float] = []
    steps: List[np.ndarray] = []
    while len(clusters) > 1:
        best, pair = None, None
        for i, a in clusters.items():
            for j, b in clusters.items():
                if i != j:
                    mean = sum(rows[x][y] for x in a for y in b) / (len(a) * len(b))
                    if best is None or mean < best:
                        best, pair = mean, (i, j)
        clusters[pair[0]] += clusters.pop(pair[1])
        labels = np.zeros(n, dtype=int)
        for label, members in enumerate(clusters.values()):
            labels[members] = label
        heights.append(best)
        steps.append(labels)
    out = []
    start = np.arange(n)
    for t in thresholds:
        merged = 0
        while merged < len(heights) and heights[merged] <= t:
            merged += 1
        out.append(steps[merged - 1] if merged else start)
    return out


def bcubed(gold: np.ndarray, test: np.ndarray) -> Tuple[float, float]:
    """Summed per-word B-cubed precision and recall for one concept (List et al. 2017, eqs. 1-2)."""
    same_gold = gold[:, None] == gold[None, :]
    same_test = test[:, None] == test[None, :]
    both = (same_gold & same_test).sum(axis=1)
    return float((both / same_test.sum(axis=1)).sum()), float((both / same_gold.sum(axis=1)).sum())


def bcubed_first_words(gold: np.ndarray, test: np.ndarray, language: np.ndarray) -> Tuple[float, float, int, int]:
    """B-cubed as LingPy's ``bcubes`` counts it, for the control against the paper's figures.

    LingPy takes, for each cognate set, only the first word of each language, and averages over
    those words. Returns the precision sum, the recall sum and the two entry counts.
    """
    def side(one: np.ndarray, other: np.ndarray) -> Tuple[float, int]:
        total, entries = 0.0, 0
        for cluster in np.unique(one):
            members = [int(np.flatnonzero((one == cluster) & (language == lang))[0]) for lang in np.unique(language[one == cluster])]
            labels = other[members]
            entries += len(members)
            total += 1.0 if len(members) == 1 else float(sum((labels == other[m]).sum() / len(members) for m in members))
        return total, entries

    recall, recall_entries = side(gold, test)
    precision, precision_entries = side(test, gold)
    return precision, recall, precision_entries, recall_entries


def f_score(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


class Concept(NamedTuple):
    gold: np.ndarray
    language: np.ndarray
    distances: np.ndarray  # normalized distance, 1.0 where a word has an unread segment
    unread: np.ndarray  # True for a word with an unread segment


def lingpy_order(group: Sequence[Word]) -> List[Word]:
    """The order of LingPy's ``get_list(row=concept, flat=True)``: every language's first word in
    alphabetical order of language, then every language's second word, and so on. The order decides
    which of several equal distances merges first in ``flat_upgma``."""
    seen: Dict[str, int] = {}
    ranked = []
    for word in group:
        ranked.append((seen.get(word.language, 0), word.language, word))
        seen[word.language] = seen.get(word.language, 0) + 1
    return [word for _, _, word in sorted(ranked, key=lambda r: r[:2])]


def concepts_of(system: System, words: Sequence[Word]) -> List[Concept]:
    """Per concept: gold labels, the pairwise normalized distances and the unread flags of one system."""
    by_concept: Dict[str, List[Word]] = {}
    for word in words:
        by_concept.setdefault(word.concept, []).append(word)
    cache: Dict[Tuple[str, ...], bool] = {}

    def is_unread(tokens: Tuple[str, ...]) -> bool:
        if tokens not in cache:
            cache[tokens] = not all(system.reads(t) for t in tokens)
        return cache[tokens]

    out = []
    for group in by_concept.values():
        group = lingpy_order(group)
        n = len(group)
        unread = np.array([is_unread(w.tokens) for w in group])
        distances = np.ones((n, n))
        for i in range(n):
            distances[i, i] = 0.0
            for j in range(i + 1, n):
                if not (unread[i] or unread[j]):
                    distances[i, j] = distances[j, i] = system.word_distance(list(group[i].tokens), list(group[j].tokens), True)
        gold = np.unique([w.cogid for w in group], return_inverse=True)[1]
        language = np.unique([w.language for w in group], return_inverse=True)[1]
        out.append(Concept(gold, language, distances, unread))
    return out


def restrict(concepts: Sequence[Concept], keep: Sequence[np.ndarray]) -> List[Concept]:
    """The concepts with only the words marked in ``keep``; concepts left empty are dropped."""
    out = []
    for c, mask in zip(concepts, keep):
        if mask.any():
            out.append(Concept(c.gold[mask], c.language[mask], c.distances[np.ix_(mask, mask)], c.unread[mask]))
    return out


def pair_scores(concepts: Sequence[Concept], skip_unread: bool) -> Tuple[np.ndarray, np.ndarray, int]:
    """Scores (negative distance), same-cognate labels and the number of pairs left out for an unread word."""
    scores, labels, skipped = [], [], 0
    for c in concepts:
        i, j = np.triu_indices(len(c.gold), 1)
        bad = c.unread[i] | c.unread[j]
        skipped += int(bad.sum())
        use = ~bad if skip_unread else np.ones(len(i), dtype=bool)
        scores.append(-c.distances[i, j][use])
        labels.append((c.gold[i] == c.gold[j])[use])
    return np.concatenate(scores), np.concatenate(labels), skipped


def cluster_scores(concepts: Sequence[Concept], thresholds: Sequence[float], counting: str = "lingpy") -> np.ndarray:
    """B-cubed (precision, recall) per threshold, shape (thresholds, 2).

    ``counting="lingpy"`` is LingPy's: first word of each language per cognate set, as in the paper's
    figures. ``counting="per_word"`` is the definition in the text of the paper: every word counts.
    """
    total = np.zeros((len(thresholds), 4))
    for c in concepts:
        seen: Dict[int, np.ndarray] = {}
        for k, labels in enumerate(flat_upgma(c.distances, thresholds)):
            if id(labels) not in seen:
                if counting == "lingpy":
                    seen[id(labels)] = np.array(bcubed_first_words(c.gold, labels, c.language), dtype=float)
                else:
                    p, r = bcubed(c.gold, labels)
                    seen[id(labels)] = np.array([p, r, len(c.gold), len(c.gold)], dtype=float)
            total[k] += seen[id(labels)]
    return np.stack([total[:, 0] / total[:, 2], total[:, 1] / total[:, 3]], axis=1)


def threshold_grid(datasets: Sequence[Sequence[Concept]]) -> List[float]:
    """0.01 to the largest read distance, at least 0.95, in steps of 0.01."""
    largest = max((c.distances[~(c.unread[:, None] | c.unread[None, :])].max(initial=0.0) for d in datasets for c in d), default=0.0)
    top = max(95, int(np.ceil(largest * 100 - 1e-9)))
    return [k / 100 for k in range(1, top + 1)]


def evaluate(systems: Dict[str, Dict[str, List[Concept]]], names: Sequence[str]) -> dict:
    """Both scores for every system on the common subset and on all words, per data set and as the mean."""
    keep_common = {
        name: [
            np.logical_and.reduce([~s[name][i].unread for s in systems.values()])
            for i in range(len(next(iter(systems.values()))[name]))
        ]
        for name in names
    }
    common = {sys_name: {n: restrict(sets[n], keep_common[n]) for n in names} for sys_name, sets in systems.items()}
    report: dict = {}
    for sys_name, sets in systems.items():
        entry: dict = {}
        for label, variant in (("common", common[sys_name]), ("unread_at_1", sets)):
            active = [n for n in names if variant[n]]
            if not active:
                entry[label] = None
                continue
            thresholds = threshold_grid([variant[n] for n in active])
            paper = [thresholds.index(t) for t in PAPER_GRID if t in thresholds]

            def summary(counting: str) -> dict:
                grid = np.array([cluster_scores(variant[n], thresholds, counting) for n in active])  # sets, thresholds, (p, r)
                f = np.vectorize(f_score)(grid[:, :, 0], grid[:, :, 1])
                best = int(f.mean(axis=0).argmax())
                best_paper = paper[int(f.mean(axis=0)[paper].argmax())]
                return {
                    "bcubed_f": {**{n: float(f[k, best]) for k, n in enumerate(active)}, "mean": float(f[:, best].mean())},
                    "bcubed_precision_mean": float(grid[:, best, 0].mean()),
                    "bcubed_recall_mean": float(grid[:, best, 1].mean()),
                    "threshold": thresholds[best],
                    "paper_grid": {
                        "threshold": thresholds[best_paper],
                        "bcubed_f": {**{n: float(f[k, best_paper]) for k, n in enumerate(active)}, "mean": float(f[:, best_paper].mean())},
                    },
                }

            ap = {}
            for n in active:
                scores, labels, _ = pair_scores(variant[n], skip_unread=label == "common")
                ap[n] = average_precision(scores, labels)
            entry[label] = {
                "data_sets_scored": active,
                "average_precision": {**ap, "mean": float(np.mean(list(ap.values())))},
                **summary("lingpy"),
                "per_word": summary("per_word"),
                "words_in": {n: sum(len(c.gold) for c in sets[n]) for n in names},
                "words_out": {n: sum(len(c.gold) for c in variant[n]) for n in names},
            }
        entry["skipped"] = {
            "words": {n: sum(int(c.unread.sum()) for c in sets[n]) for n in names},
            "pairs": {n: pair_scores(sets[n], skip_unread=True)[2] for n in names},
            "pairs_in": {n: sum(len(c.gold) * (len(c.gold) - 1) // 2 for c in sets[n]) for n in names},
        }
        report[sys_name] = entry
    return report


#: Table 6 of List et al. (2017): edit distance, mean over the six training sets, at its best threshold.
PAPER_EDIT_DISTANCE = {"threshold": 0.75, "precision": 0.8341, "recall": 0.8101, "f_score": 0.8144}


def control(levenshtein: Dict[str, List[Concept]], names: Sequence[str], directory: Path) -> dict:
    """Levenshtein under LingPy's B-cubed counting on the paper's thresholds, beside the paper's own
    per-set figures (``R_training_results.json`` of the archive)."""
    published = json.loads((directory / "R_training_results.json").read_text())
    grid = np.array([cluster_scores(levenshtein[n], PAPER_GRID) for n in names])
    grid = np.vectorize(f_score)(grid[:, :, 0], grid[:, :, 1])
    best = int(grid.mean(axis=0).argmax())
    step = round(PAPER_GRID[best] / 0.05)
    theirs = {n: published[f"{step}/edit/D_training_{n}.tsv"][2] for n in names}
    return {
        "paper_table_6": PAPER_EDIT_DISTANCE,
        "threshold": PAPER_GRID[best],
        "lingpy_counting_f": {**{n: float(grid[k, best]) for k, n in enumerate(names)}, "mean": float(grid[:, best].mean())},
        "archive_f_at_threshold": {**theirs, "mean": float(np.mean(list(theirs.values())))},
        "difference_from_paper_table_6": float(grid[:, best].mean() - PAPER_EDIT_DISTANCE["f_score"]),
    }


SPLITS = ("dev", "test")


def run(systems: List[System], split: str, cache: Path, drop_tones: bool = False) -> dict:
    """Score every system on the dev (training) or the test data sets. ``run.py`` lets the test
    sets through only with ``--final``."""
    names = TEST if split == "test" else TRAINING
    prefix = "D_test_" if split == "test" else "D_training_"
    directory = fetch(cache)
    words = {n: load(directory / f"{prefix}{n}.tsv", drop_tones) for n in names}
    sets = {system.name: {n: concepts_of(system, words[n]) for n in names} for system in systems}
    payload = {
        "source": SOURCE,
        "datasets": names,
        "tone_tokens_dropped": drop_tones,
        "words": {n: len(words[n]) for n in names},
        "systems": evaluate(sets, names),
    }
    if split == "dev" and not drop_tones and "levenshtein" in sets:
        payload["control"] = control(sets["levenshtein"], names, directory)
    return payload


def lines(payload: dict) -> List[str]:
    """One line per system: mean average precision and mean B-cubed F on all words, then on the common words."""
    def mean(variant: dict, key: str) -> str:
        return "-" if variant is None else f"{variant[key]['mean']:.4f}"

    return [
        f"{name}: all words AP {mean(e['unread_at_1'], 'average_precision')} F {mean(e['unread_at_1'], 'bcubed_f')}; "
        f"common words AP {mean(e['common'], 'average_precision')} F {mean(e['common'], 'bcubed_f')}"
        for name, e in payload["systems"].items()
    ]
