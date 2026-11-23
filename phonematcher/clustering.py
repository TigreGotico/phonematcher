"""Phonetic fuzzy search over IPA.

Phones are grouped into clusters of near sounds (UPGMA average linkage over
:func:`~phonematcher.distance.substitution_cost`). Each word of a term is indexed by its cluster
sequence and by every sequence with one or two clusters deleted, so a query finds terms that differ
by near sounds or by a dropped sound. Candidates are ranked by the feature-weighted edit distance
of :mod:`phonematcher.distance`.

Terms and queries are IPA. Use a grapheme-to-IPA library such as orthography2ipa to get IPA from
text.

Adapted from pyphone (https://github.com/lingz/pyphone) and fast_fuzzy_search
(https://github.com/lingz/fast_fuzzy_search), MIT License.
"""
import math
import unicodedata
from collections import namedtuple
from functools import lru_cache
from typing import Dict, Hashable, List, Sequence, Set, Tuple, Union

from phonematcher.distance import check_readable, edit_distance, segments, substitution_cost
from phonematcher.features import phone_features
from phonematcher.phonex import phonex
from phonematcher.tone import is_tone

#: A search result: the term's id, its readings, and its edit distance to the query.
Match = namedtuple("Match", ["id", "term", "score"])

Readings = Union[str, Sequence[str]]


def upgma(labels: Sequence[str], threshold: float, dist: Dict[Tuple[str, str], float]) -> Dict[str, int]:
    """Group *labels* by UPGMA average linkage, merging while the closest pair of groups is at most
    *threshold* apart. *dist* holds the distance of every pair ``(a, b)`` with ``a < b``. Returns
    ``label -> cluster id``.

    Distances are summed exactly, so the order in which a set yields its labels cannot change a sum
    by a rounding error. Equal distances merge the pair with the lowest cluster positions first, and
    cluster ids follow the order of *labels*."""

    def between(c1: Set[str], c2: Set[str]) -> float:
        return math.fsum(dist[min(a, b), max(a, b)] for a in c1 for b in c2) / (len(c1) * len(c2))

    clusters = [{label} for label in labels]
    while len(clusters) > 1:
        d, i, j = min((between(clusters[i], clusters[j]), i, j)
                      for i in range(len(clusters)) for j in range(i + 1, len(clusters)))
        if d > threshold:
            break
        clusters[i] |= clusters.pop(j)
    return {label: cid for cid, cluster in enumerate(clusters, start=1) for label in cluster}


@lru_cache(maxsize=None)
def _letter_costs() -> Tuple[Tuple[str, ...], Dict[Tuple[str, str], float], Tuple[float, ...]]:
    """The IPA letters and tied affricates of the table, the :func:`substitution_cost` of every pair
    ``(a, b)`` with ``a < b``, and those costs in ascending order."""
    letters = tuple(sorted(
        p for p in phone_features
        if (len(p) == 1 and unicodedata.category(p).startswith("L"))
        or (len(p) == 3 and p[1] in "\u0361\u035c")
    ))
    costs = {(a, b): substitution_cost(a, b) for a in letters for b in letters if a < b}
    return letters, costs, tuple(sorted(costs.values()))


def merge_threshold(share: float) -> float:
    """The *share* quantile of the segment costs over all pairs of distinct letters, with linear
    interpolation between the two nearest costs. Raises ``ValueError`` outside 0 to 1."""
    if not 0 <= share <= 1:
        raise ValueError(f"cluster_sensitivity is a share from 0 to 1, not {share!r}")
    ordered = _letter_costs()[2]
    position = share * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (position - low) * (ordered[high] - ordered[low])


@lru_cache(maxsize=8)
def phone_clusters(share: float) -> Dict[str, int]:
    """The clusters of the IPA letters and tied affricates in the table.

    Two groups of letters merge when their mean :func:`~phonematcher.distance.substitution_cost`
    is at most :func:`merge_threshold` of *share*. Any other segment, such as a letter with
    diacritics, takes the cluster of its nearest phone.
    """
    letters, costs, _ = _letter_costs()
    return upgma(letters, merge_threshold(share), costs)


def _as_readings(term: Readings, function: str, argument: str) -> Tuple[str, ...]:
    readings = (term,) if isinstance(term, str) else tuple(term) if isinstance(term, (list, tuple)) else None
    if readings is None or not all(isinstance(r, str) for r in readings):
        raise TypeError(f"{function}() argument {argument} must be str or a list of str, not {type(term).__name__}")
    return readings


