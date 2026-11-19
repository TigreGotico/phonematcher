"""The feature table and the segment distance.

Expected values follow the IPA chart (International Phonetic Association, Handbook of the
International Phonetic Association, 1999) and the feature definitions of PanPhon (Mortensen et al.
2016), never values read back from the table under test.
"""
import json
import unicodedata
from importlib.resources import files

import pytest

from phonematcher.features import (
    FEATURES,
    NUM_FEATURES,
    SOURCE,
    phone_features,
    phonetic_distance,
    vectorize_phones,
)



def feature(segment, name):
    return vectorize_phones(segment)[FEATURES.index(name)]


def test_every_vector_has_every_feature():
    assert all(len(vec) == NUM_FEATURES for vec in phone_features.values())


def test_the_table_names_its_source():
    assert SOURCE.startswith("PanPhon ")


def test_every_override_names_a_source_and_is_applied():
    data = files("phonematcher") / "data" / "overrides.json"
    overrides = json.loads(data.read_text(encoding="utf-8"))["overrides"]
    assert overrides
    for o in overrides:
        assert o["source"] and o["reason"], o
        assert feature(o["phone"], o["feature"]) is {"+": True, "-": False, "0": None}[o["value"]]


def test_every_ipa_letter_has_its_own_vector():
    """Two letters of the IPA chart are two sounds, so their vectors must differ."""
    letters = [k for k in phone_features
               if len(k) == 1 and unicodedata.category(k).startswith("L")]
    seen = {}
    shared = []
    for letter in letters:
        vec = phone_features[letter]
        if vec in seen:
            shared.append((seen[vec], letter))
        seen.setdefault(vec, letter)
    assert shared == []


@pytest.mark.parametrize("affricate, stop, fricative", [
    ("t͡ʃ", "t", "ʃ"), ("d͡ʒ", "d", "ʒ"), ("t͡s", "t", "s"), ("d͡z", "d", "z"),
])
def test_affricate_is_a_stop_with_a_fricative_release(affricate, stop, fricative):
    assert feature(affricate, "cont") is False
    assert feature(affricate, "delrel") is True
    assert feature(affricate, "voi") is feature(fricative, "voi")
    assert phonetic_distance(affricate, fricative) < phonetic_distance(affricate, "a")


def test_both_tie_bars_give_the_same_affricate():
    assert vectorize_phones("t͡ʃ") == vectorize_phones("t͜ʃ")


def test_precomposed_and_combining_forms_are_one_segment():
    assert vectorize_phones("ã") == vectorize_phones("ã")
    assert vectorize_phones("ç") == vectorize_phones("ç")


def test_nasal_diacritic_makes_a_vowel_nasal():
    for vowel in "aeiouɐ":
        assert feature(vowel + "̃", "nas") is True
        assert feature(vowel, "nas") is False


def test_voiceless_diacritic_devoices_a_vowel():
    assert feature("ɐ̥", "voi") is False
    assert feature("ɐ̥", "syl") is True


def test_apical_and_laminal_diacritics_set_distributed():
    assert feature("s̺", "distr") is False
    assert feature("s̻", "distr") is True


def test_glottal_fricatives_differ_in_voice():
    assert feature("ɦ", "voi") is True
    assert feature("h", "voi") is False


def test_voicing_pairs_are_nearer_than_place_pairs():
    assert phonetic_distance("p", "b") < phonetic_distance("p", "k")
    assert phonetic_distance("ʁ", "χ") < phonetic_distance("ʁ", "k")


def test_unknown_symbol_is_far_from_everything():
    assert phonetic_distance("?", "a") == 1.0
    with pytest.raises(ValueError):
        vectorize_phones("?")


@pytest.mark.parametrize("vowel", ["u", "ʊ", "o", "ɔ", "y", "ø", "ɒ"])
def test_rounded_vowels_are_labial(vowel):
    """Hayes (2009) gives every rounded vowel [+LABIAL, +round]."""
    assert feature(vowel, "lab") is True and feature(vowel, "round") is True


@pytest.mark.parametrize("vowel", ["i", "e", "ɛ", "a", "ɐ", "ɨ", "ə", "ɑ"])
def test_unrounded_vowels_are_not_labial(vowel):
    assert feature(vowel, "lab") is False and feature(vowel, "round") is False


def test_central_vowels_are_neither_front_nor_back():
    for vowel in ["ɨ", "ʉ", "ɘ", "ɵ", "ə", "ɜ", "ɞ", "ɐ"]:
        assert feature(vowel, "front") is False and feature(vowel, "back") is False, vowel


def test_trill_and_tap_differ():
    assert feature("r", "trill") is True and feature("r", "tap") is False
    assert feature("ɾ", "tap") is True and feature("ɾ", "trill") is False


