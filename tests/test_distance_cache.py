"""``feature_distance`` is cached on the ordered pair; the cache must not change a value."""
import hashlib

from phonematcher.clustering import phone_clusters
from phonematcher import features
from phonematcher.features import FEATURES, feature_distance, vectorize_phones

LETTERS = sorted(phone_clusters(0.1))
#: SHA-256 of ``a TAB b TAB repr(distance)`` lines over every ordered pair of LETTERS, as
#: ``benchmarks/speed.py`` writes them.
MATRIX_SHA256 = "44c7d449fc5d31f74b289e50ed0994c9741936e25a60944e08a31c400dfe14a9"


def test_the_letter_set_is_135_segments():
    assert len(LETTERS) == 135


def test_the_letter_pair_matrix_is_bit_identical_to_the_matrix_before_caching():
    digest = hashlib.sha256()
    for a in LETTERS:
        for b in LETTERS:
            digest.update(f"{a}\t{b}\t{feature_distance(a, b)!r}\n".encode("utf8"))
    assert digest.hexdigest() == MATRIX_SHA256


def test_cached_and_uncached_distances_agree_on_every_letter_pair():
    uncached = feature_distance.__wrapped__
    feature_distance.cache_clear()
    for a in LETTERS:
        for b in LETTERS:
            assert repr(feature_distance(a, b)) == repr(uncached(a, b)), (a, b)
    assert feature_distance.cache_info().currsize == len(LETTERS) ** 2


def test_the_cache_is_keyed_on_the_ordered_pair():
    feature_distance.cache_clear()
    feature_distance("p", "b")
    feature_distance("b", "p")
    assert feature_distance.cache_info().currsize == 2


def test_the_cache_is_bounded():
    assert feature_distance.cache_info().maxsize == 65536


def test_unreadable_and_space_cases_survive_the_cache():
    feature_distance.cache_clear()
    for _ in range(2):
        assert feature_distance("p", "☃") == 1.0
        assert feature_distance(" ", "p") == 1.0
        assert feature_distance("p", "p") == 0.0


def test_signs_are_the_vector_as_minus_one_zero_one():
    for segment in ("p", "a", "t͡s", "ʔ"):
        vector = vectorize_phones(segment)
        assert features._signs(segment) == tuple({True: 1, False: -1, None: 0}[v] for v in vector)
        assert len(features._signs(segment)) == len(FEATURES)
