"""The phonematcher system compares segments and words as the library does."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

from phonematcher import ipa_distance  # noqa: E402
from phonematcher.tone import tone_distance  # noqa: E402
from systems import PhoneMatcher, UnreadSegment  # noqa: E402

SYSTEM = PhoneMatcher()


def test_two_tones_cost_their_tone_distance_as_in_a_word():
    # ˨˨ against ˥˥: the contours (2,2,2) and (5,5,5) differ by 3 at each of 3 points, 9 over
    # 4 * 3 = 0.75; the substitution costs sqrt(0.75) = 0.866025, as the edit distance prices it,
    # and not the 1.0 that a feature distance gives two unlisted segments.
    assert SYSTEM.segment_distance("²²", "⁵⁵") == pytest.approx(0.866025, abs=1e-6)
    assert SYSTEM.segment_distance("²²", "⁵⁵") == pytest.approx(tone_distance("˨˨", "˥˥") ** 0.5)
    assert SYSTEM.segment_distance("²²", "⁵⁵") < 1.0


def test_a_diphthong_given_whole_reads_as_its_two_vowels():
    assert SYSTEM.reads("ei")
    assert SYSTEM.word_distance(["ei"], ["e", "i"]) == 0.0
    # The library splits "pei" into p, e, i: three segments, so one deletion (0.5) over three.
    assert SYSTEM.word_distance(["p", "ei"], ["p", "e"], normalized=True) == ipa_distance("pei", "pe", normalized=True)


def test_alignment_leaves_a_diphthong_given_whole_unread():
    with pytest.raises(UnreadSegment):
        SYSTEM.align(["p", "ei"], ["p", "e"])


def test_an_unreadable_segment_stays_unread():
    assert not SYSTEM.reads("☃")


def test_aline_aligns_the_ipa_g_it_reads():
    from systems import Aline

    assert Aline().align(["ɡ", "a"], ["k", "a"]) == [("ɡ", "k"), ("a", "a")]
