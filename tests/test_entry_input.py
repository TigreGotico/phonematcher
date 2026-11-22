"""Input at the public entry points: a wrong type names the argument and the type, and the silent
cases of add_term and search are the documented ones."""
import pytest

import phonematcher
from phonematcher import PhoneticFuzzySearch, align, edit_distance, ipa_distance, tone_distance, vectorize_phones
from phonematcher.version import VERSION_STR


def test_the_package_version_is_the_version_file():
    assert phonematcher.__version__ == VERSION_STR


@pytest.mark.parametrize("call, text", [
    (lambda: ipa_distance(None, "a"), "ipa_distance() argument a must be str, not NoneType"),
    (lambda: ipa_distance("a", b"ka"), "ipa_distance() argument b must be str, not bytes"),
    (lambda: edit_distance(3, ["a"]), "edit_distance() argument a must be a list of segments, not int"),
    (lambda: edit_distance(["a"], None), "edit_distance() argument b must be a list of segments, not NoneType"),
    (lambda: align(None, ["a"]), "align() argument a must be a list of segments, not NoneType"),
    (lambda: align(["a"], 1.5), "align() argument b must be a list of segments, not float"),
    (lambda: tone_distance(None, "˥"), "tone_distance() argument a must be str, not NoneType"),
    (lambda: tone_distance("˥", 4), "tone_distance() argument b must be str, not int"),
    (lambda: PhoneticFuzzySearch().add_term(None, 1), "add_term() argument term must be str or a list of str, not NoneType"),
    (lambda: PhoneticFuzzySearch().add_term(["ka", 3], 1), "add_term() argument term must be str or a list of str, not list"),
    (lambda: PhoneticFuzzySearch().search(None), "search() argument query must be str or a list of str, not NoneType"),
    (lambda: PhoneticFuzzySearch().search(b"ka"), "search() argument query must be str or a list of str, not bytes"),
    (lambda: PhoneticFuzzySearch(cluster_sensitivity="a"), "cluster_sensitivity must be a number from 0 to 1, not str"),
    (lambda: PhoneticFuzzySearch(cluster_sensitivity=None), "cluster_sensitivity must be a number from 0 to 1, not NoneType"),
])
def test_a_wrong_type_names_the_argument_and_the_type(call, text):
    with pytest.raises(TypeError) as error:
        call()
    assert str(error.value) == text


def test_a_right_type_still_works():
    assert ipa_distance("ka", "ka") == 0.0
    assert edit_distance(["k", "a"], ("k", "a")) == 0.0
    assert [pair for pair in align(["k"], ["k"])] == [("k", "k")]
    assert tone_distance("˥", "˥") == 0.0
    search = PhoneticFuzzySearch(1)
    search.add_term(("ka", "ke"), "x")
    assert search.search(["ka"])[0].id == "x"


@pytest.mark.parametrize("n_results", [0, -1])
def test_n_results_below_one_raises(n_results):
    search = PhoneticFuzzySearch()
    search.add_term("kasa", "a")
    with pytest.raises(ValueError, match=r"search\(\) argument n_results must be at least 1"):
        search.search("kasa", n_results=n_results)


def test_n_results_one_and_none_still_work():
    search = PhoneticFuzzySearch()
    search.add_term("kasa", "a")
    search.add_term("kaza", "b")
    assert len(search.search("kasa", n_results=1)) == 1
    assert len(search.search("kasa", n_results=None)) == 2


def test_a_none_id_raises_and_indexes_nothing():
    search = PhoneticFuzzySearch()
    with pytest.raises(ValueError, match="add_term.. argument id must not be None"):
        search.add_term("kasa", None)
    assert search.library == {} and search.index == {}


def test_an_empty_reading_is_stored_and_never_found():
    search = PhoneticFuzzySearch()
    search.add_term("", "empty")
    search.add_term([], "none")
    assert search.library == {"empty": ("",), "none": ()}
    assert search.index == {}


def test_a_repeated_id_replaces_the_old_readings_in_the_library_and_the_index():
    search = PhoneticFuzzySearch()
    search.add_term("kasa", "x")
    search.add_term("pɛtu", "x")
    assert search.library == {"x": ("pɛtu",)}
    assert search.search("kasa") == []
    assert search.search("pɛtu")[0].id == "x"
    fresh = PhoneticFuzzySearch()
    fresh.add_term("pɛtu", "x")
    assert search.index == fresh.index


def test_a_repeated_id_keeps_the_keys_that_another_id_holds():
    search = PhoneticFuzzySearch()
    search.add_term("kasa", "x")
    search.add_term("kasa", "y")
    search.add_term("pɛtu", "x")
    assert [m.id for m in search.search("kasa")] == ["y"]


def test_a_string_that_is_not_a_tone_raises_and_names_the_argument():
    with pytest.raises(ValueError) as error:
        tone_distance("a", "˥")
    assert str(error.value) == "tone_distance() argument a is not a tone: 'a'"
    with pytest.raises(ValueError, match="argument b is not a tone: ''"):
        tone_distance("˥", "")


def test_the_unrecognized_phone_error_shows_the_code_points_and_names_strict():
    with pytest.raises(ValueError) as error:
        vectorize_phones("̃")
    assert "(U+0303)" in str(error.value) and "strict=True" in str(error.value)
    with pytest.raises(ValueError) as error:
        vectorize_phones("ʞ")
    assert "'ʞ' (U+029E)" in str(error.value)
    with pytest.raises(ValueError) as error:
        vectorize_phones("ʞ̃")  # a base and a mark: both code points
    assert "(U+029E U+0303)" in str(error.value)
