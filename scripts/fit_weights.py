"""Score feature weightings on data they were not fitted on, and fit candidate weightings.

The data are downloaded into a cache directory, not kept in the repository:

- Yu and Do (2023), Mandarin consonants, counts from a closed-set identification test (OSF rbt8x);
- Miller and Nicely (1955), 16 English consonants, the pooled similarity matrix of the R package
  clue (data set ``Phonemes``);
- Hillenbrand, Getty, Clark and Wheeler (1995), 12 American English vowels, labels from 20
  listeners (github.com/santiagobarreda/hillenbrand_et_al_1995, MIT licence);
- PHOIBLE 2.0 (Moran and McCloy, CC BY 4.0), the allophones of each inventory.

A confusion set scores a weighting by the Spearman correlation between the distance of a pair and
how often listeners confuse it. PHOIBLE scores it by the share of an inventory's other phonemes
that lie farther from a phoneme than its allophone does; even inventory ids are for fitting and odd
ones for scoring. Weightings fitted to the confusion sets are also scored with each set left out.
The weighting in the table is "current".

    uv pip install numpy scipy pandas pyreadr
    python scripts/fit_weights.py CACHE_DIR
"""
import csv
import io
import json
import sys
import tarfile
import urllib.request
import zipfile
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from phonematcher.distance import segments  # noqa: E402
from phonematcher.features import FEATURES, WEIGHTS, vectorize_phones  # noqa: E402

MANDARIN_URL = "https://osf.io/download/k9qzg/"
CLUE_URL = "https://cran.r-project.org/src/contrib/Archive/clue/clue_0.3-55.tar.gz"
PHOIBLE_URL = "https://raw.githubusercontent.com/phoible/dev/master/data/phoible.csv"
HILLENBRAND_URL = ("https://github.com/santiagobarreda/hillenbrand_et_al_1995/raw/"
                   "main/h95-alldata.zip")

MILLER_NICELY = {"PA": "p", "TA": "t", "KA": "k", "FA": "f", "THETA": "θ", "SA": "s", "SHA": "ʃ",
                 "BA": "b", "DA": "d", "GA": "ɡ", "VA": "v", "THAT": "ð", "ZA": "z", "ZHA": "ʒ",
                 "MA": "m", "NA": "n"}
#: Hillenbrand's labels by their key words, heed ... heard, in broad IPA.
HILLENBRAND = {"iy": "i", "ih": "ɪ", "ei": "e", "eh": "ɛ", "ae": "æ", "ah": "ɑ", "aw": "ɔ",
               "oa": "o", "oo": "ʊ", "uw": "u", "uh": "ʌ", "er": "ɝ"}
#: Features that share one fitted factor, so the fit has a few free numbers, not 36.
GROUPS = {
    "major class": ("syl", "son", "cons"),
    "manner": ("cont", "delrel", "lat", "nas", "strid", "tap", "trill", "velaric"),
    "laryngeal": ("voi", "sg", "cg"),
    "place": ("ant", "cor", "distr", "lab"),
    "tongue body": ("hi", "lo", "back", "round", "front"),
    "vowel": ("tense", "long", "atr", "h1", "h2", "h3", "h4", "h5", "h6"),
    "secondary": ("palatalized", "velarized", "labialized", "pharyngealized"),
}
GROUP_OF = np.array([next(i for i, g in enumerate(GROUPS.values()) if f in g) for f in FEATURES])

#: The Mandarin file writes affricates without a tie bar.
TIED = {"ts": "t͡s", "tsʰ": "t͡sʰ", "tɕ": "t͡ɕ", "tɕʰ": "t͡ɕʰ", "ʈʂ": "ʈ͡ʂ", "ʈʂʰ": "ʈ͡ʂʰ"}


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        with urllib.request.urlopen(url) as r:
            path.write_bytes(r.read())
    return path


def symmetric_rates(labels, counts):
    """Pairs (a, b) with the mean of P(b heard for a) and P(a heard for b)."""
    rates = counts / counts.sum(axis=1, keepdims=True)
    return {(labels[i], labels[j]): (rates[i, j] + rates[j, i]) / 2
            for i, j in combinations(range(len(labels)), 2)}


def mandarin(cache: Path):
    rows = list(csv.reader(io.StringIO(fetch(MANDARIN_URL, cache / "mandarin.csv")
                                       .read_text(encoding="utf-8-sig"))))
    body = [r for r in rows[1:] if r and r[0]]
    labels = [r[-1].strip("/") for r in body]
    labels = [TIED.get(s, s) for s in labels]
    counts = np.array([[float(x) for x in r[1:1 + len(body)]] for r in body])
    return symmetric_rates(labels, counts)


def miller_nicely(cache: Path):
    import pyreadr
    tar = fetch(CLUE_URL, cache / "clue.tar.gz")
    rda = cache / "Phonemes.rda"
    if not rda.exists():
        with tarfile.open(tar) as t:
            rda.write_bytes(t.extractfile("clue/data/Phonemes.rda").read())
    df = pyreadr.read_r(str(rda))["Phonemes"]
    labels = [MILLER_NICELY[c] for c in df.columns]
    return {(labels[i], labels[j]): float(df.iat[i, j])
            for i, j in combinations(range(len(labels)), 2)}


