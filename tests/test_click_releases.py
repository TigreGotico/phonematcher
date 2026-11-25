"""A click tied to a uvular fricative or an ejective uvular reads as the click with that release.

Miller, Brugman, Sands, Namaseb, Exter and Collins (2009, JIPA 39(2)):
pp. 149 and 152: "In figure 9c the pulmonic egressive release is fricated, so that the segment is a manner
contour (affricate), as well as an airstream contour."
p. 152: "The fricated release in figure 9c is characterized by a distinct 'scraping' sound, as would
be expected of a uvular or uvulo-pharyngeal fricated release."
p. 152: "the ejected release of the linguo-glottalic click in figure 9d looks and sounds like an
ejected uvular fricative."
p. 132, Table 1 note b: "There is extensive variability in the degree of frication in uvular
glottalic affricates, which ranges from no audible frication to strong frication noise between
the stop burst and the glottalic release."

Each expected vector is the vector of the uvular-stop click ``q͡ǃ``, with the feature the release
adds set by hand: [+delayed release] for the fricated release, as in the affricate ``q͡χ``, and
[+constricted glottis] for the ejective release, as in ``qʼ``.
"""
import pytest

from phonematcher.features import FEATURES, vectorize_phones

CLICK_LETTERS = "ʘǀǃǂǁ"


def _with(segment, **features):
    vec = list(vectorize_phones(segment))
    for name, value in features.items():
        vec[FEATURES.index(name)] = value
    return tuple(vec)


@pytest.mark.parametrize("click", CLICK_LETTERS)
@pytest.mark.parametrize("order", ["{click}͡χ", "χ͡{click}", "{click}͜χ"])
def test_a_click_tied_to_chi_is_the_uvular_click_with_a_delayed_release(click, order):
    assert vectorize_phones(order.format(click=click)) == _with(f"q͡{click}", delrel=True, strid=True)


@pytest.mark.parametrize("click", CLICK_LETTERS)
@pytest.mark.parametrize("segment", ["{click}͡qʼ", "{click}͡χʼ", "χʼ͡{click}"])
def test_a_click_tied_to_an_ejective_uvular_is_the_uvular_click_with_constricted_glottis(click, segment):
    # A1 calls the frication of the ejected release variable, so qʼ and χʼ read the same.
    assert vectorize_phones(segment.format(click=click)) == _with(f"q͡{click}", cg=True)


def test_the_fricated_release_and_the_ejected_release_differ_from_the_plain_click():
    plain = vectorize_phones("q͡ǃ")
    assert vectorize_phones("ǃ͡χ") != plain
    assert vectorize_phones("ǃ͡qʼ") != plain
    assert vectorize_phones("ǃ͡χ") != vectorize_phones("ǃ͡qʼ")


@pytest.mark.parametrize("segment", ["ǃ͡ɢʱ", "ᵏʼǃ", "ǃχ", "χǃ", "ǃ͡x", "ǃ͡χʰ", "ǃʰ͡χ", "k͡ǃ͡χ", "ǃ͡q͡χ"])
def test_the_other_click_accompaniments_stay_unread(segment):
    with pytest.raises(ValueError):
        vectorize_phones(segment)


def test_an_ejective_uvular_stop_then_click_reads_as_the_click_then_stop():
    assert vectorize_phones("qʼ͡ǃ") == vectorize_phones("ǃ͡qʼ")
