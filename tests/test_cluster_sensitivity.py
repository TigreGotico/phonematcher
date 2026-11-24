"""The cluster sensitivity is a share of the segment costs, and the clusters use the segment cost."""
import itertools
import math
import statistics
import unicodedata
import warnings

import pytest

from phonematcher import PhoneticFuzzySearch, feature_distance, phonetic_distance, substitution_cost
from phonematcher.clustering import merge_threshold, phone_clusters
from phonematcher.features import phone_features
from phonematcher.version import VERSION_STR

GRID = (0.01, 0.02, 0.03, 0.05, 0.08, 0.12)
LETTERS = sorted(
    p for p in phone_features
    if (len(p) == 1 and unicodedata.category(p).startswith("L")) or (len(p) == 3 and p[1] in "͜͡")
)
COSTS = sorted(substitution_cost(a, b) for a, b in itertools.combinations(LETTERS, 2))


def test_the_letters_make_all_their_pairs():
    assert len(LETTERS) == 135
    assert len(COSTS) == 135 * 134 // 2


@pytest.mark.parametrize("share", GRID)
def test_the_threshold_is_the_quantile_of_the_costs_of_all_letter_pairs(share):
    # statistics.quantiles with method="inclusive" interpolates linearly between the sorted values
    percent = round(share * 100)
    expected = statistics.quantiles(COSTS, n=100, method="inclusive")[percent - 1]
    assert merge_threshold(share) == pytest.approx(expected, abs=1e-12)


def test_the_threshold_is_the_quantile_at_every_thousandth_between_costs():
    expected = statistics.quantiles(COSTS, n=1000, method="inclusive")
    assert [merge_threshold(k / 1000) for k in range(1, 1000)] == pytest.approx(expected, abs=1e-12)


def test_the_threshold_runs_from_the_smallest_cost_to_the_largest():
    assert merge_threshold(0.0) == COSTS[0]
    assert merge_threshold(1.0) == COSTS[-1]
    assert merge_threshold(0.5) == pytest.approx(statistics.median(COSTS), abs=1e-12)


@pytest.mark.parametrize("share", GRID)
def test_no_two_clusters_stay_within_the_threshold_of_each_other(share):
    clusters = {}
    for letter, cid in phone_clusters(share).items():
        clusters.setdefault(cid, []).append(letter)
    for one, other in itertools.combinations(clusters.values(), 2):
        mean = math.fsum(substitution_cost(a, b) for a in one for b in other) / (len(one) * len(other))
        assert mean > merge_threshold(share)


def test_a_pair_of_letters_alone_in_a_cluster_costs_at_most_the_threshold():
    share = 0.03
    clusters = {}
    for letter, cid in phone_clusters(share).items():
        clusters.setdefault(cid, []).append(letter)
    pairs = [c for c in clusters.values() if len(c) == 2]
    assert pairs
    for a, b in pairs:
        assert substitution_cost(a, b) <= merge_threshold(share)


def test_a_higher_share_never_gives_more_clusters():
    counts = [len(set(phone_clusters(share).values())) for share in (0.0, *GRID, 0.5, 1.0)]
    assert counts == sorted(counts, reverse=True)
    assert counts[-1] == 1


def test_the_cluster_of_a_segment_outside_the_letters_is_that_of_its_nearest_letter_by_cost():
    search = PhoneticFuzzySearch(0.05)
    segment = "pʰ"
    nearest = min(LETTERS, key=lambda p: (substitution_cost(segment, p), p))
    assert search.cluster_of(segment) == search.clusters[nearest]


def test_the_default_share_is_0_12():
    assert PhoneticFuzzySearch().cluster_sensitivity == 0.12


@pytest.mark.parametrize("share", [-0.01, 1.01, 2, float("nan"), float("inf")])
def test_a_share_outside_zero_to_one_raises(share):
    with pytest.raises(ValueError, match="share from 0 to 1"):
        PhoneticFuzzySearch(share)
    with pytest.raises(ValueError):
        phone_clusters(share)


def test_the_deprecated_alias_warns_with_the_computed_removal_version_and_returns_the_same_value():
    removal = f"{int(VERSION_STR.split('.')[0]) + 1}.0.0"
    with pytest.warns(DeprecationWarning, match=f"removed in {removal.replace('.', r'[.]')}") as caught:
        value = phonetic_distance("p", "b")
    assert "feature_distance" in str(caught[0].message)
    assert value == feature_distance("p", "b")
    assert caught[0].filename == __file__


def test_feature_distance_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        feature_distance("p", "b")


def test_phonetic_distance_imports_from_the_distance_module():
    from phonematcher.distance import phonetic_distance as old
    from phonematcher.features import phonetic_distance
    assert old is phonetic_distance
