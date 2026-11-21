"""Tone: the IPA chart's tone letters and tone diacritics (International Phonetic Association,
The IPA Chart, footer "IPA Chart revised to 2015/2005", "Tones and word accents")."""
import pytest

from phonematcher import ipa_distance, segments
from phonematcher.distance import substitution_cost
from phonematcher.tone import is_tone, tone_distance, tone_levels


@pytest.mark.parametrize("mark, letters", [
    ("̋", "˥"), ("́", "˦"), ("̄", "˧"), ("̀", "˨"), ("̏", "˩"),
    ("̌", "˩˥"), ("̂", "˥˩"), ("᷄", "˧˥"), ("᷅", "˩˧"), ("᷈", "˧˦˨"),
])
def test_a_tone_diacritic_reads_as_the_tone_letters_the_chart_gives_beside_it(mark, letters):
    assert segments("ma" + mark) == segments("ma" + letters) == ["m", "a", letters]


def test_tone_letters_give_levels_five_high_to_one_low():
    assert tone_levels("˥") == (5,) and tone_levels("˩") == (1,) and tone_levels("˨˩˦") == (2, 1, 4)


def test_tone_numerals_read_as_tone_letters():
    assert segments("ma²¹⁴") == segments("ma˨˩˦")


def test_a_run_of_tone_letters_is_one_tone_after_its_syllable():
    assert segments("man˥˩ ta˧") == ["m", "a", "n", "˥˩", " ", "t", "a", "˧"]


def test_downstep_upstep_and_global_marks_carry_no_segment():
    assert segments("ꜜma˦ ꜛma˦↗↘") == ["m", "a", "˦", " ", "m", "a", "˦"]


def test_a_tone_is_not_a_phone():
    assert is_tone("˥˩") and not is_tone("a") and not is_tone(" ")
    assert substitution_cost("˥", "a") == 1.0


def test_extreme_levels_are_furthest_and_equal_tones_coincide():
    assert tone_distance("˥", "˩") == 1.0
    assert tone_distance("˥˩", "˥˩") == 0.0


def test_tone_distance_follows_the_shape_of_the_contour():
    """A high rise is nearer a rise than a fall is; a near level is nearer than a far one."""
    assert tone_distance("˧˥", "˩˥") < tone_distance("˥˩", "˩˥")
    assert tone_distance("˦", "˥") < tone_distance("˨", "˥")


def test_a_tone_substitution_costs_one_quarter_per_level_step():
    assert ipa_distance("ma˥", "ma˦") == pytest.approx(0.25)
    assert ipa_distance("ma˥", "ma˩") == pytest.approx(1.0)
    assert ipa_distance("ma˥", "ma") == 1.0


def test_tone_letters_are_not_listed_as_phones():
    from phonematcher.features import phone_features
    assert not [s for s in phone_features if any(c in s for c in "˥˦˧˨˩")]


def test_search_finds_a_syllable_with_another_tone_and_ranks_the_same_tone_first():
    from phonematcher import PhoneticFuzzySearch
    search = PhoneticFuzzySearch()
    search.add_term("ma˥", "high")
    search.add_term("ma˨˩˦", "dipping")
    found = search.search("ma˥")
    assert [m.id for m in found] == ["high", "dipping"] and found[0].score == 0.0


def test_a_peaking_tone_differs_from_the_level_it_starts_and_ends_on():
    """The middle of the syllable counts, so ˨˦˨ is not ˨."""
    assert tone_distance("˨˦˨", "˨") > 0


def test_a_tone_diacritic_and_the_tone_letters_after_it_are_one_tone():
    assert segments("má˥") == ["m", "a", "˦˥"]


def test_left_stem_tone_letters_read_as_their_levels():
    assert segments("ma꜒꜖") == segments("ma˥˩")


def test_the_neutral_tone_numeral_carries_no_segment():
    assert segments("ma⁰") == ["m", "a"]
