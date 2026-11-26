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
import unicodedata
from collections import namedtuple
from fractions import Fraction
from functools import lru_cache
from operator import itemgetter
from typing import Dict, Hashable, List, Sequence, Set, Tuple, Union

from phonematcher.distance import check_readable, edit_distance, segments, substitution_cost
from phonematcher.features import TIES, phone_and_tone, phone_features
from phonematcher.phonex import phonex
from phonematcher.tone import is_tone

#: A search result: the term's id, its readings, and its edit distance to the query.
Match = namedtuple("Match", ["id", "term", "score"])

Readings = Union[str, Sequence[str]]


def upgma(labels: Sequence[str], threshold: float, dist: Dict[Tuple[str, str], float]) -> Dict[str, int]:
    """Group *labels* by UPGMA average linkage, merging while the closest pair of groups is at most
    *threshold* apart. *dist* holds the distance of every pair ``(a, b)`` with ``a < b``. Returns
    ``label -> cluster id``.

    Each pair of groups keeps the exact sum of its pair distances, so a merge adds two rows
    (Lance-Williams) and no sum depends on the order of the additions. Equal distances merge the
    pair with the lowest positions first, and cluster ids follow the order of *labels*."""
    members = {i: [label] for i, label in enumerate(labels)}
    total = {(i, j): Fraction(dist[min(a, b), max(a, b)])
             for i, a in enumerate(labels) for j, b in enumerate(labels) if i < j}
    mean = {pair: float(value) for pair, value in total.items()}
    while mean:
        (i, j), d = min(mean.items(), key=itemgetter(1, 0))
        if d > threshold:
            break
        members[i] += members.pop(j)
        del total[i, j], mean[i, j]
        for k in members:
            if k != i:
                ik, jk = (min(i, k), max(i, k)), (min(j, k), max(j, k))
                total[ik] += total.pop(jk)
                del mean[jk]
                mean[ik] = float(total[ik]) / (len(members[i]) * len(members[k]))
    return {label: cid for cid, i in enumerate(sorted(members), start=1) for label in members[i]}


@lru_cache(maxsize=None)
def _letter_costs() -> Tuple[Tuple[str, ...], Dict[Tuple[str, str], float], Tuple[float, ...]]:
    """The IPA letters and tied affricates of the table, the :func:`substitution_cost` of every pair
    ``(a, b)`` with ``a < b``, and those costs in ascending order."""
    letters = tuple(sorted(
        p for p in phone_features
        if (len(p) == 1 and unicodedata.category(p).startswith("L"))
        or (len(p) == 3 and p[1] in TIES)
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
    if isinstance(term, str):
        return (term,)
    if isinstance(term, (list, tuple)) and all(isinstance(r, str) for r in term):
        return tuple(term)
    raise TypeError(f"{function}() argument {argument} must be str or a list of str, not {type(term).__name__}")


class PhoneticFuzzySearch:
    """An index of IPA terms, searched by sound.

    A term is one IPA string or several readings of the same item; a match on any reading counts.
    *cluster_sensitivity* is a share from 0 to 1. The UPGMA merge threshold is that quantile of the
    segment costs over all pairs of letters, so a higher share puts more phones in one cluster,
    which finds more candidates.

    A segment that phonematcher cannot read is at distance 1 from every other segment. With
    *strict*, :meth:`add_term` and :meth:`search` raise ``ValueError`` for a term or query that holds one.
    """

    def __init__(self, cluster_sensitivity: float = 0.12, *, strict: bool = False):
        if isinstance(cluster_sensitivity, bool) or not isinstance(cluster_sensitivity, (int, float)):
            raise TypeError(f"cluster_sensitivity must be a number from 0 to 1, not {type(cluster_sensitivity).__name__}")
        self.cluster_sensitivity = cluster_sensitivity
        self.strict = strict
        self.clusters = phone_clusters(cluster_sensitivity)
        self.index: Dict[Tuple[int, ...], Set[Hashable]] = {}
        self.library: Dict[Hashable, Tuple[str, ...]] = {}
        self._segmented: Dict[Hashable, Tuple[List[str], ...]] = {}
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

    @staticmethod
    def _words(segs: Sequence[str]) -> List[List[str]]:
        words: List[List[str]] = [[]]
        for seg in segs:
            if seg == " ":
                words.append([])
            elif not is_tone(seg):
                words[-1].append(unicodedata.normalize("NFC", phone_and_tone(seg)[0]))
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
        segmented = tuple(self._segments(reading) for reading in readings)
        self.library.pop(id, None)
        for segs in self._segmented.pop(id, ()):
            for word in self._words(segs):
                for key in self._keys(word):
                    ids = self.index.get(key)
                    if ids is not None:
                        ids.discard(id)
                        if not ids:
                            del self.index[key]
        self.library[id] = readings
        self._segmented[id] = segmented
        for segs in segmented:
            for word in self._words(segs):
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
        q_segs = [self._segments(q) for q in queries]
        candidates: Set[Hashable] = set()
        for segs in q_segs:
            words = self._words(segs)
            if words:
                per_word = [set().union(*(self.index.get(key, ()) for key in self._keys(w))) for w in words]
                candidates |= set.intersection(*per_word)
        matches = []
        for id in candidates:
            score = min(edit_distance(q, t) for q in q_segs for t in self._segmented[id])
            matches.append(Match(id, self.library[id], score))
        matches.sort(key=lambda m: (m.score, type(m.id).__name__, str(m.id)))
        return matches[:n_results]
