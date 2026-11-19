"""Fit the feature weights to human perceptual confusions, and score weightings on held-out data.

The data are downloaded into a cache directory, not kept in the repository:

- Yu and Do (2023), Mandarin consonants, counts from a closed-set identification test (OSF rbt8x);
- Miller and Nicely (1955), 16 English consonants, the pooled similarity matrix of the R package
  clue (data set ``Phonemes``);
- Hillenbrand, Getty, Clark and Wheeler (1995), 12 American English vowels, labels from 20
  listeners (github.com/santiagobarreda/hillenbrand_et_al_1995, MIT licence).

A weighting is scored per data set by the Spearman correlation between the feature distance of a
pair and how often listeners confuse it. The fit runs leave one data set out: it fits on two and
scores on the third, so every reported score is on data the fit did not see.

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
from phonematcher.features import FEATURES, WEIGHTS, vectorize_phones  # noqa: E402

MANDARIN_URL = "https://osf.io/download/k9qzg/"
CLUE_URL = "https://cran.r-project.org/src/contrib/Archive/clue/clue_0.3-55.tar.gz"
HILLENBRAND_URL = ("https://github.com/santiagobarreda/hillenbrand_et_al_1995/raw/"
                   "main/h95-alldata.zip")

MILLER_NICELY = {"PA": "p", "TA": "t", "KA": "k", "FA": "f", "THETA": "θ", "SA": "s", "SHA": "ʃ",
                 "BA": "b", "DA": "d", "GA": "ɡ", "VA": "v", "THAT": "ð", "ZA": "z", "ZHA": "ʒ",
                 "MA": "m", "NA": "n"}
#: Hillenbrand's labels by their key words, heed ... heard, in broad IPA.
HILLENBRAND = {"iy": "i", "ih": "ɪ", "ei": "e", "eh": "ɛ", "ae": "æ", "ah": "ɑ", "aw": "ɔ",
               "oa": "o", "oo": "ʊ", "uw": "u", "uh": "ʌ", "er": "ɝ"}
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


def fit(start, train, penalty=0.05):
    """Weights as start * exp(theta), so they stay positive; the penalty keeps theta near 0."""
    def loss(theta):
        w = start * np.exp(theta)
        return -np.mean([score(w, d) for d in train]) + penalty * np.mean(theta ** 2)
    res = minimize(loss, np.zeros(len(start)), method="Powell",
                   options={"maxiter": 20000, "xtol": 1e-3, "ftol": 1e-5})
    return start * np.exp(res.x)


def main(cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    sets = {"mandarin": mandarin(cache), "miller_nicely": miller_nicely(cache),
            "hillenbrand": hillenbrand(cache)}
    data = {}
    for name, pairs in sets.items():
        keys = list(pairs)
        data[name] = (feature_costs(keys), np.array([pairs[k] for k in keys]))
        print(f"{name}: {len(keys)} pairs")
    current = np.array(WEIGHTS, dtype=float)
    uniform = np.ones(len(FEATURES))
    report = {}
    for held in data:
        train = [d for n, d in data.items() if n != held]
        fitted = fit(current, train)
        report[held] = {"current": score(current, data[held]),
                        "uniform": score(uniform, data[held]),
                        "fitted": score(fitted, data[held])}
        print(held, {k: round(v, 3) for k, v in report[held].items()})
    print(json.dumps(report))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
