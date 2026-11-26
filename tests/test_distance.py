"""Segmentation of IPA strings and the feature-weighted edit distance."""
import math

import pytest

from phonematcher.distance import edit_distance, ipa_distance, segments, substitution_cost
from phonematcher.features import feature_distance


def test_segments_keep_diacritics_and_ties_with_their_base():
    assert segments("ˈt͡ʃɐ̃w̃") == ["t͡ʃ", "ɐ̃", "w̃"]
    assert segments("s̺aː") == ["s̺", "aː"]


def test_segments_drop_stress_and_syllable_marks():
    assert segments("ˈka.zɐ") == ["k", "a", "z", "ɐ"]


def test_untied_letters_are_two_segments():
    assert segments("tʃ") == ["t", "ʃ"]


def test_words_are_separated_by_one_space_segment():
    assert segments("  a   bɐ ") == ["a", " ", "b", "ɐ"]


def test_identical_strings_are_at_zero():
    assert ipa_distance("ˈpojʃ", "ˈpojʃ") == 0.0


def test_a_substitution_costs_the_square_root_of_the_feature_distance():
    # s and ʃ are 0.0394737 apart (3/76); the square root is 0.198680.
    assert ipa_distance("pojs", "pojʃ") == pytest.approx(0.198680, abs=1e-6)
    assert ipa_distance("pojs", "pojʃ") == pytest.approx(math.sqrt(feature_distance("s", "ʃ")))


def test_insertion_and_deletion_cost_one_half():
    assert edit_distance(["a"], ["a", "b"]) == 0.5
    assert edit_distance(["a", "b"], ["b"]) == 0.5


def test_a_near_sound_is_nearer_than_a_far_one():
    assert ipa_distance("ˈʁatu", "ˈχatu") < ipa_distance("ˈʁatu", "ˈkatu")


def test_distance_is_symmetric():
    assert ipa_distance("ˈfɔɡɐ̃w̃", "fuˈɡɐ̃w̃") == ipa_distance("fuˈɡɐ̃w̃", "ˈfɔɡɐ̃w̃")


def test_a_prenasalization_or_preaspiration_mark_joins_the_following_stop():
    assert segments("ⁿdaʰta") == ["ⁿd", "a", "ʰt", "a"]


def test_a_mark_after_a_final_vowel_stays_in_its_word():
    assert segments("maʰ m") == ["m", "aʰ", " ", "m"]
    assert segments("maʰ") == ["m", "aʰ"]


def test_the_cached_substitution_cost_gives_the_uncached_values():
    from phonematcher.clustering import phone_clusters

    segs = [*sorted(phone_clusters(0.1)), "˥", "˩˥", "˧˧", "k̃", " "]
    for a in segs:
        for b in segs:
            assert repr(substitution_cost(a, b)) == repr(substitution_cost.__wrapped__(a, b)), (a, b)
    # a tone against a phone costs a deletion plus an insertion
    assert substitution_cost("˥", "a") == substitution_cost("a", "˥") == 1.0
