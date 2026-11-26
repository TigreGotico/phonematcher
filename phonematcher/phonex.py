"""Phonex keys: an IPA word as the sequence of its phone clusters.

Adapted from pyphone (https://github.com/lingz/pyphone), MIT License.
"""
from itertools import groupby
from typing import Callable, Sequence, Tuple


def phonex(word: Sequence[str], cluster_of: Callable[[str], int]) -> Tuple[int, ...]:
    """The cluster ids of the segments of *word*, with repeats of one cluster collapsed."""
    return tuple(cid for cid, _ in groupby(map(cluster_of, word)))
