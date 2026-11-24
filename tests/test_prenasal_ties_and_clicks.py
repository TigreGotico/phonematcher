"""A prenasal mark before an affricate, and a click with its accompaniment and no tie bar.

IPA chart (``IPA_Kiel.pdf``, footer "IPA Chart revised to 2015/2005"), note under "Other symbols":
"Affricates and double articulations can be represented by two symbols joined by a tie bar if
necessary." A prenasalized stop reads as the nasal tied to the stop (``ⁿd`` is ``n͡d``, see
``test_features.py``), so ``ⁿd͡z`` is the nasal tied to ``d͡z``.

Handbook of the International Phonetic Association (Cambridge, 1999), section 2.5, p. 10: "Since
any click involves a velar or uvular closure, it is possible to symbolize factors such as
voicelessness, voicing, or nasality of the click by combining the click symbol with the appropriate
velar or uvular symbol", written there with a tie bar over the two symbols.

Each expected vector is the vector of the tied form, read by another path: a nasal, a stop and a
fricative joined by ``compose_tie``, or a stop and a click joined by a tie bar.
"""
import pytest

from phonematcher.features import FEATURES, vectorize_phones

PRENASAL = [
    ("ⁿdz", "n͡d͡z"), ("ⁿdzʷ", "n͡d͡zʷ"), ("ⁿdʐ", "n͡d͡ʐ"), ("ⁿdʑ", "n͡d͡ʑ"), ("ⁿdʒ", "n͡d͡ʒ"),
    ("ⁿtʃ", "n͡t͡ʃ"), ("ⁿd͡z", "n͡d͡z"), ("ⁿd͡ʒ", "n͡d͡ʒ"), ("ⁿt͡ʃʰ", "n͡t͡ʃʰ"), ("ᵐdz", "m͡d͡z"),
    ("ᵑd͡ʒ", "ŋ͡d͡ʒ"),
]


@pytest.mark.parametrize("marked, tied", PRENASAL)
def test_a_prenasal_mark_reads_an_affricate_as_a_nasal_tied_before_it(marked, tied):
    assert vectorize_phones(marked) == vectorize_phones(tied)


def test_a_prenasal_affricate_is_the_affricate_with_nasal_plus():
    # By hand: d͡z is [-continuant, +delayed release]. ⁿ adds [+nasal] and changes nothing else.
    plain = list(vectorize_phones("d͡z"))
    plain[FEATURES.index("nas")] = True
    assert vectorize_phones("ⁿd͡z") == tuple(plain)
    assert vectorize_phones("ⁿd͡z")[FEATURES.index("delrel")] is True


def test_a_prenasal_mark_still_refuses_a_base_that_is_not_a_stop():
    # ⁿ before a fricative or a vowel has no reading; it stays refused.
    for segment in ("ⁿs", "ⁿa", "ⁿʃ"):
        with pytest.raises(ValueError):
            vectorize_phones(segment)


# Every click in the orthography2ipa inventories that has no tie bar and a velar or uvular letter
# before it.
CLICKS = ["kǀ", "kǁ", "kǃ", "ŋǀ", "ŋǁ", "ŋǃ", "ɡǀ", "ɡǁ", "ɡǂ", "ɡǃ", "ɡʘ", "ɢǀ", "ɢǁ", "ɢǂ", "ɢǃ", "ɢʘ",
          "qǃ"]


@pytest.mark.parametrize("untied", CLICKS)
def test_a_click_after_its_velar_or_uvular_letter_reads_as_the_tied_click(untied):
    tied = untied[0] + "͡" + untied[1:]
    assert vectorize_phones(untied) == vectorize_phones(tied)


@pytest.mark.parametrize("segment", ["tǀ", "pǃ", "ʔǃ", "ǀǃ", "ǃǀ", "mǀ", "kǀǃ"])
def test_a_click_after_another_letter_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


def _value(segment, name):
    return vectorize_phones(segment)[FEATURES.index(name)]


@pytest.mark.parametrize("segment, voiced, nasal", [
    ("k͡ǃ", False, False), ("ɡ͡ǃ", True, False), ("ŋ͡ǃ", True, True),
    ("ɡǃ", True, False), ("ŋǃ", True, True), ("ɢ͡ǂ", True, False), ("ɴ͡ǁ", True, True), ("q͡ǀ", False, False),
])
def test_a_click_takes_its_voicing_and_nasality_from_its_velar_or_uvular_letter(segment, voiced, nasal):
    # The Handbook quote above: the velar or uvular symbol states the voicing and nasality of the
    # click. k q are voiceless oral, ɡ ɢ voiced oral, ŋ ɴ voiced nasal (IPA chart, pulmonic table).
    assert _value(segment, "voi") is voiced
    assert _value(segment, "nas") is nasal


def test_a_voiced_click_differs_from_the_voiceless_one_by_the_full_voicing_weight():
    # By hand: ɡ͡ǃ and k͡ǃ differ only in [voice], + against -, weight 0.125 of a total 9.5.
    a, b = vectorize_phones("ɡ͡ǃ"), vectorize_phones("k͡ǃ")
    assert [name for name, x, y in zip(FEATURES, a, b) if x != y] == ["voi"]


@pytest.mark.parametrize("segment", ["k͡ǃ", "ɡ͡ǃ", "ŋ͡ǃ", "ɢ͡ǂ", "ɴ͡ǁ", "ŋǃ"])
def test_a_click_tie_stays_a_click_with_the_place_of_the_click_letter(segment):
    # The click letter gives the airstream and the place; the velar or uvular letter states only
    # voicing and nasality (Handbook quote above).
    click = vectorize_phones(next(c for c in segment if c in "ʘǀǃǂǁ"))
    assert _value(segment, "velaric") is True
    for name in ("ant", "cor", "distr", "lab", "hi", "back"):
        assert _value(segment, name) is click[FEATURES.index(name)]
