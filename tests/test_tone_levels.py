"""tone_levels: the public reader of a tone's Chao levels. Expected values are written by hand
from Chao's scale (1 extra low to 5 extra high) and from the Unicode character names."""
import unicodedata

import pytest

import phonematcher
from phonematcher.tone import tone_levels

#: the level word of each Unicode tone letter name, on Chao's five-point scale
CHAO = {"EXTRA-LOW": 1, "LOW": 2, "MID": 3, "HIGH": 4, "EXTRA-HIGH": 5}


@pytest.mark.parametrize("tone, levels", [
    ("˧˦˧", (3, 4, 3)),      # rising-falling: mid, high, mid
    ("˥", (5,)), ("˩", (1,)),
    ("˨˩˦", (2, 1, 4)),      # Mandarin third tone, 214
    ("²¹⁴", (2, 1, 4)),      # the same tone in numerals
    ("⁵⁵", (5, 5)),
    ("꜒꜔", (5, 3)),         # left-stem extra-high then mid
    ("˧³", (3, 3)),          # letters and numerals mix
])
def test_hand_values(tone, levels):
    assert tone_levels(tone) == levels


@pytest.mark.parametrize("letter", ["꜒", "꜓", "꜔", "꜕", "꜖", "˥", "˦", "˧", "˨", "˩"])
def test_each_tone_letter_reads_as_the_level_its_unicode_name_gives(letter):
    # e.g. "MODIFIER LETTER EXTRA-HIGH LEFT-STEM TONE BAR" -> EXTRA-HIGH -> 5
    word = unicodedata.name(letter).split()[2]
    assert tone_levels(letter) == (CHAO[word],)


def test_it_is_exported_from_the_root():
    assert "tone_levels" in phonematcher.__all__
    assert vars(phonematcher).get("tone_levels") is tone_levels


@pytest.mark.parametrize("value", ["", "a", "ma˥", "⁰", "˥ "])
def test_a_string_that_is_not_a_tone_raises_value_error(value):
    with pytest.raises(ValueError, match="not a tone"):
        tone_levels(value)


def test_a_value_that_is_not_a_string_raises_type_error():
    with pytest.raises(TypeError):
        tone_levels(5)


def test_the_private_names_still_work():
    from phonematcher.tone import DIACRITIC_TONES, NUMERALS, _contour
    assert NUMERALS["³"] == "˧" and DIACRITIC_TONES["́"] == "˦"
    assert _contour(tone_levels("˩˥")) == (1.0, 3.0, 5.0)  # linear: 1, mid-point 3, 5
