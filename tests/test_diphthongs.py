"""A diphthong costs as two segments, as in Nerbonne and Heeringa (1997). The second vowel of a
tied pair is its offglide: the IPA chart writes it with ◌̯, "Non-syllabic"."""
import pytest

from phonematcher import ipa_distance, segments, vectorize_phones
from phonematcher.distance import align


@pytest.mark.parametrize("ipa, expected", [
    ("a͡i", ["a", "i̯"]),
    ("a͜u", ["a", "u̯"]),
    ("ei̯", ["e", "i̯"]),
    ("a͡i̯", ["a", "i̯"]),
    ("a͡iː", ["a", "i̯ː"]),
    ("t͡ʃa͡i", ["t͡ʃ", "a", "i̯"]),
    ("t͡ʃ", ["t͡ʃ"]),
    ("ai", ["a", "i"]),
])
def test_segments_of_a_diphthong(ipa, expected):
    assert segments(ipa) == expected


def test_tied_diphthong_reads_as_the_non_syllabic_form():
    assert segments("a͡i") == segments("ai̯")
    assert ipa_distance("a͡i", "ai̯") == 0


def test_offglide_is_not_syllabic():
    assert vectorize_phones(segments("a͡i")[1])[0] is False


def test_diphthong_differs_from_hiatus():
    # a.i is [a, i]. i̯ and i differ only in syl, + against −, at weight 1 of 9.5:
    # sqrt(1 / 9.5) = 0.324443.
    assert ipa_distance("a͡i", "a.i") == pytest.approx(0.324443, abs=1e-6)
    assert ipa_distance("a͡i", "ai") == pytest.approx(0.324443, abs=1e-6)


def test_diphthong_is_near_vowel_and_glide():
    # i̯ against j: ant is 0 against −, and h1 to h6 are − against 0, each at half its weight:
    # (0.25 + 6 * 0.125) / 2 / 9.5 = 0.052632, and sqrt(0.052632) = 0.229416.
    assert ipa_distance("ai̯", "aj") == pytest.approx(0.229416, abs=1e-6)
    assert ipa_distance("a͡i", "aj") < ipa_distance("a͡i", "a.i")


def test_diphthong_costs_one_indel_against_its_first_vowel():
    # a͡i is [a, i̯]; against [a] the alignment is a match and one deletion of i̯, which costs 0.5.
    assert ipa_distance("a͡i", "a") == 0.5
    assert align(segments("a͡i"), segments("a")) == [("a", "a"), ("i̯", None)]


@pytest.mark.parametrize("diphthong", ["a͡i", "ai", "ei̯"])
def test_whole_diphthong_has_no_vector(diphthong):
    with pytest.raises(ValueError, match="a diphthong is two segments, a vowel and a non-syllabic vowel"):
        vectorize_phones(diphthong)


def test_other_unreadable_phone_does_not_mention_diphthong():
    with pytest.raises(ValueError) as err:
        vectorize_phones("l͡j")
    assert "diphthong" not in str(err.value)


# A glide already marked on the first vowel makes a rising diphthong: the second vowel stays syllabic.
def test_a_marked_first_glide_keeps_the_second_vowel_syllabic():
    assert segments("i̯͡a") == segments("i̯a") == ["i̯", "a"]


# Three tied vowels: the first is the nucleus, each later vowel an offglide.
def test_a_tied_triphthong_reads_one_nucleus():
    assert segments("a͡i͡u") == ["a", "i̯", "u̯"]
