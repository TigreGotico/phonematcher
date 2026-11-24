"""Marks that a base refuses.

PanPhon's rule for a mark applies only to some bases. This table widens a rule only where a chart
prints the mark on that class of base. The expected values below follow the IPA chart (footer "IPA
Chart revised to 2015/2005"), the extIPA chart (revised to 2015) and the Unicode Standard 18.0
code charts, never values read back from the table.
"""
import re

import pytest

from phonematcher.features import vectorize_phones
from tests.conftest import feature, differs


# IPA chart, diacritics: "Nasalized" with the example ẽ, a vowel. The chart ties the mark to no
# voicing, so a voiceless vowel takes it. Nasalization sets [nas] and nothing else, as it does on
# ẽ against e.
@pytest.mark.parametrize("nasalized, plain", [("ɐ̥̃", "ɐ̥"), ("ɨ̥̃", "ɨ̥"), ("ũ̥", "u̥")])
def test_nasalized_voiceless_vowel_differs_by_nasal_alone(nasalized, plain):
    assert differs(nasalized, plain) == {"nas"}
    assert feature(nasalized, "nas") is True
    assert feature(plain, "nas") is False


def test_nasalized_vowel_that_already_read_is_unchanged():
    assert differs("ẽ", "e") == {"nas"}
    assert feature("ɐ̃", "nas") is True


# IPA chart: the chart prints "Nasalized" on a vowel only. A consonant with the mark, and a nasal
# that is nasal already, stay refused.
@pytest.mark.parametrize("segment", ["k̃", "f̃", "h̃", "m̃", "ñ"])
def test_nasalized_consonant_stays_unread(segment):
    with pytest.raises(ValueError, match=re.escape("'̃' does not apply")):
        vectorize_phones(segment)


# A base the chart does not print the mark on, grouped by mark. Each row of the census class
# "condition" that a chart does not cover is here once, and its mark is the reason it fails.
REFUSED = {
    # Nasalized: the IPA chart prints the mark on the vowel in ẽ and on no consonant.
    '̃': "f̃ h̃ h̃ʷ k̃ m̃ p̃ s̃ t̃ x̃ ñ ħ̃ ʔ̃ χ̃",
    # Creaky voiced: the IPA chart prints b̰ and a̰, both voiced. These bases are voiceless.
    '̰': "k̰ k̰ʲ p̰ s̰ t̰",
    # Lateral release: the IPA chart prints dˡ, a stop at the alveolar ridge. These bases are nasals and non-coronal stops.
    'ˡ': "mˡ nˡ pˡ pˡʰ ᵐbˡ ᵐpˡʰ",
    # Extra-short: the IPA chart prints ĕ, a vowel. These bases are consonants and glides.
    '̆': "ĭ̯ ŭ̯ ɭ̆ ɭ̆ʱ ɳ̆",
    # Aspirated: the IPA chart prints tʰ and dʰ, the extIPA chart ʰp. These bases are vowels, nasals, liquids, glides and ʔ.
    'ʰ': "aʰ aːʰ eʰ eːʰ iʰ jʰ lʰ l̥ʰ mʰ m̥ʰ nʰ n̥ʰ oʰ oːʰ rʰ r̥ʰ uʰ w̥ʰ yʰ øːʰ œʰ ɑʰ ɑːʰ ɔʰ əʰ ɛʰ ɪʰ ɲʰ ɵʰ ɾʰ ʊʰ ʌʰ ʔʰ ʰj ʰr̥ ŋ̊ʰ",
    # Labialized: the IPA chart prints tʷ and dʷ. These bases are vowels and a syllabic fricative.
    'ʷ': "oʷː uʷ uʷː yʷː z̩ʷ øʷː ɔʷ ʉʷ ʉʷː ʊʷ ʏʷ",
    # Nasal release: the IPA chart prints dⁿ. These bases are vowels, fricatives, liquids, glides and a nasal.
    'ⁿ': "aⁿ eⁿ iⁿ oⁿ uⁿ ãⁿ äⁿ ɑⁿ ᵐf ᵐfʷ ᵐm ᵐv ᵐw ᵐz ᵑɣᶣ ᵑʃ ⁿf ⁿh ⁿhʷ ⁿj ⁿl ⁿlʷ ⁿs ⁿsʷ ⁿv ⁿw ⁿz ⁿz̤ ⁿʃ ⁿʒ ⁿθ ⁿç ⁿçʷ",
    # Lowered: the IPA chart prints β̞ on a fricative. These bases are stops.
    '̞': "d̞ k̞ʰ t̞ ɡ̞",
    # Palatalized: the IPA chart prints tʲ and dʲ. These bases are vowels.
    'ʲ': "aʲ eʲ iʲ ãʲ ẽʲ",
    # Syllabic: the IPA chart prints n̩, a nasal, and Unicode U0250 spells the apical vowel ɿ as z̩. These bases are vowels and a stop.
    '̩': "a̩ a̩ː i̩ i̩ː m̩̩ o̩ o̩ː u̩ u̩ː ɔ̩ ɔ̩ː ɛ̩ ɛ̩ː ɟ̰̩ ɪ̩ ɪ̩ː ʊ̩ ʊ̩ː",
    # Breathy voiced: the Unicode chart gives the name and no base. These bases are voiceless clicks and q.
    'ʱ': "qʱ ǀʱ ǁʱ ǃʱ",
    # Long: the IPA chart prints ː once, and no overlong mark.
    'ː': "eːː iːː kːː lːː pːː tːː ĩːː",
    # Non-syllabic: the IPA chart prints e̯. This base is already non-syllabic.
    '̯': "u̯̯",
    # Ejective: the IPA chart prints p’ t’ k’ s’. This base is a lateral approximant.
    'ʼ': "ʎʼ",
    # Centralized: the IPA chart prints ë, a vowel. These bases are a stop and a glide.
    '̈': "d̠̈ ẅ",
    # Laminal: the IPA chart prints t̻ and d̻. This base is a labial nasal.
    '̻': "m̻",
    # Linguolabial: the IPA chart prints t̼ and d̼. These bases are labial.
    '̼': "m̼ p̼ v̼",
    # Glottal stop modifier: no chart gives the mark a meaning on a vowel.
    'ˀ': "ɑ̰ˀ ʊ̰ˀ",
}


