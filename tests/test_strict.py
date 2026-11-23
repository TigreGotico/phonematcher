"""Strict input raises on an unread segment; without it, an unread segment costs as much as a missing one."""
import math
import random

import pytest

from phonematcher import GAP_COST, PhoneticFuzzySearch, align, edit_distance, ipa_distance, segments, substitution_cost, vectorize_phones
from phonematcher.features import phone_features

UNREAD = ["k̃", "ˁ", "ʳ", "ʅ", "aʰ"]
LETTERS = list("pbtdkgqʔmnɲŋfvszʃʒxχhrlɾjwaeiouɛɔəɪʊæɑɨʉ")
TONES = ["˥", "˩˥", "˧"]

#: p and b differ in [voice] alone, weight 0.125 of the table's 9.5; a substitution costs the square root
VOICE = math.sqrt(0.125 / 9.5)


def random_strings(count=2000):
    rng = random.Random(0)

    def word():
        parts = []
        for _ in range(rng.randint(1, 6)):
            r = rng.random()
            parts.append(rng.choice(UNREAD) if r < 0.15 else rng.choice(TONES) if r < 0.2 else rng.choice(LETTERS))
        return "".join(parts)

    return [f"{word()} {word()}" if rng.random() < 0.2 else word() for _ in range(count)]


def test_the_unread_segments_are_unread():
    for seg in UNREAD:
        with pytest.raises(ValueError):
            vectorize_phones(seg)


def test_the_random_strings_hold_unread_segments():
    assert any(u in s for s in random_strings() for u in UNREAD)


def test_without_strict_each_alignment_costs_the_edit_distance_of_its_pair():
    strs = random_strings()
    for a, b in zip(strs[0::2], strs[1::2]):
        sa, sb = segments(a), segments(b)
        cost = math.fsum(GAP_COST if x is None or y is None else substitution_cost(x, y) for x, y in align(sa, sb))
        assert cost == pytest.approx(edit_distance(sa, sb)) == pytest.approx(ipa_distance(a, b)), (a, b)


def test_without_strict_each_search_score_is_the_least_distance_to_a_reading():
    strs = random_strings()
    search = PhoneticFuzzySearch()
    for i, term in enumerate(strs[:500]):
        search.add_term(term, i)
    for query in strs[1000:1100]:
        for match in search.search(query):
            assert match.score == ipa_distance(query, strs[match.id]), (query, match)


def test_without_strict_an_unread_segment_is_priced_in_each_entry_point():
    # an unread segment costs 1 against any segment and 0.5 as a gap; a tone against a phone costs 1
    assert edit_distance(["m", "a", "k̃"], ["m", "a"]) == 0.5
    assert edit_distance(["k̃"], ["p"]) == 1.0
    assert edit_distance(["˥"], ["a"]) == 1.0
    assert align(["p", "a", "ʅ"], ["b", "a"]) == [("p", "b"), ("a", "a"), ("ʅ", None)]
    assert ipa_distance("pa", "ba") == pytest.approx(VOICE)
    assert ipa_distance("pa", "ba", True) == pytest.approx(VOICE / 2)
    # the space between two words is a segment: p a, space, t a against p a is three gaps
    assert ipa_distance("pa ta", "pa") == 1.5
    search = PhoneticFuzzySearch()
    search.add_term("baʅ", "x")
    assert [(m.id, m.score) for m in search.search("ba")] == [("x", 0.5)]


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
