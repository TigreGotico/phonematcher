"""A tie bar with nothing before it does not read, and raises ValueError like any unread segment."""
import pytest

from phonematcher import ipa_distance, vectorize_phones


@pytest.mark.parametrize("segment", ["͡ǃ", "͜ǃ", "͡ǀ", "͡k", "ǃ͡"])
def test_a_tie_bar_at_an_end_raises_value_error(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


@pytest.mark.xfail(strict=True, reason="#208")
def test_a_leading_tie_bar_in_a_word_raises_when_strict():
    with pytest.raises(ValueError):
        ipa_distance("͡ǃa", "ǃa", strict=True)
