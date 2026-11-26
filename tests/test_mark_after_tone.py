"""A length mark or a combining mark written after a tone belongs to the segment that carries the
tone, as if written before it. A modifier letter after a tone, with no stop after it, has no base and
stays unread. Expected values are counted by hand, one code point at a time, in the comment beside
each case, or come from the form with the mark written before the tone."""
import pytest

from phonematcher import segment_spans, segments, substitution_cost, vectorize_phones


@pytest.mark.parametrize("text, segs, spans", [
    # a0 ˥1 ː2
    ("a˥ː", ["aː˥"], [(0, 3)]),
    # a0 ˥1 ˑ2
    ("a˥ˑ", ["aˑ˥"], [(0, 3)]),
    # a0 ˥1 ◌̃2
    ("a˥̃", ["ã˥"], [(0, 3)]),
    # m0 a1 ˥2 ː3
    ("ma˥ː", ["m", "aː˥"], [(0, 1), (1, 4)]),
    # a0 ˥1 ː2 t3
    ("a˥ːt", ["aː˥", "t"], [(0, 3), (3, 4)]),
    # a0 ˥1 ◌̃2 space3 t4
    ("a˥̃ t", ["ã˥", " ", "t"], [(0, 3), (4, 5)]),
    # t0 a1 m2 ˧3 ː4: a coda stands between, so the mark stays on the tone, as on dev
    ("tam˧ː", ["t", "a", "m", "˧ː"], [(0, 1), (1, 2), (2, 3), (3, 5)]),
    # y0 ȶ1 ⁵2 ◌̩3: the same with a numeral tone
    ("yȶ⁵̩", ["y", "ȶ", "˥̩"], [(0, 1), (1, 2), (2, 4)]),
    # a0 ˥1 ː2 ˧3: the second tone has no bearer without a tone
    ("a˥ː˧", ["aː˥", "˧"], [(0, 3), (3, 4)]),
    # a0 ˥1 ː2 ʰ3 t4: ʰ before a stop is a pre-mark of the stop
    ("a˥ːʰt", ["aː˥", "ʰt"], [(0, 3), (3, 5)]),
    # a0 ˥1 ◌̃2 ◌̈3: two combining marks
    ("a˥̃̈", ["ã̈˥"], [(0, 4)]),
    # ˥0 ː1: no bearer
    ("˥ː", ["˥ː"], [(0, 2)]),
    # m0 a1 ˥2 ʰ3: ʰ has no stop after it, so it stays on the tone
    ("ma˥ʰ", ["m", "a", "˥ʰ"], [(0, 1), (1, 2), (2, 4)]),
    # a0 ˥1 ʷ2
    ("a˥ʷ", ["a", "˥ʷ"], [(0, 1), (1, 3)]),
    # a0 ˥1 ː2 ʰ3: the length mark moves, ʰ stays unread
    ("a˥ːʰ", ["a", "˥ːʰ"], [(0, 1), (1, 4)]),
    # a0 ˧1 ⁿ2: no stop follows
    ("a˧ⁿ", ["a", "˧ⁿ"], [(0, 1), (1, 3)]),
])
def test_segments_and_spans(text, segs, spans):
    assert segments(text) == segs
    assert segment_spans(text) == spans


@pytest.mark.parametrize("after, before", [
    ("a˥ː", "aː˥"),
    ("a˥ˑ", "aˑ˥"),
    ("a˥̃", "ã˥"),
    ("ma˥ː", "maː˥"),
    ("ma˥̃t", "mã˥t"),
    ("a˥ːʰt", "aː˥ʰt"),
    ("a˥̃ ma˩ː", "ã˥ maː˩"),
])
def test_equals_mark_before_tone(after, before):
    assert segments(after) == segments(before)
    assert [vectorize_phones(s) for s in segments(after) if s != " "] == [vectorize_phones(s) for s in segments(before) if s != " "]
    assert [substitution_cost(a, b) for a, b in zip(segments(after), segments(before))] == [0.0] * len(segments(before))


def test_unread_tone_costs_one():
    assert substitution_cost("˥ʰ", "a˥") == 1.0
    assert substitution_cost("˥ːʰ", "aː˥") == 1.0
