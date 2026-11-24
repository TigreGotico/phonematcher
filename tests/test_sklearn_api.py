"""The scikit-learn abstractions: a feature transformer and a precomputed distance matrix.

The core tests use no scikit-learn. ``clone`` is tested against scikit-learn from the ``bench``
extra, and that test fails if the extra is not installed.
"""
import math
import warnings

import pytest

from phonematcher import FEATURES, PhoneFeatures, feature_distance, ipa_distance, pairwise_distances, vectorize_phones
from phonematcher.features import phone_features

TERNARY = {True: 1.0, False: -1.0, None: 0.0}
SEGMENTS = ["p", "b", "t͡s", "a", "ɛ", "ŋ", "ǃ", "a˥", "ã˧˥"]
WORDS = ["kasa", "kaza", "ˈmesa", "pɾato", "bɔla", " ", ""]


def ternary(vector):
    """The expected row of a vector: a tone pitch is its own number, any other value is mapped."""
    return [float(v) if isinstance(v, float) else TERNARY[v] for v in vector]


def test_every_table_letter_transforms_to_the_ternary_row_of_its_vector():
    letters = sorted(phone_features)
    rows = PhoneFeatures().transform(letters)
    bad = [letter for letter, row in zip(letters, rows) if row != ternary(vectorize_phones(letter))]
    assert len(rows) == len(letters) > 6000
    assert bad == []


def test_a_toned_vowel_carries_its_pitches_and_a_plain_segment_has_zeros():
    rows = dict(zip(["a", "a˥"], PhoneFeatures().transform(["a", "a˥"])))
    start = FEATURES.index("tone_start")
    assert rows["a"][start - 1:start + 3] == [0.0, 0.0, 0.0, 0.0]
    assert rows["a˥"][start - 1:start + 3] == [1.0, 1.0, 1.0, 1.0]


def test_a_row_has_one_value_per_feature_name_and_the_names_are_features():
    transformer = PhoneFeatures().fit(SEGMENTS)
    assert transformer.get_feature_names_out() == list(FEATURES)
    assert len(FEATURES) == 40
    assert all(len(row) == 40 for row in transformer.transform(SEGMENTS))


def test_fit_transform_equals_transform_and_takes_any_iterable():
    transformer = PhoneFeatures()
    assert transformer.fit_transform(iter(SEGMENTS)) == transformer.transform(SEGMENTS)


def test_an_unreadable_segment_raises_when_strict_and_is_nan_otherwise():
    with pytest.raises(ValueError):
        PhoneFeatures().transform(["a", "?"])
    rows = PhoneFeatures(strict=False).transform(["a", "?"])
    assert rows[0] == PhoneFeatures().transform(["a"])[0]
    assert len(rows[1]) == 40 and all(math.isnan(v) for v in rows[1])


def test_get_params_and_set_params_round_trip():
    transformer = PhoneFeatures()
    assert transformer.get_params() == {"strict": True}
    assert transformer.set_params(strict=False) is transformer
    assert transformer.get_params(deep=False) == {"strict": False}
    with pytest.raises(ValueError):
        transformer.set_params(loose=True)


def test_the_segment_matrix_equals_a_double_loop_of_the_feature_distance():
    matrix = pairwise_distances(SEGMENTS)
    assert matrix == [[feature_distance(x, y) for y in SEGMENTS] for x in SEGMENTS]


def test_the_word_matrix_equals_a_double_loop_of_the_ipa_distance():
    matrix = pairwise_distances(WORDS, metric="word")
    assert matrix == [[ipa_distance(x, y) for y in WORDS] for x in WORDS]


def test_a_matrix_of_one_list_is_symmetric_with_a_zero_diagonal():
    for metric, items in (("segment", SEGMENTS), ("word", WORDS)):
        matrix = pairwise_distances(items, metric=metric)
        assert all(matrix[i][i] == 0.0 for i in range(len(items)))
        assert all(matrix[i][j] == matrix[j][i] for i in range(len(items)) for j in range(len(items)))


def test_a_matrix_of_two_lists_has_the_rows_of_the_first_and_the_columns_of_the_second():
    matrix = pairwise_distances(["kasa", "meza"], ["kaza", "pɾato", "bɔla"], metric="word")
    assert [len(row) for row in matrix] == [3, 3]
    assert matrix[1][0] == ipa_distance("meza", "kaza")
    assert matrix[0][2] == ipa_distance("kasa", "bɔla")


def test_a_symmetric_matrix_computes_each_pair_once(monkeypatch):
    calls = []
    monkeypatch.setattr("phonematcher.distance.ipa_distance", lambda x, y: calls.append((x, y)) or 1.0)
    pairwise_distances(["a", "b", "c", "d"], metric="word")
    assert len(calls) == 6


def test_a_strict_matrix_raises_for_an_unreadable_item_and_a_loose_one_costs_1():
    for metric, items in (("segment", ["a", "?"]), ("word", ["ka", "k?"])):
        with pytest.raises(ValueError, match="cannot read"):
            pairwise_distances(items, metric=metric)
        with pytest.raises(ValueError, match="cannot read"):
            pairwise_distances(items[:1], items[1:], metric=metric)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            loose = pairwise_distances(items, metric=metric, strict=False)
        assert loose[0][1] == (1.0 if metric == "segment" else ipa_distance(*items))
    assert pairwise_distances(["ka"], metric="word") == [[0.0]]


def test_a_bare_string_for_either_argument_raises_type_error():
    with pytest.raises(TypeError, match="argument a must be a list"):
        pairwise_distances("pa")
    with pytest.raises(TypeError, match="argument b must be a list"):
        pairwise_distances(["a"], "pa")


def test_an_unknown_metric_raises():
    with pytest.raises(ValueError, match="metric"):
        pairwise_distances(SEGMENTS, metric="cosine")


def test_the_names_are_exported():
    import phonematcher
    assert {"PhoneFeatures", "pairwise_distances"} <= set(phonematcher.__all__)


def test_scikit_learn_clones_a_transformer_and_clusters_a_precomputed_matrix():
    from sklearn.base import clone
    from sklearn.cluster import DBSCAN
    from sklearn.pipeline import make_pipeline

    original = PhoneFeatures(strict=False)
    copy = clone(original)
    assert copy is not original and copy.get_params() == {"strict": False}
    labels = DBSCAN(eps=0.6, min_samples=2, metric="precomputed").fit(
        pairwise_distances(["kasa", "kaza", "pɾato", "pɾatu"], metric="word")).labels_
    assert labels.tolist() == [0, 0, 1, 1]
    assert make_pipeline(PhoneFeatures(), DBSCAN(eps=0.2, min_samples=2)).fit_predict(["p", "b", "a", "e"]).shape == (4,)
