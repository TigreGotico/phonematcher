"""Tone as four features of the segment that carries it: tone_is, tone_start, tone_mid and tone_end,
each pitch the Chao level as (level - 3) / 2, as in the tone block of phoonnx
(phoonnx_train/features_json.py)."""
import itertools
import math

import pytest

from phonematcher import FEATURES, WEIGHTS, feature_distance, ipa_distance, segment_spans, segments, tone_levels, vectorize_phones
from phonematcher.distance import carry_tones, substitution_cost
from phonematcher.features import phone_and_tone

#: The tone weights the build sets: tone_is, then the three pitches.
W_IS, W_PITCH = 0.25, 0.125
SEGMENT_WEIGHT = 9.5


def phoonnx_tone_block(symbol):
    """phoonnx_train/features_json.py ``tone_block`` at TigreGotico/phoonnx dev, copied."""
    levels = tone_levels(symbol)
    if len(levels) == 1:
        contour = levels * 3
    else:
        contour = []
        for k in range(3):
            x = k * (len(levels) - 1) / 2
            i = min(int(x), len(levels) - 2)
            contour.append(levels[i] + (levels[i + 1] - levels[i]) * (x - i))
    points = [(level - 3) / 2 for level in contour]
    return [1] + [int(p) if p.is_integer() else p for p in points]


def test_the_four_tone_features_end_every_vector():
    assert FEATURES[-4:] == ("tone_is", "tone_start", "tone_mid", "tone_end")
    assert WEIGHTS[-4:] == (W_IS, W_PITCH, W_PITCH, W_PITCH)
    assert len(vectorize_phones("p")) == len(FEATURES) == 40
    assert vectorize_phones("p")[-4:] == (None, None, None, None)


@pytest.mark.parametrize("letters", ["".join(t) for n in (1, 2, 3) for t in itertools.product("˩˨˧˦˥", repeat=n)])
def test_the_tone_features_are_the_tone_block_of_phoonnx(letters):
    assert list(vectorize_phones("a" + letters)[-4:]) == phoonnx_tone_block(letters)


@pytest.mark.parametrize("tone, expected", [
    # one level: the same pitch three times; ˥ is level 5, (5 - 3) / 2 = 1
    ("˥", (True, 1.0, 1.0, 1.0)),
    # two levels 3 and 5: the middle is level 4, so 0, 0.5, 1
    ("˧˥", (True, 0.0, 0.5, 1.0)),
    # three levels 2, 1, 4: the middle point is the middle level, 1
    ("˨˩˦", (True, -0.5, -1.0, 0.5)),
])
def test_hand_worked_tone_features(tone, expected):
    assert vectorize_phones("a" + tone)[-4:] == expected


def test_the_segment_features_of_a_toned_vowel_are_those_of_the_vowel():
    assert vectorize_phones("a˥˩")[:-4] == vectorize_phones("a")[:-4]
    assert vectorize_phones("â") == vectorize_phones("a˥˩") == vectorize_phones("a⁵¹")


@pytest.mark.parametrize("segment", ["m˥", "p˩", "˥", "j˧"])
def test_a_tone_on_a_segment_that_is_not_syllabic_does_not_read(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


@pytest.mark.parametrize("ipa, expected", [
    ("ma˥", ["m", "a˥"]),
    ("má", ["m", "a˦"]),
    ("tam˧˧", ["t", "a˧˧", "m"]),
    ("pz̩˥", ["p", "z̩˥"]),
    ("ma˥ta˩", ["m", "a˥", "t", "a˩"]),
    ("ma˥ ˩", ["m", "a˥", " ", "˩"]),
    ("˥˩", ["˥˩"]),
    ("ɡ˩a", ["ɡ", "˩", "a"]),
    ("ma˥˩˧", ["m", "a˥˩˧"]),
])
def test_a_tone_goes_to_the_last_vowel_or_syllabic_consonant_before_it_in_its_word(ipa, expected):
    assert segments(ipa) == expected


def test_a_tone_after_a_coda_is_a_gap_and_each_segment_keeps_its_span():
    # t0 a1 m2 ˧3 ˧4: three segments t, a˧˧, m; the tone letters after the coda are a gap
    assert segments("tam˧˧") == ["t", "a˧˧", "m"]
    assert segment_spans("tam˧˧") == [(0, 1), (1, 2), (2, 3)]


def test_a_tone_right_after_its_vowel_is_in_the_span_of_the_vowel():
    # m0 a1 ˥2: the span of a˥ holds the tone letter
    assert segment_spans("ma˥") == [(0, 1), (1, 3)]


def test_a_tone_on_a_tied_diphthong_goes_to_its_nucleus():
    assert segments("a͡i˥") == segments("ai̯˥") == ["a˥", "i̯"]


def test_carry_tones_reads_a_token_list_as_segments_reads_a_string():
    assert carry_tones(["t", "a", "m", "˧˧"]) == segments("tam˧˧")
    assert carry_tones(["˥˩"]) == ["˥˩"]


def test_phone_and_tone():
    assert phone_and_tone("a˥˩") == ("a", "˥˩") == phone_and_tone("â")
    assert phone_and_tone("a") == ("a", "")


def test_hand_worked_distances_of_toned_vowels():
    # ˥ against ˦: each pitch differs by 0.5, at half its weight: 3 * 0.25 * W_PITCH
    assert feature_distance("a˥", "a˦") == pytest.approx(3 * 0.25 * W_PITCH / SEGMENT_WEIGHT)
    # ˥ against ˩: each pitch differs by 2: 3 * 1 * W_PITCH
    assert feature_distance("a˥", "a˩") == pytest.approx(3 * W_PITCH / SEGMENT_WEIGHT)
    # ˥ against no tone: tone_is True against None, and each pitch 1 against 0
    assert feature_distance("a˥", "a") == pytest.approx((W_IS / 2 + 3 * 0.5 * W_PITCH) / SEGMENT_WEIGHT)
    # ˧ against no tone: tone_is only, the pitches are all 0
    assert feature_distance("a˧", "a") == pytest.approx(W_IS / 2 / SEGMENT_WEIGHT)
    assert ipa_distance("ma˥", "ma˩") == pytest.approx(math.sqrt(3 * W_PITCH / SEGMENT_WEIGHT))


def test_a_tone_adds_to_the_distance_of_two_segments():
    # i against e is 0.5 / 9.5 (hi, h1, h2); a tone on one adds its own share
    assert feature_distance("i˥", "e") == pytest.approx(feature_distance("i", "e") + feature_distance("a˥", "a"))


def test_a_tone_segment_of_its_own_is_compared_by_the_tone_distance():
    assert substitution_cost("˥", "˦") == pytest.approx(0.5)
    assert substitution_cost("˥", "a˥") == 1.0

