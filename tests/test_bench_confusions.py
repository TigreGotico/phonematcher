"""C3: the confusion sets, the alignment and the score on tiny inputs.

Hand values.

``symmetric_rates``: counts [[8, 2], [4, 6]] are rates [[0.8, 0.2], [0.4, 0.6]]; the pair is
(0.2 + 0.4) / 2 = 0.3.

``align`` of a b c against a x c: the walk starts at the end, so it lists (c, c), (b, x), (a, a).

``substitutions``: the target "a b" heard as "a c" with Consistency 3 adds 3 to the pair (b, c).
The Spanish spellings g, tʃ and ʤ read as ɡ, t͡ʃ and d͡ʒ.

Spearman of the negative distance: distances 1, 2, 3 against confusions 30, 20, 10 are in the same
rank order, so 1.0. Against 10, 20, 30 the order is reversed, so -1.0.
"""
import numpy as np
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_fake import Fake

from tasks import common, confusions  # noqa: E402


def test_symmetric_rates():
    pairs = confusions.symmetric_rates(["x", "y"], np.array([[8.0, 2.0], [4.0, 6.0]]))
    assert pairs == {("x", "y"): pytest.approx(0.3)}


def test_align_lists_substitutions_from_the_end():
    assert confusions.align(list("abc"), list("axc")) == [("c", "c"), ("b", "x"), ("a", "a")]


def test_substitutions_weight_by_listeners_and_respell():
    text = "Target-IPA,Confusion-IPA,Consistency\na b,a c,3\ng a ʤ !,ɡ a tʃ .,2\n"
    counts, inventory = confusions.substitutions(text)
    assert counts == {("b", "c"): 3, ("d͡ʒ", "t͡ʃ"): 2}
    assert inventory == ["a", "b", "d͡ʒ", "ɡ"]


def test_spearman_follows_rank_order():
    assert common.similarity_score([1, 2, 3], [30, 20, 10]) == 1.0
    assert common.similarity_score([1, 2, 3], [10, 20, 30]) == -1.0


def test_a_constant_side_has_no_score():
    assert common.similarity_score([1, 1, 1], [3, 2, 1]) is None


def test_bootstrap_interval_is_seeded_and_brackets_a_perfect_order():
    first = common.bootstrap_interval([1, 2, 3, 4], [40, 30, 20, 10])
    assert first == common.bootstrap_interval([1, 2, 3, 4], [40, 30, 20, 10])
    assert first["low"] == first["high"] == 1.0


def test_a_score_counts_an_unread_pair_at_distance_one_and_the_common_subset_leaves_it_out():
    system = Fake("x", "ab", {("a", "b"): 0.2})
    pairs = {("a", "b"): 5.0, ("a", "z"): 1.0, ("b", "z"): 9.0}
    full = confusions.score_set(system, pairs)
    # distances 0.2, 1, 1 against 5, 1, 9: similarities -0.2, -1, -1. Ranks of similarity 3, 1.5, 1.5;
    # ranks of confusion 2, 1, 3. Pearson of those ranks: mean 2 and 2; deviations (1, -.5, -.5) and (0, -1, 1);
    # cross 0 + .5 - .5 = 0.
    assert full["score"] == pytest.approx(0.0)
    assert full["pairs_out"] == 3
    only = confusions.score_set(system, pairs, [("a", "b")])
    assert only["pairs_out"] == 1 and only["score"] is None
