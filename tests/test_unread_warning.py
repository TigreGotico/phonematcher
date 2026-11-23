"""Without strict, an unread segment raises one UserWarning per process, naming it."""
import warnings

import pytest

from phonematcher import features, ipa_distance, substitution_cost


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    # each test starts as a new process would: no segment has warned, no cost is cached
    monkeypatch.setattr(features, "_WARNED", set(), raising=False)
    features.feature_distance.cache_clear()
    substitution_cost.cache_clear()


def test_the_first_call_warns_with_the_segment_its_code_points_and_strict():
    # ʅ is U+0285, a letter the table does not read
    with pytest.warns(UserWarning) as caught:
        assert ipa_distance("ʅ", "a") == 1.0
    assert len(caught) == 1
    message = str(caught[0].message)
    assert "'ʅ'" in message and "U+0285" in message and "strict=True" in message


def test_a_second_call_with_the_same_segment_does_not_warn():
    with pytest.warns(UserWarning):
        ipa_distance("ʅ", "a")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert ipa_distance("ʅ", "o") == 1.0
        assert ipa_distance("maʅ", "pak") > 0


def test_two_unread_segments_warn_once_each():
    with pytest.warns(UserWarning) as caught:
        ipa_distance("ʅ", "k̃")
    assert sorted("U+0285" in str(w.message) for w in caught) == [False, True]


def test_strict_still_raises_and_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValueError, match="'ʅ'"):
            ipa_distance("ma", "maʅ", strict=True)


def test_readable_input_never_warns():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ipa_distance("ˈt͡ʃɐ̃w̃ ma˥", "ˈpojʃ ta˩˥")


def test_the_standard_filter_silences_it():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warnings.filterwarnings("ignore", message="Unrecognized phone", category=UserWarning)
        assert ipa_distance("ʅ", "a") == 1.0


def test_a_mark_that_does_not_apply_names_the_segment_and_strict():
    # ʰ before a vowel has no rule: ʰə is U+02B0 U+0259
    with pytest.warns(UserWarning) as caught:
        ipa_distance("ʰə", "a")
    message = str(caught[0].message)
    assert message.startswith("Unrecognized phone 'ʰə' (U+02B0 U+0259)") and "strict=True" in message
