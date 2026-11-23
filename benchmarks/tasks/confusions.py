"""C3: do the distances of segment pairs follow how often listeners confuse them?

Four confusion sets, each a list of segment pairs with a confusion value:

- Mandarin consonants: Yu and Do (2023), Data in Brief, doi 10.1016/j.dib.2023.109868, OSF rbt8x.
  Raw identification counts; a pair is the mean of the two directions.
- Miller and Nicely (1955), 16 English consonants: the pooled similarity matrix of the R package
  clue 0.3-55, data set ``Phonemes``. Used as given, for ranks only.
- Hillenbrand, Getty, Clark and Wheeler (1995), 12 American English vowels, 20 listeners per
  token (MIT licence); a pair is the mean of the two directions.
- Spanish word-in-noise confusions: Toth, Garcia Lecumberri, Tang and Cooke (2015), JASA 137(2),
  EL184-EL189; Zenodo 3521449, CC BY 4.0, file ``confusionsCorpus.csv`` of
  ``SpanishConfusionsCorpus.zip``. A target and a heard word are aligned by a unit-cost edit
  distance, and each substitution adds the listener count (the Consistency column) to its pair.
  The pairs are all pairs of target segments. The corpus writes ASCII g, an untied tʃ and the
  ligature ʤ; they are read as ɡ, t͡ʃ and d͡ʒ.

The score of a system on a set is the Spearman correlation of the negative segment distance with
the confusion. ``unread_at_1`` scores every pair, with distance 1 when a system cannot read a
segment. ``common_subset`` scores the pairs whose two segments every system reads. Each score has
a 95% bootstrap interval from 1,000 resamples of pairs (seed 0).
"""
import csv
import io
import tarfile
import zipfile
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from phonematcher import align
from systems import System
from tasks.common import bootstrap_interval, fetch, sha256, similarity_score

CACHE_NAME = "C3"
SPLITS = ("seen",)

MANDARIN_URL = "https://osf.io/download/k9qzg/"
CLUE_URL = "https://cran.r-project.org/src/contrib/Archive/clue/clue_0.3-55.tar.gz"
HILLENBRAND_URL = "https://github.com/santiagobarreda/hillenbrand_et_al_1995/raw/main/h95-alldata.zip"
SPANISH_URL = "https://zenodo.org/api/records/3521449/files/SpanishConfusionsCorpus.zip/content"
SPANISH_MD5 = "c9367123ebc2d6e290b7bc97f526a274"
SPANISH_MEMBER = "SpanishConfusionsCorpus/confusionsCorpus.csv"

MILLER_NICELY = {
    "PA": "p", "TA": "t", "KA": "k", "FA": "f", "THETA": "θ", "SA": "s", "SHA": "ʃ", "BA": "b",
    "DA": "d", "GA": "ɡ", "VA": "v", "THAT": "ð", "ZA": "z", "ZHA": "ʒ", "MA": "m", "NA": "n",
}
#: Hillenbrand's labels by their key words, heed ... heard, in broad IPA.
HILLENBRAND = {
    "iy": "i", "ih": "ɪ", "ei": "e", "eh": "ɛ", "ae": "æ", "ah": "ɑ", "aw": "ɔ", "oa": "o",
    "oo": "ʊ", "uw": "u", "uh": "ʌ", "er": "ɝ",
}
#: The Mandarin file writes affricates without a tie bar.
TIED = {"ts": "t͡s", "tsʰ": "t͡sʰ", "tɕ": "t͡ɕ", "tɕʰ": "t͡ɕʰ", "ʈʂ": "ʈ͡ʂ", "ʈʂʰ": "ʈ͡ʂʰ"}
SPANISH_SPELLING = {"g": "ɡ", "tʃ": "t͡ʃ", "ʤ": "d͡ʒ"}
NOT_SEGMENTS = {"!", "."}

Pairs = Dict[Tuple[str, str], float]


def symmetric_rates(labels: List[str], counts: np.ndarray) -> Pairs:
    """Per pair, the mean of P(b heard for a) and P(a heard for b)."""
    rates = counts / counts.sum(axis=1, keepdims=True)
    return {
        (labels[i], labels[j]): (rates[i, j] + rates[j, i]) / 2 for i, j in combinations(range(len(labels)), 2)
    }


def mandarin(text: str) -> Pairs:
    body = [r for r in list(csv.reader(io.StringIO(text)))[1:] if r and r[0]]
    labels = [TIED.get(s, s) for s in (r[-1].strip("/") for r in body)]
    counts = np.array([[float(x) for x in r[1 : 1 + len(body)]] for r in body])
    return symmetric_rates(labels, counts)


def miller_nicely(matrix: List[List[float]], columns: List[str]) -> Pairs:
    """Pairs of the upper triangle of the pooled matrix, with the columns named as in clue."""
    labels = [MILLER_NICELY[c] for c in columns]
    return {(labels[i], labels[j]): float(matrix[i][j]) for i, j in combinations(range(len(labels)), 2)}


def hillenbrand(text: str) -> Pairs:
    keys = list(HILLENBRAND)
    counts = np.zeros((len(keys), len(keys)))
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 14 and parts[0][:1] in "mwbg" and parts[0][1:3].isdigit():
            counts[keys.index(parts[0][3:5])] += [float(x) for x in parts[2:14]]
    return symmetric_rates([HILLENBRAND[k] for k in keys], counts)


