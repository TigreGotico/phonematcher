"""UPGMA average linkage, on hand-worked cases and against a direct implementation."""
import math
import random
from itertools import combinations

import pytest

from phonematcher.clustering import upgma


def direct_upgma(labels, threshold, dist):
    """Average linkage that recomputes every group distance on every merge."""

    def between(c1, c2):
        return math.fsum(dist[min(a, b), max(a, b)] for a in c1 for b in c2) / (len(c1) * len(c2))

    clusters = [{label} for label in labels]
    while len(clusters) > 1:
        d, i, j = min((between(clusters[i], clusters[j]), i, j)
                      for i in range(len(clusters)) for j in range(i + 1, len(clusters)))
        if d > threshold:
            break
        clusters[i] |= clusters.pop(j)
    return {label: cid for cid, cluster in enumerate(clusters, start=1) for label in cluster}


def test_three_labels_merge_by_the_mean_of_the_pair_distances():
    dist = {("a", "b"): 0.1, ("a", "c"): 0.4, ("b", "c"): 0.6}
    # a and b merge at 0.1; then {a, b} against c is (0.4 + 0.6) / 2 = 0.5
    assert upgma("abc", 0.5, dist) == {"a": 1, "b": 1, "c": 1}
    assert upgma("abc", 0.49, dist) == {"a": 1, "b": 1, "c": 2}
    assert upgma("abc", 0.09, dist) == {"a": 1, "b": 2, "c": 3}


def test_a_threshold_between_two_link_distances_stops_the_merges():
    dist = {(a, b): 0.2 for a, b in combinations("abcd", 2)}
    dist["c", "d"] = 0.1
    # c and d merge at 0.1; every other group distance is 0.2, so 0.15 stops there and 0.2 merges all
    assert upgma("abcd", 0.15, dist) == {"a": 1, "b": 2, "c": 3, "d": 3}
    assert upgma("abcd", 0.2, dist) == {"a": 1, "b": 1, "c": 1, "d": 1}


def test_a_tie_that_shares_a_label_merges_the_lower_pair():
    dist = {("a", "b"): 0.2, ("b", "c"): 0.2, ("a", "c"): 0.3}
    # a-b and b-c tie at 0.2; a and b merge, then {a, b} against c is (0.3 + 0.2) / 2 = 0.25
    assert upgma("abc", 0.24, dist) == {"a": 1, "b": 1, "c": 2}


def test_no_label_and_one_label():
    assert upgma([], 1.0, {}) == {}
    assert upgma(["a"], 1.0, {}) == {"a": 1}


@pytest.mark.parametrize("seed", range(40))
def test_the_groups_equal_a_direct_recomputation_with_many_ties(seed):
    rng = random.Random(seed)
    labels = [f"x{k:02d}" for k in range(rng.randint(2, 18))]
    values = [0.1, 0.2, 0.3, 0.7] if seed % 2 else [rng.random() for _ in range(5)]
    dist = {(a, b): rng.choice(values) for a, b in combinations(labels, 2)}
    for threshold in (0.0, 0.15, 0.2, 0.25, 0.5, 1.0):
        assert upgma(labels, threshold, dist) == direct_upgma(labels, threshold, dist)
