"""The feature table and the segment distance.

Expected values follow the IPA chart (International Phonetic Association, revised to 2015) and the feature definitions of PanPhon (Mortensen et al.
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


def test_a_listed_diacritic_keeps_its_effect_on_a_chart_vowel():
    """A listed segment keeps its mark: pharyngealized [ɤˤ] has a retracted root, nasal [ɤ̃] is
    nasal, and both differ from [ɤ]."""
    assert feature("ɤˤ", "atr") is False and feature("ɤ̃", "nas") is True
    assert vectorize_phones("ɤˤ") != vectorize_phones("ɤ") != vectorize_phones("ɤ̃")


def test_tongue_root_is_its_own_feature():
    """Casali (2007), after Lindau (1979): [ATR] is a pharyngeal-cavity contrast, not vowel height."""
    assert feature("ɛ̘", "atr") is True and feature("ɛ̘", "tense") is feature("ɛ", "tense")
    assert feature("u̙", "atr") is False and vectorize_phones("u̙") != vectorize_phones("ʊ")


def test_centralized_vowel_is_neither_front_nor_back():
    """The IPA chart names ◌̈ 'Centralized'; this table reads it as the central column."""
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
    """The tongue body cannot be raised and lowered at once."""
    hi, lo = FEATURES.index("hi"), FEATURES.index("lo")
    both = [s for s, v in phone_features.items() if v[hi] is True and v[lo] is True]
    assert both == []


@pytest.mark.parametrize("letter, near, feat", [
    ("ⱱ", "ɾ", "tap"), ("ʜ", "ħ", "trill"), ("ʢ", "ʕ", "trill"), ("ʡ", "ħ", "cont"),
])
def test_chart_letters_panphon_lacks(letter, near, feat):
    """Labiodental flap (IPA chart) and the epiglottals (Hassan et al. 2011; Esling 1996)."""
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


@pytest.mark.parametrize("segment, base", [("kˤ", "k"), ("iˤ", "i"), ("ɠˤ", "ɠ")])
def test_pharyngealization_keeps_a_high_base_high(segment, base):
    """A secondary articulation does not undo the primary one: a pharyngealized velar is still a
    velar, and a pharyngealized [i] is still close."""
    assert feature(segment, "hi") is True and feature(segment, "lo") is False
    assert feature(segment, "back") is feature(base, "back")
    assert vectorize_phones(segment) != vectorize_phones(base)


@pytest.mark.parametrize("segment", ["ħʷ", "ʕʲ", "a˞"])
def test_raising_marks_keep_a_low_base_low(segment):
    assert feature(segment, "lo") is True and feature(segment, "hi") is False


def test_implosives_stay_apart_when_pharyngealized():
    assert vectorize_phones("ʛˤ") != vectorize_phones("ɠˤ")


@pytest.mark.parametrize("segment, base", [
    ("ħʲ", "ħ"), ("ʕʲ", "ʕ"), ("aˠ", "a"), ("æˠ", "æ"), ("ɐˠ", "ɐ"),
])
def test_a_secondary_mark_changes_its_base(segment, base):
    """A palatalized or velarized sound differs from its plain base, even when the base's height
    blocks the mark's [+high]: the mark still moves the tongue body front or back."""
    assert vectorize_phones(segment) != vectorize_phones(base)


@pytest.mark.parametrize("a, b", [("ɡˤ", "ɟˤ"), ("ɠˤ", "ʄˤ"), ("ɘˤ", "ɤˤ"), ("ʉˤ", "uˤ")])
def test_pharyngealization_keeps_the_base_column(a, b):
    """ˤ retracts the root; it does not turn a palatal into a velar or a central vowel into a back
    one."""
    assert vectorize_phones(a) != vectorize_phones(b)


def test_a_listed_stack_equals_the_same_stack_read_by_the_rules():
    """A sound has one vector whether the table lists its exact stack or vectorize_phones builds
    it from a shorter base. Raised and lowered marks move a vowel only in listed stacks."""
    from phonematcher import features as f
    checked = 0
    for seg, listed in phone_features.items():
        for end in range(len(seg) - 1, 0, -1):
            base, marks = seg[:end], seg[end:]
            if base in phone_features and all((m, "post") in f._DIACRITICS for m in marks):
                try:
                    vec = phone_features[base]
                    for m in marks:
                        vec = f._apply_if(f._DIACRITICS[m, "post"], vec, seg)
                except ValueError:
                    break
                checked += 1
                assert vec == listed, seg
                break
    assert checked > 5000


