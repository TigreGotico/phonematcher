"""Letters that PanPhon does not list and the Unicode charts annotate.

Each curl letter has the manner of its plain letter and the place of ɕ. The expected values come
from the method stated in ``data/overrides.json`` and from PHOIBLE 2.0's rows for the same letters,
written out below, not read back from the table under test.
"""
import pytest

from phonematcher.features import FEATURES, vectorize_phones

PLACE = ("ant", "cor", "distr", "hi", "lo", "back", "front")


def feature(segment, name):
    return vectorize_phones(segment)[FEATURES.index(name)]


# Curl letter, its plain letter, and the values PHOIBLE 2.0 gives for the features that carry the
# letter's identity (the same in every one of its inventories that lists the letter).
CURL = [
    ("ȵ", "n", {"son": True, "cont": False, "nas": True, "lat": False, "voi": True}),
    ("ȶ", "t", {"son": False, "cont": False, "nas": False, "lat": False, "voi": False}),
    ("ȴ", "l", {"son": True, "cont": True, "nas": False, "lat": True, "voi": True}),
]


@pytest.mark.parametrize("letter, plain, manner", CURL)
def test_a_curl_letter_has_the_place_of_c_curl_and_the_rest_of_its_plain_letter(
        letter, plain, manner):
    for f in FEATURES:
        expected = "ɕ" if f in PLACE else plain
        assert feature(letter, f) is feature(expected, f), f


@pytest.mark.parametrize("letter, plain, manner", CURL)
def test_a_curl_letter_has_the_values_phoible_gives_it(letter, plain, manner):
    for f, value in manner.items():
        assert feature(letter, f) is value, f
    # PHOIBLE: [+coronal, +dorsal, +high, -low, +front, -back, +distributed]
    expected_place = {"cor": True, "hi": True, "lo": False, "front": True, "back": False,
                      "distr": True}
    for f, value in expected_place.items():
        assert feature(letter, f) is value, f


def test_the_retroflex_implosive_has_the_manner_of_the_alveolar_and_the_place_of_the_stop():
    for f in FEATURES:
        expected = "ɖ" if f in PLACE else "ɗ"
        assert feature("ᶑ", f) is feature(expected, f), f
    # PHOIBLE: [+coronal, -anterior, -distributed]
    assert (feature("ᶑ", "cor"), feature("ᶑ", "ant"), feature("ᶑ", "distr")) == (True, False, False)


def test_the_apical_vowel_has_the_vector_of_syllabic_z():
    # Unicode chart U0250: 027F "IPA spelling - 007A z 0329"
    assert vectorize_phones("ɿ") == vectorize_phones("z̩")
    assert feature("ɿ", "syl") is True


def test_the_labialized_apical_vowel_is_the_apical_vowel_with_lip_rounding():
    # Unicode chart U0250: 02AE "labialized apical dental vowel". A rounded vowel is [+round,
    # +lab] in the table, as [y] is, and [y] has [-labialized].
    assert (feature("y", "round"), feature("y", "lab"), feature("y", "labialized")) == (
        True, True, False)
    for f in FEATURES:
        expected = "y" if f in ("round", "lab") else "ɿ"
        assert feature("ʮ", f) is feature(expected, f), f


@pytest.mark.parametrize("letter", ["ᴇ", "ᵻ"])
def test_a_letter_with_no_stated_meaning_stays_unread(letter):
    # U+1D07 has no annotation; U+1D7B is "used with different meanings by Americanists and
    # Oxford dictionaries".
    with pytest.raises(ValueError):
        vectorize_phones(letter)
