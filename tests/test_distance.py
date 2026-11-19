"""Segmentation of IPA strings and the feature-weighted edit distance."""
import pytest

from phonematcher.distance import edit_distance, ipa_distance, segments
from phonematcher.features import phonetic_distance


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


def test_a_substitution_costs_the_feature_distance():
    assert ipa_distance("pojs", "pojʃ") == pytest.approx(phonetic_distance("s", "ʃ"))


def test_insertion_and_deletion_cost_one():
    assert edit_distance(["a"], ["a", "b"]) == 1.0
    assert edit_distance(["a", "b"], ["b"]) == 1.0


def test_a_near_sound_is_nearer_than_a_far_one():
    assert ipa_distance("ˈʁatu", "ˈχatu") < ipa_distance("ˈʁatu", "ˈkatu")


def test_distance_is_symmetric():
    assert ipa_distance("ˈfɔɡɐ̃w̃", "fuˈɡɐ̃w̃") == ipa_distance("fuˈɡɐ̃w̃", "ˈfɔɡɐ̃w̃")
