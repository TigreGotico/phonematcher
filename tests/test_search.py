"""Phonetic search over IPA terms.

The terms are Portuguese words in broad IPA, from orthography2ipa for pt-PT. The queries are the
same words as orthography2ipa writes them for other varieties: coda /S/ as [s] or [ʃ], /R/ as [ʁ],
[χ] or [x], /t d/ before [i] as stops or affricates.
"""
import math

import pytest

from phonematcher.clustering import PhoneticFuzzySearch

#: p/b, t/d and s/z differ in [voice] alone, weight 0.125 of the table's 9.5, and a substitution
#: costs the square root of the feature distance
VOICE = math.sqrt(0.125 / 9.5)

TERMS = {
    "pois": "ˈpojʃ",
    "retirada": "ʁetiˈɾadɐ",
    "carro": "ˈkaʁu",
    "casa": "ˈkazɐ",
    "dia": "ˈdiɐ",
    "mesa": "ˈmezɐ",
}


def index(**kwargs):
    search = PhoneticFuzzySearch(**kwargs)
    for name, ipa in TERMS.items():
        search.add_term(ipa, name)
    return search


def test_each_term_finds_itself_first():
    search = index()
    for name, ipa in TERMS.items():
        assert search.search(ipa)[0].id == name


def test_a_regional_reading_finds_its_word():
    search = index()
    assert search.search("ˈpojs")[0].id == "pois"
    assert search.search("χet͡ʃiˈɾadɐ")[0].id == "retirada"
    assert search.search("ˈkaxu")[0].id == "carro"
    assert search.search("ˈd͡ʒiɐ")[0].id == "dia"


def test_a_term_may_have_several_readings():
    search = PhoneticFuzzySearch()
    search.add_term(["ˈpojʃ", "ˈpojs"], "pois")
    match = search.search("ˈpojs")[0]
    assert match.id == "pois" and match.score == 0.0


def test_a_multi_word_query_needs_every_word():
    search = PhoneticFuzzySearch()
    search.add_term("ɐ ˈkazɐ", "a casa")
    search.add_term("ɐ ˈmezɐ", "a mesa")
    search.add_term("ˈkazɐ ˈnovɐ", "casa nova")
    ids = [m.id for m in search.search("ɐ ˈkazɐ")]
    assert ids[0] == "a casa" and "casa nova" not in ids


def test_each_score_is_the_edit_distance_worked_out_by_hand():
    search = PhoneticFuzzySearch()
    for term in ("pata", "bata", "bada", "pat", "patas"):
        search.add_term(term, term)
    found = [(m.id, m.score) for m in search.search("pata", None)]
    # bata: one voicing; bada: two; pat and patas: one gap at 0.5 each, tied and ordered by id
    assert found == [
        ("pata", 0.0), ("bata", pytest.approx(VOICE)), ("bada", pytest.approx(2 * VOICE)), ("pat", 0.5), ("patas", 0.5),
    ]


def test_an_unrelated_word_scores_far_below_a_near_one():
    search = index()
    near = search.search("ˈkasɐ")[0]
    assert near.id == "casa" and near.score == pytest.approx(VOICE)
    assert all(m.score > 2 for m in search.search("ˈstɾɐ̃ʒejɾu"))
