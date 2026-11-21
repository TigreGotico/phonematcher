"""Phonetic fuzzy search over IPA.

Phones are grouped into clusters of near sounds (UPGMA average linkage over
:func:`~phonematcher.features.phonetic_distance`). Each word of a term is indexed by its cluster
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
from functools import lru_cache
from typing import Dict, Hashable, Iterable, List, Sequence, Set, Tuple, Union

from phonematcher.distance import edit_distance, segments
from phonematcher.features import phone_features, phonetic_distance
from phonematcher.phonex import phonex
from phonematcher.tone import is_tone

#: A search result: the term's id, its readings, and its edit distance to the query.
Match = namedtuple("Match", ["id", "term", "score"])

Readings = Union[str, Sequence[str]]


def upgma(labels: Sequence[str], threshold: float) -> Dict[str, int]:
    """Group *labels* by UPGMA average linkage, merging while the closest pair of groups is at most
    *threshold* apart. Returns ``label -> cluster id``."""
    dist = {(a, b): phonetic_distance(a, b) for a in labels for b in labels if a < b}

    def between(c1: Set[str], c2: Set[str]) -> float:
        return sum(dist[min(a, b), max(a, b)] for a in c1 for b in c2) / (len(c1) * len(c2))

    clusters = [{label} for label in labels]
    while len(clusters) > 1:
        d, i, j = min((between(clusters[i], clusters[j]), i, j)
                      for i in range(len(clusters)) for j in range(i + 1, len(clusters)))
        if d > threshold:
            break
        clusters[i] |= clusters.pop(j)
    return {label: cid for cid, cluster in enumerate(clusters, start=1) for label in cluster}


@lru_cache(maxsize=8)
def phone_clusters(threshold: float) -> Dict[str, int]:
    """The clusters of the IPA letters and tied affricates in the table at *threshold*.

    Any other segment, such as a letter with diacritics, takes the cluster of its nearest phone.
    """
    phones = [p for p in phone_features
              if (len(p) == 1 and unicodedata.category(p).startswith("L"))
              or (len(p) == 3 and p[1] in "\u0361\u035c")]
    return upgma(sorted(phones), threshold)


def _as_readings(term: Readings) -> Tuple[str, ...]:
    return (term,) if isinstance(term, str) else tuple(term)


class PhoneticFuzzySearch:
    """An index of IPA terms, searched by sound.

    A term is one IPA string or several readings of the same item; a match on any reading counts.
    *cluster_sensitivity* is the UPGMA merge threshold: higher values put more phones in one
    cluster, which finds more candidates.
    """

    def __init__(self, cluster_sensitivity: float = 0.1):
        self.cluster_sensitivity = cluster_sensitivity
        self.clusters = phone_clusters(cluster_sensitivity)
        self.index: Dict[Tuple[int, ...], Set[Hashable]] = {}
        self.library: Dict[Hashable, Tuple[str, ...]] = {}
        self._cluster_memo: Dict[str, int] = {}

    def cluster_of(self, segment: str) -> int:
        """The cluster of *segment*; a segment outside the table takes its nearest phone's."""
        if segment in self.clusters:
            return self.clusters[segment]
        if segment not in self._cluster_memo:
            nearest = min(self.clusters, key=lambda p: (phonetic_distance(segment, p), p))
            self._cluster_memo[segment] = self.clusters[nearest]
        return self._cluster_memo[segment]

    def _words(self, ipa: str) -> List[List[str]]:
        words: List[List[str]] = [[]]
        for seg in segments(ipa):
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
        """Index *term*, an IPA string or a list of IPA readings, under *id*."""
        readings = _as_readings(term)
        self.library[id] = readings
        for reading in readings:
            for word in self._words(reading):
                for key in self._keys(word):
                    self.index.setdefault(key, set()).add(id)

    def _ids_for_word(self, word: Sequence[str]) -> Set[Hashable]:
        found: Set[Hashable] = set()
        for key in self._keys(word):
            found |= self.index.get(key, set())
        return found

    def search(self, query: Readings, n_results: int = 10) -> List[Match]:
        """Terms that sound like *query*, nearest first.

        A candidate must match every word of at least one query reading. Its score is the smallest
        feature-weighted edit distance between a query reading and a term reading.
        """
        queries = _as_readings(query)
        candidates: Set[Hashable] = set()
        for q in queries:
            per_word: Iterable[Set[Hashable]] = (self._ids_for_word(w) for w in self._words(q))
            candidates |= set.intersection(*per_word) if self._words(q) else set()
        q_segs = [segments(q) for q in queries]
        matches = []
        for id in candidates:
            score = min(edit_distance(q, segments(t)) for q in q_segs for t in self.library[id])
            matches.append(Match(id, self.library[id], score))
        matches.sort(key=lambda m: (m.score, str(m.id)))
        return matches[:n_results]
