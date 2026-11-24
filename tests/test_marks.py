"""Marks that carry a meaning in a quoted chart: the extIPA strong and weak articulation, the IPA
chart's ring above a descender, and the Unicode code chart annotations ``IPA: ...``.

The expected values come from the chart text quoted in each row of ``data/overrides.json``
and from PanPhon's own segment rows, not from the rules under test.
"""
import pytest

from phonematcher.distance import segment_spans, segments
from phonematcher.features import feature_distance, vectorize_phones
from tests.conftest import feature, differs


# IPA chart, note under the diacritics: "Some diacritics may be placed above a symbol with a
# descender, e.g. ŋ̊". The ring is the ring of "Voiceless", so ŋ̊ is ŋ̥ and ɡ̊ is ɡ̥.
@pytest.mark.parametrize("above, below", [("ŋ̊", "ŋ̥"), ("ɡ̊", "ɡ̥"), ("ɲ̊", "ɲ̥"), ("j̊", "j̥")])
def test_ring_above_reads_as_the_ring_below(above, below):
    assert vectorize_phones(above) == vectorize_phones(below)
    assert feature(above, "voi") is False


# PanPhon 0.22.2 lists eight segments of a letter plus ◌̪ (for example t̪, d̪, n̪, l̪, s̪), and each
# differs from its bare letter in [distributed] alone, - to +. ɾ̪ and ɮ̪ are not listed.
@pytest.mark.parametrize("letter", ["ɾ", "ɮ", "θ", "ɹ"])
def test_dental_sets_only_distributed(letter):
    assert differs(letter + "̪", letter) <= {"distr"}
    assert feature(letter + "̪", "distr") is True


# Unicode U0300: "0322 COMBINING RETROFLEX HOOK BELOW • IPA: retroflexion". The chart's retroflex
# letters ʈ ɖ ɳ ɭ ɻ ɽ ʂ ʐ are [+coronal, -anterior]; ɺ is [+coronal, +anterior].
def test_retroflexion_moves_a_coronal_to_the_retroflex_place():
    assert differs("ɺ̢", "ɺ") == {"ant"}
    assert feature("ɺ̢", "ant") is feature("ʈ", "ant") is False
    assert feature("ɺ̢", "cor") is True


# Unicode U0300: "0347 COMBINING EQUALS SIGN BELOW • IPA: alveolar". The alveolar letters
# t d n s z l r are [+coronal, +anterior], and ʐ is [-anterior].
@pytest.mark.parametrize("retroflex, alveolar", [("ʐ͇", "z"), ("ʂ͇", "s")])
def test_equals_sign_below_gives_a_retroflex_the_alveolar_place(retroflex, alveolar):
    assert feature(retroflex, "ant") is feature(alveolar, "ant") is True
    assert differs(retroflex, retroflex[0]) == {"ant"}


# Unicode U0300: "0323 COMBINING DOT BELOW • IPA: closer variety of vowel". The rows come from the
# IPA chart's vowel quadrilateral: a is open and æ near-open; ɐ is near-open and ɜ open-mid; ɛ is
# open-mid and ə mid.
HEIGHT = ("hi", "lo", "h1", "h2", "h3", "h4", "h5", "h6")


@pytest.mark.parametrize("raised, closer", [("ạ", "æ"), ("ɐ̣", "ɜ"), ("ɛ̣", "ə")])
def test_dot_below_moves_a_vowel_one_row_closer(raised, closer):
    assert all(feature(raised, f) is feature(closer, f) for f in HEIGHT)


# Unicode U0300 gives "032D COMBINING CIRCUMFLEX ACCENT BELOW" the annotation "Americanist:
# fronted articulation" and "031F" the annotation "IPA: advanced or fronted articulation".
@pytest.mark.parametrize("vowel", ["a", "i", "o", "u", "ɨ"])
def test_circumflex_below_reads_as_advanced(vowel):
    assert vectorize_phones(vowel + "̭") == vectorize_phones(vowel + "̟")


def test_a_back_vowel_fronted_is_central():
    assert (feature("ṷ", "front"), feature("ṷ", "back")) == (False, False)


# extIPA chart (revised to 2015): "strong articulation" and "weak articulation". The chart gives
# neither a feature, so both read as the base.
@pytest.mark.parametrize("stop", ["p", "t", "k", "t͡ɕ", "s", "ʈ", "t̪", "m", "f"])
def test_strong_articulation_changes_no_feature(stop):
    assert vectorize_phones(stop + "͈") == vectorize_phones(stop)


