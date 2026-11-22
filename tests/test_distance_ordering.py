"""
Distance-ordering and metric-property tests over the distinctive-feature table.

These assert that feature_distance ranks segment pairs in line with their
articulatory similarity: minimal feature differences score nearer than larger
ones, and cross-class (vowel vs consonant) pairs are maximally distant.
"""
import pytest

from phonematcher.features import (
    phone_features,
    feature_distance,
    is_vowel_phone,
)


# ---------------------------------------------------------------------------
# Metric properties
# ---------------------------------------------------------------------------
def test_identity_is_zero():
    for ph in phone_features:
        assert feature_distance(ph, ph) == 0.0, ph


def test_symmetry():
    phones = list(phone_features)
    for a in phones[:12]:
        for b in phones[:12]:
            assert feature_distance(a, b) == feature_distance(b, a)


def test_non_negative_and_bounded():
    phones = list(phone_features)
    for a in phones[:8]:
        for b in phones:
            d = feature_distance(a, b)
            # consonant scaling uses factor 2.0, so the in-class ceiling is 2.0;
            # cross-class pairs are clamped to 1.0
            assert 0.0 <= d <= 2.0, (a, b, d)


# ---------------------------------------------------------------------------
# Cross-class separation: a vowel and a consonant are maximally distant
# ---------------------------------------------------------------------------
def test_vowel_and_consonant_are_far_apart():
    # The major-class features carry PanPhon's largest weights: a stop and a vowel are farther
    # apart than two stops of different place.
    assert feature_distance("p", "a") > feature_distance("p", "k")
    assert feature_distance("a", "p") == feature_distance("p", "a")


def test_any_vowel_is_nearer_to_a_vowel_than_to_an_obstruent():
    """Major class outweighs vowel quality: two chart vowels are nearer than a vowel and a stop or
    fricative."""
    vowels = "iyɨʉɯuɪʏʊeøɘɵɤoəɛœɜɞʌɔæɐaɶɑɒ"
    obstruents = "pbtdkɡqʔfvszʃʒxχh"
    widest_vowel_pair = max(feature_distance(a, b) for a in vowels for b in vowels)
    nearest_obstruent = min(feature_distance(a, b) for a in vowels for b in obstruents)
    assert widest_vowel_pair < nearest_obstruent


def test_cross_class_farther_than_within_class():
    # /p/ to any vowel is farther than /p/ to its voiced partner /b/
    assert feature_distance("p", "a") > feature_distance("p", "b")
    # /i/ to any consonant is farther than /i/ to a neighbouring vowel /e/
    assert feature_distance("i", "p") > feature_distance("i", "e")


# ---------------------------------------------------------------------------
# Consonant ordering: voicing < place < cross-class
# ---------------------------------------------------------------------------
def test_roadmap_ordering_p_b_k_a():
    # The canonical example from the roadmap.
    assert (
        feature_distance("p", "b")
        < feature_distance("p", "k")
        < feature_distance("p", "a")
    )


def test_voicing_is_smallest_consonant_step():
    voicing = feature_distance("p", "b")
    place = feature_distance("p", "t")
    assert 0.0 < voicing < place


def test_place_ordering_for_stops():
    # /p/ (bilabial) nearer /t/ (alveolar) than /k/ (velar)
    assert feature_distance("p", "t") < feature_distance("p", "k")


def test_fricative_voicing_vs_place():
    # /s/-/z/ differ only in voice -> nearer than /s/-/ʃ/ (place shift)
    assert feature_distance("s", "z") < feature_distance("s", "ʃ")


def test_manner_step_present():
    # /t/ (stop) vs /s/ (fricative): same coronal place, manner differs ->
    # a non-zero, sub-maximal distance
    d = feature_distance("t", "s")
    assert 0.0 < d < 1.0


def test_glottal_voicing_pair():
    # /h/ and /ɦ/ form a voicing pair after the table correction.
    d = feature_distance("h", "ɦ")
    assert 0.0 < d < feature_distance("h", "k")


# ---------------------------------------------------------------------------
# Vowel ordering: height, backness, rounding
# ---------------------------------------------------------------------------
def test_vowel_height_ordering():
    # /i/ (close) nearer /e/ (close-mid) than /a/ (open)
    assert feature_distance("i", "e") < feature_distance("i", "a")


def test_vowel_backness_ordering():
    # /i/ (front) nearer /e/ (front) than /u/ (back)
    assert feature_distance("i", "e") < feature_distance("i", "u")


def test_vowel_rounding_ordering():
    # /i/-/y/ differ only in rounding -> nearer than /i/-/u/ (back and round)
    assert feature_distance("i", "y") < feature_distance("i", "u")


def test_central_vowels_pattern_with_front_on_backness():
    # After the correction, central vowels (ə, ɨ, ɜ, ɐ) are [-back] like front
    # vowels, so each is nearer its front counterpart than a back vowel.
    assert feature_distance("ɨ", "i") < feature_distance("ɨ", "u")
    assert feature_distance("ə", "e") < feature_distance("ə", "o")


# ---------------------------------------------------------------------------
# Corrected coronal approximants: /ɹ/ is coronal, not dorsal
# ---------------------------------------------------------------------------
def test_alveolar_approximant_is_coronal_not_dorsal():
    # /ɹ/ should sit nearer its coronal/retroflex partner /ɻ/ than the velar
    # approximant /ɰ/.
    assert feature_distance("ɹ", "ɻ") < feature_distance("ɹ", "ɰ")


# ---------------------------------------------------------------------------
# Space handling
# ---------------------------------------------------------------------------
def test_space_only_matches_space():
    assert feature_distance(" ", " ") == 0.0
    assert feature_distance(" ", "a") == 1.0
    assert feature_distance("a", " ") == 1.0


def test_is_vowel_classification():
    assert is_vowel_phone("a") is True
    assert is_vowel_phone("p") is False
