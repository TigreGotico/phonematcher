"""The order of tied search results does not depend on the hash seed, and n_results is checked."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from phonematcher import PhoneticFuzzySearch

ROOT = Path(__file__).resolve().parent.parent

PROBE = """
from phonematcher import PhoneticFuzzySearch
s = PhoneticFuzzySearch()
s.add_term("maʃ", "1")
s.add_term("maʃ", 1)
s.add_term("maʃ", "a")
print([m.id for m in s.search("maʃ")])
"""


def test_tied_ids_of_mixed_types_sort_the_same_under_every_hash_seed():
    # Same score for all three; the rule is (type name, text): "int" < "str", then "1" < "a".
    expected = "[1, '1', 'a']"
    # the 16 processes run at once
    processes = {
        seed: subprocess.Popen([sys.executable, "-c", PROBE], env={**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONPATH": str(ROOT)},
                               stdout=subprocess.PIPE, text=True)
        for seed in range(16)
    }
    for seed, process in processes.items():
        out, _ = process.communicate()
        assert process.returncode == 0 and out.strip() == expected, f"PYTHONHASHSEED={seed}"


@pytest.fixture
def search():
    s = PhoneticFuzzySearch()
    s.add_term("kasa", "a")
    s.add_term("kaza", "b")
    return s


@pytest.mark.parametrize("n_results, name", [(True, "bool"), (False, "bool"), (2.5, "float"), (1.0, "float"), ("2", "str")])
def test_n_results_that_is_not_an_int_raises_type_error(search, n_results, name):
    with pytest.raises(TypeError, match=rf"^search\(\) argument n_results must be int or None, not {name}$"):
        search.search("kasa", n_results=n_results)
