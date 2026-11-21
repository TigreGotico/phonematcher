"""Count the segments of three corpora that phonematcher cannot read.

    python scripts/coverage.py CACHE_DIR

Corpora: PHOIBLE 2.0 (CC BY 4.0), WikiPron (Apache-2.0) and the phone inventories of the
orthography2ipa specs. The first two are downloaded into CACHE_DIR; orthography2ipa must be
installed (``uv pip install --prerelease=allow orthography2ipa``). It is not a dependency of
phonematcher. A segment is read when ``vectorize_phones`` returns without ``ValueError``.
For each corpus the script prints one table and writes CACHE_DIR/unread-<corpus>.tsv.
"""
import csv
import io
import subprocess
import sys
import unicodedata
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Tuple

from phonematcher import segments, vectorize_phones
from phonematcher.tone import is_tone

PHOIBLE_URL = "https://raw.githubusercontent.com/phoible/dev/master/data/phoible.csv"
WIKIPRON_URL = "https://github.com/CUNY-CL/wikipron"
PHOIBLE_ROWS, PHOIBLE_INVENTORIES = 105_484, 3_020
TIE = "͡"


@dataclass
class Census:
    """The outcome of reading every distinct segment of one corpus."""
    distinct: int
    read: int
    read_by_tie: int
    unread: Dict[str, int]
    tokens: int
    tokens_read: int
    #: Unread segments that ``segments`` splits into pieces that each read or are tones, and
    #: their tokens. They are a subset of ``unread``.
    split_readable: int = 0
    tokens_split_readable: int = 0


def reads(segment: str) -> bool:
    try:
        vectorize_phones(segment)
    except ValueError:
        return False
    return True


def census(counts: Mapping[str, int], tie_retry: bool = False) -> Census:
    """Read each segment of *counts* (segment to token count).

    With *tie_retry*, a segment that fails is read a second time with a tie bar between the parts
    that ``segments`` finds in it. Those segments count in ``read_by_tie``, not in ``read``.
    """
    read = read_by_tie = tokens_read = split_readable = tokens_split_readable = 0
    unread: Dict[str, int] = {}
    for segment, n in counts.items():
        if reads(segment):
            read += 1
        elif tie_retry and reads(TIE.join(segments(segment))):
            read_by_tie += 1
        else:
            unread[segment] = n
            pieces = segments(segment)
            if len(pieces) > 1 and all(is_tone(p) or reads(p) for p in pieces):
                split_readable += 1
                tokens_split_readable += n
            continue
        tokens_read += n
    return Census(len(counts), read, read_by_tie, unread, sum(counts.values()), tokens_read,
                  split_readable, tokens_split_readable)


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        with urllib.request.urlopen(url) as response:
            path.write_bytes(response.read())
    return path


def phoible(cache: Path) -> Tuple[Dict[str, int], Dict[str, str], int, int]:
    """Segments of PHOIBLE: each Phoneme and each item of Allophones. A token is one inventory
    that lists the segment."""
    text = fetch(PHOIBLE_URL, cache / "phoible.csv").read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    inventories: Dict[str, set] = {}
    for r in rows:
        items = [r["Phoneme"]]
        if r["Allophones"] not in ("", "NA"):
            items += r["Allophones"].split()
        for item in items:
            inventories.setdefault(item, set()).add(r["InventoryID"])
    counts = {s: len(ids) for s, ids in inventories.items()}
    examples = {s: min(ids, key=int) for s, ids in inventories.items()}
    return counts, examples, len(rows), len({r["InventoryID"] for r in rows})


def wikipron(cache: Path) -> Tuple[Dict[str, int], Dict[str, str], int]:
    """Segments of column 2 of every WikiPron TSV, split on spaces. A token is one occurrence."""
    repo = cache / "wikipron"
    if not repo.exists():
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                        WIKIPRON_URL, str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "data/scrape/tsv"],
                       check=True)
    counts: Counter = Counter()
    examples: Dict[str, str] = {}
    files = sorted((repo / "data" / "scrape" / "tsv").glob("*.tsv"))
    for path in files:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 2:
                    continue
                for segment in fields[1].split():
                    counts[segment] += 1
                    examples.setdefault(segment, f"{path.stem}:{fields[0]}")
    return dict(counts), examples, len(files)


def orthography2ipa_inventories() -> Tuple[Dict[str, int], Dict[str, str], int]:
    """Segments of ``phoneme_inventory`` of every language spec. A token is one spec."""
    from orthography2ipa import registry
    from orthography2ipa.inventory import phoneme_inventory

    codes = registry.available_codes()
    counts: Counter = Counter()
    examples: Dict[str, str] = {}
    for code in codes:
        for segment in phoneme_inventory(registry.get(code)):
            counts[segment] += 1
            examples.setdefault(segment, code)
    return dict(counts), examples, len(codes)


def codepoints(segment: str) -> str:
    return " ".join(f"U+{ord(c):04X}" for c in segment)


def report(name: str, counts: Mapping[str, int], examples: Mapping[str, str], cache: Path,
           unit: str, tie_retry: bool = False) -> Census:
    result = census(counts, tie_retry)
    total_read = result.read + result.read_by_tie
    unread = len(result.unread)
    assert total_read + unread == result.distinct == len(counts)
    print(f"\n{name}  ({unit})")
    print(f"  distinct segments in : {result.distinct}")
    print(f"  read                 : {result.read}")
    if tie_retry:
        print(f"  read after tie bar   : {result.read_by_tie}")
    print(f"  unread               : {unread}")
    print(f"  read + unread = in   : {total_read} + {unread} = {total_read + unread}")
    print(f"  share read by type   : {total_read / result.distinct:.4f}")
    if tie_retry:
        print(f"  share read, no retry : {result.read / result.distinct:.4f}")
    print(f"  tokens read / total  : {result.tokens_read} / {result.tokens}")
    print(f"  share read by token  : {result.tokens_read / result.tokens:.4f}")
    print(f"  unread, readable once segments() splits them: {result.split_readable} segments, "
          f"{result.tokens_split_readable} tokens")
    out = cache / f"unread-{name}.tsv"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("segment\tcodepoints\ttokens\texample\n")
        for segment, n in sorted(result.unread.items(), key=lambda kv: (-kv[1], kv[0])):
            fh.write(f"{segment}\t{codepoints(unicodedata.normalize('NFD', segment))}\t{n}\t"
                     f"{examples[segment]}\n")
    print(f"  wrote {unread} rows to {out}")
    return result


def main(cache_dir: str) -> None:
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    counts, examples, rows, inventories = phoible(cache)
    print(f"PHOIBLE rows: {rows} (expected {PHOIBLE_ROWS}); inventories: {inventories} "
          f"(expected {PHOIBLE_INVENTORIES})")
    report("phoible", counts, examples, cache, "segment; token = inventory", tie_retry=True)

    counts, examples, files = wikipron(cache)
    print(f"\nWikiPron files: {files}")
    report("wikipron", counts, examples, cache, "segment; token = occurrence")

    counts, examples, specs = orthography2ipa_inventories()
    print(f"\northography2ipa specs: {specs}")
    report("orthography2ipa", counts, examples, cache, "phone; token = spec")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