def hillenbrand(cache: Path):
    with zipfile.ZipFile(fetch(HILLENBRAND_URL, cache / "h95.zip")) as z:
        text = z.read("iddata.dat").decode("latin-1")
    keys = list(HILLENBRAND)
    counts = np.zeros((len(keys), len(keys)))
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 14 and parts[0][:1] in "mwbg" and parts[0][1:3].isdigit():
            counts[keys.index(parts[0][3:5])] += [float(x) for x in parts[2:14]]
    return symmetric_rates([HILLENBRAND[k] for k in keys], counts)


def feature_costs(pairs):
    """Per pair, the cost of each feature: 0 equal, 0.5 for 0 against + or -, 1 for + against -."""
    def cost(x, y):
        return 0.0 if x == y else 0.5 if x is None or y is None else 1.0
    return np.array([[cost(x, y) for x, y in zip(vectorize_phones(a), vectorize_phones(b))]
                     for a, b in pairs])


def score(weights, data) -> float:
    """Spearman correlation of similarity (negative distance) with confusion."""
    costs, confusion = data
    return spearmanr(-(costs @ weights), confusion).statistic


def phoible(cache: Path):
    """Phoneme-allophone items of every PHOIBLE inventory: the costs from the phoneme to the
    allophone, and to each other phoneme of the inventory. A multi-letter PHOIBLE segment is one
    segment, so its letters are joined by a tie bar."""
    rows = csv.DictReader(io.StringIO(fetch(PHOIBLE_URL, cache / "phoible.csv")
                                      .read_text(encoding="utf-8")))
    inventories = {}
    for r in rows:
        inventories.setdefault(int(r["InventoryID"]), []).append(r)
    vectors = {}

    def vector(s):
        if s not in vectors:
            vectors[s] = None
            for form in (s, "\u0361".join(segments(s))):
                try:
                    vectors[s] = np.array([2 if x is None else int(x)
                                           for x in vectorize_phones(form)])
                    break
                except ValueError:
                    pass
        return vectors[s]

    def cost(a, b):
        return np.where(a == b, 0.0, np.where((a == 2) | (b == 2), 0.5, 1.0))

    items = {0: [], 1: []}
    for iid, rs in inventories.items():
        phonemes = [r["Phoneme"] for r in rs if vector(r["Phoneme"]) is not None]
        for r in rs:
            p = r["Phoneme"]
            for a in r["Allophones"].split() if r["Allophones"] not in ("", "NA") else []:
                others = [q for q in phonemes if q not in (p, a)]
                if a != p and vector(p) is not None and vector(a) is not None and others:
                    items[iid % 2].append((cost(vector(p), vector(a)),
                                           np.array([cost(vector(p), vector(q)) for q in others])))
    return items


def allophone_score(weights, items) -> float:
    """Mean share of an inventory's other phonemes that lie farther from a phoneme than its
    allophone does."""
    shares = []
    for to_allophone, to_others in items:
        a, o = to_allophone @ weights, to_others @ weights
        shares.append(((o > a).sum() + 0.5 * (o == a).sum()) / len(o))
    return float(np.mean(shares))


def fit(start, objective, penalty=0.05):
    """Seven group factors that maximize *objective*: weights are start * exp(theta) per group,
    so they stay positive, and the penalty keeps theta near 0."""
    def loss(theta):
        return -objective(start * np.exp(theta[GROUP_OF])) + penalty * np.mean(theta ** 2)
    res = minimize(loss, np.zeros(len(GROUPS)), method="Powell",
                   options={"maxiter": 20000, "xtol": 1e-3, "ftol": 1e-5})
    return start * np.exp(res.x[GROUP_OF])


def main(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    confusion = {}
    for name, load in (("mandarin", mandarin), ("miller_nicely", miller_nicely),
                       ("hillenbrand", hillenbrand)):
        pairs = load(cache)
        keys = list(pairs)
        confusion[name] = (feature_costs(keys), np.array([pairs[k] for k in keys]))
    allophones = phoible(cache)
    print({n: len(d[1]) for n, d in confusion.items()},
          {"allophones, train": len(allophones[0]), "allophones, test": len(allophones[1])})

    current, uniform = np.array(WEIGHTS, dtype=float), np.ones(len(FEATURES))
    candidates = {"current": current, "uniform": uniform}
    for start_name, start in (("current", current), ("uniform", uniform)):
        candidates[f"variant from {start_name}"] = fit(
            start, lambda w: allophone_score(w, allophones[0]))
        candidates[f"perceptual from {start_name}"] = fit(
            start, lambda w: np.mean([score(w, d) for d in confusion.values()]))
    # Perceptual weights are also fitted with each confusion set left out, to score them on it.
    for name, w in candidates.items():
        row = {"allophones (odd inventories)": allophone_score(w, allophones[1])}
        row.update({n: score(w, d) for n, d in confusion.items()})
        print(name, {k: round(float(v), 4) for k, v in row.items()})
    for held in confusion:
        train = [d for n, d in confusion.items() if n != held]
        for start_name, start in (("current", current), ("uniform", uniform)):
            w = fit(start, lambda w: np.mean([score(w, d) for d in train]))
            print(f"perceptual from {start_name}, {held} left out:",
                  round(float(score(w, confusion[held])), 4))
    out = {name: {f: round(float(x), 4) for f, x in zip(FEATURES, w)}
           for name, w in candidates.items()}
    (cache / "candidates.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
