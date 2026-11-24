"""A small ᶢ before a click is the click's voiced velar closure.

Ladefoged and Maddieson (1996), The Sounds of the World's Languages, p. 264: "Every click involves
a back closure, but since it may be either velar or uvular in place this aspect of a click must be
written separately. This is done by writing a symbol for a velar or uvular consonant before the
symbol for the click type. [...] Other features of the click, such as presence or absence of
voicing, as well as presence or absence of nasal air flow are indicated by choosing between, k, g,
ŋ [...]". The Unicode code chart U1D80 gives ᶢ as "≈ <super> 0261 ɡ".
"""
import pytest

from phonematcher.features import vectorize_phones
from tests.conftest import differs, feature

CLICKS = ["ǀ", "ǁ", "ǂ", "ǃ", "ʘ"]


@pytest.mark.parametrize("click", CLICKS)
def test_script_g_before_a_click_is_the_voiced_velar_click(click):
    assert vectorize_phones("ᶢ" + click) == vectorize_phones("ɡ͡" + click)


# By hand: g is voiced and oral, k voiceless and oral. So ᶢǃ differs from the k-click in [voice]
# alone, it is a click (velaric +), and it is not nasal.
@pytest.mark.parametrize("click", CLICKS)
def test_script_g_click_differs_from_the_k_click_in_voice_alone(click):
    assert differs("ᶢ" + click, "k͡" + click) == {"voi"}
    assert feature("ᶢ" + click, "voi") is True
    assert feature("ᶢ" + click, "velaric") is True
    assert feature("ᶢ" + click, "nas") is False


# The source states the letter before the click only. ᶢ elsewhere stays unread.
@pytest.mark.parametrize("segment", ["ᶢ", "ŋᶢ", "ᶢa", "ᶢt"])
def test_script_g_away_from_a_click_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)
