"""The tilde on a continuant consonant is nasalization.

Ladefoged and Maddieson (1996), The Sounds of the World's Languages, pp. 132 to 133: "The second
major type of nasalized consonants are oral continuants (fricatives and approximants) produced
with a lowered velum so that air is also free to pass out through the nasal passage", and
"nasalized voiceless approximants do occur contrastively in some Southern Bantu languages. Both
Kwangali and ThiMbukushu [...] have clear contrasts between h and h̃".
"""
import pytest

from phonematcher.features import vectorize_phones
from tests.conftest import differs, feature


# By hand: a lowered velum adds nasal airflow and moves no oral articulator, so each segment
# differs from its base in [nasal] alone, and [nasal] is +.
@pytest.mark.parametrize("nasalized, plain", [
    ("h̃", "h"), ("f̃", "f"), ("s̃", "s"), ("x̃", "x"), ("ħ̃", "ħ"), ("χ̃", "χ"), ("θ̃", "θ"), ("ɬ̃", "ɬ"),
])
def test_tilde_on_a_voiceless_continuant_adds_only_nasal(nasalized, plain):
    assert differs(nasalized, plain) == {"nas"}
    assert feature(nasalized, "nas") is True


# The source names continuants only. A voiceless stop takes no nasal airflow during its closure.
@pytest.mark.parametrize("segment", ["k̃", "p̃", "t̃", "ʔ̃"])
def test_tilde_on_a_voiceless_stop_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


# The source names fricatives and approximants. It names no trill, and PanPhon marks trills [+cont].
@pytest.mark.parametrize("segment", ["r̥̃", "ʀ̥̃", "ʙ̥̃"])
def test_tilde_on_a_voiceless_trill_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)
