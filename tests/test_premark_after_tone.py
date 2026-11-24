"""A prenasal mark after a tone letter prenasalizes the next stop, and a stress mark between a
prenasal mark and its stop lies inside the span of that segment. Expected values are counted by
hand, one code point at a time, in the comment beside each case."""
import pytest

from phonematcher import segment_spans, segments


@pytest.mark.parametrize("text, segs, spans", [
    # a0 ˧1 ᵐ2 b3 i4 ˥5
    ("a˧ᵐbi˥", ["a", "˧", "ᵐb", "i", "˥"], [(0, 1), (1, 2), (2, 4), (4, 5), (5, 6)]),
    # a0 ˧1 ˥2 ᵐ3 b4 (a run of tone letters)
    ("a˧˥ᵐb", ["a", "˧˥", "ᵐb"], [(0, 1), (1, 3), (3, 5)]),
    # ˧0 ᵐ1 b2 a3 (a tone letter at the word start)
    ("˧ᵐba", ["˧", "ᵐb", "a"], [(0, 1), (1, 3), (3, 4)]),
    # a0 ˧1 space2 ᵐ3 b4
    ("a˧ ᵐb", ["a", "˧", " ", "ᵐb"], [(0, 1), (1, 2), (3, 5)]),
    # k0 ˧1 ᵐ2 b3: a consonant before the tone letter is no vowel, so ᵐ stays alone
    ("k˧ᵐb", ["k", "˧", "ᵐ", "b"], [(0, 1), (1, 2), (2, 3), (3, 4)]),
    # ɲ0 a1 ⁿ2 ˈ3 d4 u5: the stress mark is inside the span of ⁿd
    ("ɲaⁿˈdu", ["ɲ", "a", "ⁿd", "u"], [(0, 1), (1, 2), (2, 5), (5, 6)]),
    # a0 ˧1 ᵐ2 ˈ3 b4
    ("a˧ᵐˈb", ["a", "˧", "ᵐb"], [(0, 1), (1, 2), (2, 5)]),
])
def test_segments_and_spans(text, segs, spans):
    assert segments(text) == segs
    assert segment_spans(text) == spans


@pytest.mark.parametrize("text", ["ɲaⁿˈdu", "a˧ᵐbi˥", "a˧ᵐˈb"])
def test_each_span_is_its_segment(text):
    for seg, (s, e) in zip(segments(text), segment_spans(text)):
        assert segments(text[s:e]) == [seg]
