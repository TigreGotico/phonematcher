"""Strict input raises on an unread segment; the default behaviour is the one before the option."""
import hashlib
import random

import pytest

from phonematcher import PhoneticFuzzySearch, align, edit_distance, ipa_distance, segments, vectorize_phones
from phonematcher.features import phone_features

UNREAD = ["k̃", "ˁ", "ʳ", "ʅ", "aʰ"]
LETTERS = list("pbtdkgqʔmnɲŋfvszʃʒxχhrlɾjwaeiouɛɔəɪʊæɑɨʉ")
TONES = ["˥", "˩˥", "˧"]

#: SHA-256 over the results of the four entry points on 2,000 seeded strings that include unread
#: segments, taken before the option existed. A change of the feature table or the costs changes it.
NON_STRICT_DIGEST = "edf321e8d1031d35462d687fa529f6b1ca0c327485450b065fd2262e95df82e2"


def random_strings(count=2000):
    rng = random.Random(0)

    def word():
        parts = []
        for _ in range(rng.randint(1, 6)):
            r = rng.random()
            parts.append(rng.choice(UNREAD) if r < 0.15 else rng.choice(TONES) if r < 0.2 else rng.choice(LETTERS))
        return "".join(parts)

    return [f"{word()} {word()}" if rng.random() < 0.2 else word() for _ in range(count)]


def non_strict_digest():
    strs = random_strings()
    parts = {name: hashlib.sha256() for name in ("ipa_distance", "edit_distance", "align", "search")}
    for a, b in zip(strs[0::2], strs[1::2]):
        parts["ipa_distance"].update(repr((ipa_distance(a, b), ipa_distance(a, b, True))).encode())
        sa, sb = segments(a), segments(b)
        parts["edit_distance"].update(repr(edit_distance(sa, sb)).encode())
        parts["align"].update(repr(align(sa, sb)).encode())
    search = PhoneticFuzzySearch()
    for i, term in enumerate(strs[:1000]):
        search.add_term(term, i)
    for query in strs[1000:]:
        parts["search"].update(repr(search.search(query)).encode())
    return hashlib.sha256("".join(p.hexdigest() for p in parts.values()).encode()).hexdigest()


def test_the_unread_segments_are_unread():
    for seg in UNREAD:
        with pytest.raises(ValueError):
            vectorize_phones(seg)


def test_without_strict_the_four_entry_points_give_the_results_they_gave_before_the_option():
    assert any(u in s for s in random_strings() for u in UNREAD)
    assert non_strict_digest() == NON_STRICT_DIGEST


@pytest.mark.parametrize("seg", UNREAD)
def test_ipa_distance_strict_raises_and_names_the_segment_and_the_string(seg):
    with pytest.raises(ValueError) as error:
        ipa_distance("ma", f"ba{seg}", strict=True)
    assert repr(seg) in str(error.value) and repr(f"ba{seg}") in str(error.value)
    with pytest.raises(ValueError):
        ipa_distance(f"ma{seg}", "ba", normalized=True, strict=True)


@pytest.mark.parametrize("seg", UNREAD)
def test_edit_distance_and_align_strict_raise_and_name_the_segment(seg):
    for entry in (edit_distance, align):
        with pytest.raises(ValueError, match=repr(seg)):
            entry(["m", "a"], ["b", "a", seg], strict=True)
        with pytest.raises(ValueError, match=repr(seg)):
            entry([seg], ["b"], strict=True)


@pytest.mark.parametrize("seg", UNREAD)
def test_a_strict_search_raises_on_an_unread_term_and_query_and_indexes_nothing(seg):
    search = PhoneticFuzzySearch(strict=True)
    with pytest.raises(ValueError, match=repr(seg)):
        search.add_term(["ba", f"ma{seg}"], "x")
    assert not search.library and not search.index
    search.add_term("ba", "ok")
    with pytest.raises(ValueError, match=repr(seg)):
        search.search(f"ba{seg}")


def test_an_unread_segment_costs_as_much_as_a_missing_one():
    # Substituting an unread segment costs one deletion plus one insertion, 0.5 + 0.5, the price of
    # a segment that is missing on one side and extra on the other.
    assert ipa_distance("ʅ", "a") == ipa_distance("k̃", "a") == ipa_distance("ʅ", "k̃") == 0.5 + 0.5
    assert ipa_distance("ʅ", "") == ipa_distance("a", "") == 0.5


def test_strict_accepts_every_segment_of_the_table_and_gives_the_same_value():
    keys = sorted(phone_features)
    for i, key in enumerate(keys):
        other = keys[(i * 7 + 3) % len(keys)]
        assert ipa_distance(key, other, strict=True) == ipa_distance(key, other)
    assert len(keys) > 100


def test_strict_accepts_spaces_and_tones_and_gives_the_same_value():
    a, b = "ma˥ ta˩˥", "pa˧ ka"
    assert ipa_distance(a, b, strict=True) == ipa_distance(a, b)
    assert edit_distance(segments(a), segments(b), strict=True) == edit_distance(segments(a), segments(b))
    assert align(segments(a), segments(b), strict=True) == align(segments(a), segments(b))
    search = PhoneticFuzzySearch(strict=True)
    search.add_term(a, 1)
    assert search.search(a)[0].score == 0.0


def test_strict_accepts_every_random_readable_string():
    readable = [s for s in random_strings() if not any(u in s for u in UNREAD)]
    assert len(readable) > 500
    for a, b in zip(readable[0::2], readable[1::2]):
        assert ipa_distance(a, b, strict=True) == ipa_distance(a, b)
