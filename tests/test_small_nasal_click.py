"""A small velar or uvular nasal before a click is the nasal click.

The IPA Handbook, section 2.5, p. 10: "Since any click involves a velar or uvular closure, it is
possible to symbolize factors such as voicelessness, voicing, or nasality of the click by combining
the click symbol with the appropriate velar or uvular symbol." The nasal letter is ŋ or ɴ, and the
Unicode chart gives ᵑ as the small ŋ and ᶰ as the small ɴ.
"""
import pytest

from phonematcher.features import vectorize_phones
from tests.conftest import differs, feature

CLICKS = ["ǀ", "ǁ", "ǂ", "ǃ", "ʘ"]


@pytest.mark.parametrize("click", CLICKS)
@pytest.mark.parametrize("small, letter", [("ᵑ", "ŋ"), ("ᶰ", "ɴ")])
def test_small_nasal_before_a_click_is_the_tied_nasal_click(small, letter, click):
    assert vectorize_phones(small + click) == vectorize_phones(letter + "͡" + click)


# By hand: ŋ is voiced and nasal, k voiceless and oral. So ᵑǃ differs from the k-click in
# [voice] and [nasal] alone, and it stays a click.
@pytest.mark.parametrize("click", CLICKS)
def test_small_nasal_click_differs_from_the_k_click_in_voice_and_nasal(click):
    assert differs("ᵑ" + click, "k͡" + click) == {"voi", "nas"}
    assert feature("ᵑ" + click, "voi") is True
    assert feature("ᵑ" + click, "nas") is True
    assert feature("ᵑ" + click, "velaric") is True


# The source names velar and uvular letters only: ⁿ before a click keeps its prenasal reading.
def test_small_alveolar_nasal_before_a_click_is_unchanged():
    assert feature("ⁿǃ", "voi") is False


def test_small_nasal_before_a_stop_is_unchanged():
    assert vectorize_phones("ᵑɡ") == vectorize_phones("ŋ͡ɡ")
