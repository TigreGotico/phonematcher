"""The feature table and the segment distance.

Expected values follow the IPA chart (International Phonetic Association; footer "IPA Chart revised to 2015/2005") and the feature definitions of PanPhon (Mortensen et al.
2016), never values read back from the table under test.
"""
import json
import unicodedata
from importlib.resources import files
from pathlib import Path

import pytest

from phonematcher.features import (
    FEATURES,
    NUM_FEATURES,
    SOURCE,
    phone_features,
    feature_distance,
    vectorize_phones,
)
from tests.conftest import feature


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
    assert feature_distance(affricate, fricative) < feature_distance(affricate, "a")


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
    assert feature_distance("p", "b") < feature_distance("p", "k")
    assert feature_distance("ʁ", "χ") < feature_distance("ʁ", "k")


def test_unknown_symbol_is_far_from_everything():
    assert feature_distance("?", "a") == 1.0
    with pytest.raises(ValueError):
        vectorize_phones("?")


@pytest.mark.parametrize("vowel", ["u", "ʊ", "o", "ɔ", "y", "ø", "ɒ"])
def test_rounded_vowels_are_labial(vowel):
    """The Hayes (2009) CSV gives every rounded vowel [+LABIAL, +round]."""
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
    """[æ] and [ɐ] are near-open (IPA chart); PHOIBLE 2.0 marks both [+low] in every inventory row.
    The Hayes CSV marks [æ] [+low] and lists no [ɐ]."""
    assert feature("æ", "lo") is True and feature("ɐ", "lo") is True
    assert feature_distance("ɐ", "a") < feature_distance("ɐ", "e")


def test_a_listed_diacritic_keeps_its_effect_on_a_chart_vowel():
    """A listed segment keeps its mark: pharyngealized [ɤˤ] has a retracted root, nasal [ɤ̃] is
    nasal, and both differ from [ɤ]."""
    assert feature("ɤˤ", "atr") is False and feature("ɤ̃", "nas") is True
    assert vectorize_phones("ɤˤ") != vectorize_phones("ɤ") != vectorize_phones("ɤ̃")


def test_tongue_root_is_its_own_feature():
    """Casali (2007): pharyngeal-cavity expansion measures the [ATR] contrast better than tongue
    root position alone, so this table gives [ATR] its own feature and not a vowel height."""
    assert feature("ɛ̘", "atr") is True and feature("ɛ̘", "tense") is feature("ɛ", "tense")
    assert feature("u̙", "atr") is False and vectorize_phones("u̙") != vectorize_phones("ʊ")


def test_centralized_vowel_is_neither_front_nor_back():
    """The IPA chart names ◌̈ 'Centralized'; this table reads it as the central column."""
    assert feature("ë", "front") is False and feature("ë", "back") is False
    assert vectorize_phones("ë") != vectorize_phones("e")


@pytest.mark.parametrize("segment, stop", [("ⁿd", "d"), ("ᵐb", "b"), ("ᵑɡ", "ɡ")])
def test_prenasalized_stop_is_a_nasal_stop(segment, stop):
    assert feature(segment, "nas") is True and feature(segment, "cont") is False
    assert feature_distance(segment, stop) < feature_distance(segment, "a")


def test_preaspirated_stop_has_spread_glottis():
    assert feature("ʰt", "sg") is True


#: Height row of each front vowel in this table's seven rows, from close (0) to open (6); the
#: front column has no mid (3) letter.
CHART_HEIGHT = {"i": 0, "ɪ": 1, "e": 2, "ɛ": 4, "æ": 5, "a": 6}


def test_vowel_distance_grows_with_chart_height_difference():
    """Down the front column of the chart, each step away from [i] is farther than the last."""
    rows = sorted(CHART_HEIGHT, key=CHART_HEIGHT.get)
    steps = [feature_distance("i", v) for v in rows]
    assert steps == sorted(steps) and len(set(steps)) == len(steps)


def test_mid_central_vowel_sits_between_close_mid_and_open_mid():
    """[ə] is mid on the chart, halfway between [ɘ] and [ɜ]."""
    assert feature_distance("ə", "ɘ") == pytest.approx(feature_distance("ə", "ɜ"))
    assert feature_distance("ə", "ɘ") < feature_distance("ɘ", "ɜ")


def test_open_a_is_front_and_near_open_a_is_central():
    """The chart draws [a] at the open front corner and [ɐ] in the central column, between open-mid and open."""
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
    """Labiodental flap (IPA chart) and the epiglottals (Hassan et al. 2011)."""
    assert vectorize_phones(letter) != vectorize_phones(near)
    assert feature_distance(letter, near) < feature_distance(letter, "a")
    expected = {"tap": True, "trill": True, "cont": False}[feat]
    assert feature(letter, feat) is expected


def test_labiodental_flap_has_the_place_of_v():
    for f in ("lab", "ant", "cor"):
        assert feature("ⱱ", f) is feature("v", f)


