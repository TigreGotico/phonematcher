"""A superscript nasal letter stays unread before a glottalic consonant.

Ladefoged and Maddieson (1996), The Sounds of the World's Languages, p. 119: "Pre- and
postnasalization do not seem to occur with glottalic consonants. We know of no cases of
prenasalized implosives. Prenasalized ejectives are at best marginal." The book judges the Zulu
strings of nasal and ejective not to be unitary prenasalized ejectives.
"""
import pytest

from phonematcher.features import vectorize_phones


@pytest.mark.parametrize("segment", [
    "ⁿɓ", "ᵐɓ", "ⁿɗ", "ᶮʄ", "ᵑɠ", "ᶰʛ",
    "ⁿtʼ", "ᵑkʼ", "ᵐpʼ", "ⁿsʼ", "ⁿtsʼ", "ⁿt͡sʼ", "ⁿʔ",
])
def test_a_superscript_nasal_before_a_glottalic_consonant_stays_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


# Prenasalized plain stops and clicks are attested (pp. 118 to 119 and chapter 9) and keep reading.
@pytest.mark.parametrize("segment", ["ⁿd", "ᵐb", "ᵑɡ", "ⁿs", "ⁿǃ", "ᵑǀ"])
def test_a_superscript_nasal_before_a_plain_obstruent_still_reads(segment):
    assert vectorize_phones(segment)
