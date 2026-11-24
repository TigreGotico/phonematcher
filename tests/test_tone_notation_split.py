"""A tone run splits where its notation changes.

The IPA adopted left-stem ("reversed") tone letters at the 1989 Kiel Convention; the chart does not
print them. In sandhi notation the right-stem letters give the underlying tone and the left-stem
letters after them the surface tone: Mandarin ``ni˨˩˦꜔꜒`` is the tone 214, then the tone 35. Two
notations are never one contour, so right-stem letters, left-stem letters and superscript numerals
each start a new tone. The first tone goes onto its vowel; a second tone on the same vowel stays a
tone segment of its own, the surface tone of the sandhi.
"""
import pytest

from phonematcher import segment_spans, segments
from phonematcher.tone import tone_levels


def test_chao_letters_then_left_stem_letters_are_two_tones():
    assert segments("ni˨˩˦꜔꜒") == ["n", "i˨˩˦", "˧˥"]
    assert segment_spans("ni˨˩˦꜔꜒") == [(0, 1), (1, 5), (5, 7)]
    assert tone_levels("˨˩˦") == (2, 1, 4)
    assert tone_levels("꜔꜒") == (3, 5)


def test_a_chao_letter_then_a_numeral_are_two_tones():
    assert segments("ni˥⁵") == ["n", "i˥", "˥"]


@pytest.mark.parametrize("text, expected, spans", [
    ("ma˥˩", ["m", "a˥˩"], [(0, 1), (1, 4)]),
    ("ni⁵¹", ["n", "i˥˩"], [(0, 1), (1, 4)]),
    ("ni꜔꜒", ["n", "i˧˥"], [(0, 1), (1, 4)]),
    ("ni⁵⁰", ["n", "i˥"], [(0, 1), (1, 3)]),  # ⁰ has no level and is dropped
])
def test_one_notation_stays_one_tone(text, expected, spans):
    assert segments(text) == expected
    assert segment_spans(text) == spans


def test_a_second_tone_on_one_vowel_stays_a_tone_segment():
    # sandhi: the underlying tone goes to the vowel, the surface tone stays a standalone run
    assert segments("ma˥˩꜒") == ["m", "a˥˩", "˥"]
    assert segments("ni˨˩˦꜔꜒")[2] == "˧˥"
