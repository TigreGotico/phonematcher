"""Letters with no tie bar read as the tied segment, and marks before them apply to it.

The IPA chart (``IPA_Kiel.pdf``, footer "IPA Chart revised to 2015/2005"), note under "Other
symbols": "Affricates and double articulations can be represented by two symbols joined by a tie
bar if necessary." Only a segment given whole is read this way; ``segments`` keeps two letters in
running text as two segments.
"""
import pytest

from phonematcher import segments
from phonematcher.features import FEATURES, vectorize_phones

# Untied form, tied form: affricates, double articulations and prenasalized stops, with and without
# marks after them. The tied form is in the table or built by ``compose_tie`` as before.
PAIRS = [
    ("ts", "t͡s"), ("dz", "d͡z"), ("tʃ", "t͡ʃ"), ("dʒ", "d͡ʒ"), ("tɕ", "t͡ɕ"), ("pf", "p͡f"),
    ("tɬ", "t͡ɬ"), ("kx", "k͡x"), ("cç", "c͡ç"), ("ʈʂ", "ʈ͡ʂ"), ("kp", "k͡p"), ("ɡb", "ɡ͡b"),
    ("mb", "m͡b"), ("nd", "n͡d"), ("ŋɡ", "ŋ͡ɡ"), ("ndz", "n͡d͡z"),
    ("tsʰ", "t͡sʰ"), ("tʃʼ", "t͡ʃʼ"), ("dʒʱ", "d͡ʒʱ"), ("tsː", "t͡sː"), ("tːs", "tː͡s"),
    ("t̠ʃ", "t̠͡ʃ"), ("t̠ʃʰ", "t̠͡ʃʰ"), ("tsʲ", "t͡sʲ"),
]


@pytest.mark.parametrize("untied, tied", PAIRS)
def test_letters_with_no_tie_bar_read_as_the_tied_segment(untied, tied):
    assert vectorize_phones(untied) == vectorize_phones(tied)


def test_ts_in_running_text_is_two_segments():
    assert segments("ts") == ["t", "s"]
    assert segments("tʃ") == ["t", "ʃ"]
    assert segments("t͡s") == ["t͡s"]


def _with(vec, **values):
    out = list(vec)
    for name, value in values.items():
        out[FEATURES.index(name)] = value
    return tuple(out)


# The IPA chart: ◌ʰ aspirated is [+spread glottis]; ◌ⁿ nasal release and prenasalization add [+nasal].
@pytest.mark.parametrize("marked, base, change", [
    ("ʰts", "t͡s", {"sg": True}),
    ("ʰt̠ʃ", "t̠͡ʃ", {"sg": True}),
    ("ʰtːs", "tː͡s", {"sg": True}),
    ("ᵐɡb", "ɡ͡b", {"nas": True}),
    ("ᵑᵐɡb", "ɡ͡b", {"nas": True}),
    ("ⁿkp", "k͡p", {"nas": True}),
])
def test_a_mark_before_untied_letters_applies_to_the_tied_segment(marked, base, change):
    assert vectorize_phones(marked) == _with(vectorize_phones(base), **change)


# compose_tie has no reading for most of these, so the whole segment has none. A doubled letter is
# a geminate, not a tie of a letter with itself.
@pytest.mark.parametrize("segment", ["ʤ͡v", "ʧ͡f", "t͡ʃ͡f", "d͡ʒ͡v", "ab", "ɑi", "ãb", "dʒ˩", "bvf", "dzs",
                                    "nn", "tt", "kk", "ŋnn"])
def test_ties_compose_tie_refuses_stay_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


@pytest.mark.parametrize("letter", ["n", "t", "k", "m"])
def test_a_doubled_letter_does_not_read_as_the_single_letter(letter):
    with pytest.raises(ValueError):
        vectorize_phones(letter + letter)


def test_a_click_reads_with_a_tie_bar():
    vectorize_phones("k͡ǀ")


def test_a_glottal_stop_before_a_stop_ties_as_two_stops():
    # ʔ is [-sonorant, -continuant] in the Hayes CSV, a stop, so ʔt takes the rule for two stops,
    # as kp does.
    assert vectorize_phones("ʔt") == vectorize_phones("ʔ͡t")
