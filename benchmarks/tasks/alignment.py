"""Task alignment: reproduce the gold pairwise alignments of the Benchmark Database of Phonetic
Alignments (List and Prokic 2014).

The gold standard is ``benchmark/psa/full.psa`` (7,126 word pairs) and ``covington.psa`` (81 pairs)
of github.com/SequenceComparison/SupplementaryMaterial. The data is read from a cache and never
committed. An item's split key is the file name and the pair index, as ``full.psa:17``.

Scores, as List (2014, ch. 4.2) defines them:

* perfect alignments score (PAS): the share of pairs whose test alignment equals the gold alignment.
* column score (CS): ``2 * |Ct & Cr| / (|Cr| + |Ct|)`` for the columns of one alignment, averaged
  over the pairs. A column is a residue pair: the index of the segment in each word, or 0 for a gap.

A system skips an item when it cannot read a segment of either word. The common-subset score runs
over the items no system skips. The all-items score gives a skipped item 0 for both measures.
"""
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from split import is_test
from systems import UnreadSegment, build

URL = "https://github.com/SequenceComparison/SupplementaryMaterial"
SHA = "cc4bf855f9549867e86157f49ac03608717b95c2"
FILES = ("full.psa", "covington.psa")
SYSTEMS = ("phonematcher", "levenshtein", "aline", "sca")

Row = List[str]
Item = Tuple[str, Row, Row]


def fetch(cache: Path) -> Path:
    """The data directory at the pinned commit, fetched into *cache* when missing."""
    clone = Path(cache) / "alignment" / f"SupplementaryMaterial-{SHA[:8]}"
    if not clone.exists():
        clone.mkdir(parents=True)
        git = ["git", "-C", str(clone)]
        subprocess.run([*git, "init", "--quiet"], check=True)
        subprocess.run([*git, "fetch", "--quiet", "--depth", "1", URL, SHA], check=True)
        subprocess.run([*git, "-c", "advice.detachedHead=false", "checkout", "--quiet", "FETCH_HEAD"], check=True)
    return clone / "benchmark" / "psa"


def parse(text: str) -> List[Tuple[Row, Row]]:
    """The gold alignments of one PSA file, as pairs of rows with ``-`` for a gap. A block holds a
    title line, two rows (a language name, then one segment per tab-separated field) and a ``#`` score line."""
    blocks = text.split("\n\n")
    pairs = []
    for block in blocks:
        lines = [line for line in block.strip("\n").split("\n") if line]
        rows = [line.split("\t")[1:] for line in lines if "\t" in line]
        if len(rows) == 2:
            pairs.append((rows[0], rows[1]))
    return pairs


def load(directory: Path, split: str) -> Tuple[List[Item], int]:
    """The items of *split* (``dev`` or ``seen``) and the number of items left out for the other side."""
    items: List[Item] = []
    left_out = 0
    for name in FILES:
        for index, (a, b) in enumerate(parse((directory / name).read_text(encoding="utf8"))):
            key = f"{name}:{index}"
            if is_test(key) == (split == "test"):
                items.append((key, a, b))
            else:
                left_out += 1
    return items, left_out


def columns(row_a: Sequence[str], row_b: Sequence[str]) -> List[Tuple[int, int]]:
    """The residue pairs of an alignment: the 1-based index of each segment, 0 for a gap."""
    x = y = 0
    out = []
    for a, b in zip(row_a, row_b):
        if a != "-":
            x += 1
        if b != "-":
            y += 1
        out.append((x if a != "-" else 0, y if b != "-" else 0))
    return out


def column_score(gold: Tuple[Row, Row], test: Tuple[Row, Row]) -> float:
    cr, ct = columns(*gold), columns(*test)
    return 2 * len(set(cr) & set(ct)) / (len(cr) + len(ct))


def as_rows(pairs) -> Tuple[Row, Row]:
    return [a or "-" for a, _ in pairs], [b or "-" for _, b in pairs]


def evaluate(system, items: Sequence[Item]) -> Dict[str, Optional[Tuple[float, float]]]:
    """Per item key: ``(perfect, column score)``, or ``None`` when the system skips the item."""
    scores: Dict[str, Optional[Tuple[float, float]]] = {}
    for key, a, b in items:
        word_a, word_b = [s for s in a if s != "-"], [s for s in b if s != "-"]
        try:
            test = as_rows(system.align(word_a, word_b))
        except UnreadSegment:
            scores[key] = None
            continue
        scores[key] = (float(test == (a, b)), column_score((a, b), test))
    return scores


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def summarize(per_system: Dict[str, Dict[str, Optional[Tuple[float, float]]]], keys: Sequence[str]) -> dict:
    common: Set[str] = {k for k in keys if all(per_system[n][k] is not None for n in per_system)}
    systems = {}
    for name, scores in per_system.items():
        read = [scores[k] for k in keys if scores[k] is not None]
        on_common = [scores[k] for k in keys if k in common]
        everything = [scores[k] or (0.0, 0.0) for k in keys]
        systems[name] = {
            "n_in": len(keys),
            "n_scored": len(read),
            "n_skipped": len(keys) - len(read),
            "common_pas": mean([p for p, _ in on_common]),
            "common_cs": mean([c for _, c in on_common]),
            "unread_at_zero_pas": mean([p for p, _ in everything]),
            "unread_at_zero_cs": mean([c for _, c in everything]),
        }
    return {"n_common": len(common), "systems": systems}


def score(names: Sequence[str], cache: Path, split: str, limit: int = 0) -> Tuple[dict, Dict[str, Dict[str, Optional[Tuple[float, float]]]]]:
    """Score the systems on the items of *split*; also returns each system's score per item key.
    *limit* keeps about that many items, evenly spaced."""
    directory = fetch(cache)
    items, left_out = load(directory, split)
    items = items[:: -(-len(items) // limit)] if limit else items
    keys = [key for key, _, _ in items]
    per_system = {name: evaluate(build(name, cache), items) for name in names}
    by_file = {}
    for name in FILES:
        file_keys = [k for k in keys if k.startswith(name + ":")]
        by_file[name] = {"n_in": len(file_keys), **summarize(per_system, file_keys)}
    payload = {
        "data": {"source": URL, "sha": SHA, "files": list(FILES)},
        "n_in": len(items) + left_out,
        "n_items": len(items),
        "n_left_out": left_out,
        "all": summarize(per_system, keys),
        "by_file": by_file,
    }
    return payload, per_system


def run(names: Sequence[str], cache: Path, split: str) -> dict:
    """Score the systems on the items of *split*. Returns the payload that ``run.py`` writes."""
    return score(names, cache, split)[0]