def test_near_open_vowels_are_low():
    """[æ] and [ɐ] are near-open (IPA chart); Hayes and PHOIBLE mark near-open vowels [+low]."""
    assert feature("æ", "lo") is True and feature("ɐ", "lo") is True
    assert phonetic_distance("ɐ", "a") < phonetic_distance("ɐ", "e")


def test_a_listed_diacritic_keeps_its_effect_on_a_hayes_vowel():
    """PanPhon's rule for ◌ˤ adds [+low, +back]; the Hayes vowel values must not erase it."""
    assert feature("ɤˤ", "lo") is True and feature("ɤ", "lo") is False
    assert vectorize_phones("ɤˤ") != vectorize_phones("ɤ")


def test_tongue_root_is_its_own_feature():
    """Lindau (1978): advanced tongue root is not the tense/lax distinction."""
    assert feature("ɛ̘", "atr") is True and feature("ɛ̘", "tense") is feature("ɛ", "tense")
    assert feature("u̙", "atr") is False and vectorize_phones("u̙") != vectorize_phones("ʊ")


def test_centralized_vowel_is_neither_front_nor_back():
    """◌̈ marks a centralized vowel (IPA Handbook 1999)."""
    assert feature("ë", "front") is False and feature("ë", "back") is False
    assert vectorize_phones("ë") != vectorize_phones("e")


@pytest.mark.parametrize("segment, stop", [("ⁿd", "d"), ("ᵐb", "b"), ("ᵑɡ", "ɡ")])
def test_prenasalized_stop_is_a_nasal_stop(segment, stop):
    assert feature(segment, "nas") is True and feature(segment, "cont") is False
    assert phonetic_distance(segment, stop) < phonetic_distance(segment, "a")


def test_preaspirated_stop_has_spread_glottis():
    assert feature("ʰt", "sg") is True


#: Height of each front vowel on the chart, from close (0) to open (6); the front column has no
#: mid (3) letter.
CHART_HEIGHT = {"i": 0, "ɪ": 1, "e": 2, "ɛ": 4, "æ": 5, "a": 6}


def test_vowel_distance_grows_with_chart_height_difference():
    """Down the front column of the chart, each step away from [i] is farther than the last."""
    rows = sorted(CHART_HEIGHT, key=CHART_HEIGHT.get)
    steps = [phonetic_distance("i", v) for v in rows]
    assert steps == sorted(steps) and len(set(steps)) == len(steps)


def test_mid_central_vowel_sits_between_close_mid_and_open_mid():
    """[ə] is mid on the chart, halfway between [ɘ] and [ɜ]."""
    assert phonetic_distance("ə", "ɘ") == pytest.approx(phonetic_distance("ə", "ɜ"))
    assert phonetic_distance("ə", "ɘ") < phonetic_distance("ɘ", "ɜ")


def test_open_a_is_front_and_near_open_a_is_central():
    """The chart places [a] open front and [ɐ] near-open central."""
    assert feature("a", "front") is True and feature("ɐ", "front") is False
    assert feature("ɐ", "round") is False


def test_no_segment_is_both_high_and_low():
    """Chomsky and Halle (1968): [+high, +low] is impossible."""
    hi, lo = FEATURES.index("hi"), FEATURES.index("lo")
    both = [s for s, v in phone_features.items() if v[hi] is True and v[lo] is True]
    assert both == []


@pytest.mark.parametrize("letter, near, feat", [
    ("ⱱ", "ɾ", "tap"), ("ʜ", "ħ", "trill"), ("ʢ", "ʕ", "trill"), ("ʡ", "ħ", "cont"),
])
def test_chart_letters_panphon_lacks(letter, near, feat):
    """Labiodental flap (IPA chart) and the epiglottals (Esling 2005)."""
    assert vectorize_phones(letter) != vectorize_phones(near)
    assert phonetic_distance(letter, near) < phonetic_distance(letter, "a")
    expected = {"tap": True, "trill": True, "cont": False}[feat]
    assert feature(letter, feat) is expected


def test_labiodental_flap_has_the_place_of_v():
    for f in ("lab", "ant", "cor"):
        assert feature("ⱱ", f) is feature("v", f)


def test_lowered_and_raised_marks_move_a_vowel_one_chart_row():
    """◌̞ lowers and ◌̝ raises (IPA chart): lowered close-mid [e̞] is nearer open-mid [ɛ] than [e]
    is, and raised [ɛ̝] is nearer [e] than [ɛ] is."""
    assert phonetic_distance("e̞", "ɛ") < phonetic_distance("e", "ɛ")
    assert phonetic_distance("ɛ̝", "e") < phonetic_distance("ɛ", "e")
