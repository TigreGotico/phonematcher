"""A modifier letter on the rear letter of a click tie reads in both orders or in neither."""
import pytest

from phonematcher.features import vectorize_phones


@pytest.mark.xfail(strict=True, reason="#219")
@pytest.mark.parametrize("modifier", ["ʷ", "ʰ"])
def test_a_rear_letter_with_a_modifier_then_click_reads_as_the_click_then_rear_letter(modifier):
    assert vectorize_phones(f"q{modifier}͡ǃ") == vectorize_phones(f"ǃ͡q{modifier}")
