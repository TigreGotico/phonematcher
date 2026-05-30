import pytest
from phonematcher.distance import (
    phone_features,
    vectorize_phones,
    NUM_FEATURES,
    _bad_phones,
)

def test_all_vectors_length():
    for ph, vec in phone_features.items():
        assert len(vec) == NUM_FEATURES, f"{ph} has length {len(vec)}"

def test_no_duplicate_keys():
    # Python dicts prevent duplicates by construction
    # This test ensures no accidental aliasing due to normalization rules.
    normalized = {}
    for ph in phone_features:
        norm = _bad_phones.get(ph, ph)
        assert norm not in normalized, f"duplicate normalized key: {norm}"
        normalized[norm] = True

def test_get_vector_identity():
    """_get_vector(phone) should return the canonical stored vector for base phones."""
    for ph, expected in phone_features.items():
        v = vectorize_phones(ph)
        assert len(v) == NUM_FEATURES
        assert v == expected

def test_bad_phone_normalization():
    for bad, good in _bad_phones.items():
        assert vectorize_phones(bad) == vectorize_phones(good)

def test_modifier_application_single():
    # example: length mark should set [+long]
    base = "a"
    vec_base = vectorize_phones(base)
    vec_mod = vectorize_phones("aː")
    assert vec_mod != vec_base
    assert vec_mod[20] is True

def test_modifier_application_multiple():
    # apply rhoticization + length
    base = "ɜ"
    vec = vectorize_phones("ɜ˞ː")
    assert vec[20] is True  # long
    # rhoticization modifies: 11 (anterior), 15 (high), 18 (round)
    assert vec[11] is False
    assert vec[15] is True
    assert vec[18] is True

def test_unknown_phone_raises():
    with pytest.raises(ValueError):
        vectorize_phones("???") # ValueError: Unrecognized phone '?'


def test_nasalized_vowel_combining_tilde():
    # base vowel + combining tilde (U+0303) -> [+nasal]
    base = vectorize_phones("a")
    nas = vectorize_phones("ã")
    assert nas[6] is True            # nasal
    assert nas[0] is True            # still a vowel (syllabic)
    assert base[6] is not True


def test_nasalized_vowel_precomposed_equals_combining():
    # precomposed "ã" must decompose to the same vector as "a" + tilde
    assert vectorize_phones("ã") == vectorize_phones("ã")


def test_nasalized_consonant_resolves():
    # nasalized glide w̃ should resolve (not raise) and be [+nasal]
    v = vectorize_phones("w̃")
    assert v[6] is True
