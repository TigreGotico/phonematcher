"""A prenasal written as two tied marks.

Plan ruling on prenasals: "after a vowel, a space or the start of a word it prenasalizes the next
stop (``aⁿda`` gives ``a``, ``ⁿd``, ``a``)". The prenasal of a labial-velar is written ``ᵑᵐ`` or,
tied, ``ᵑ͡ᵐ`` (orthography2ipa bax). The tie bar joins the two marks, so the pair stays before the
stop. ``ᶮ`` has no quoted meaning (see ``test_marks.py``), so it stays its own segment. The
expected vectors come from the nasal tied to the stop, a path that does not read marks.
"""
import pytest

from phonematcher import segment_spans, segments
from phonematcher.features import vectorize_phones

CASES = [
    ("aᵑ͡ᵐk͡pa", ["a", "ᵑ͡ᵐk͡p", "a"], [(0, 1), (1, 7), (7, 8)]),
    ("aᵑ͡ᵐɡ͡ba", ["a", "ᵑ͡ᵐɡ͡b", "a"], [(0, 1), (1, 7), (7, 8)]),
    ("ᵑ͡ᵐk͡pa", ["ᵑ͡ᵐk͡p", "a"], [(0, 6), (6, 7)]),
    ("ᵑᵐɡ͡bala", ["ᵑᵐɡ͡b", "a", "l", "a"], [(0, 5), (5, 6), (6, 7), (7, 8)]),
    ("aᶮɟiŋ", ["a", "ᶮɟ", "i", "ŋ"], [(0, 1), (1, 3), (3, 4), (4, 5)]),
]


@pytest.mark.parametrize("text, expected, spans", CASES)
def test_a_prenasal_after_a_vowel_starts_the_next_stop(text, expected, spans):
    assert segments(text) == expected
    assert segment_spans(text) == spans


def test_the_same_marks_after_a_consonant_stay_apart():
    # ᵐ is not the IPA nasal-release mark (that is ⁿ), so after t it is left as its own segment.
    assert segments("tᵐa") == ["t", "ᵐ", "a"]
    assert segments("tⁿa") == ["tⁿ", "a"]


@pytest.mark.parametrize("marked, tied", [
    ("ᵑ͡ᵐk͡p", "ŋ͡m͡k͡p"), ("ᵑ͡ᵐɡ͡b", "ŋ͡m͡ɡ͡b"),
])
def test_a_prenasal_mark_reads_as_the_nasal_tied_before_the_stop(marked, tied):
    assert vectorize_phones(marked) == vectorize_phones(tied)
