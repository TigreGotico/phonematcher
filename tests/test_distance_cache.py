"""The cache of ``feature_distance`` gives the uncached values, and the letter matrix matches its published digest."""
import hashlib

from phonematcher.clustering import phone_clusters
from phonematcher import features
from phonematcher.features import FEATURES, feature_distance, vectorize_phones

LETTERS = sorted(phone_clusters(0.1))
#: SHA-256 of ``a TAB b TAB repr(distance)`` lines over every ordered pair of LETTERS, as
#: ``benchmarks/speed.py`` writes them; ``docs/benchmarks.md`` and ``results/speed.json`` state it.
MATRIX_SHA256 = "a8ca4788713ffab74dae3469aa7ea8d0aa34cd6d56c2b18a34a2d8a36106625d"


def test_the_letter_set_is_135_segments():
    assert len(LETTERS) == 135


def test_the_letter_pair_matrix_matches_the_digest_the_benchmarks_page_states():
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


def test_the_cache_cannot_grow_without_bound():
    assert feature_distance.cache_info().maxsize is not None


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
