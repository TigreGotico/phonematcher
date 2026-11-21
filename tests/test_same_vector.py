"""No two base letters of the table share one feature vector.

``EXPECTED_GROUPS`` lists the groups of letters with identical vectors that are allowed. A letter
pair at distance 0 is a synonym (two letters for one sound) or a missing contrast; each group is
added here only with a ruling. A new collision fails this test.
"""
import importlib.util
from itertools import combinations
from pathlib import Path

from phonematcher import vectorize_phones
from phonematcher.features import phonetic_distance

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "same_vector.py"
_spec = importlib.util.spec_from_file_location("same_vector_script", SCRIPT)
same_vector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(same_vector)

EXPECTED_GROUPS = []


def test_the_groups_of_letters_with_one_vector_are_the_expected_ones():
    assert same_vector.same_vector_groups() == EXPECTED_GROUPS


def test_no_two_base_letters_are_at_distance_zero():
    letters = same_vector.base_letters()
    assert len(letters) == 129
    zero = [(a, b) for a, b in combinations(letters, 2) if phonetic_distance(a, b) == 0]
    assert zero == [pair for group in EXPECTED_GROUPS for pair in combinations(group, 2)]


def test_a_collision_is_reported_as_a_group(monkeypatch):
    # ɓ is the implosive bilabial and b the plain voiced one; giving ɓ the vector of b must group them.
    monkeypatch.setattr(same_vector, "vectorize_phones",
                        lambda s: vectorize_phones("b" if s == "ɓ" else s))
    assert same_vector.same_vector_groups() == [["b", "ɓ"]]
