"""Helpers that the seen-data tasks share: downloads, Spearman and its bootstrap interval."""
import hashlib
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
from scipy.stats import spearmanr

PHOIBLE_URL = "https://raw.githubusercontent.com/phoible/dev/master/data/phoible.csv"


def fetch(url: str, path: Path, md5: Optional[str] = None) -> Path:
    """Download *url* to *path* unless the file exists. With *md5*, raise ``SystemExit`` when the
    file has another md5."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as response:
            path.write_bytes(response.read())
    if md5 is not None and hashlib.md5(path.read_bytes()).hexdigest() != md5:
        raise SystemExit(f"{path} does not match md5 {md5}")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spearman(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Spearman correlation, or ``None`` when either side is constant and the value is undefined."""
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    return float(spearmanr(x, y).statistic)


def similarity_score(distances: Sequence[float], confusion: Sequence[float]) -> Optional[float]:
    """Spearman correlation of the negative distance with the confusion."""
    return spearman([-d for d in distances], confusion)


def bootstrap_interval(
    distances: Sequence[float], confusion: Sequence[float], resamples: int = 1000, seed: int = 0
) -> Dict[str, Optional[float]]:
    """The 2.5th and 97.5th percentiles of ``similarity_score`` over *resamples* resamples of the
    pairs, drawn with replacement. The generator depends on the seed and the number of pairs only,
    so every system sees the same resamples of one set. A resample in which either side is
    constant has no score and is counted in ``undefined``."""
    x, y = np.array([-d for d in distances], dtype=float), np.array(confusion, dtype=float)
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(resamples):
        pick = rng.integers(0, len(x), len(x))
        score = spearman(x[pick], y[pick])
        if score is not None:
            scores.append(score)
    if not scores:
        return {"low": None, "high": None, "undefined": resamples}
    low, high = np.percentile(scores, [2.5, 97.5])
    return {"low": float(low), "high": float(high), "undefined": resamples - len(scores)}
