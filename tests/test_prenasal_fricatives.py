"""A superscript nasal letter before an obstruent prenasalizes it.

Ladefoged and Maddieson (1996), The Sounds of the World's Languages, pp. 118 to 119: the partially
nasal consonants are "prenasalized stops (including affricates), prenasalized fricatives,
prestopped nasals, and, perhaps, prenasalized trills"; prenasalized stops "are often notated by a
superscript nasal symbol preceding the stop symbol, i.e. as ᵐb, ⁿd, ᵑg"; and "We do not know of any
cases of prenasalized lateral or central approximants". The Unicode code chart U1D80 gives ᶬ ᶮ ᶯ ᶰ
as "≈ <super>" of the nasal letters ɱ ɲ ɳ ɴ.
"""
import pytest

from phonematcher.features import vectorize_phones
from tests.conftest import differs, feature


# By hand: prenasalization adds nasal airflow before the oral part and leaves the oral part as it
# is, so each segment differs from its base in [nasal] alone, and [nasal] is +.
@pytest.mark.parametrize("prenasal, base", [
    ("ⁿs", "s"), ("ⁿz", "z"), ("ⁿʃ", "ʃ"), ("ⁿʒ", "ʒ"), ("ⁿf", "f"), ("ⁿθ", "θ"), ("ⁿh", "h"),
    ("ᵐv", "v"), ("ᶬv", "v"), ("ᶬf", "f"), ("ᶮʃ", "ʃ"),
    ("ᶮɟ", "ɟ"), ("ᶮc", "c"), ("ᶯɖ", "ɖ"), ("ᶰɢ", "ɢ"), ("ᶮd͡ʒ", "d͡ʒ"),
])
def test_a_superscript_nasal_adds_only_nasal(prenasal, base):
    assert differs(prenasal, base) == {"nas"}
    assert feature(prenasal, "nas") is True


# By hand: the superscript nasal is the nasal letter written small, so the segment is the nasal
# letter tied before the obstruent, which compose_tie reads as prenasalized.
@pytest.mark.parametrize("prenasal, tied", [
    ("ⁿs", "n͡s"), ("ⁿz", "n͡z"), ("ᶬv", "ɱ͡v"), ("ᶬf", "ɱ͡f"), ("ᶮɟ", "ɲ͡ɟ"), ("ᶮc", "ɲ͡c"),
])
def test_a_superscript_nasal_reads_as_the_tied_nasal(prenasal, tied):
    assert vectorize_phones(prenasal) == vectorize_phones(tied)


# "We do not know of any cases of prenasalized lateral or central approximants."
@pytest.mark.parametrize("segment", ["ⁿl", "ⁿj", "ⁿw", "ᶮj", "ᶬʋ"])
def test_a_superscript_nasal_before_an_approximant_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)
