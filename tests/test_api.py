"""The package root exports exactly the stable API, and docs/api.md documents it."""
import re
from pathlib import Path

import pytest

import phonematcher

API = (Path(__file__).resolve().parent.parent / "docs" / "api.md").read_text(encoding="utf-8")

STABLE = {
    "Match", "PhoneticFuzzySearch", "align", "edit_distance", "feature_distance", "ipa_distance",
    "segments", "substitution_cost", "vectorize_phones", "tone_distance", "is_tone",
    "FEATURES", "WEIGHTS", "GAP_COST",
}
DEPRECATED = {"phonetic_distance"}
SUBMODULE_ONLY = {"phonex"}
INTERNAL = {
    "upgma", "phone_clusters", "merge_threshold", "compose_tie", "check_readable", "is_vowel_phone",
    "tone_levels", "scales", "SPELLINGS", "PRE_DIACRITICS", "POST_DIACRITICS", "SUPRASEGMENTALS",
    "LEVELS", "DIACRITIC_TONES", "NUMERALS", "PHRASE_MARKS", "NUM_FEATURES", "SOURCE",
}


def section(name):
    """The lines of docs/api.md that open a reference entry for *name*."""
    return re.findall(rf"^(?:- |#+ )(?:`\w+`, )*`{re.escape(name)}\b", API, flags=re.M)


def table_names():
    stable = API.split("## Stable API", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `(\w+)` \|", stable, flags=re.M))


def internal_names():
    internal = API.split("\n## Internal\n", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"\w+", " ".join(re.findall(r"`([^`]+)`", internal)))) - {"phonematcher"}


def test_all_is_the_stable_set_plus_the_deprecated_name():
    assert set(phonematcher.__all__) == STABLE | DEPRECATED
    assert len(phonematcher.__all__) == len(STABLE | DEPRECATED)


@pytest.mark.parametrize("name", sorted(STABLE | DEPRECATED))
def test_every_exported_name_imports_from_the_root(name):
    namespace = {}
    exec(f"from phonematcher import {name}", namespace)
    assert namespace[name] is getattr(phonematcher, name)


@pytest.mark.parametrize("name", sorted(STABLE | SUBMODULE_ONLY))
def test_every_stable_name_is_documented(name):
    assert section(name), f"docs/api.md has no section for {name}"
    assert name in table_names(), f"{name} is not in the Stable API table"


def test_the_table_lists_only_stable_names():
    assert table_names() == STABLE | SUBMODULE_ONLY


@pytest.mark.parametrize("name", sorted(INTERNAL))
def test_no_internal_name_is_exported(name):
    assert name not in phonematcher.__all__


def test_the_internal_section_lists_every_internal_name():
    assert INTERNAL <= internal_names()
    assert not internal_names() & (STABLE | SUBMODULE_ONLY)


def test_phonex_is_imported_from_its_module():
    import phonematcher.phonex as module
    from phonematcher.phonex import phonex

    assert phonematcher.phonex is module
    assert module.phonex is phonex
    assert "phonex" not in phonematcher.__all__
    assert "`from phonematcher.phonex import phonex`" in API


def test_the_deprecated_name_warns():
    with pytest.warns(DeprecationWarning):
        assert phonematcher.phonetic_distance("p", "b") == phonematcher.feature_distance("p", "b")
