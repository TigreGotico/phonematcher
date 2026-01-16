"""
Phonetic fuzzy search utility.

Implements:
- Levenshtein distance (baseline, O(n*m); consider replacing with rapidfuzz).
- Phone-level mapping and clustering using UPGMA average-linkage.
- Phonetic variant expansion for approximate dictionary indexing.
- Term lookup using phonetic keys and Levenshtein ranking.

This module is adapted from:
https://github.com/lingz/pyphone
https://github.com/lingz/fast_fuzzy_search/
MIT License.
"""

import operator
import re
from collections import namedtuple
from functools import reduce

from rapidfuzz.distance import Levenshtein

from phonematcher.distance import phonetic_distance

# Result container: (id, term, score)
Match = namedtuple("Result", ["id", "term", "score"])


# ---------------------------------------------------------------------------
# Core Search Class
# ---------------------------------------------------------------------------
class PhoneticFuzzySearch:
    """
    Combined phonetic + edit-distance fuzzy search.

    Primary workflow:
        1. Build a phonetic index of terms via add_term().
        2. Query the index using search().
        3. Search returns candidates ranked by Levenshtein distance.

    Attributes:
        mapping (dict):
            Grapheme → list of phonemes.
        index (dict):
            phonex_tuple → set of IDs referencing items containing that phonex.
        library (dict):
            id → original term.
        cluster_sensitivity (float):
            Threshold for UPGMA average-link clustering.
        phone_set (set):
            Unique set of phonemes extracted from mapping.
    """

    def __init__(self, mapping: dict, cluster_sensitivity=0.5):
        self.index = {}  # variant_tuple → {ids}
        self.library = {}  # id → term
        self.cluster_sensitivity = cluster_sensitivity
        self.mapping = mapping
        self.phone_set = self.get_phone_set(mapping)

    # -----------------------------------------------------------------------
    # Phone clustering
    # -----------------------------------------------------------------------
    def cluster_phones(self):
        """
        Cluster phones into numeric cluster IDs using UPGMA average-linkage.

        The computed clusters are regenerated per call. If repeatedly used,
        caching should be considered.
        """
        phones = sorted(self.phone_set)

        # Precompute pairwise phonetic distances to reduce phonetic_distance calls.
        dist = {}
        for i in range(len(phones)):
            for j in range(i + 1, len(phones)):
                a = phones[i]
                b = phones[j]
                dist[(a, b)] = phonetic_distance(a, b)

        return self._upgma_average_linkage(dist, phones, self.cluster_sensitivity)

    @staticmethod
    def get_phone_set(mapping: dict) -> set:
        """
        Extract unique phonemes from grapheme → phoneme mappings.
        """
        phone_set = set()
        for _, phones in mapping.items():
            for phone in phones:
                phone_set.add(phone)
        return phone_set

    @staticmethod
    def _upgma_average_linkage(distance_matrix, labels, threshold=0.5):
        """
        Cluster phones using UPGMA average-linkage with a merge threshold.

        Args:
            distance_matrix: dict[(str, str), float]
                Symmetric phone distance pairs; only (a,b) with a<b required.
            labels: list[str]
                Phone labels to cluster.
            threshold: float
                Maximum average inter-cluster distance to allow merging.

        Returns:
            dict: phone -> cluster_id
        """

        # Convert each label into its own initial cluster
        clusters = [{lbl} for lbl in labels]

        # Average-link distance between two clusters
        def cluster_distance(c1, c2):
            total = 0.0
            count = 0
            for a in c1:
                for b in c2:
                    if a == b:
                        continue
                    d = distance_matrix.get((a, b), distance_matrix.get((b, a)))
                    total += d
                    count += 1
            return total / count if count else 0.0

        merged = True
        while merged:
            merged = False
            best_pair = None
            best_dist = float("inf")

            # Identify the closest pair of clusters.
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    d = cluster_distance(clusters[i], clusters[j])
                    if d < best_dist:
                        best_dist = d
                        best_pair = (i, j)

            # Merge if below threshold.
            if best_pair and best_dist <= threshold:
                i, j = best_pair
                clusters[i] |= clusters[j]
                del clusters[j]
                merged = True

        # Assign consistent numeric cluster IDs.
        cluster_map = {}
        for cid, cl in enumerate(clusters, start=1):
            for lbl in cl:
                cluster_map[lbl] = cid

        return cluster_map

    # -----------------------------------------------------------------------
    # Phonetic transformation
    # -----------------------------------------------------------------------
    def _phoneticize(self, word) -> set:
        """
        Expand a raw orthographic word into all phonetic sequences using
        grapheme-to-phoneme mapping expansion.

        Returns:
            set[tuple[str]]:
                All deduplicated phoneme sequences after replacement and
                repeat-stripping.
        """

        def _tokenize(w):
            # Marks each character for stable substring replacement.
            return "".join(["_" + letter for letter in w])

        def _strip_repeats(w):
            # Remove consecutive duplicate phonemes and strip leading tokens.
            stripped = []
            last_letter = None
            w = filter(None, w.split("$"))
            for letter in w:
                if letter != last_letter and not letter.startswith("_"):
                    stripped.append(letter)
                last_letter = letter
            return tuple(stripped)

        tokenized = _tokenize(word.lower())
        next_words = {tokenized}
        results = set()

        # Precompute tokenized mapping keys for replacer.
        tokenized_mappings = {
            _tokenize(key): ["$" + ph for ph in mapping]
            for (key, mapping) in self.mapping.items()
        }

        # BFS-like substitution traversal.
        while next_words:
            next_word = next_words.pop()
            has_replacements = False

            for key, replacements in tokenized_mappings.items():
                if key in next_word:
                    has_replacements = True
                    for replacement in replacements:
                        # Replace only first occurrence each time to avoid collapse.
                        next_words.add(next_word.replace(key, replacement, 1))

            if not has_replacements:
                # Terminal form; strip repeats.
                results.add(_strip_repeats(next_word))

        return results

    def phonex(self, word):
        """
        Map a word to all possible sequences of phone clusters.

        Returns:
            list[tuple[int]]:
                Each phonex tuple is a sequence of cluster IDs.
        """
        phone_variants = self._phoneticize(word)
        clusters = self.cluster_phones()
        results = []

        for phone_variant in phone_variants:
            try:
                phonex_variant = tuple(clusters[p] for p in phone_variant)
                results.append(phonex_variant)
            except:
                print('Error:', word, phone_variant)
                raise
        return results

    # -----------------------------------------------------------------------
    # Index construction
    # -----------------------------------------------------------------------
    def add_term(self, term, id):
        """
        Add a term to the phonetic index.

        Args:
            term (str): Full text of item.
            id (hashable): External identifier for the term.
        """
        self.library[id] = term
        words = term.split()

        for word in words:
            variants = self._generate_phonetic_variants(word)
            for variant in variants:
                if not variant:
                    continue
                ids = self.index.setdefault(variant, set())
                ids.add(id)

    # -----------------------------------------------------------------------
    # Search
    # -----------------------------------------------------------------------
    def search(self, query, n_results=10):
        """
        Search for fuzzy phonetic matches to a query string.

        Workflow:
            1. Expand each query word into phonetic variants.
            2. Intersect all ID sets for multi-word queries.
            3. Rank final candidates via Levenshtein score.

        Args:
            query (str)
            n_results (int)

        Returns:
            list[Match]: Up to n_results matches sorted by score (ascending).
        """
        query_words = query.split()
        res_sets = map(self.ids_for_query_word, query_words)

        try:
            common_ids = set.intersection(*res_sets)
        except TypeError:
            return []

        candidates = map(lambda id: self.score_for_id(id, query), common_ids)
        ranked = sorted(candidates, key=lambda m: m.score)

        return ranked[:n_results]

    # -----------------------------------------------------------------------
    # Variant generation
    # -----------------------------------------------------------------------
    def _generate_phonetic_variants(self, word):
        """
        Generate phonetic variants by:
            - Taking full phonex sequence.
            - Removing one position.
            - Removing two positions (flattened).

        This amplifies recall in fuzzy matching.

        Returns:
            list[tuple[int]]
        """
        res = []
        phonexes = self.phonex(word)

        for phone in phonexes:
            one_delete = self._deletes(phone)
            # Flatten
            two_deletes = reduce(operator.add, map(self._deletes, one_delete))

            res.append(phone)
            res.extend(one_delete)
            res.extend(two_deletes)

        return res

    @staticmethod
    def _deletes(term):
        """
        Generate sequences with exactly one deletion for each position.

        Args:
            term (tuple[int])

        Returns:
            list[tuple[int]]
        """
        return [term[:i] + term[i + 1:] for i in range(len(term))]

    # -----------------------------------------------------------------------
    # Scoring / lookup
    # -----------------------------------------------------------------------
    def score_for_id(self, id, query):
        """
        Produce a Match for a given ID vs. full query.

        Ranking is performed using Levenshtein distance.
        """
        term = self.library.get(id)
        score = Levenshtein.distance(term.lower(), query.lower())
        return Match(id, term, score)

    def ids_for_query_word(self, query_word):
        """
        Return all IDs whose indexed phonetic variants match the query word.
        """
        variants = self._generate_phonetic_variants(query_word)

        # Retrieve all non-empty variant hits.
        res_sets = [
            s for s in (self.index.get(v) for v in variants) if s is not None
        ]

        return set.union(*res_sets) if res_sets else set()


