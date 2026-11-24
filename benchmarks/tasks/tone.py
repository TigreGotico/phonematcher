"""C7: does the tone distance follow how often Cantonese listeners confuse two tones?

Data: Wong, Cheng and Chen (2018), Frontiers in Psychology 9:1604, CC BY 4.0, Tables 12 and 13
(cue ORI, background QUI), transcribed by hand into ``benchmarks/data/cantonese-tone-confusions.csv``.
Two agents transcribed the tables independently and the files were byte-identical. The file gives
the table number in each row and the page in no row, because the article is online only. Each row
is a presented tone at one of three bands (B04, B08, B16) and the percent of responses per tone.
The rate P(y | x) is the mean of the three band rows of x, as a fraction. The rate of the pair
{x, y} is the mean of P(y | x) and P(x | y). All six tones are presented, so there are 15 pairs.

Chao values of the six Hong Kong Cantonese tones, read in full text from Europe PMC.

``main``: Alderete J. (2024), Frontiers in Psychology 15:1270433, doi 10.3389/fpsyg.2024.1270433,
Table 8 (online only, no page), caption "The six tones of Cantonese (Matthews and Yip, 2011, 27)."
Rows: "High level 55 ... High rising 35 ... Mid level 33 ... Low falling 21 ... Low rising 23 ...
Low level 22". So T1 55, T2 35, T3 33, T4 21, T5 23, T6 22.

``alternative``: Chen S. et al. (2024), PLoS ONE 19:e0306272, doi 10.1371/journal.pone.0306272,
introduction: "Tone 1 (55/53) ... Tone 2 (25) ... Tone 3 (33) ... Tone 4 (21) ... Tone 5 (23) ...
Tone 6 (22) (the numbers in bracket are Chao Tone Numeral, which marks the lowest pitch point with
1 and the highest with 5)". It differs from ``main`` in T2 (25 for 35); T1 is read as 55.

A Chao digit is a level, so the digits 3 and 5 become the tone letters ˧ and ˥: 35 is ˧˥.

Score: Spearman correlation of the negative ``phonematcher.tone.tone_distance`` with the pair rate.
The row ``phonematcher_features`` scores the feature distance of the vowel ``a`` with each tone, as
a word distance prices two toned vowels. The same is done for a baseline that has distance 0 when two tones have the same contour direction
(level, rising or falling, from the first and last digit) and 1 when they have not. A 95% bootstrap
interval comes from 1,000 resamples of the 15 pairs (seed 0). With 15 pairs this is a small check.
Only phonematcher and the baseline are scored. The other systems have no tone model.
"""
import csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

from phonematcher import feature_distance
from phonematcher.tone import tone_distance
from systems import System
from tasks.common import bootstrap_interval, sha256, similarity_score

SPLITS = ("seen",)

DATA = Path(__file__).resolve().parent.parent / "data" / "cantonese-tone-confusions.csv"
DATA_SHA256 = "3b61f7c48adf0617b8f9c7bb2b9ebcb67429d31e742ecc2e71648fc71fc50629"
SOURCE = "Wong, Cheng and Chen (2018), Frontiers in Psychology 9:1604, Tables 12 and 13, CC BY 4.0"
TONES = ["T1", "T2", "T3", "T4", "T5", "T6"]

CHAO = {
    "main": {"T1": "55", "T2": "35", "T3": "33", "T4": "21", "T5": "23", "T6": "22"},
    "alternative": {"T1": "55", "T2": "25", "T3": "33", "T4": "21", "T5": "23", "T6": "22"},
}
CHAO_SOURCES = {
    "main": "Alderete 2024, Frontiers in Psychology 15:1270433, Table 8, after Matthews and Yip 2011, p. 27",
    "alternative": "Chen et al. 2024, PLoS ONE 19:e0306272, introduction (T2 25, T1 read as 55)",
}
LETTERS = "˩˨˧˦˥"

Pairs = Dict[Tuple[str, str], float]


def tone_letters(chao: str) -> str:
    """The tone letters of a Chao numeral: ``35`` is ``˧˥``."""
    return "".join(LETTERS[int(digit) - 1] for digit in chao)


def direction(chao: str) -> str:
    """``level``, ``rising`` or ``falling``, from the first and last digit of a Chao numeral."""
    first, last = int(chao[0]), int(chao[-1])
    return "level" if first == last else "rising" if last > first else "falling"


def read_rows(path: Path = DATA) -> List[dict]:
    with open(path, encoding="utf8", newline="") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


def pair_rates(rows: List[dict]) -> Pairs:
    """The symmetric confusion rate of each pair of presented tones, as a fraction."""
    sums: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    bands: Dict[str, int] = defaultdict(int)
    for row in rows:
        bands[row["presented"]] += 1
        for tone in TONES:
            sums[row["presented"]][tone] += float(row[tone]) / 100
    rate = {x: {y: sums[x][y] / bands[x] for y in TONES} for x in bands}
    return {(x, y): (rate[x][y] + rate[y][x]) / 2 for x, y in combinations(TONES, 2)}


def phonematcher_distance(chao: Dict[str, str], a: str, b: str) -> float:
    return tone_distance(tone_letters(chao[a]), tone_letters(chao[b]))


def feature_row_distance(chao: Dict[str, str], a: str, b: str) -> float:
    return feature_distance("a" + tone_letters(chao[a]), "a" + tone_letters(chao[b]))


def direction_distance(chao: Dict[str, str], a: str, b: str) -> float:
    return 0.0 if direction(chao[a]) == direction(chao[b]) else 1.0


def score(distances: List[float], confusion: List[float]) -> dict:
    return {
        "score": similarity_score(distances, confusion),
        "interval": bootstrap_interval(distances, confusion),
        "pairs_in": len(confusion),
        "pairs_out": len(distances),
        "distance_range": [min(distances), max(distances)],
    }


def run(systems: List[System], split: str, cache: Path) -> dict:
    digest = sha256(DATA)
    if digest != DATA_SHA256:
        raise SystemExit(f"{DATA} has sha256 {digest}, not {DATA_SHA256}")
    pairs = pair_rates(read_rows())
    keys = list(pairs)
    confusion = [pairs[k] for k in keys]
    payload = {
        "data": {"source": SOURCE, "file": "benchmarks/data/cantonese-tone-confusions.csv", "sha256": digest},
        "pairs": len(pairs),
        "pair_rates": {f"{a}-{b}": r for (a, b), r in pairs.items()},
        "chao": {name: {"values": chao, "source": CHAO_SOURCES[name]} for name, chao in CHAO.items()},
        "scored": {},
        "not_scored": [s.name for s in systems if s.name != "phonematcher"],
        "not_scored_reason": "no tone model",
    }
    for name, chao in CHAO.items():
        row = {"direction_baseline": score([direction_distance(chao, a, b) for a, b in keys], confusion)}
        if any(s.name == "phonematcher" for s in systems):
            row["phonematcher"] = score([phonematcher_distance(chao, a, b) for a, b in keys], confusion)
            row["phonematcher_features"] = score([feature_row_distance(chao, a, b) for a, b in keys], confusion)
        payload["scored"][name] = row
    return payload


def lines(payload: dict) -> List[str]:
    def show(r: dict) -> str:
        i = r["interval"]
        return f"{r['score']:.3f} [{i['low']:.3f}, {i['high']:.3f}] (pairs {r['pairs_in']} in, {r['pairs_out']} out)"

    out = [f"{name} Chao values: {system} {show(r)}" for name, row in payload["scored"].items() for system, r in row.items()]
    out.append("not scored, no tone model: " + ", ".join(payload["not_scored"]))
    return out