def substitution_pairs(a: List[str], b: List[str]) -> List[Tuple[str, str]]:
    """The substitution pairs of one unit-cost alignment of *a* and *b*, chosen deterministically,
    from the end of the words back."""
    pairs = align(a, b, substitution=lambda x, y: float(x != y), gap=1.0)
    return [(x, y) for x, y in reversed(pairs) if x is not None and y is not None]


def substitutions(text: str) -> Tuple[Counter, List[str]]:
    """Listener-weighted substitution counts per ordered segment pair (smaller first), and the
    segments of the targets, sorted."""
    counts: Counter = Counter()
    inventory = set()
    for row in csv.DictReader(io.StringIO(text)):
        target = [SPANISH_SPELLING.get(s, s) for s in row["Target-IPA"].split() if s not in NOT_SEGMENTS]
        heard = [SPANISH_SPELLING.get(s, s) for s in row["Confusion-IPA"].split() if s not in NOT_SEGMENTS]
        inventory.update(target)
        for a, b in substitution_pairs(target, heard):
            if a != b:
                counts[min(a, b), max(a, b)] += int(row["Consistency"])
    return counts, sorted(inventory)


def spanish(text: str) -> Pairs:
    counts, inventory = substitutions(text)
    return {pair: float(counts[pair]) for pair in combinations(inventory, 2)}


def load(cache: Path) -> Tuple[Dict[str, Pairs], dict]:
    """The four sets, and a description of each data source."""
    import pyreadr

    mandarin_file = fetch(MANDARIN_URL, cache / "mandarin.csv")
    clue_file = fetch(CLUE_URL, cache / "clue.tar.gz")
    hillenbrand_file = fetch(HILLENBRAND_URL, cache / "h95.zip")
    spanish_zip = fetch(SPANISH_URL, cache / "SpanishConfusionsCorpus.zip")
    spanish_file = cache / "confusionsCorpus.csv"
    with zipfile.ZipFile(spanish_zip) as z:
        spanish_file.write_bytes(z.read(SPANISH_MEMBER))
    rda = cache / "Phonemes.rda"
    with tarfile.open(clue_file) as t:
        rda.write_bytes(t.extractfile("clue/data/Phonemes.rda").read())
    frame = pyreadr.read_r(str(rda))["Phonemes"]
    with zipfile.ZipFile(hillenbrand_file) as z:
        vowels = z.read("iddata.dat").decode("latin-1")
    sets = {
        "mandarin": mandarin(mandarin_file.read_text(encoding="utf-8-sig")),
        "miller_nicely": miller_nicely(frame.values.tolist(), list(frame.columns)),
        "hillenbrand": hillenbrand(vowels),
        "spanish": spanish(spanish_file.read_text(encoding="utf-8")),
    }
    data = {
        "mandarin": {"url": MANDARIN_URL, "sha256": sha256(mandarin_file)},
        "miller_nicely": {"url": CLUE_URL, "sha256": sha256(clue_file), "version": "clue 0.3-55"},
        "hillenbrand": {"url": HILLENBRAND_URL, "sha256": sha256(hillenbrand_file)},
        "spanish": {"url": SPANISH_URL, "md5": SPANISH_MD5, "sha256": sha256(spanish_zip), "version": "Zenodo 3521449 v1"},
    }
    return sets, data


def score_set(system: System, pairs: Pairs, keep: Optional[List[Tuple[str, str]]] = None) -> dict:
    """The Spearman score and its bootstrap interval for the pairs in *keep* (all pairs when ``None``)."""
    chosen = list(pairs) if keep is None else keep
    distances = [system.segment_distance_or_one(a, b) for a, b in chosen]
    confusion = [pairs[p] for p in chosen]
    return {
        "score": similarity_score(distances, confusion),
        "interval": bootstrap_interval(distances, confusion),
        "pairs_out": len(chosen),
        "distance_range": [min(distances), max(distances)] if distances else None,
    }


def run(systems: List[System], split: str, cache: Path) -> dict:
    sets, data = load(Path(cache) / CACHE_NAME)
    payload = {"data": data, "pairs": {name: len(pairs) for name, pairs in sets.items()}, "systems": {}}
    common = {
        name: [p for p in pairs if all(s.reads(p[0]) and s.reads(p[1]) for s in systems)]
        for name, pairs in sets.items()
    }
    payload["common_subset_pairs"] = {name: len(keep) for name, keep in common.items()}
    for system in systems:
        row = {}
        for name, pairs in sets.items():
            unread = sum(not (system.reads(a) and system.reads(b)) for a, b in pairs)
            row[name] = {
                "pairs_in": len(pairs),
                "skipped": unread,
                "unread_at_1": score_set(system, pairs),
                "common_subset": score_set(system, pairs, common[name]),
            }
        payload["systems"][system.name] = row
    return payload


def lines(payload: dict) -> List[str]:
    def show(score: dict) -> str:
        return "undefined" if score["score"] is None else f"{score['score']:.3f}"

    return [
        f"{name}: " + "; ".join(f"{s} {show(r['unread_at_1'])} (skipped {r['skipped']})" for s, r in row.items())
        for name, row in payload["systems"].items()
    ]