# ---------------------------------------------------------------------------
# English phone mapping
# ---------------------------------------------------------------------------
EN_MAPPING = {
    "b": ["b"],
    "d": ["d"],
    "g": ["ɡ", "dʒ", "ʒ"],
    "j": ["dʒ"],
    "th": ["ð", "θ"],
    "the": ["ð"],
    "f": ["f"],
    "h": ["h"],
    "wh": ["hw"],
    "y": ["j", "i"],
    "c": ["k"],
    "k": ["k"],
    "q": ["k"],
    "ck": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "ng": ["ŋ"],
    "p": ["p"],
    "r": ["r"],
    "s": ["s"],
    "sh": ["ʃ"],
    "ti": ["ʃ"],
    "t": ["t"],
    "ch": ["tʃ"],
    "tch": ["tʃ"],
    "v": ["v"],
    "ve": ["v"],
    "w": ["w"],
    "x": ["k"],
    "z": ["z"],
    "si": ["ʒ"],
    "a": ["ɑ"],
    "e": ["ɛ"],
    "i": ["i"],
    "o": ["ou"],
    "u": ["u", "ɑ"],
    "ph": ["f"],
    "ar": ["ɑr"],
    "or": ["ar", "or"],
    "arr": ["ar"],
    "ire": ["aiɛr"],
    "our": ["ur"],
    "err": ["ɛr"],
    "are": ["ɛr"],
    "ir": ["ir"],
    "irr": ["ir"],
    "aur": ["or"],
    "oir": ["oiɛr"],
    "ore": ["oɛr"],
    "oar": ["oɛr"],
    "oor": ["uɛr"],
    "ur": ["ɜr"],
    "er": ["ɜr"],
    "urr": ["ʌr"],
    "ie": ["ai"],
    "ou": ["au"],
    "ai": ["ei"],
    "ay": ["ei"],
    "ey": ["i"],
    "ee": ["i"],
    "ea": ["i"],
    "ough": ["o"],
    "au": ["o"],
    "aw": ["o"],
    "oi": ["oi"],
    "oy": ["oi"],
    "oa": ["ou"],
    "oo": ["u"],
    "eau": ["ju"],
    "le": ["ɛl"],
    "on": ["ɛn"],
}

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Phonetic distances ===")
    print("m vs n:", phonetic_distance('m', 'n'))  # ~0.26
    print("b vs p:", phonetic_distance('b', 'p'))  # ~0.043
    print("e vs i:", phonetic_distance('e', 'i'))  # ~0.059
    print("a vs e:", phonetic_distance('a', 'e'))  # ~0.118
    print("f vs v:", phonetic_distance('f', 'v'))  # ~0.043
    print("p vs k:", phonetic_distance('p', 'k'))  # ~0.348

    alpha_only = re.compile('[^a-zA-Z]')
    ffs = PhoneticFuzzySearch(EN_MAPPING)

    # Add terms
    ffs.add_term('hello world', 0)
    ffs.add_term('hello friend', 1)
    ffs.add_term('goodbye world', 2)
    ffs.add_term('greetings', 3)
    ffs.add_term('friendship', 4)

    print("\n=== Single-word search ===")
    results = ffs.search('hello')
    print("Query: 'hello' ->", results)

    results = ffs.search('greetins')  # Intentional typo
    print("Query: 'greetins' ->", results)

    results = ffs.search('frend')  # Should match 'friend' and 'friendship'
    print("Query: 'frend' ->", results)

    print("\n=== Multi-word search ===")
    results = ffs.search('helo wrld')  # Approximate 'hello world'
    print("Query: 'helo wrld' ->", results)

    results = ffs.search('hello frend')  # Approximate 'hello friend'
    print("Query: 'hello frend' ->", results)

    results = ffs.search('goodby world')  # Approximate 'goodbye world'
    print("Query: 'goodby world' ->", results)

    print("\n=== Edge cases ===")
    results = ffs.search('')  # Empty query
    print("Query: '' ->", results)

    results = ffs.search('nonexistent')  # No matching terms
    print("Query: 'nonexistent' ->", results)

    results = ffs.search('hello world', n_results=1)  # Limit results
    print("Query: 'hello world' with n_results=1 ->", results)
