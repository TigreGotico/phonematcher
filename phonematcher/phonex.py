"""Phonex keys: an IPA word as the sequence of its phone clusters.

Adapted from pyphone (https://github.com/lingz/pyphone), MIT License.
"""
from typing import Callable, Sequence, Tuple


def phonex(word: Sequence[str], cluster_of: Callable[[str], int]) -> Tuple[int, ...]:
    """The cluster ids of the segments of *word*, with repeats of one cluster collapsed."""
    key = []
    for seg in word:
        cid = cluster_of(seg)
        if not key or key[-1] != cid:
            key.append(cid)
    return tuple(key)
