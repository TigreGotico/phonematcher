"""C1: how many of the segments in three corpora each system reads.

The orthography2ipa inventory is a set of TTS tokens. It holds the stress marks ˈ and ˌ on purpose
whenever a spec has stress rules, so both are dropped before counting, for every system. The bare
length mark ː and the bare ʲ stay in the count as unread: they are a known spec defect
(orthography2ipa issue 2443).

Corpora: PHOIBLE 2.0 (CC BY 4.0, a token is one inventory), the WikiPron TSV files (Apache-2.0,
a token is one occurrence) and the phone inventories of the orthography2ipa specs (a token is
one spec). A system reads a segment when its ``reads`` is true. For PHOIBLE a second count lets a
failed segment through when it reads with a tie bar between the pieces that
``phonematcher.segments`` finds in it. Every system gets the same retry.

``phonematcher_readings`` counts phonematcher twice: ``segments_only`` is ``vectorize_phones``
alone, and ``with_tones`` is the ``phonematcher`` system, which also reads the tones that the
library's tone parser accepts.

The empty string is never a segment. ``segments`` returns no pieces for a lone tone arrow, and
the empty join must not count as read.
"""
import csv
import io
import subprocess
from collections import Counter
from importlib import metadata
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

from phonematcher import segments, vectorize_phones

from systems import System
from tasks.common import PHOIBLE_URL, TIE, fetch, sha256

CACHE_NAME = "C1"
STRESS_MARKS = ("ˈ", "ˌ")
SPLITS = ("seen",)
WIKIPRON_URL = "https://github.com/CUNY-CL/wikipron"
Counts = Mapping[str, int]


class SegmentsOnly(System):
    """The reading rule of phonematcher without tones: ``vectorize_phones`` alone."""

    name = "segments_only"

    def reads(self, segment: str) -> bool:
        try:
            vectorize_phones(segment)
        except ValueError:
            return False
        return True


def phoible(cache: Path) -> Tuple[Dict[str, int], int, int]:
    """Segments of PHOIBLE, each Phoneme and each item of Allophones, with the inventories that
    list them. Returns the counts, the number of rows and the number of inventories."""
    text = fetch(PHOIBLE_URL, cache / "phoible.csv").read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    inventories: Dict[str, set] = {}
    for row in rows:
        items = [row["Phoneme"]]
        if row["Allophones"] not in ("", "NA"):
            items += row["Allophones"].split()
        for item in items:
            inventories.setdefault(item, set()).add(row["InventoryID"])
    return {s: len(ids) for s, ids in inventories.items()}, len(rows), len({r["InventoryID"] for r in rows})


def wikipron(cache: Path) -> Tuple[Dict[str, int], int]:
    """Segments of column 2 of every WikiPron TSV, split on spaces, with their occurrences."""
    repo = cache / "wikipron"
    if not repo.exists():
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", WIKIPRON_URL, str(repo)], check=True
        )
        subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "data/scrape/tsv"], check=True)
    counts: Counter = Counter()
    files = sorted((repo / "data" / "scrape" / "tsv").glob("*.tsv"))
    for path in files:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if len(fields) >= 2:
                    counts.update(fields[1].split())
    return dict(counts), len(files)


def orthography2ipa_inventories() -> Tuple[Dict[str, int], int]:
    """Segments of ``phoneme_inventory`` of every orthography2ipa spec, with the specs that list them."""
    from orthography2ipa import registry
    from orthography2ipa.inventory import phoneme_inventory

    codes = registry.available_codes()
    counts: Counter = Counter()
    for code in codes:
        counts.update(s for s in phoneme_inventory(registry.get(code)) if s not in STRESS_MARKS)
    return dict(counts), len(codes)


def reads(system: System, segment: str, tie_retry: bool = False) -> bool:
    """True when the system reads the segment, or with *tie_retry* the segment tied between its pieces."""
    if segment and system.reads(segment):
        return True
    if not tie_retry:
        return False
    tied = TIE.join(segments(segment))
    return bool(tied) and system.reads(tied)


def census(system: System, counts: Counts, tie_retry: bool = False) -> dict:
    """Types and tokens read by *system*, with the tie retry when *tie_retry* is set."""
    read = [s for s in counts if reads(system, s, tie_retry)]
    types, tokens = len(counts), sum(counts.values())
    tokens_read = sum(counts[s] for s in read)
    return {
        "types": types,
        "types_read": len(read),
        "types_unread": types - len(read),
        "type_share": len(read) / types,
        "tokens": tokens,
        "tokens_read": tokens_read,
        "token_share": tokens_read / tokens,
    }


def common(systems: List[System], counts: Counts, tie_retry: bool = False) -> dict:
    """The segments that every system reads: how many types and tokens."""
    shared = [s for s in counts if all(reads(system, s, tie_retry) for system in systems)]
    return {"types_read_by_all": len(shared), "tokens_read_by_all": sum(counts[s] for s in shared)}


def run(systems: List[System], split: str, cache: Path) -> dict:
    cache = Path(cache) / CACHE_NAME
    cache.mkdir(parents=True, exist_ok=True)
    phoible_counts, rows, inventories = phoible(cache)
    wikipron_counts, files = wikipron(cache)
    o2i_counts, specs = orthography2ipa_inventories()
    corpora = {
        "phoible": (phoible_counts, True),
        "wikipron": (wikipron_counts, False),
        "orthography2ipa": (o2i_counts, False),
    }
    commit = subprocess.run(
        ["git", "-C", str(cache / "wikipron"), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    payload = {
        "data": {
            "phoible": {"url": PHOIBLE_URL, "sha256": sha256(cache / "phoible.csv"), "rows": rows, "inventories": inventories},
            "wikipron": {"url": WIKIPRON_URL, "commit": commit, "files": files},
            "orthography2ipa": {"version": metadata.version("orthography2ipa"), "specs": specs, "dropped": list(STRESS_MARKS)},
        },
        "systems": {},
        "common_subset": {},
    }
    for name, (counts, retry_for_phoible) in corpora.items():
        payload["common_subset"][name] = {"direct": common(systems, counts)}
        if retry_for_phoible:
            payload["common_subset"][name]["tie_retry"] = common(systems, counts, tie_retry=True)
    for system in systems:
        payload["systems"][system.name] = {
            name: {"direct": census(system, counts), **({"tie_retry": census(system, counts, True)} if retry else {})}
            for name, (counts, retry) in corpora.items()
        }
    readings = {"segments_only": SegmentsOnly()}
    readings.update({"with_tones": system for system in systems if system.name == "phonematcher"})
    payload["phonematcher_readings"] = {
        label: {
            name: {"direct": census(reader, counts), **({"tie_retry": census(reader, counts, True)} if retry else {})}
            for name, (counts, retry) in corpora.items()
        }
        for label, reader in readings.items()
    }
    return payload


def lines(payload: dict) -> List[str]:
    out = []
    for name, corpora in payload["systems"].items():
        parts = []
        for corpus, variants in corpora.items():
            best = variants.get("tie_retry", variants["direct"])
            parts.append(f"{corpus} types {best['type_share']:.4f} tokens {best['token_share']:.4f}")
        out.append(f"{name}: " + "; ".join(parts))
    return out
