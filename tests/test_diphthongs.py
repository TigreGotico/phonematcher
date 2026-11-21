"""A diphthong costs as two segments, as in Nerbonne and Heeringa (1997)."""
import pytest

from phonematcher import ipa_distance, segments, vectorize_phones
from phonematcher.distance import align
from phonematcher.features import phonetic_distance


@pytest.mark.parametrize("ipa, expected", [
    ("a͡i", ["a", "i"]),
    ("a͜u", ["a", "u"]),
    ("ei̯", ["e", "i̯"]),
    ("a͡i̯", ["a", "i̯"]),
    ("t͡ʃa͡i", ["t͡ʃ", "a", "i"]),
    ("t͡ʃ", ["t͡ʃ"]),
])
def test_segments_of_a_diphthong(ipa, expected):
    assert segments(ipa) == expected


def test_tied_and_untied_diphthong_are_equal():
    assert ipa_distance("a͡i", "ai") == 0


def test_diphthong_costs_one_indel_against_its_first_vowel():
    # a͡i is [a, i]; against [a] the alignment is a match and one deletion of i, which costs 1.
    assert ipa_distance("a͡i", "a") == 1.0
    assert align(segments("a͡i"), segments("a")) == [("a", "a"), ("i", None)]


def test_diphthong_glide_substitution_is_gradual():
    # a͡i against aj: a matches a, then i is replaced by j.
    assert 0 < ipa_distance("a͡i", "aj") == phonetic_distance("i", "j") < 1


@pytest.mark.parametrize("diphthong", ["a͡i", "ai", "ei̯"])
def test_whole_diphthong_has_no_vector(diphthong):
    with pytest.raises(ValueError, match="a diphthong is two segments"):
        vectorize_phones(diphthong)


def test_other_unreadable_phone_does_not_mention_diphthong():
    with pytest.raises(ValueError) as err:
        vectorize_phones("l͡j")
    assert "diphthong" not in str(err.value)