@pytest.mark.parametrize("a, b", [("kʲ", "cʲ"), ("kʲ", "qʲ"), ("kʷ", "qʷ"), ("ɡʲ", "ɟ"), ("ŋʲ", "ɲ")])
def test_a_secondary_mark_keeps_the_primary_place(a, b):
    """Clements and Hume (1995): a secondary articulation adds to the primary one and does not replace it, so a palatalized
    velar is not a palatal and a labialized velar is not a labialized uvular."""
    assert vectorize_phones(a) != vectorize_phones(b)


@pytest.mark.parametrize("segment, base", [("kʲ", "k"), ("qʷ", "q"), ("ħʲ", "ħ"), ("sˠ", "s"), ("tˤ", "t")])
def test_a_secondary_mark_leaves_the_primary_place_as_it_is(segment, base):
    for f in ("hi", "lo", "back", "front", "ant", "cor"):
        assert feature(segment, f) is feature(base, f), f



@pytest.mark.parametrize("rhotic, vowel", [("ə˞", "ə"), ("a˞", "a"), ("ɚ", "ə"), ("ɝ", "ɜ")])
def test_rhoticity_keeps_the_vowel_height_and_rounding(rhotic, vowel):
    """[ɚ] is a mid central unrounded vowel with r-colouring (IPA chart): the mark changes neither
    the height nor the rounding of its vowel, but the vowel is still a different sound."""
    for f in ("hi", "lo", "round", "front", "back", "h3", "h4"):
        assert feature(rhotic, f) is feature(vowel, f), f
    assert vectorize_phones(rhotic) != vectorize_phones(vowel)


def test_precomposed_rhotic_vowels_equal_their_decomposed_forms():
    assert vectorize_phones("ɚ") == vectorize_phones("ə˞")
    assert vectorize_phones("ɝ") == vectorize_phones("ɜ˞")


def test_raised_and_lowered_marks_work_in_any_order():
    """The run-time rule moves a vowel one chart row, as the build does for listed stacks."""
    assert vectorize_phones("eː̞") == vectorize_phones("e̞ː")
    assert vectorize_phones("ɛ̝̃") != vectorize_phones("ɛ̃")


def test_pharyngealization_and_retracted_tongue_root_are_distinct():
    """Hermes et al. (2017, rt-MRI) and Al-Solami (2017, ultrasound): emphatics constrict the upper
    pharynx with the tongue dorsum, with inconsistent tongue-root retraction, so [iˤ] is not [i̙];
    both still retract the root."""
    assert vectorize_phones("iˤ") != vectorize_phones("i̙")
    assert feature("iˤ", "pharyngealized") is True and feature("i̙", "pharyngealized") is False
    assert feature("iˤ", "atr") is False and feature("i̙", "atr") is False


def test_velarized_or_pharyngealized_mark_leaves_the_choice_open():
    """The IPA chart names ◌̴ 'Velarized or pharyngealized': one of the two, not known which."""
    assert feature("l̴", "velarized") is None and feature("l̴", "pharyngealized") is None
    assert vectorize_phones("ɫ") == vectorize_phones("l̴")


@pytest.mark.parametrize("segment", ["d̥", "s̬", "t̬", "ɔ̹", "ɔ̜", "e̽", "d̚", "eˑ"])
def test_every_chart_diacritic_reads(segment):
    vectorize_phones(segment)


def test_voicing_marks_set_voice_on_any_base():
    assert feature("d̥", "voi") is False and feature("s̬", "voi") is True


def test_advanced_and_retracted_move_a_vowel_one_column():
    """IPA chart: ◌̟ advanced, ◌̠ retracted. [u̟] moves toward central, [e̠] too."""
    assert feature("u̟", "back") is False and feature("u̟", "front") is False
    assert feature("e̠", "front") is False and feature("e̠", "back") is False
    assert feature("ɨ̟", "front") is True


def test_rounding_marks_move_one_step_on_the_rounding_scale():
    """IPA chart: ◌̹ more rounded, ◌̜ less rounded."""
    assert feature("ɔ̜", "round") is None and feature("ɛ̹", "round") is None
    assert phonetic_distance("ɔ̜", "ʌ") < phonetic_distance("ɔ", "ʌ")


def test_half_long_sits_between_short_and_long():
    assert feature("eˑ", "long") is None
    assert phonetic_distance("eˑ", "e") == pytest.approx(phonetic_distance("eˑ", "eː"))


def test_mid_centralized_moves_to_the_centre_and_toward_mid():
    """IPA chart: ◌̽ mid-centralized. [e̽] is central and one row nearer mid than [e]."""
    assert feature("e̽", "front") is False and feature("e̽", "back") is False
    assert phonetic_distance("e̽", "ə") < phonetic_distance("ë", "ə")