@pytest.mark.parametrize(
    "mark, segment", [(m, s) for m, row in REFUSED.items() for s in row.split()])
def test_mark_stays_refused_where_no_chart_prints_it(mark, segment):
    with pytest.raises(ValueError, match=re.escape(f"{mark!r} does not apply")):
        vectorize_phones(segment)


# Unicode chart U0250, PDF p. 5: "027F ɿ ... IPA spelling - 007A z 0329", the syllabic mark on a
# fricative. A fricative of any release takes the mark and changes [syl] alone.
@pytest.mark.parametrize("syllabic, plain", [("ɮ̩", "ɮ"), ("ɮ̩̻", "ɮ̻"), ("z̩", "z"), ("ʃ̩", "ʃ")])
def test_syllabic_fricative_differs_by_syl_alone(syllabic, plain):
    assert differs(syllabic, plain) == {"syl"}
    assert feature(syllabic, "syl") is True


def test_apical_vowel_letter_equals_syllabic_z():
    assert vectorize_phones("ɿ") == vectorize_phones("z̩")


# Unicode chart U1D00, U+1D61: "≈ <super> 03C7 χ". The mark has no meaning of its own, and the
# note under ˠ about affricates does not name it.
@pytest.mark.parametrize("segment", ["ʣᵡ", "ʣᵡʼ", "ʦᵡ", "ʦᵡʼ"])
def test_superscript_chi_after_an_affricate_stays_unread(segment):
    with pytest.raises(ValueError, match="Unrecognized phone"):
        vectorize_phones(segment)


# The marks that move a chart vowel along a column move nothing on a consonant, so the consonant
# reads as its bare letter. The IPA chart prints each mark on a vowel only.
@pytest.mark.parametrize("mark", ["̟", "̠", "̭", "˖", "˗"])
def test_column_marks_on_a_consonant_read_as_the_bare_letter(mark):
    assert vectorize_phones("t" + mark) == vectorize_phones("t")


# The IPA chart prints ◌̝ on an approximant (ɹ̝) and ◌̞ on a fricative (β̞). Raising a fricative
# or lowering an approximant has no consonant reading, so the consonant reads as its bare letter.
@pytest.mark.parametrize("mark, base", [("̝", "s"), ("˔", "s"), ("̞", "ɹ"), ("˕", "ɹ")])
def test_row_marks_with_no_consonant_reading_read_as_the_bare_letter(mark, base):
    assert vectorize_phones(base + mark) == vectorize_phones(base)
