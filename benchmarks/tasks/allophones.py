"""C2: does a system keep a phoneme nearer to its allophone than to the other phonemes?

Data: the Allophones column of PHOIBLE 2.0 (CC BY 4.0). An item is one phoneme, one of its
allophones, and the other phonemes of the same inventory. The score of an item is the share of
those other phonemes that lie farther from the phoneme than the allophone does, where a tie
counts one half. The score of a system is the mean over items. A multi-letter PHOIBLE segment
that a system does not read is read a second time with a tie bar between its pieces
(``tie_retry``); the ``direct`` variant gives every system the segments unchanged.

Three scores come from every variant:

- ``read_only``: items whose phoneme and allophone the system reads, against the other phonemes
  that it reads. Items the system cannot score are skipped and counted.
- ``common_subset``: the same, but a segment counts only when every system reads it.
- ``unread_at_1``: every item, against every other phoneme. An unread segment is at distance 1.
"""
import csv
import io
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

from phonematcher import segments

from systems import System
from tasks.common import PHOIBLE_URL, TIE, fetch, sha256

CACHE_NAME = "C2"
SPLITS = ("seen",)


class Item(NamedTuple):
    inventory: int
    phoneme: str
    allophone: str
    phonemes: Tuple[str, ...]


def items(text: str) -> List[Item]:
    """Every phoneme-allophone pair of a PHOIBLE CSV whose allophone differs from the phoneme."""
    inventories: Dict[int, List[dict]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        inventories.setdefault(int(row["InventoryID"]), []).append(row)
    found = []
    for inventory, rows in inventories.items():
        phonemes = tuple(r["Phoneme"] for r in rows)
        for row in rows:
            listed = row["Allophones"].split() if row["Allophones"] not in ("", "NA") else []
            found += [Item(inventory, row["Phoneme"], a, phonemes) for a in listed if a != row["Phoneme"]]
    return found


def share_farther(to_allophone: float, to_others: List[float]) -> float:
    """The share of *to_others* above *to_allophone*, ties counting one half."""
    farther = sum(d > to_allophone for d in to_others) + 0.5 * sum(d == to_allophone for d in to_others)
    return farther / len(to_others)


def form_of(system: System, segment: str, tie_retry: bool) -> Optional[str]:
    """The string the system reads for *segment*, or ``None``: the segment itself, or with *tie_retry*
    the segment tied between the pieces that ``segments`` finds in it."""
    if segment and system.reads(segment):
        return segment
    tied = TIE.join(segments(segment)) if tie_retry else ""
    return tied if tied and system.reads(tied) else None


def score_items(
    found: List[Item], form: Callable[[str], Optional[str]], distance: Callable[[str, str], float], keep_unread: bool
) -> Tuple[Optional[float], int]:
    """The mean item score and the number of items scored.

    With *keep_unread* every item scores and ``distance`` gets ``None`` for an unread segment;
    otherwise an item needs a readable phoneme and allophone, and only readable other phonemes count.
    """
    shares = []
    for item in found:
        p, a = form(item.phoneme), form(item.allophone)
        others = [q for q in item.phonemes if q not in (item.phoneme, item.allophone)]
        if not keep_unread:
            if p is None or a is None:
                continue
            others = [q for q in others if form(q) is not None]
        if not others:
            continue
        shares.append(share_farther(distance(p, a), [distance(p, form(q)) for q in others]))
    return (sum(shares) / len(shares) if shares else None), len(shares)


def variant(systems: List[System], found: List[Item], tie_retry: bool) -> dict:
    """The scores of every system for one reading rule, as ``{system: {inventory subset: scores}}``."""
    forms: Dict[Tuple[str, str], Optional[str]] = {}
    shared: Dict[str, bool] = {}

    def form(system: System, segment: str) -> Optional[str]:
        if (system.name, segment) not in forms:
            forms[system.name, segment] = form_of(system, segment, tie_retry)
        return forms[system.name, segment]

    def read_by_all(segment: str) -> bool:
        if segment not in shared:
            shared[segment] = all(form(s, segment) is not None for s in systems)
        return shared[segment]

    results: Dict[str, dict] = {}
    for system in systems:
        memo: Dict[Tuple[str, str], float] = {}

        def own(segment: str) -> Optional[str]:
            return form(system, segment)

        def common(segment: str) -> Optional[str]:
            return form(system, segment) if read_by_all(segment) else None

        def distance(x: Optional[str], y: Optional[str]) -> float:
            if x is None or y is None:
                return 1.0
            if (x, y) not in memo:
                memo[x, y] = 0.0 if x == y else system.segment_distance(x, y)
            return memo[x, y]

        row = {}
        subsets = {"all": found, "odd": [i for i in found if i.inventory % 2], "even": [i for i in found if not i.inventory % 2]}
        for label, parts in subsets.items():
            row[label] = {"items_in": len(parts)}
            for key, reading, keep in (("read_only", own, False), ("common_subset", common, False), ("unread_at_1", own, True)):
                score, out = score_items(parts, reading, distance, keep_unread=keep)
                row[label][key] = {"score": score, "items_out": out, "skipped": len(parts) - out}
        results[system.name] = row
    return results


def run(systems: List[System], split: str, cache: Path) -> dict:
    cache = Path(cache) / CACHE_NAME
    path = fetch(PHOIBLE_URL, cache / "phoible.csv")
    found = items(path.read_text(encoding="utf-8"))
    payload = {"data": {"phoible": {"url": PHOIBLE_URL, "sha256": sha256(path), "items": len(found)}}, "systems": {}}
    by_variant = {"direct": variant(systems, found, False), "tie_retry": variant(systems, found, True)}
    for system in systems:
        payload["systems"][system.name] = {name: results[system.name] for name, results in by_variant.items()}
    return payload


def lines(payload: dict) -> List[str]:
    out = []
    for name, variants in payload["systems"].items():
        parts = []
        for label, row in variants.items():
            score = row["all"]["unread_at_1"]["score"]
            parts.append(f"{label} unread-at-1 {score:.4f} read-only {row['all']['read_only']['score']:.4f}")
        out.append(f"{name}: " + "; ".join(parts))
    return out
