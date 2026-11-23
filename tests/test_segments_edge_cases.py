"""Tone marks, tie bars and format characters in unexpected places.

Expected segments are written by hand from the rules in the ``segments`` docstring: a tone is one
segment of tone letters after its syllable (U+0301 is ``˦``, U+0300 is ``˨``, from the IPA chart's
tone diacritics), a space is a word boundary, and a format character carries no sound.
"""
import pytest

from phonematcher import ipa_distance, segments

ACUTE, GRAVE, TIE = "́", "̀", "͡"


def test_tone_mark_typed_after_a_tie_reads_as_on_the_syllable():
    # Typed t, tie, acute, s, a: NFD orders the acute (ccc 230) before the tie (ccc 234).
    typed = "t" + TIE + ACUTE + "sa"
    assert segments(typed) == ["t͡s", "a", "˦"]
    assert segments(typed) == segments("t͡sá")
    assert ipa_distance(typed, "t͡sá") == 0.0


def test_tone_mark_after_a_tie_with_no_following_base():
    assert segments("t" + TIE + ACUTE + "s") == ["t͡s", "˦"]


def test_tie_after_a_space_does_not_join_across_the_space():
    assert segments("a " + TIE + "ba") == ["a", " ", "b", "a"]
    assert ipa_distance("a " + TIE + "ba", "a ba") == 0.0


def test_tie_at_the_start_is_dropped():
    assert segments(TIE + "ab") == ["a", "b"]


def test_tone_mark_after_a_tone_letter_folds_into_that_tone():
    # ˥ then U+0301 (˦): one tone ˥˦, not two tone segments.
    assert segments("ma˥" + ACUTE) == ["m", "a", "˥˦"]


@pytest.mark.parametrize("text, expected", [
    (ACUTE + "a", ["a", "˦"]),
    ("pa " + GRAVE + "ma", ["p", "a", " ", "m", "˨", "a"]),
])
def test_word_initial_tone_mark_belongs_to_the_next_base(text, expected):
    assert segments(text) == expected


@pytest.mark.parametrize("mark", ["​", "‌", "‍", "⁠", "﻿", "­"])
def test_format_characters_are_dropped(mark):
    assert segments("a" + mark + "b") == ["a", "b"]
    assert segments(mark + "pa") == ["p", "a"]
    assert ipa_distance("a" + mark + "b", "ab") == 0.0
