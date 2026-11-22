"""Task C8, speed, on tiny inputs. No test checks a time.

The hash of a 2-segment matrix is the SHA-256 of these four lines, each ending in a newline, with
the distance as ``repr`` of a float. For the distance 0 on the diagonal and 0.5 off it:

    a TAB a TAB 0.0 / a TAB b TAB 0.5 / b TAB a TAB 0.5 / b TAB b TAB 0.0
"""
import hashlib
import sys
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import speed  # noqa: E402

TEXT = "a\ta\t0.0\na\tb\t0.5\nb\ta\t0.5\nb\tb\t0.0\n"


def half(a: str, b: str) -> float:
    return 0.0 if a == b else 0.5


def test_matrix_hash_matches_hand_text():
    assert speed.matrix_hash(["a", "b"], half) == hashlib.sha256(TEXT.encode()).hexdigest()


def test_matrix_hash_changes_with_one_distance():
    def changed(a: str, b: str) -> float:
        return 0.5000000000000001 if (a, b) == ("b", "a") else half(a, b)

    assert speed.matrix_hash(["a", "b"], changed) != speed.matrix_hash(["a", "b"], half)


def test_time_pairs_counts_ordered_pairs_with_diagonal():
    seen = []
    pairs, seconds = speed.time_pairs(["a", "b", "c"], lambda a, b: seen.append((a, b)) or 0.0)
    assert pairs == 9 and len(seen) == 9 and seconds >= 0


def test_pick_pairs_is_seeded_and_counted():
    pool = ["w", "x", "y", "z"]
    first = speed.pick_pairs(pool, 5)
    assert first == speed.pick_pairs(pool, 5)
    assert len(first) == 5 and all(a != b for a, b in first)


def test_read_prons_skips_rows_without_pronunciation(tmp_path):
    path = tmp_path / "x.tsv"
    path.write_text("cat\tk æ t\ncat\tk ɑ t\ndog\td ɔ g\ncot\tk ɑ t\nbad\t\n", encoding="utf8")
    assert speed.read_prons(path) == ["kæt", "kɑt", "dɔg", "kɑt"]


def test_time_search_on_three_terms():
    result = speed.time_search(["kæt", "dɔg", "sʌn"], ["kæt"], 0.1)
    assert set(result) == {"build_seconds", "queries_per_second"}


def test_letter_set_has_affricates_and_matrix_is_stable():
    segs = speed.letters()
    assert "p" in segs and "t͡s" in segs
    assert speed.matrix_hash(segs[:6], speed.feature_distance) == speed.matrix_hash(segs[:6], speed.feature_distance)


def test_machine_names_the_cpu():
    assert speed.machine()["cpu"] != "?"
