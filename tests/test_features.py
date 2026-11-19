"""The feature table and the segment distance.

Expected values follow the IPA chart (International Phonetic Association, Handbook of the
International Phonetic Association, 1999) and the feature definitions of PanPhon (Mortensen et al.
2016), never values read back from the table under test.
"""
import json
import unicodedata
from pathlib import Path

import pytest

from phonematcher.features import (
    FEATURES,
    NUM_FEATURES,
    SOURCE,
    phone_features,
    phonetic_distance,
    vectorize_phones,
)

DATA = Path(__file__).resolve().parent.parent / "phonematcher" / "data"


def feature(segment, name):
    return vectorize_phones(segment)[FEATURES.index(name)]


def test_every_vector_has_every_feature():
    assert all(len(vec) == NUM_FEATURES for vec in phone_features.values())


def test_the_table_names_its_source():
    assert SOURCE.startswith("PanPhon ")


def test_every_override_names_a_source_and_is_applied():
    overrides = json.loads((DATA / "overrides.json").read_text(encoding="utf-8"))["overrides"]
    assert overrides
    for o in overrides:
        assert o["source"] and o["reason"], o
        assert feature(o["phone"], o["feature"]) is {"+": True, "-": False, "0": None}[o["value"]]


#: Letters that share a vector because no published feature table separates them: PHOIBLE gives
#: mid central [ə] and open-mid central [ɜ] identical values, and Hayes (2009) lists no [ɜ].
SHARED = {("ə", "ɜ")}


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
    assert {tuple(sorted(pair)) for pair in shared} == SHARED


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
    for vowel in ["ɨ", "ə", "ɐ", "a", "ɜ"]:
        assert feature(vowel, "front") is False and feature(vowel, "back") is False, vowel


def test_trill_and_tap_differ():
    assert feature("r", "trill") is True and feature("r", "tap") is False
    assert feature("ɾ", "tap") is True and feature("ɾ", "trill") is False


def test_near_open_vowels_are_low():
    """[æ] and [ɐ] are near-open (IPA chart); Hayes and PHOIBLE mark near-open vowels [+low]."""
    assert feature("æ", "lo") is True and feature("ɐ", "lo") is True
    assert phonetic_distance("ɐ", "a") < phonetic_distance("ɐ", "e")
