"""Alignment and normalized distance."""
import random

import pytest

from phonematcher.distance import align, edit_distance, ipa_distance, substitution_cost
from phonematcher.features import phone_features

LETTERS = sorted(s for s in phone_features if len(s) == 1)


def test_align_places_a_gap_for_the_missing_segment():
    assert align(["p", "a", "t"], ["p", "t"]) == [("p", "p"), ("a", None), ("t", "t")]


def test_align_of_an_empty_sequence_is_all_gaps():
    assert align(["a"], []) == [("a", None)]
    assert align([], ["a"]) == [(None, "a")]
    assert align([], []) == []


def test_align_prefers_substitution_when_it_ties_with_two_gaps():
    # "p" against "b" costs the feature distance, always below the 2.0 of a deletion plus an
    # insertion, so the single pair is chosen.
    assert align(["p"], ["b"]) == [("p", "b")]


def test_align_breaks_a_tie_toward_deletion():
    # ["p","p"] against ["p"]: the optimal paths are (p,p),(p,None) and (p,None),(p,p).
    # The traceback from the end tries a substitution first, so the deletion lands first.
    assert align(["p", "p"], ["p"]) == [("p", None), ("p", "p")]


def test_align_reproduces_both_sequences_and_the_edit_distance():
    rng = random.Random(0)
    for _ in range(500):
        a = [rng.choice(LETTERS) for _ in range(rng.randint(0, 6))]
        b = [rng.choice(LETTERS) for _ in range(rng.randint(0, 6))]
        pairs = align(a, b)
        assert [x for x, _ in pairs if x is not None] == a
        assert [y for _, y in pairs if y is not None] == b
        total = sum(
            substitution_cost(x, y) if x is not None and y is not None else 1.0 for x, y in pairs
        )
        assert total == pytest.approx(edit_distance(a, b), abs=1e-9)


def test_normalized_distance_divides_by_the_longer_segment_count():
    # "pat" against "pt": one deletion costs 1, the longer string has 3 segments.
    assert ipa_distance("pat", "pt", normalized=True) == pytest.approx(1 / 3)
    assert ipa_distance("pat", "pt") == 1.0


def test_normalized_distance_of_two_empty_strings_is_zero():
    assert ipa_distance("", "", normalized=True) == 0.0
