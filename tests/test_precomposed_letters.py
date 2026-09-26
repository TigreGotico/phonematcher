"""An IPA letter that Unicode also encodes as base plus diacritic.

U+00E7 is the voiceless palatal fricative, one IPA letter. Unicode canonical
decomposition turns it into "c" plus combining cedilla U+0327, which is not an
IPA modifier. The vectorizer decomposed every input before looking it up, so
the modifier path raised ValueError for the cedilla, and
phonetic_distance("ç", "ç") returned 3.0 rather than 0.0.
"""
import unicodedata

from phonematcher.distance import (phone_features, phonetic_distance,
                                   vectorize_phones)


def test_precomposed_ipa_letter_is_not_decomposed():
    assert unicodedata.normalize("NFD", "ç") != "ç"
    assert vectorize_phones("ç") == phone_features["ç"]
    assert phonetic_distance("ç", "ç") == 0.0


def test_the_letter_is_closest_to_its_neighbours():
    """A restored vector must be phonetically placed, not merely non-raising."""
    to_x = phonetic_distance("ç", "x")       # voiceless dorsal fricative, velar
    to_esh = phonetic_distance("ç", "ʃ")     # voiceless fricative, postalveolar
    to_j = phonetic_distance("ç", "j")       # palatal, but voiced approximant
    to_a = phonetic_distance("ç", "a")       # a vowel
    assert to_x < to_esh < to_j < to_a


def test_decomposition_still_applies_to_a_real_diacritic():
    """The fast path must not stop a genuine combining mark being merged."""
    assert "ã" not in phone_features
    assert vectorize_phones("ã") != vectorize_phones("a")
    assert phonetic_distance("ã", "ã") == 0.0


def test_every_table_key_is_identical_to_itself():
    for phone in phone_features:
        assert phonetic_distance(phone, phone) == 0.0, phone