class PhoneticFuzzySearch:
    """An index of IPA terms, searched by sound.

    A term is one IPA string or several readings of the same item; a match on any reading counts.
    *cluster_sensitivity* is a share from 0 to 1. The UPGMA merge threshold is that quantile of the
    segment costs over all pairs of letters, so a higher share puts more phones in one cluster,
    which finds more candidates.

    A segment that the feature table cannot read costs as much as a missing one. With *strict*,
    :meth:`add_term` and :meth:`search` raise ``ValueError`` for a term or query that holds one.
    """

    def __init__(self, cluster_sensitivity: float = 0.08, *, strict: bool = False):
        if isinstance(cluster_sensitivity, bool) or not isinstance(cluster_sensitivity, (int, float)):
            raise TypeError(f"cluster_sensitivity must be a number from 0 to 1, not {type(cluster_sensitivity).__name__}")
        self.cluster_sensitivity = cluster_sensitivity
        self.strict = strict
        self.clusters = phone_clusters(cluster_sensitivity)
        self.index: Dict[Tuple[int, ...], Set[Hashable]] = {}
        self.library: Dict[Hashable, Tuple[str, ...]] = {}
        self._cluster_memo: Dict[str, int] = {}

    def cluster_of(self, segment: str) -> int:
        """The cluster of *segment*; a segment outside the table takes its nearest phone's."""
        if segment in self.clusters:
            return self.clusters[segment]
        cid = self._cluster_memo.get(segment)
        if cid is None:
            nearest = min(self.clusters, key=lambda p: (substitution_cost(segment, p), p))
            cid = self._cluster_memo[segment] = self.clusters[nearest]
        return cid

    def _segments(self, ipa: str) -> List[str]:
        segs = segments(ipa)
        if self.strict:
            check_readable(segs, ipa)
        return segs

    def _words(self, ipa: str) -> List[List[str]]:
        words: List[List[str]] = [[]]
        for seg in self._segments(ipa):
            if seg == " ":
                words.append([])
            elif not is_tone(seg):
                words[-1].append(seg)
        return [w for w in words if w]

    def _keys(self, word: Sequence[str]) -> Set[Tuple[int, ...]]:
        key = phonex(word, self.cluster_of)
        one = {key[:i] + key[i + 1:] for i in range(len(key))}
        two = {k[:i] + k[i + 1:] for k in one for i in range(len(k))}
        return {k for k in {key} | one | two if k}

    def add_term(self, term: Readings, id: Hashable) -> None:
        """Index *term*, an IPA string or a list of IPA readings, under *id*.

        *id* must not be ``None``, and it must be hashable. Adding an id again replaces it: the old
        readings leave the library and the index. A term with no reading, or a reading with no sound, is stored and never found.
        """
        readings = _as_readings(term, "add_term", "term")
        if id is None:
            raise ValueError("add_term() argument id must not be None")
        if self.strict:
            for reading in readings:
                self._segments(reading)
        for reading in self.library.pop(id, ()):
            for word in self._words(reading):
                for key in self._keys(word):
                    ids = self.index.get(key)
                    if ids is not None:
                        ids.discard(id)
                        if not ids:
                            del self.index[key]
        self.library[id] = readings
        for reading in readings:
            for word in self._words(reading):
                for key in self._keys(word):
                    self.index.setdefault(key, set()).add(id)

    def search(self, query: Readings, n_results: int = 10) -> List[Match]:
        """Terms that sound like *query*, nearest first.

        A candidate must match every word of at least one query reading. Its score is the smallest
        feature-weighted edit distance between a query reading and a term reading. *n_results* is a
        count of at least 1, or ``None`` for every match. Matches with the same score are ordered by
        the type name of their id, then by the id as text, so the order does not change between runs.
        """
        if n_results is not None and (isinstance(n_results, bool) or not isinstance(n_results, int)):
            raise TypeError(f"search() argument n_results must be int or None, not {type(n_results).__name__}")
        if n_results is not None and n_results < 1:
            raise ValueError(f"search() argument n_results must be at least 1, not {n_results!r}")
        queries = _as_readings(query, "search", "query")
        candidates: Set[Hashable] = set()
        for q in queries:
            words = self._words(q)
            if words:
                per_word = [set().union(*(self.index.get(key, ()) for key in self._keys(w))) for w in words]
                candidates |= set.intersection(*per_word)
        q_segs = [self._segments(q) for q in queries]
        matches = []
        for id in candidates:
            score = min(edit_distance(q, segments(t)) for q in q_segs for t in self.library[id])
            matches.append(Match(id, self.library[id], score))
        matches.sort(key=lambda m: (m.score, type(m.id).__name__, str(m.id)))
        return matches[:n_results]