@pytest.mark.parametrize("stop", ["p", "t", "k", "ʈ", "t̪", "s", "m", "j"])
def test_weak_articulation_changes_no_feature(stop):
    assert vectorize_phones(stop + "͉") == vectorize_phones(stop)


# Unicode U02B0: ˔ "vowel raising or closing → 031D", ˕ "vowel lowering or opening → 031E",
# ˖ "advanced or fronted articulation → 031F", ˗ "retracted or backed articulation → 0320".
# The chart's rows: ɛ is open-mid, ə is mid and æ is near-open, so ɛ˔ has the height of ə and ɛ˕
# the height of æ.
def test_spacing_raised_and_lowered_move_one_row():
    assert all(feature("ɛ˔", f) is feature("ə", f) for f in HEIGHT)
    assert all(feature("ɛ˕", f) is feature("æ", f) for f in HEIGHT)


def test_spacing_advanced_and_retracted_move_one_column():
    assert (feature("ɨ˖", "front"), feature("ɨ˖", "back")) == (True, False)
    assert (feature("ɨ˗", "front"), feature("ɨ˗", "back")) == (False, True)


# The charts give these marks no meaning that a feature can carry, so they stay unread.
@pytest.mark.parametrize("segment", [
    "dˁ",   # U+02C1: "typographical alternate for 02BF ʿ", the Arabic ain transliteration
    "jᵊ", "ɡᵝ", "tˢ", "eˣ",   # "≈ <super>" letters: only the letter's identity
    "n̍", "a̍", "ʔ̍", "ʎ̍", "ɬ̍",   # U+030D on a letter with no descender: "this is not the Greek tonos; Marshallese"
    "ɑʶː",  # U+02B6: "r-coloring or r-offglides"
    "ʄ̵", "ɾ͓", "a͠",   # U+0335, U+0353, U+0360: no annotation
])
def test_a_mark_with_no_quoted_meaning_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


# IPA chart, note under the diacritics: "Some diacritics may be placed above a symbol with a
# descender, e.g. ŋ̊". The mark ◌̍ (U+030D) above a letter with a descender is the syllabic mark
# ◌̩ (U+0329) of the chart, as the ring above is the ring below.
@pytest.mark.parametrize("above, below", [("ŋ̍", "ŋ̩"), ("ɲ̍", "ɲ̩"), ("j̍", "j̩"), ("ɻ̍", "ɻ̩"), ("ç̍", "ç̩"), ("ɰ̍", "ɰ̩"), ("ɭ̍", "ɭ̩"), ("ɱ̍", "ɱ̩")])
def test_mark_above_a_descender_reads_as_syllabic(above, below):
    assert vectorize_phones(above) == vectorize_phones(below)
    assert feature(above, "syl") is True


@pytest.mark.parametrize("above, below", [("ɡ̍", "ɡ̩"), ("g̍", "ɡ̩"), ("p̍", "p̩")])
def test_mark_above_a_descender_has_the_refusal_of_the_mark_below(above, below):
    with pytest.raises(ValueError, match="does not apply"):
        vectorize_phones(below)
    with pytest.raises(ValueError, match="does not apply"):
        vectorize_phones(above)


def test_mark_above_a_descender_after_another_mark():
    assert vectorize_phones("ŋ̊̍") == vectorize_phones("ŋ̩̊")


def test_mark_above_a_descender_carries_a_tone():
    assert segments("ŋ̍˩˧") == ["ŋ̍˩˧"]
    assert vectorize_phones("ŋ̍˩˧") == vectorize_phones("ŋ̩˩˧")
    assert segments("maŋ̍˩˧") == ["m", "a", "ŋ̍˩˧"]


@pytest.mark.parametrize("text, spans", [("ŋ̍˩˧", [(0, 4)]), ("aŋ̍ˈn", [(0, 1), (1, 3), (4, 5)]),
                                         ("ŋ̍ ɲ̍", [(0, 2), (3, 5)]), ("ŋ̊̍a", [(0, 3), (3, 4)])])
def test_mark_above_a_descender_keeps_offsets(text, spans):
    assert segment_spans(text) == spans


# A spelling is read as its tied form first, so the mark reads as on t͡ʃ, which refuses it.
@pytest.mark.parametrize("segment, tied", [("ʧ̍", "t͡ʃ̩"), ("ʤ̍", "d͡ʒ̩"), ("ʨ̍", "t͡ɕ̩"), ("ʥ̍", "d͡ʑ̩")])
def test_mark_above_a_ligature_reads_as_on_its_tied_form(segment, tied):
    with pytest.raises(ValueError):
        vectorize_phones(tied)
    with pytest.raises(ValueError):
        vectorize_phones(segment)