def test_lowered_and_raised_marks_move_a_vowel_one_chart_row():
    """◌̞ lowers and ◌̝ raises (IPA chart): lowered close-mid [e̞] is nearer open-mid [ɛ] than [e]
    is, and raised [ɛ̝] is nearer [e] than [ɛ] is."""
    assert feature_distance("e̞", "ɛ") < feature_distance("e", "ɛ")
    assert feature_distance("ɛ̝", "e") < feature_distance("ɛ", "e")


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
    it from a shorter base."""
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
    """A secondary articulation adds to the primary one and does not replace it, so a palatalized
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
    this table gives both [-atr]."""
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
    assert feature_distance("ɔ̜", "ʌ") < feature_distance("ɔ", "ʌ")


def test_half_long_sits_between_short_and_long():
    assert feature("eˑ", "long") is None
    assert feature_distance("eˑ", "e") == pytest.approx(feature_distance("eˑ", "eː"))


def test_mid_centralized_moves_to_the_centre_and_toward_mid():
    """IPA chart: ◌̽ mid-centralized. [e̽] is central and one row nearer mid than [e]."""
    assert feature("e̽", "front") is False and feature("e̽", "back") is False
    assert feature_distance("e̽", "ə") < feature_distance("ë", "ə")


def test_vectorize_phones_returns_the_table_row_for_every_listed_segment():
    """No listed segment is read differently from its table row, for example by a letter
    translation."""
    differ = [s for s, vec in phone_features.items() if vectorize_phones(s) != vec]
    assert differ == []


TIED_BASES = sorted({s for s in phone_features if "͡" in s
                     and not any(unicodedata.combining(c) for c in s.replace("͡", ""))
                     and all(c not in s for c in "ʰʲʷˠˤᶣːˀʼⁿˡ")})


def test_every_listed_tie_is_one_the_rule_rebuilds():
    """The rule for unlisted ties reproduces PanPhon's 23 bare ties, so it is checked against
    data it did not write."""
    from phonematcher.features import compose_tie
    assert len(TIED_BASES) == 23
    wrong = [s for s in TIED_BASES
             if compose_tie([vectorize_phones(p) for p in s.split("͡")]) != phone_features[s]]
    # PanPhon's rows for these leave hi and lo at 0, although the fricative's are -, and make
    # ɟ͡ʝ coronal and distributed with front 0, although ʝ is none of these; the rule follows the
    # fricative.
    assert wrong == ["b͡β", "p͡ɸ", "ɖ͡ʐ", "ɟ͡ʝ", "ʈ͡ʂ"]


@pytest.mark.parametrize("tied, like", [("t̠͡ʃ", "t͡ʃ"), ("t̠͡ʃʰ", "t͡ʃʰ"), ("m͡b", "ᵐb"),
                                        ("ŋ͡m͡ɡ͡b", "ᵑɡ͡b")])
def test_an_unlisted_tie_reads_by_the_rule(tied, like):
    assert feature_distance(tied, like) < 0.05


def test_a_nasal_tied_to_an_affricate_prenasalizes_it():
    assert feature("n̠͡d̠͡ʒ", "nas") is True and feature("n̠͡d̠͡ʒ", "delrel") is True


def test_breathy_release_reads_as_breathy_voice():
    assert vectorize_phones("bʱ") == vectorize_phones("b̤") == vectorize_phones("bʰ")


@pytest.mark.parametrize("tied", ["a͡i", "i͡a", "l͡j", "m͡l", "s͡t"])
def test_a_tie_the_rule_does_not_cover_raises(tied):
    """A vowel sequence is two segments, and a tie of two sonorants or a fricative before a stop
    has no reading here: it raises, it does not blend the parts."""
    with pytest.raises(ValueError):
        vectorize_phones(tied)


def test_an_affricate_keeps_the_glottal_features_of_its_stop():
    assert feature("tʼ͡s", "cg") is True and feature("tʰ͡s", "sg") is True


def test_the_first_22_features_are_the_columns_of_the_panphon_weight_file():
    # docs/design.md states that PanPhon 0.22.2's data has 22 features; the table's own come after them.
    import csv

    import panphon

    path = Path(panphon.__file__).parent / "data" / "feature_weights.csv"
    with open(path, encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert len(header) == 22
    assert list(FEATURES[:22]) == header


# Expected values from the IPA chart, not from the code. Vowels (a, i) are syllabic. The glides
# j and w are the non-syllabic counterparts of i and u. The chart's diacritic "◌̩ syllabic" makes
# m̩ syllabic. The chart's diacritic "◌˞ rhoticity" on ə gives ɚ, a vowel, so it is syllabic.
@pytest.mark.parametrize("segment, syllabic", [
    ("a", True), ("i", True), ("j", False), ("w", False), ("m̩", True), ("ɚ", True),
    ("m", False), ("zzz", False),
])
def test_is_vowel_phone_is_true_for_a_syllabic_segment(segment, syllabic):
    from phonematcher import is_vowel_phone

    assert is_vowel_phone(segment) is syllabic
