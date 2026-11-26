"""Count the segments of three corpora that phonematcher cannot read.

    python scripts/coverage.py CACHE_DIR

Corpora: PHOIBLE 2.0 (CC BY 4.0), WikiPron (Apache-2.0) and the phone inventories of the
orthography2ipa specs, read by the loaders of ``benchmarks/tasks/coverage.py``, which also drop
the stress marks of the orthography2ipa inventories. The first two are downloaded into CACHE_DIR.
The script needs the ``bench`` extra, which holds orthography2ipa. A segment is read when
``vectorize_phones`` returns without ``ValueError``. For each corpus the script prints one table
and writes CACHE_DIR/unread-<corpus>.tsv.
"""
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

from phonematcher import segments  # noqa: E402
from phonematcher.tone import is_tone  # noqa: E402
from tasks.coverage import SegmentsOnly, orthography2ipa_inventories, phoible, reads, wikipron  # noqa: E402

PHOIBLE_ROWS, PHOIBLE_INVENTORIES = 105_484, 3_020
READER = SegmentsOnly()


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


def census(counts: Mapping[str, int], tie_retry: bool = False) -> Census:
    """Read each segment of *counts* (segment to token count) with the reading rule of
    ``benchmarks/tasks/coverage.py``.

    With *tie_retry*, a segment that fails is read a second time with a tie bar between the parts
    that ``segments`` finds in it. Those segments count in ``read_by_tie``, not in ``read``.
    """
    read = read_by_tie = tokens_read = split_readable = tokens_split_readable = 0
    unread: Dict[str, int] = {}
    for segment, n in counts.items():
        if reads(READER, segment):
            read += 1
        elif tie_retry and reads(READER, segment, tie_retry=True):
            read_by_tie += 1
        else:
            unread[segment] = n
            pieces = segments(segment)
            if len(pieces) > 1 and all(is_tone(p) or reads(READER, p) for p in pieces):
                split_readable += 1
                tokens_split_readable += n
            continue
        tokens_read += n
    return Census(len(counts), read, read_by_tie, unread, sum(counts.values()), tokens_read,
                  split_readable, tokens_split_readable)


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
            codepoints = " ".join(f"U+{ord(c):04X}" for c in unicodedata.normalize("NFD", segment))
            fh.write(f"{segment}\t{codepoints}\t{n}\t{examples[segment]}\n")
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
