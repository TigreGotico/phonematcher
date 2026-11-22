"""The cognate task against LingPy itself. Needs the ``bench-copyleft`` extra, so no CI job runs it.

Run: ``pytest --import-mode=importlib benchmarks/test_cognates_lingpy.py``
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

lingpy_algorithm = pytest.importorskip("lingpy.algorithm")

from tasks import cognates  # noqa: E402


@pytest.mark.parametrize("levels", [1000, 6])
def test_flat_upgma_equals_lingpy_on_matrices_with_ties(levels):
    # With 6 levels most distances tie, as edit distances do.
    rng = np.random.default_rng(0)
    for _ in range(200):
        n = int(rng.integers(2, 12))
        upper = np.triu(rng.integers(0, levels, (n, n)) / (levels - 1), 1)
        matrix = upper + upper.T
        threshold = float(rng.integers(0, levels) / (levels - 1))
        theirs = lingpy_algorithm.flat_upgma(threshold, matrix.tolist(), list(range(n)))
        ours = cognates.flat_upgma(matrix, [threshold])[0]
        assert {frozenset(v) for v in theirs.values()} == {frozenset(np.flatnonzero(ours == x).tolist()) for x in set(ours.tolist())}
