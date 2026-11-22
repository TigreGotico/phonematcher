"""The SCA system. CI does not run this file: LingPy is GPL-3.0 and sits in the ``bench-copyleft``
extra. Run it with ``pytest --import-mode=importlib benchmarks/test_sca.py``.

LingPy's own ``distance=True`` is the oracle for the normalized distance. SCA puts ``p`` and ``b``
in one sound class (P), so their distance is 0; ``p`` and ``t`` are in classes P and T.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import systems  # noqa: E402
from lingpy.align.pairwise import Pairwise  # noqa: E402

SCA = systems.build("sca", Path.home() / ".cache" / "phonematcher-bench")


def test_identical_words_are_at_distance_zero():
    assert SCA.word_distance(["p", "a"], ["p", "a"]) == 0
    assert SCA.word_distance(["p", "a"], ["p", "a"], normalized=True) == 0


def test_a_change_of_place_is_a_positive_distance():
    assert SCA.word_distance(["p", "a"], ["t", "a"]) > 0


def test_voicing_is_no_change_in_sca():
    assert SCA.word_distance(["p", "a"], ["b", "a"]) == 0


def test_normalized_distance_equals_lingpy_distance():
    pair = Pairwise(["p", "a"], ["t", "a"])
    pair.align(mode="global", distance=True)
    assert abs(SCA.word_distance(["p", "a"], ["t", "a"], normalized=True) - pair.alignments[0][2]) < 1e-9


def test_a_segment_outside_the_classes_is_unread():
    assert SCA.reads("p") and not SCA.reads("☃")
    try:
        SCA.word_distance(["☃"], ["p"])
    except systems.UnreadSegment:
        return
    raise AssertionError("no UnreadSegment")
