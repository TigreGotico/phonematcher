"""The paired record of ``benchmarks/corrections.py``, on per-unit scores worked out by hand.

Cognates: one data set of two concepts, each with scores -0.1, -0.9. The pairs of both concepts pool.
With labels F, T on both, the two -0.1 pairs are misses and the two -0.9 pairs hits: one threshold
of 4 items and 2 hits, recall gain 1, precision 1/2, so the average precision is 1/2. With labels
T, F on both, the -0.1 pairs come first, and the average precision is 1. Alignment: three pairs, one that only "after"
reads. Retrieval: one language pair of four queries.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

import corrections  # noqa: E402


def concept(labels):
    return np.array([-0.1, -0.9]), np.array(labels)


BEFORE = {
    "cognates": {"set": [concept([False, True]), concept([False, True])]},
    "alignment": {"a": 0.5, "b": 0.7, "c": None},
    "retrieval": {"p": ([0, 1, 2, 3], [0.0, 0.0, 1.0, 1.0])},
}
AFTER = {
    "cognates": {"set": [concept([True, False]), concept([True, False])]},
    "alignment": {"a": 0.6, "b": 0.7, "c": 0.9},
    "retrieval": {"p": ([0, 1, 2, 3], [1.0, 0.0, 1.0, 1.0])},
}


def test_each_estimate_is_the_mean_of_its_units():
    result = corrections.paired(BEFORE, AFTER)
    assert result["cognates"]["estimates"]["before"]["estimate"] == pytest.approx(0.5)
    assert result["cognates"]["estimates"]["after"]["estimate"] == pytest.approx(1.0)
    assert result["alignment"]["units"] == 2
    assert result["alignment"]["estimates"]["after"]["estimate"] == pytest.approx(0.65)
    assert result["retrieval"]["estimates"]["before"]["estimate"] == pytest.approx(0.5)
    assert result["retrieval"]["estimates"]["after"]["estimate"] == pytest.approx(0.75)


def test_the_paired_difference_is_after_minus_before():
    result = corrections.paired(BEFORE, AFTER)
    assert result["cognates"]["paired"]["after"]["diff"] == pytest.approx(0.5)
    assert result["alignment"]["paired"]["after"]["diff"] == pytest.approx(0.05)
    assert result["retrieval"]["paired"]["after"]["diff"] == pytest.approx(0.25)


def test_a_library_that_loses_on_every_unit_is_not_adopted(monkeypatch):
    monkeypatch.setattr(corrections, "git", lambda *args: "")
    record = corrections.record(AFTER, BEFORE)
    assert record["adopted"] is False
    assert record["before"]["cognates_ap"] == pytest.approx(1.0)
