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
from collections import namedtuple
from functools import reduce

from rapidfuzz.distance import Levenshtein

from phonematcher.distance import phonetic_distance
from phonematcher.eudex import eudex_hash, weighted_hamming_distance
from phonematcher.phonex import phonex


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
        3. Search returns candidates ranked by Eudex/Levenshtein distance.

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

    def __init__(self, mapping: dict, cluster_sensitivity=0.5, use_eudex=False, eudex_threshold=100):
        self.index = {}  # variant_tuple → {ids}
        self.library = {}  # id → term
        self.cluster_sensitivity = cluster_sensitivity
        self.mapping = mapping
        self.phone_set = self.get_phone_set(mapping)
        self.clusters = self._cluster_phones()
        self.use_eudex = use_eudex
        self.eudex_threshold = eudex_threshold

    # -----------------------------------------------------------------------
    # Phone clustering
    # -----------------------------------------------------------------------
    def _cluster_phones(self):
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
        phonexes = phonex(word, self.mapping, self.clusters)

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
        term = self.library[id]
        if self.use_eudex:
            # Use weighted Hamming distance of whole words as score
            q_words = query.split()
            t_words = term.split()
            score = sum(weighted_hamming_distance(eudex_hash(q), eudex_hash(t))
                        for q, t in zip(q_words, t_words))
            # Add penalty for extra words
            score += abs(len(q_words) - len(t_words)) * 255
            return Match(id, term, score / self.eudex_threshold)
        else:
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
# Phone mapping - LLM Generated placeholders: TODO - review
# ---------------------------------------------------------------------------
# Canonical IPA fallback mapping for individual letters (Latin, Cyrillic, Arabic, etc.)
# Each letter maps to a list of IPA symbols; one-to-many allowed where ambiguous.
BASE_LATIN = {
    # -----------------------
    # Latin lowercase (core)
    # -----------------------
    "a": ["ɑ", "a", "ɐ", "ã", "ɑ̃"],
    "á": ["a"],
    "à": ["a"],
    "â": ["ɐ"],
    "ä": ["æ", "a"],
    "ã": ["ɐ̃"],
    "å": ["ɔ"],
    "ā": ["a"],
    "b": ["b"],
    "c": ["k", "s", "tʃ"],
    "ç": ["s"],
    "d": ["d"],
    "e": ["ɛ", "e", "ə"],
    "é": ["ɛ"],
    "è": ["ɛ"],
    "ê": ["e"],
    "ë": ["ə", "e"],
    "f": ["f"],
    "g": ["ɡ", "ʒ", "dʒ"],
    "h": ["h", ""],  # silent context-sensitive
    "i": ["i", "ɪ"],
    "í": ["i"],
    "î": ["i"],
    "ï": ["i"],
    "j": ["ʒ", "dʒ", "j"],
    "k": ["k"],
    "l": ["l", "ɫ"],
    "m": ["m"],
    "n": ["n", "ŋ"],
    "ñ": ["ɲ"],
    "o": ["o", "ɔ", "ɵ"],
    "ó": ["o"],
    "ô": ["o"],
    "ö": ["ø", "o"],
    "õ": ["õ"],
    "ø": ["ø"],
    "ō": ["o"],
    "p": ["p"],
    "q": ["k"],
    "r": ["r", "ɾ", "ʁ"],
    "s": ["s", "z", "ʃ"],
    "t": ["t"],
    "u": ["u", "ʊ", "w"],
    "ú": ["u"],
    "û": ["u"],
    "ü": ["y", "u"],
    "v": ["v", "β"],
    "w": ["w"],
    "x": ["ks", "ʃ", "z"],
    "y": ["i", "j", "ʝ"],
    "ý": ["i"],
    "ÿ": ["i", "y"],
    "z": ["z", "θ", "ʒ"],

    # -----------------------
    # Common Latin digraphs/trigraphs
    # -----------------------
    "ch": ["tʃ", "ʃ"],
    "sh": ["ʃ"],
    "zh": ["ʒ"],
    "ph": ["f"],
    "th": ["θ", "ð"],
    "ng": ["ŋ", "ŋɡ"],
    "sch": ["ʃ"],
    "gn": ["ɲ"],
    "rr": ["r", "ʁ"],
    "ll": ["ʎ", "ʝ"],

    # -----------------------
    # Digits: canonical spoken-word fallbacks (IPA, English-like canonical forms).
    # Per-language maps should override with local lexical forms.
    # -----------------------
    "0": ["ˈzɪəroʊ", "ˈzɪrəʊ"],  # "zero" (US / UK variants)
    "1": ["wʌn", "wən"],        # "one"
    "2": ["tuː", "tu"],         # "two"
    "3": ["θriː", "θri"],       # "three"
    "4": ["fɔːr", "fɔr"],       # "four"
    "5": ["faɪv"],              # "five"
    "6": ["sɪks"],              # "six"
    "7": ["sɛvən", "sɛvn"],     # "seven"
    "8": ["eɪt"],               # "eight"
    "9": ["naɪn"],              # "nine"
}
BASE_CYR = {
    # -----------------------
    # Cyrillic lowercase (partial but full essentials)
    # -----------------------
    "а": ["ɑ", "a"], "б": ["b"], "в": ["v"], "г": ["ɡ"], "д": ["d"],
    "е": ["e", "ɛ"], "ё": ["jo", "ʲo"], "ж": ["ʒ"], "з": ["z"], "и": ["i"],
    "й": ["j"], "к": ["k"], "л": ["l"], "м": ["m"], "н": ["n"], "о": ["o"],
    "п": ["p"], "р": ["r"], "с": ["s"], "т": ["t"], "у": ["u"], "ф": ["f"],
    "х": ["x", "h"], "ц": ["ts"], "ч": ["tʃ"], "ш": ["ʃ"], "щ": ["ɕː", "ʃtʃ"],
    "ъ": [""], "ы": ["ɨ"], "ь": [""], "э": ["ɛ"], "ю": ["ju"], "я": ["ja"],
}
BASE_AR = {

    # -----------------------
    # Arabic letters (essential + Persian extensions)
    # -----------------------
    "ا": ["ɑ", "a"], "ب": ["b"], "پ": ["p"], "ت": ["t"], "ث": ["θ"], "ج": ["dʒ", "ʒ"],
    "ح": ["ħ"], "خ": ["x", "χ"], "د": ["d"], "ذ": ["ð"], "ر": ["r"], "چ": ["tʃ"],
    "ژ": ["ʒ"], "ز": ["z"], "س": ["s"], "ش": ["ʃ"], "ص": ["sˤ"], "ض": ["dˤ"], "ط": ["tˤ"],
    "ظ": ["ðˤ"], "ع": ["ʕ"], "غ": ["ɣ"], "ف": ["f"], "ق": ["q"], "ك": ["k"],
    "گ": ["ɡ"], "ل": ["l"], "م": ["m"], "ن": ["n"], "ه": ["h"], "و": ["w", "u"],
    "ي": ["j", "i"], "ء": ["ʔ"], "ى": ["ɑ"], "ة": ["h", "t"],
}
BASE_DEVAN = {
    # -----------------------
    # Devanagari letters (essential consonants + vowels)
    # -----------------------
    "अ": ["ə"], "आ": ["aː"], "इ": ["i"], "ई": ["iː"], "उ": ["u"], "ऊ": ["uː"], "ए": ["eː"], "ऐ": ["ɛː"],
    "ओ": ["oː"], "औ": ["ɔː"],

    "क": ["k"], "ख": ["kʰ"], "ग": ["ɡ"], "घ": ["ɡʰ"], "ङ": ["ŋ"],
    "च": ["tʃ"], "छ": ["tʃʰ"], "ज": ["dʒ"], "झ": ["dʒʰ"], "ञ": ["ɲ"],
    "ट": ["ʈ"], "ठ": ["ʈʰ"], "ड": ["ɖ"], "ढ": ["ɖʰ"], "ण": ["ɳ"],
    "त": ["t̪"], "थ": ["t̪ʰ"], "द": ["d̪"], "ध": ["d̪ʰ"], "न": ["n̪"],
    "प": ["p"], "फ": ["pʰ"], "ब": ["b"], "भ": ["bʰ"], "म": ["m"],
    "य": ["j"], "र": ["r"], "ल": ["l"], "व": ["ʋ"], "श": ["ʃ"], "ष": ["ʂ"],
    "स": ["s"], "ह": ["ɦ"],
}
BASE_GERMANIC = {
    **BASE_LATIN,
    # -----------------------
    # Latin lowercase (Germanic essentials + diacritics)
    # -----------------------
    "a": ["ɑ", "a", "æ", "ɐ"],
    "á": ["a"], "à": ["a"], "â": ["ɑ"], "ä": ["ɛ", "æ"], "ã": ["ɑ̃"], "å": ["ɔ"],
    "ā": ["a"],

    "b": ["b"],

    "c": ["k", "s", "tʃ"], "ç": ["s"],

    "d": ["d"],

    "e": ["ɛ", "e", "ə"], "é": ["e"], "è": ["ɛ"], "ê": ["e"], "ë": ["ə"],

    "f": ["f"],

    "g": ["ɡ", "ʒ", "dʒ"],

    "h": ["h", ""],  # silent in some contexts

    "i": ["i", "ɪ"], "í": ["i"], "î": ["i"], "ï": ["i"],

    "j": ["j", "ʒ"],

    "k": ["k"],

    "l": ["l", "ɫ"],

    "m": ["m"],

    "n": ["n", "ŋ"],

    "o": ["o", "ɔ", "ɵ"], "ó": ["o"], "ô": ["o"], "ö": ["ø", "œ", "o"], "õ": ["ɔ̃"], "ø": ["ø"], "ō": ["o"],

    "p": ["p"],

    "q": ["k"],

    "r": ["r", "ɾ", "ʁ"],

    "s": ["s", "z", "ʃ"],

    "t": ["t"],

    "u": ["u", "ʊ", "w"], "ú": ["u"], "û": ["u"], "ü": ["y", "u"],

    "v": ["v", "f"],

    "w": ["w"],

    "x": ["ks", "ʃ"],

    "y": ["i", "j", "ʏ"], "ý": ["i"], "ÿ": ["i", "y"],

    "z": ["z", "ts"],

    "ß": ["s", "ss"],

    # -----------------------
    # Digraphs / trigraphs common in Germanic
    # -----------------------
    "ch": ["x", "ç", "k"],   # German: /x/ back, /ç/ front, Dutch: /x/
    "sch": ["ʃ"],
    "th": ["θ", "ð"],        # English
    "ph": ["f"],
    "ng": ["ŋ", "ŋɡ"],
    "sh": ["ʃ"],             # English
    "wh": ["ʍ", "w"],        # English dialects
    "ck": ["k"],             # Germanic spelling

    # -----------------------
    # Digits (IPA fallback English)
    # -----------------------
    "0": ["ˈzɪəroʊ", "ˈzɪrəʊ"],  # "zero" US/UK
    "1": ["wʌn", "wən"],
    "2": ["tuː", "tu"],
    "3": ["θriː", "θri"],
    "4": ["fɔːr", "fɔr"],
    "5": ["faɪv"],
    "6": ["sɪks"],
    "7": ["sɛvən", "sɛvn"],
    "8": ["eɪt"],
    "9": ["naɪn"],
}

# Canonical IPA mapping for individual languages
PT_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a", "ɐ"],            # open/near-open variants (contextual)
    "b": ["b"],
    "c": ["k", "s"],            # /s/ before e/i handled in digraphs
    "d": ["d"],
    "e": ["e", "ɛ"],            # closed/open variants
    "f": ["f"],
    "g": ["ɡ", "ʒ"],            # /ʒ/ before e/i (handle in digraphs too)
    "h": [""],                  # silent
    "i": ["i"],
    "j": ["ʒ"],
    "k": ["k"],
    "l": ["l", "ɫ"],            # dark l in coda
    "m": ["m", "̃m"],           # nasalized in coda contexts (representative)
    "n": ["n", "̃n"],           # nasalized in coda contexts
    "o": ["o", "ɔ"],
    "p": ["p"],
    "q": ["k"],                 # always followed by u in orthography
    "r": ["ʁ", "ɾ"],            # initial/rr -> ʁ, intervocalic -> ɾ (include both)
    "s": ["s", "z", "ʃ"],       # variants: s/z between vowels, ʃ in some clusters
    "t": ["t"],
    "u": ["u", "w"],            # /w/ when part of diphthong or glide
    "v": ["v"],
    "w": ["w"],
    "x": ["ʃ", "ks", "z", "s"], # multiple realizations depending on position
    "y": ["i"],
    "z": ["z"],

    # accented vowels (explicit)
    "á": ["a"],
    "à": ["a"],
    "â": ["ɐ"],
    "ã": ["ɐ̃"],
    "é": ["ɛ"],   # acute = open e in PT-PT
    "ê": ["e"],   # circumflex = closed e
    "í": ["i"],
    "ó": ["ɔ"],   # acute = open o
    "ô": ["o"],   # circumflex = closed o
    "õ": ["õ"],
    "ú": ["u"],
    "ü": ["u"],   # rare, in loans, treat as /u/

    # common consonant digraphs / clusters (PT-specific)
    "ch": ["ʃ"],
    "lh": ["ʎ"],
    "nh": ["ɲ"],
    "rr": ["ʁ"],
    "ss": ["s"],      # medial or word-internal
    "sc": ["ʃ", "sk"],# loan/cluster variants
    "xc": ["ks", "ʃ"],# depends on word
    "sh": ["ʃ"],      # loanwords/foreign
    "zh": ["ʒ"],      # loanwords/foreign

    # g/c + front vowels contexts (explicit digraphs)
    "ge": ["ʒ"], "gi": ["ʒ"],
    "gue": ["ɡe"], "gui": ["ɡi"],  # 'u' is not pronounced as /w/ here (it is orthographic)
    "que": ["ke"], "qui": ["ki"],

    # q+u and g+u special cases (silent u where orthographic)
    "qu": ["k", "kw"],  # 'qu' before a/o/u -> kw sometimes, before e/i -> k (u silent)
    "gu": ["ɡ", "ɡw"],  # similar behavior

    # vowel digraphs / diphthongs (include nasal ones)
    "ai": ["aj"], "au": ["aw"], "ei": ["ej"], "oi": ["oj"],
    "ou": ["ow"], "ui": ["uj"], "eu": ["ew"],

    # nasal diphthongs / sequences
    "ão": ["ɐ̃w̃"], "ãe": ["ɐ̃j̃"], "õe": ["õj̃"], "om": ["õ"], "on": ["õ"],
    "an": ["ɐ̃"], "am": ["ɐ̃"], "em": ["ẽ"], "en": ["ẽ"], "im": ["ĩ"], "in": ["ĩ"],
    "um": ["ũ"], "un": ["ũ"],

    # cedilla and other orthographic markers
    "ç": ["s"],

    # digits - PT (canonical lexical pronunciations in IPA)
    "0": ["ˈzɛɾu"],   # zero
    "1": ["ũ", "um"], # um / ũ
    "2": ["ˈdojʃ"],   # dois
    "3": ["tɾeʃ"],    # três
    "4": ["ˈkwatɾu"], # quatro
    "5": ["ˈsiŋku"],  # cinco (note: nasalization of 'n' can be encoded)
    "6": ["ˈsejʃ"],   # seis
    "7": ["ˈsɛtʃi"],  # sete (pt-pt: ['sɛtɨ] or ['sɛt(ɨ)] — adjust to preferred system)
    "8": ["ˈoitu"],   # oito
    "9": ["ˈnɔvɐ"],   # nove
}
PT_BR = {
    **PT_MAPPING,
    # Brazilian Portuguese differences
    "r": ["ɾ", "ʁ"],        # trilled r less common, tap intervocalic dominant
    "s": ["s", "z", "ʃ"],   # /ʃ/ before sibilant clusters or loanwords
    "x": ["ʃ", "ks", "s"],   # /z/ less common, /ʃ/ more common in Rio
    "z": ["z", "s"],         # word-final devoicing sometimes
    # Nasal vowels: slightly different quality
    "ão": ["ɐ̃w̃"],          # nasal diphthong more open
    "õe": ["õj̃"],
    "em": ["ẽ"],              # nasalized mid vowel
}
PT_AO = {
    **PT_MAPPING,
    # Angolan Portuguese
    "r": ["ʁ"],              # uvular trilled r dominant in all positions
    "s": ["s"],              # no intervocalic /z/ in most speakers
    "x": ["ks", "ʃ"],         # /ʃ/ less frequent
    "ão": ["ãw̃"],            # slightly different nasal realization
}
GL_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a", "ɐ"],         # open/near-open variants
    "b": ["b"],
    "c": ["k", "s"],          # /s/ before e/i handled in digraphs
    "d": ["d"],
    "e": ["e", "ɛ"],          # closed/open variants
    "f": ["f"],
    "g": ["ɡ", "ʒ"],          # /ʒ/ before e/i
    "i": ["i"],
    "j": ["ʒ"],
    "k": ["k"],
    "l": ["l", "ɫ"],          # dark l in coda
    "m": ["m", "̃m"],         # nasalized in coda
    "n": ["n", "̃n"],         # nasalized in coda
    "o": ["o", "ɔ"],
    "p": ["p"],
    "q": ["k"],               # always followed by u
    "r": ["ɾ", "ʁ"],          # intervocalic tap, initial/rr uvular/trill
    "s": ["s", "z", "ʃ"],     # s/z variation
    "t": ["t"],
    "u": ["u", "w"],          # /w/ in diphthongs/glides
    "v": ["v"],
    "w": ["w"],
    "x": ["ʃ", "ks", "z", "s"],  # multiple realizations
    "y": ["i"],
    "z": ["z"],

    # accented vowels
    "á": ["a"],
    "à": ["a"],
    "â": ["ɐ"],
    "ã": ["ɐ̃"],
    "é": ["ɛ"],   # acute = open e
    "ê": ["e"],   # circumflex = closed e
    "í": ["i"],
    "ó": ["ɔ"],   # acute = open o
    "ô": ["o"],   # circumflex = closed o
    "õ": ["õ"],
    "ú": ["u"],
    "ü": ["u"],   # rare, typically in loans

    # common consonant digraphs / clusters
    "ch": ["ʃ"],
    "lh": ["ʎ"],
    "nh": ["ɲ"],
    "rr": ["ʁ"],
    "ss": ["s"],        # medial or word-internal
    "sc": ["ʃ", "sk"],  # loanwords or clusters
    "xc": ["ks", "ʃ"],  # cluster variants
    "sh": ["ʃ"],        # loanwords
    "zh": ["ʒ"],        # loanwords

    # g/c + front vowels contexts (explicit digraphs)
    "ge": ["ʒ"], "gi": ["ʒ"],
    "gue": ["ɡe"], "gui": ["ɡi"],
    "que": ["ke"], "qui": ["ki"],

    # q+u and g+u special cases
    "qu": ["k", "kw"],  # 'u' silent in front of e/i
    "gu": ["ɡ", "ɡw"],

    # vowel digraphs / diphthongs
    "ai": ["aj"], "au": ["aw"], "ei": ["ej"], "oi": ["oj"],
    "ou": ["ow"], "ui": ["uj"], "eu": ["ew"],

    # nasal diphthongs / sequences (less common than PT)
    "ão": ["ɐ̃w̃"], "ãe": ["ɐ̃j̃"], "õe": ["õj̃"], "om": ["õ"], "on": ["õ"],
    "an": ["ɐ̃"], "am": ["ɐ̃"], "em": ["ẽ"], "en": ["ẽ"], "im": ["ĩ"], "in": ["ĩ"],
    "um": ["ũ"], "un": ["ũ"],

    # cedilla and orthographic markers
    "ç": ["s"],

    # silent/context-sensitive
    "h": [""],

    # digits - Galician
    "0": ["ˈθeɾo"],  # cero
    "1": ["un"],      # un / ũ
    "2": ["dos"],     # dois
    "3": ["tɾes"],    # tres
    "4": ["catɾo"],   # catro
    "5": ["θiŋko"],   # cinco
    "6": ["sejɾe"],   # seis
    "7": ["sete"],    # sete
    "8": ["oito"],    # oito
    "9": ["nove"],    # nove
}
ES_MAPPING = {
    **BASE_LATIN,
    # Consonants
    "b": ["b"],
    "v": ["b"],          # Spanish: b and v often pronounced the same
    "c": ["k"],          # before a, o, u
    "ch": ["tʃ"],
    "d": ["d"],
    "f": ["f"],
    "g": ["ɡ"],          # before a, o, u
    "gu": ["ɡ"],         # before e, i (silent u otherwise)
    "h": [],             # silent
    "j": ["x"],
    "k": ["k"],
    "l": ["l"],
    "ll": ["ʎ", "ʝ"],    # y-like in some regions
    "m": ["m"],
    "n": ["n"],
    "ñ": ["ɲ"],
    "p": ["p"],
    "q": ["k"],          # always with u: qu
    "r": ["ɾ"],          # tapped r
    "s": ["s"],
    "t": ["t"],
    "x": ["ks", "s"],    # borrowed words
    "y": ["ʝ", "i"],     # vowel y / consonant y
    "z": ["θ"],          # Castilian Spanish; ["s"] in Latin America

    # Digraphs / combinations
    "ce": ["θe"],
    "ci": ["θi"],
    "ge": ["xe"],
    "gi": ["xi"],
    "gue": ["ɡe"],
    "gui": ["ɡi"],
    "que": ["ke"],
    "qui": ["ki"],

    # Vowels
    "a": ["a"],
    "á": ["a"],
    "e": ["e"],
    "é": ["e"],
    "i": ["i"],
    "í": ["i"],
    "o": ["o"],
    "ó": ["o"],
    "u": ["u"],
    "ú": ["u"],
    "ü": ["u"],         # in gue/gui to indicate u is pronounced

    # Diphthongs / common vowel sequences
    "ai": ["ai"],
    "ay": ["ai"],
    "ei": ["ei"],
    "ey": ["ei"],
    "oi": ["oi"],
    "oy": ["oi"],
    "au": ["au"],
    "eu": ["eu"],
    "ou": ["ou"],

    # Syllable combinations
    "rr": ["r"],         # trilled
    "qu": ["k"],         # before e/i

    # Endings
    "ción": ["θjon"],
    "sión": ["sjɔn"],
    "dad": ["ðad"],
    "tad": ["tad"],
}
ES_LA = {
    **ES_MAPPING,
    # Latin American Spanish
    "c": ["k", "s"],         # no /θ/, always /s/
    "z": ["s"],              # /s/ instead of /θ/
    "s": ["s", "z"],         # intervocalic /z/ minimal
    "ll": ["ʝ"],             # yeísmo: /ʎ/ merged with /ʝ/
    "y": ["ʝ"],              # consonantal y merged with ll
    "v": ["b"],              # merged with /b/
}
ES_AR = {
    **ES_LA,
    # Argentinian / Rioplatense
    "ll": ["ʃ"],             # zheísmo: /ʝ/ → /ʃ/
    "y": ["ʃ"],              # zheísmo
    "s": ["s"],              # no intervocalic /z/
}
CA_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a", "ə"],           # open/central variants
    "b": ["b", "β"],           # intervocalic /β/
    "c": ["k", "s"],           # /k/ before a/o/u, /s/ before e/i
    "d": ["d", "ð"],           # intervocalic /ð/
    "e": ["e", "ɛ", "ə"],      # closed/open/central
    "f": ["f"],
    "g": ["ɡ", "ʒ", "ɣ"],      # /ɡ/ before a/o/u, /ʒ/ before e/i, intervocalic /ɣ/
    "h": [""],                 # always silent
    "i": ["i", "j"],           # /j/ in diphthongs
    "j": ["ʒ"],                # palatal fricative
    "k": ["k"],
    "l": ["l", "ʎ"],           # lateral /ʎ/ in digraphs
    "m": ["m"],
    "n": ["n", "ŋ"],           # /ŋ/ before velars in some contexts
    "o": ["o", "ɔ"],
    "p": ["p"],
    "q": ["k"],                # always followed by u
    "r": ["ɾ", "r"],           # intervocalic tap /ɾ/, trilled initial /r/
    "s": ["s", "z"],           # intervocalic voiced /z/
    "t": ["t"],
    "u": ["u", "w"],           # /w/ in diphthongs
    "v": ["v", "β"],           # intervocalic /β/
    "w": ["w"],                # loanwords
    "x": ["ʃ", "ks", "s"],     # /ʃ/ (x inicial), /ks/ (loanwords)
    "y": ["i", "j"],           # consonantal /j/
    "z": ["z", "s"],           # intervocalic /z/, word-initial /s/

    # special Catalan letters
    "ç": ["s"],                # cedilla
    "l·l": ["lː"],             # geminated /l/ (ela geminada)
    "ny": ["ɲ"],               # palatal nasal

    # accented vowels (acute, grave, diaeresis)
    "à": ["a"], "á": ["a"],    # open a
    "è": ["ɛ"], "é": ["e"],    # open vs closed e
    "í": ["i"],
    "ï": ["i"],                 # diaeresis marks pronounced /i/
    "ò": ["ɔ"], "ó": ["o"],    # open vs closed o
    "ú": ["u"], "ü": ["w"],    # ü = /w/ in gü sequences

    # common digraphs / trigraphs
    "ch": ["tʃ"],               # loanwords
    "ll": ["ʎ"],                # palatal lateral
    "rr": ["r"],                # trilled /r/
    "gu": ["ɡ", "ɡw"],         # silent u before e/i in gue/gui
    "qu": ["k"],                # silent u before e/i
    "ge": ["ʒe"], "gi": ["ʒi"], # /ʒ/ before e/i
    "ce": ["se"], "ci": ["si"], # /s/ before e/i
    "sc": ["sk", "s"],          # loanwords
    "sh": ["ʃ"],                # loanwords
    "zh": ["ʒ"],                # loanwords

    # diphthongs
    "ai": ["aj"], "au": ["aw"], "ei": ["ej"], "oi": ["oj"],
    "ou": ["ow"], "ui": ["uj"], "iu": ["iw"], "ie": ["je"], "ue": ["we"],

    # nasal / consonant sequences (limited)
    "ng": ["ŋɡ"],               # loanwords
    "nm": ["nm"],               # rare

    # silent or context-sensitive letters
    "h": [""],
    "ü": ["w"],                # indicates pronounced /w/ in gü sequences

    # digits - Catalan lexical pronunciations in IPA
    "0": ["ˈzer"],             # zero
    "1": ["ˈu"],               # un / u
    "2": ["ˈdos"],             # dos
    "3": ["ˈtɾes"],            # tres
    "4": ["ˈkwa.tɾə"],         # quatre
    "5": ["ˈsiŋk"],            # cinc
    "6": ["ˈsis"],             # sis
    "7": ["ˈset"],             # set
    "8": ["ˈvuit"],            # vuit
    "9": ["ˈnɔu"],             # nou
}
OC_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a"],
    "b": ["b"],
    "c": ["k", "s"],          # /s/ before e/i
    "d": ["d"],
    "e": ["e", "ɛ"],           # open/closed variants
    "f": ["f"],
    "g": ["ɡ", "ʒ"],           # /ʒ/ before e/i
    "h": [""],                 # usually silent
    "i": ["i", "j"],           # /j/ in diphthongs
    "j": ["ʒ"],
    "k": ["k"],
    "l": ["l", "ʎ"],           # lateral-palatal in some dialects
    "m": ["m"],
    "n": ["n", "ŋ"],           # /ŋ/ in some loanwords or clusters
    "o": ["o", "ɔ"],
    "p": ["p"],
    "q": ["k"],                # usually followed by u
    "r": ["r", "ɾ"],           # trilled word-initial /r/, tap intervocalic
    "s": ["s", "z"],            # intervocalic voicing
    "t": ["t"],
    "u": ["y", "u", "w"],       # /y/ typical in Occitan, /w/ in diphthongs
    "v": ["v"],
    "w": ["w"],                 # loanwords
    "x": ["ks", "ʃ"],           # /ks/ in clusters, /ʃ/ in some dialects
    "y": ["i"],                 # mostly in loanwords
    "z": ["z", "ʒ"],            # /ʒ/ in some dialects

    # accented vowels (all Occitan orthography)
    "à": ["a"],
    "á": ["a"],   # dialectal
    "è": ["ɛ"],
    "é": ["e"],
    "ê": ["e"],   # closed e
    "ì": ["i"],
    "í": ["i"],   # dialectal
    "ò": ["ɔ"],
    "ó": ["o"],
    "òu": ["u"],  # rare vowel cluster
    "ù": ["u"],
    "ü": ["y"],   # front rounded vowel
    "ï": ["i"],   # diaeresis for hiatus

    # nasal vowels
    "an": ["ã"], "am": ["ã"],
    "en": ["ẽ"], "em": ["ẽ"],
    "on": ["õ"], "om": ["õ"],
    "un": ["ũ"], "um": ["ũ"],

    # common digraphs / trigraphs
    "ch": ["ʃ"],
    "nh": ["ɲ"],
    "lh": ["ʎ"],
    "ss": ["s"],
    "rr": ["r"],        # trilled
    "gn": ["ɲ"],
    "qu": ["k"],        # silent u before e/i
    "gu": ["ɡ"],        # silent u before e/i
    "ge": ["ʒe"], "gi": ["ʒi"], # /ʒ/ before e/i
    "ce": ["se"], "ci": ["si"], # /s/ before e/i
    "sc": ["sk"],        # loanwords
    "sh": ["ʃ"],         # loanwords
    "zh": ["ʒ"],         # loanwords

    # diphthongs / vowel sequences
    "ai": ["aj"], "au": ["aw"], "ei": ["ej"], "eu": ["ew"],
    "oi": ["oj"], "ou": ["ow"], "ui": ["uj"], "iu": ["ju"],

    # digits - Occitan lexical pronunciation
    "0": ["ˈzɛɾu"],   # zero
    "1": ["ˈun"],     # un
    "2": ["ˈdos"],    # dos
    "3": ["ˈtres"],   # tres
    "4": ["ˈkatɾo"],  # quatre
    "5": ["ˈsink"],   # cinc
    "6": ["ˈsɛis"],   # sies
    "7": ["ˈset"],    # sèt
    "8": ["ˈut"],     # uèch
    "9": ["ˈnøv"],    # nòu
}
FR_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a"],
    "b": ["b"],
    "c": ["k", "s"],          # /k/ default, /s/ before e/i
    "d": ["d"],
    "e": ["ə", "e", "ɛ"],      # schwa, closed/open e
    "f": ["f"],
    "g": ["ɡ", "ʒ"],           # /ʒ/ before e/i
    "h": [""],                  # silent
    "i": ["i", "j"],            # /j/ in diphthongs
    "j": ["ʒ"],
    "k": ["k"],
    "l": ["l"],
    "m": ["m", "̃m"],           # nasal in context
    "n": ["n", "̃n"],           # nasal in context
    "o": ["o", "ɔ"],
    "p": ["p"],
    "q": ["k"],
    "r": ["ʁ"],                 # uvular fricative
    "s": ["s", "z"],            # intervocalic /z/
    "t": ["t"],
    "u": ["y"],                 # front rounded
    "v": ["v"],
    "w": ["w"],                 # mostly in loans
    "x": ["ks", "ɡz"],          # /ks/ or /ɡz/ in some clusters
    "y": ["i", "j"],            # /j/ in diphthongs
    "z": ["z"],

    # accented vowels
    "à": ["a"],
    "â": ["ɑ"],
    "ä": ["a"],
    "é": ["e"],
    "è": ["ɛ"],
    "ê": ["ɛ"],
    "ë": ["ə"],
    "î": ["i"],
    "ï": ["i"],
    "ô": ["o"],
    "ö": ["o"],
    "ù": ["y"],                 # same as u but with grave
    "û": ["y"],
    "ü": ["y"],
    "ÿ": ["i"],

    # common digraphs / trigraphs
    "ai": ["ɛ", "e"],            # depending on context
    "au": ["o"],                 # or /ɔ/ in some words
    "ei": ["ɛ"],
    "eu": ["ø", "œ"],            # context-dependent
    "ou": ["u"],
    "oi": ["wa"],
    "ui": ["ɥi"],
    "eau": ["o"],
    "au": ["o"],
    "ou": ["u"],
    "an": ["ɑ̃"],                 # nasal
    "en": ["ɑ̃"],                 # nasal
    "in": ["ɛ̃"],                 # nasal
    "on": ["ɔ̃"],                 # nasal
    "un": ["œ̃"],                 # nasal
    "ien": ["jɛ̃"],               # nasal
    "ill": ["j"],                 # vowel + ill -> glide
    "gn": ["ɲ"],                  # palatal nasal
    "ch": ["ʃ"],
    "ph": ["f"],                  # Greek loans
    "th": ["t"],                  # mostly silent, classical loans
    "qu": ["k"],
    "gu": ["ɡ"],                  # u silent except before e/i

    # silent letters
    "h": [""],
    "s": ["s", ""],               # often silent at word end
    "t": ["t", ""],               # often silent at word end
    "x": ["ks", "z", ""],         # silent at word end in many plurals
    "p": ["p", ""],               # often silent at word end
    "d": ["d", ""],               # silent at word end

    # digits - French lexical IPA
    "0": ["zə.ʁo"],              # zéro
    "1": ["œ̃"],                   # un
    "2": ["dø"],                  # deux
    "3": ["tʁwɑ"],               # trois
    "4": ["katʁ"],                # quatre
    "5": ["sɛ̃k"],                # cinq
    "6": ["sis"],                  # six
    "7": ["sɛt"],                 # sept
    "8": ["ɥit"],                 # huit
    "9": ["nœf"],                 # neuf
}
IT_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a"],
    "b": ["b"],
    "c": ["k", "tʃ"],        # /k/ before a/o/u, /tʃ/ before e/i
    "d": ["d"],
    "e": ["e", "ɛ"],          # closed/open vowels
    "f": ["f"],
    "g": ["ɡ", "dʒ"],         # /ɡ/ before a/o/u, /dʒ/ before e/i
    "h": [""],               # silent, used in orthography
    "i": ["i", "j"],          # /j/ in diphthongs or glide
    "j": ["j"],               # rare, loanwords
    "k": ["k"],               # loanwords
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "o": ["o", "ɔ"],          # closed/open vowels
    "p": ["p"],
    "q": ["k"],               # always followed by u
    "r": ["r", "ɾ"],          # trilled/ tapped
    "s": ["s", "z"],          # voiceless/voiced intervocalic
    "t": ["t"],
    "u": ["u", "w"],          # /w/ in diphthongs or after q/g
    "v": ["v"],
    "w": ["w"],               # loanwords
    "x": ["ks"],              # loanwords
    "y": ["i", "j"],          # loanwords, consonantal /j/
    "z": ["ts", "dz"],        # /ts/ or /dz/ depending on word

    # accented vowels (Italian acute/grave)
    "à": ["a"],
    "è": ["ɛ"],
    "é": ["e"],
    "ì": ["i"],
    "ò": ["ɔ"],
    "ó": ["o"],
    "ù": ["u"],

    # common digraphs
    "ch": ["k"],              # hard c before e/i
    "gh": ["ɡ"],              # hard g before e/i
    "ci": ["tʃ"],             # soft c before i
    "ce": ["tʃ"],             # soft c before e
    "gi": ["dʒ"],             # soft g before i
    "ge": ["dʒ"],             # soft g before e
    "gl": ["ʎ"],              # palatal lateral (gli)
    "gn": ["ɲ"],              # palatal nasal
    "sc": ["ʃ", "sk"],        # /ʃ/ before e/i, /sk/ elsewhere
    "qu": ["kw"],             # always followed by u
    "i+vowel": ["j"],         # consonantal i forming glide in diphthongs

    # nasal/diphthongs (main Italian sequences)
    "ai": ["ai"], "au": ["au"], "ei": ["ei"], "eu": ["eu"], "oi": ["oi"], "ui": ["ui"], "iu": ["iu"], "ie": ["je"], "uo": ["wo"],

    # silent letters / context-sensitive
    "h": [""],
    "u": ["w"],               # in gue/gui, qu + vowel, diphthongs

    # digits - Italian lexical pronunciations in IPA
    "0": ["ˈdzɛro"],       # zero
    "1": ["ˈuno"],         # uno
    "2": ["ˈduːe"],        # due
    "3": ["ˈtɾɛ"],         # tre
    "4": ["ˈkwat.tɾo"],    # quattro
    "5": ["ˈtʃinko"],      # cinque
    "6": ["ˈsɛi"],         # sei
    "7": ["ˈsɛtte"],       # sette
    "8": ["ˈɔt.to"],       # otto
    "9": ["ˈnɔːve"],       # nove
}

EN_MAPPING = {
    **BASE_GERMANIC,
    # single letters (lowercase)
    "a": ["æ", "ɑ", "eɪ", "ə"],       # depending on word: cat, father, make, about
    "b": ["b"],
    "c": ["k", "s"],                   # cat/k vs cent/s
    "d": ["d"],
    "e": ["ɛ", "i", "ə"],              # bed, me, taken
    "f": ["f"],
    "g": ["ɡ", "dʒ"],                  # go vs gem
    "h": ["h"],
    "i": ["ɪ", "i", "aɪ"],             # sit, machine, like
    "j": ["dʒ"],
    "k": ["k"],
    "l": ["l", "ɫ"],                   # dark l in coda
    "m": ["m"],
    "n": ["n", "ŋ"],                   # sing /ŋ/
    "o": ["ɒ", "oʊ", "ɔ"],             # lot, go, thought
    "p": ["p"],
    "q": ["k"],                        # always /kw/ in qu
    "r": ["ɹ"],                         # GA rhotic
    "s": ["s", "z"],                   # sea, rose
    "t": ["t", "ʔ", "ɾ"],              # top, bottle (glottal/tap)
    "u": ["ʌ", "u", "ju", "ʊ"],        # cup, rule, music, put
    "v": ["v"],
    "w": ["w"],
    "x": ["ks", "ɡz"],                 # box, exact
    "y": ["j", "i"],                   # yes, happy
    "z": ["z", "s"],                   # zoo, xylophone

    # accented letters (loanwords, diacritics)
    "á": ["eɪ"], "à": ["ɑ"], "â": ["æ"], "ä": ["æ", "ɑ"], "é": ["eɪ"], "è": ["ɛ"],
    "ê": ["i"], "í": ["aɪ"], "ï": ["i"], "ó": ["oʊ"], "ô": ["oʊ"], "ö": ["oʊ", "ɔ"],
    "ú": ["u"], "ü": ["ju", "u"], "ñ": ["n"], "ç": ["s"],

    # common digraphs / trigraphs
    "ch": ["tʃ", "k"],         # church vs chem
    "sh": ["ʃ"],
    "th": ["θ", "ð"],           # thin vs this
    "ph": ["f"],
    "wh": ["w", "ʍ"],           # which (voiceless /ʍ/), who
    "ck": ["k"],
    "gh": ["ɡ", "f", ""],       # ghost, laugh, though
    "ng": ["ŋ", "ŋɡ"],          # sing, finger
    "qu": ["kw"],
    "tch": ["tʃ"],
    "dge": ["dʒ"],
    "wr": ["ɹ"],                 # write: silent w
    "kn": ["n"],                 # know: silent k
    "gn": ["n", "ɡn"],           # gnome, signature
    "sc": ["sk", "s"],           # school, science

    # vowel digraphs / sequences
    "ai": ["eɪ"], "au": ["ɔ"], "ay": ["eɪ"], "ea": ["i", "ɛ"], "ee": ["i"],
    "ei": ["i", "eɪ"], "ie": ["aɪ", "i"], "oa": ["oʊ"], "oo": ["u", "ʊ"],
    "ou": ["aʊ", "ʌ"], "ow": ["aʊ", "oʊ"], "ue": ["ju", "u"], "ui": ["ju", "u"],

    # r-controlled vowels
    "ar": ["ɑɹ"], "er": ["ɝ", "ɚ"], "ir": ["ɝ", "ɚ"], "or": ["ɔɹ"], "ur": ["ɝ", "ɚ"],

    # consonant sequences / clusters
    "spr": ["spr"], "str": ["str"], "spl": ["spl"], "scr": ["skr"],

    # silent letters / context-sensitive
    "h": [""],
    "k": ["k", ""],            # silent k in 'kn'
    "w": ["w", ""],            # silent w in 'write'

    # digits - English lexical IPA
    "0": ["zɪrɵ"], "1": ["wʌn"], "2": ["tuː"], "3": ["θriː"], "4": ["fɔːr"],
    "5": ["faɪv"], "6": ["sɪks"], "7": ["sɛvən"], "8": ["eɪt"], "9": ["naɪn"],

    "the": ["ð"],
    "ti": ["ʃ"],
    "ve": ["v"],
    "si": ["ʒ"],
    "arr": ["ar"],
    "ire": ["aiɛr"],
    "our": ["ur"],
    "err": ["ɛr"],
    "are": ["ɛr"],
    "irr": ["ir"],
    "aur": ["or"],
    "oir": ["oiɛr"],
    "ore": ["oɛr"],
    "oar": ["oɛr"],
    "oor": ["uɛr"],
    "urr": ["ʌr"],
    "ey": ["i"],
    "ough": ["o"],
    "aw": ["o"],
    "oi": ["oi"],
    "oy": ["oi"],
    "eau": ["ju"],
    "le": ["ɛl"],
    "on": ["ɛn"],
}
NL_MAPPING = {
    **BASE_GERMANIC,
    # single letters (lowercase)
    "a": ["a", "ɑ"],            # open a /ɑ/
    "b": ["b"],
    "c": ["k", "s"],            # /k/ default, /s/ before e/i
    "d": ["d"],
    "e": ["e", "ɛ", "ə"],       # open/close schwa
    "f": ["f"],
    "g": ["ɡ", "ɣ", "x"],       # Dutch 'g' regional variants /ɣ/ (north), /x/ (south)
    "h": ["h"],
    "i": ["i", "ɪ"],
    "j": ["j"],
    "k": ["k"],
    "l": ["l", "ɫ"],             # dark l in coda
    "m": ["m"],
    "n": ["n", "ŋ"],             # /ŋ/ in ng sequences
    "o": ["o", "ɔ"],             # close/open variants
    "p": ["p"],
    "q": ["k"],                  # rare, loanwords
    "r": ["r", "ɾ", "ʁ"],        # alveolar tap/trill, uvular variants
    "s": ["s", "z"],
    "t": ["t"],
    "u": ["y", "ʏ", "u"],        # front rounded /y/ and short /ʏ/
    "v": ["v", "f"],             # intervocalic voicing variation
    "w": ["ʋ", "w"],             # approximant /ʋ/, sometimes /w/
    "x": ["ks"],                 # /ks/ only in loanwords
    "y": ["ɛi", "i"],            # rare, usually as diphthong in loanwords
    "z": ["z"],

    # accented vowels (mostly loanwords or stressed forms)
    "á": ["a"], "à": ["a"], "â": ["a"], "ä": ["a"],   # mostly loanwords
    "é": ["e"], "è": ["ɛ"], "ê": ["e"],
    "í": ["i"], "ï": ["i"],
    "ó": ["o"], "ô": ["o"], "ö": ["o"],
    "ú": ["y"], "ü": ["y"],

    # common Dutch digraphs
    "aa": ["aː"],
    "ee": ["eː"],
    "oo": ["oː"],
    "uu": ["yː"],
    "ij": ["ɛi", "ɛɪ"],   # canonical diphthong
    "ei": ["ɛi", "ɛɪ"],
    "ou": ["ʌu"],          # /au/ in northern NL
    "au": ["ʌu"],          # /au/ variant
    "ui": ["œy"],          # unique Dutch diphthong
    "oe": ["u"],           # /u/ vowel
    "eu": ["ø"],           # /ø/ vowel
    "ie": ["iː"],          # long /i/
    "ei": ["ɛi"],          # repeated, safe for completeness

    # common Dutch trigraphs
    "sch": ["sx", "sχ"],    # /sx/ or /sχ/ depending on region
    "ngs": ["ŋs"],           # as in "zangs"
    "cht": ["xt"],           # common loanword cluster
    "ijk": ["ɛik"],          # proper diphthong sequence
    "eau": ["oː"],           # French loans

    # consonant clusters (some overlap with digraphs)
    "ng": ["ŋ"],             # nasal velar
    "nk": ["ŋk"],            # common in coda

    # silent letters / context-sensitive
    "h": ["h"],               # mostly pronounced
    "c": ["k", "s"],          # repeated context

    # digits - Dutch lexical pronunciations in IPA
    "0": ["ˈnul"],          # nul
    "1": ["ˈeɪn"],          # een
    "2": ["ˈtweɪ"],         # twee
    "3": ["ˈdri"],          # drie
    "4": ["ˈfiːr"],         # vier
    "5": ["ˈfaɪf"],         # vijf
    "6": ["ˈsɛks"],         # zes
    "7": ["ˈzɛvən"],        # zeven
    "8": ["ˈɑχt"],          # acht
    "9": ["ˈniːn"],         # negen
}
DE_MAPPING = {
    **BASE_GERMANIC,
    # single letters (lowercase)
    "a": ["a"],                # short/long variants not distinguished here
    "b": ["b", "p"],           # final devoicing: b → p
    "c": ["k", "ts"],          # k before a/o/u, ts in loanwords (z/c)
    "d": ["d", "t"],           # final devoicing
    "e": ["e"],                # short/long e: ɛ / eː (optional variants)
    "f": ["f"],
    "g": ["ɡ", "k"],           # final devoicing: g → k
    "h": ["h", ""],            # silent in some words after vowel
    "i": ["i"],                # long/short: i / iː
    "j": ["j"],
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "o": ["o"],                # long/short o: ɔ / oː
    "p": ["p"],
    "q": ["k"],                # always followed by u
    "r": ["ʁ", "r"],           # uvular fricative/trill or alveolar
    "s": ["z", "s", "ʃ"],      # /s/ initial or after voiceless, /z/ intervocalic, /ʃ/ in loanwords
    "t": ["t"],
    "u": ["u"],                # long/short: u / uː
    "v": ["f", "v"],           # /v/ in loanwords, /f/ native
    "w": ["v"],                # pronounced /v/
    "x": ["ks"],               # /ks/ standard
    "y": ["y", "i"],           # in loanwords
    "z": ["ts"],               # always /ts/

    # German umlauts / accented vowels
    "ä": ["ɛ"],                # can also be [eː] in some contexts
    "ö": ["ø"],                # long: øː optional
    "ü": ["y"],                # long: yː optional
    "ß": ["s"],                # sharp s

    # accented vowels (rare, mostly in loanwords)
    "é": ["e"],
    "è": ["ɛ"],
    "á": ["a"],
    "à": ["a"],

    # common digraphs
    "ch": ["ç", "x"],          # /ç/ after front vowels, /x/ elsewhere
    "sch": ["ʃ"],               # standard
    "ei": ["ai"],               # diphthong
    "ie": ["iː"],               # long i
    "au": ["au"],               # diphthong
    "eu": ["ɔy"],               # diphthong
    "äu": ["ɔy"],               # diphthong, same as eu
    "tz": ["ts"],               # common trigraph in word endings: e.g., "Herz" = /ts/
    "pf": ["pf"],               # common onset cluster
    "tsch": ["tʃ"],             # trigraph: e.g., "Tschechien"
    "sp": ["ʃp"],               # word-initial: "Spiel" /ʃpiːl/
    "st": ["ʃt"],               # word-initial: "Stadt" /ʃtat/

    # silent letters / context-sensitive
    "h": ["h", ""],             # already included above
    "g": ["ɡ", "k"],            # already included, context-sensitive

    # digits - German lexical pronunciations in IPA
    "0": ["ˈnʊl"],              # null
    "1": ["ˈaɪn"],              # eins
    "2": ["ˈtsoː"],              # zwei
    "3": ["ˈdʁaɪ"],             # drei
    "4": ["ˈfɪɐ̯"],             # vier
    "5": ["ˈfʏnf"],             # fünf
    "6": ["ˈzeks"],             # sechs
    "7": ["ˈziːbn̩"],           # sieben
    "8": ["ˈaχt"],              # acht
    "9": ["ˈnɔɪn"],             # neun
}
SV_MAPPING = {
    **BASE_GERMANIC,
    # single letters (lowercase)
    "a": ["a", "ɑ"],           # open/near-open variants
    "b": ["b"],
    "c": ["k", "s"],           # /s/ before e/i/y/ä/ö
    "d": ["d"],
    "e": ["e", "ɛ"],           # open/close
    "f": ["f"],
    "g": ["ɡ", "j"],           # soft g before e/i/y/ä/ö → /j/
    "h": ["h"],
    "i": ["i", "ɪ"],
    "j": ["j"],
    "k": ["k", "ɕ"],           # soft k before e/i/y/ä/ö → /ɕ/
    "l": ["l"],
    "m": ["m"],
    "n": ["n", "ŋ"],           # /ŋ/ before velars
    "o": ["o", "u"],           # o can be rounded [u] in loanwords
    "p": ["p"],
    "q": ["k"],                # mostly in loanwords
    "r": ["r"],                # alveolar trill
    "s": ["s", "ɧ"],           # /ɧ/ in sj/skj contexts
    "t": ["t", "ɕ"],           # soft t in tj/dj → /ɕ/
    "u": ["ʉ", "y"],           # standard u /ʉ/, fronted variants /y/
    "v": ["v"],
    "w": ["v", "w"],           # w often realized as /v/
    "x": ["ks"],
    "y": ["y"],
    "z": ["s"],                # usually /s/ in Swedish

    # accented vowels (loanwords / rare)
    "á": ["a"], "é": ["e"], "í": ["i"], "ó": ["o"], "ú": ["u"], "ý": ["y"], "ä": ["ɛ"], "å": ["o"], "ö": ["ø"],

    # common digraphs
    "sj": ["ɧ"],               # sj-sound, standard
    "skj": ["ɧ"],              # same as sj before front vowels
    "stj": ["ɧ"],              # Swedish stj-sound
    "tj": ["ɕ"],               # tj-sound (soft t)
    "dj": ["ɕ"],               # dj-sound
    "ng": ["ŋɡ"],              # ng sequence
    "nk": ["ŋk"],              # nasal + k
    "ch": ["ʃ"],               # loanwords

    # trigraphs / sequences
    "sch": ["ʃ"],              # German loanwords
    "rsk": ["ɧ"],              # rare cluster producing sj-like sound
    "rkj": ["ɧ"],              # trigraph in certain dialects

    # vowels + nasalization (rare, mainly in loanwords)
    "an": ["an"], "en": ["ɛn"], "in": ["in"], "on": ["on"], "un": ["ʉn"],

    # digits - Swedish lexical pronunciations in IPA
    "0": ["ˈnɔlː"],       # noll
    "1": ["ˈen"],         # ett/én
    "2": ["ˈtɔː"],        # två
    "3": ["ˈtreː"],       # tre
    "4": ["ˈfyːɾa"],      # fyra
    "5": ["ˈfɛmː"],       # fem
    "6": ["ˈsɛks"],       # sex
    "7": ["ˈsjʉː"],       # sju
    "8": ["ˈɔtːa"],       # åtta
    "9": ["ˈniː"],        # nio
}
DA_MAPPING = {
    **BASE_GERMANIC,
    # single letters (lowercase)
    "a": ["a", "ɑ", "æ"],       # open/near-open variants
    "b": ["b"],
    "c": ["k", "s"],             # /k/ before a/o/u, /s/ before e/i (loanwords)
    "d": ["d", "ð"],             # intervocalic soft d
    "e": ["e", "ɛ", "ə"],        # unstressed = schwa /ə/
    "f": ["f"],
    "g": ["ɡ", "ɡ̊", "ʔ"],       # final g may be devoiced or glottalized
    "h": ["h"],
    "i": ["i", "ɪ"],
    "j": ["j"],
    "k": ["k"],
    "l": ["l", "ɫ"],             # dark l in coda
    "m": ["m"],
    "n": ["n", "ŋ"],             # /ŋ/ before velars
    "o": ["o", "ɔ", "u"],        # context-sensitive
    "p": ["p"],
    "q": ["k"],                  # always followed by u in loanwords
    "r": ["ʁ", "ɐ˞", "ɾ"],       # uvular/trilled /r/ or tap depending on position
    "s": ["s", "z"],             # intervocalic voiced /s/
    "t": ["t", "ʔ"],             # final /t/ may be glottalized
    "u": ["u", "ʉ", "y"],        # rounded front variants
    "v": ["v"],
    "w": ["v", "w"],             # loanwords
    "x": ["ks"],
    "y": ["y"],
    "z": ["s", "z"],             # /s/ in loanwords, otherwise rare
    "æ": ["ɛ"],
    "ø": ["ø"],
    "å": ["ɔ"],

    # accented vowels (Danish uses mainly diacritics in loanwords)
    "á": ["a"], "é": ["e"], "í": ["i"], "ó": ["o"], "ú": ["u"], "ý": ["y"],

    # common digraphs
    "aa": ["ɑː"],        # traditional spelling for long 'å'
    "ae": ["ɛ"],         # loanwords or older orthography
    "oe": ["ø"],         # loanwords
    "au": ["ɑu"],        # diphthong
    "ai": ["aj"],        # diphthong
    "ei": ["ej"],
    "oi": ["ɔj"],
    "ui": ["ʉj"],
    "iu": ["ju"],

    # consonant digraphs
    "ng": ["ŋ"],         # velar nasal
    "kj": ["ç"],         # soft palatalized k
    "sj": ["ɕ"],         # soft s (common in loanwords)
    "tj": ["tɕ"],        # palatalized t
    "skj": ["ɕ"],        # common trigraph (palatalized s)
    "rj": ["ʁj"],        # rhotic + glide cluster
    "dr": ["dʁ"],        # cluster

    # context-sensitive letters
    "d": ["ð"],           # soft d intervocalic
    "g": ["ɡ̊", "ʔ"],    # final devoicing or glottal stop

    # digits - Danish lexical IPA
    "0": ["ˈnul"],         # nul
    "1": ["ˈen"],          # en
    "2": ["ˈtoː"],         # to
    "3": ["ˈtreː"],        # tre
    "4": ["ˈfiːɐ̯"],       # fire
    "5": ["ˈfæm"],         # fem
    "6": ["ˈseks"],        # seks
    "7": ["ˈsjuː"],        # syv
    "8": ["ˈoː"],          # otte
    "9": ["ˈniː"],         # ni
}
NO_MAPPING = {
    **BASE_GERMANIC,
    # single letters (lowercase)
    "a": ["ɑ", "a"],       # open and near-open variants
    "b": ["b"],
    "c": ["k", "s"],       # mostly in loanwords; before e/i = /s/
    "d": ["d"],
    "e": ["e", "ɛ"],
    "f": ["f"],
    "g": ["ɡ", "j"],       # /j/ in some loanwords, soft g
    "h": ["h"],
    "i": ["i"],
    "j": ["j"],
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n", "ŋ"],       # /ŋ/ before velars
    "o": ["u", "o"],       # /u/ in some dialects, /o/ canonical
    "p": ["p"],
    "q": ["k"],             # mostly loanwords
    "r": ["r", "ɾ"],        # trilled or tapped
    "s": ["s", "ʃ"],        # /ʃ/ in loanwords
    "t": ["t"],
    "u": ["ʉ", "u"],        # /ʉ/ central rounded vowel
    "v": ["v"],
    "w": ["v", "w"],        # mostly loanwords
    "x": ["ks"],
    "y": ["y"],
    "z": ["s", "z"],        # mostly loanwords
    "æ": ["æ"],
    "ø": ["ø", "œ"],
    "å": ["oː", "ɔ"],       # long and short variants

    # accented letters / diacritics (rare)
    "á": ["ɑ"], "é": ["e"], "í": ["i"], "ó": ["o"], "ú": ["u"], "ý": ["y"],
    "ǻ": ["oː"], "ǿ": ["ø"], "ǽ": ["æ"],

    # common digraphs
    "kj": ["ç"],            # voiceless palatal fricative
    "skj": ["ʃ"],           # voiceless postalveolar fricative
    "sj": ["ʃ"],            # same as skj
    "ng": ["ŋ"],            # velar nasal
    "tj": ["ç"],            # voiceless palatal fricative (loan/cluster)
    "rs": ["ʂ", "rs"],      # depending on dialect: /ʂ/ retroflex or /rs/ cluster
    "rt": ["ʈ", "rt"],      # retroflex /ʈ/ in some dialects
    "rd": ["ɖ", "rd"],      # retroflex /ɖ/ in some dialects
    "nt": ["nt", "ʈ"],      # cluster vs retroflex
    "ld": ["ɭ", "ld"],      # retroflex lateral

    # trigraphs (common)
    "sch": ["ʃ"],           # loanwords (German/English)
    "tju": ["çʉ"],          # common initial cluster /tʃy/ approximate
    "kjø": ["çø"],          # initial palatal cluster

    # vowel sequences / diphthongs
    "ei": ["æi", "ei"], "øy": ["øy"], "au": ["ɑʉ"], "ai": ["ɑi"], "oi": ["ɔi"], "ou": ["oʉ"],

    # special Norwegian letters sequences
    "aa": ["ɑː"],           # long /aː/, orthographic variant of å

    # silent letters / context-sensitive
    "h": ["h"],             # mostly pronounced
    "g": ["ɡ", "j"],        # soft g in some positions
    "r": ["r", "ɾ"],        # retroflex vs tap

    # digits - Norwegian lexical IPA
    "0": ["ˈsɛːrə"],        # null / zero
    "1": ["ˈɛn"],           # en
    "2": ["ˈtoː"],          # to
    "3": ["ˈtreː"],         # tre
    "4": ["ˈfiːr"],         # fire
    "5": ["ˈfem"],          # fem
    "6": ["ˈseks"],         # seks
    "7": ["ˈsju", "ˈsyv"], # sju (7) / syv
    "8": ["ˈåːt"],          # åtte
    "9": ["ˈniː"],          # ni
}

EUS_MAPPING = {
    **BASE_LATIN,
    # single letters (lowercase)
    "a": ["a"],
    "b": ["b"],
    "d": ["d"],
    "e": ["e"],
    "f": ["f"],
    "g": ["ɡ", "ɣ"],        # intervocalic /ɣ/
    "h": [""],              # mostly silent in standard Basque
    "i": ["i"],
    "j": ["j"],             # palatal approximant
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n", "ŋ"],        # /ŋ/ occurs before velars
    "o": ["o"],
    "p": ["p"],
    "r": ["ɾ", "r"],        # single tap /ɾ/, trilled /r/ word-initial or rr
    "s": ["s", "z"],        # voicing alternation in some dialects
    "t": ["t"],
    "u": ["u"],
    "v": ["b"],             # borrowed /v/ realized as /b/
    "x": ["ʃ"],             # x = /ʃ/
    "z": ["s", "θ"],        # /s/ (standard), /θ/ in dialectal Castilian influence
    "y": ["i"],             # loanwords
    "w": ["w"],             # loanwords
    "q": ["k"],             # loanwords only
    "ñ": ["ɲ"],             # loanwords /n palatal
    "ç": ["s"],             # rare, loanwords

    # accented vowels (mostly loanwords)
    "á": ["a"],
    "é": ["e"],
    "í": ["i"],
    "ó": ["o"],
    "ú": ["u"],

    # digraphs / trigraphs
    "dd": ["dː"],           # geminate /d/
    "ll": ["lː"],           # geminate /l/
    "rr": ["rː"],           # trilled /r/
    "ts": ["ts"],
    "tz": ["ts"],
    "tx": ["tʃ"],           # Basque-specific palatal affricate
    "txe": ["tʃe"],         # explicit context
    "tz": ["ts"],

    # common vowel sequences / diphthongs
    "ai": ["ai"], "ei": ["ei"], "oi": ["oi"], "au": ["au"],
    "eu": ["ew"], "iu": ["iu"], "oi": ["oi"], "ui": ["ui"],

    # nasal sequences / consonant clusters
    "ng": ["ŋɡ"],            # in loanwords

    # silent or context-sensitive letters
    "h": [""],               # reiterated for clarity

    # digits - Basque lexical forms
    "0": ["ˈzɐɾu"],          # zero
    "1": ["ˈbat"],           # bat
    "2": ["ˈbi"],            # bi
    "3": ["ˈhiru"],          # hiru
    "4": ["ˈlau"],           # lau
    "5": ["ˈbost"],          # bost
    "6": ["ˈsei"],           # sei
    "7": ["ˈzazpi"],         # zazpi
    "8": ["ˈzortzi"],        # zortzi
    "9": ["ˈbederatzi"],     # bederatzi
}

UK_MAPPING = {
    **BASE_CYR,
    # vowels
    "а": ["ɑ"],
    "е": ["ɛ"],
    "є": ["jɛ"],        # palatalized /je/
    "и": ["ɪ"],         # close central unrounded
    "і": ["i"],
    "ї": ["ji"],        # /ji/
    "о": ["ɔ", "o"],    # open vs mid
    "у": ["u"],
    "ю": ["ju"],
    "я": ["ja"],

    # consonants
    "б": ["b"],
    "в": ["v"],
    "г": ["ɦ"],          # voiced glottal fricative
    "ґ": ["ɡ"],          # hard g
    "д": ["d"],
    "ж": ["ʒ"],
    "з": ["z"],
    "й": ["j"],
    "к": ["k"],
    "л": ["l", "ɫ"],     # dark l in coda
    "м": ["m"],
    "н": ["n"],
    "п": ["p"],
    "р": ["r"],          # trilled r
    "с": ["s"],
    "т": ["t"],
    "ф": ["f"],
    "х": ["x"],          # voiceless velar fricative
    "ц": ["ts"],
    "ч": ["tʃ"],
    "ш": ["ʃ"],
    "щ": ["ʃtʃ"],       # historical /ɕː/, simplified
    "ь": [""],           # palatalization marker (soft sign)
    "’": [""],           # apostrophe in Ukrainian orthography
    "ю": ["ju"],
    "я": ["ja"],

    # digraphs / trigraphs (common palatalized sequences)
    "дь": ["dʲ"],
    "ть": ["tʲ"],
    "нь": ["nʲ"],
    "ль": ["lʲ"],
    "сь": ["sʲ"],
    "зь": ["zʲ"],
    "ц": ["ts"],          # can be palatalized in some contexts
    "щ": ["ʃtʃ"],         # trigraph pronunciation

    # digits in Ukrainian IPA
    "0": ["nʲolʲ"],        # нуль
    "1": ["odˈnʲinɑ"],     # один
    "2": ["dvi"],           # два
    "3": ["tri"],           # три
    "4": ["tʃotɪrʲi"],    # чотири
    "5": ["pʲjatʲ"],       # п’ять
    "6": ["ʃistʲ"],        # шість
    "7": ["sʲim"],         # сім
    "8": ["vʲismʲ"],       # вісім
    "9": ["devʲʲjatʲ"],    # дев’ять
}
RU_MAPPING = {
    **BASE_CYR,
    # single letters (lowercase)
    "а": ["a"],
    "б": ["b"],
    "в": ["v"],
    "г": ["ɡ"],
    "д": ["d"],
    "е": ["je", "e"],       # /je/ initial or after vowel/soft sign, /e/ after consonant
    "ё": ["jo"],             # stressed, otherwise often /o/ reduced
    "ж": ["ʐ"],
    "з": ["z"],
    "и": ["i"],
    "й": ["j"],              # palatal approximant
    "к": ["k"],
    "л": ["l", "ʎ"],        # soft l [ʎ] after palatalized consonants
    "м": ["m"],
    "н": ["n", "ɲ"],        # soft n [ɲ] after palatalized
    "о": ["o"],              # unstressed → [ɐ] in reduction
    "п": ["p"],
    "р": ["r"],              # trilled
    "с": ["s"],
    "т": ["t"],
    "у": ["u"],
    "ф": ["f"],
    "х": ["x"],              # velar fricative
    "ц": ["ts"],
    "ч": ["tʃ"],
    "ш": ["ʂ"],
    "щ": ["ɕː"],             # long soft fricative
    "ъ": [""],               # hard sign, no sound
    "ы": ["ɨ"],
    "ь": [""],               # soft sign, palatalizes preceding consonant
    "э": ["ɛ"],
    "ю": ["ju"],
    "я": ["ja"],

    # digraphs / palatalized consonants (explicit for fuzzy matching)
    "ья": ["ja"], "ье": ["je"], "ьи": ["ji"], "ьо": ["jo"], "ью": ["ju"],

    # common consonant + j sequences
    "дь": ["dʲ"], "ть": ["tʲ"], "нь": ["nʲ"], "ль": ["lʲ"], "сь": ["sʲ"],
    "зь": ["zʲ"], "чь": ["tʃʲ"], "шч": ["ʂtʃ"],

    # vowel reduction contexts (optional, can be simplified)
    "о́": ["o"], "е́": ["je"], "ё́": ["jo"], "у́": ["u"], "а́": ["a"], "и́": ["i"], "ы́": ["ɨ"], "э́": ["ɛ"], "ю́": ["ju"], "я́": ["ja"],

    # digits in Russian lexical IPA
    "0": ["ˈnʲulʲ"],       # ноль
    "1": ["ˈadʲin"],       # один
    "2": ["dva"],           # два
    "3": ["tri"],           # три
    "4": ["tʲetʲɪrʲɪ"],   # четыре
    "5": ["pʲɪtʲ"],        # пять
    "6": ["ʂɨstʲ"],        # шесть
    "7": ["sʲemʲ"],        # семь
    "8": ["vosʲimʲ"],      # восемь
    "9": ["dʲevʲitʲ"],     # девять
}

AR_MAPPING = {
    **BASE_AR,
    # Arabic letters (isolated forms)
    "ا": ["ɑ"],           # alif
    "أ": ["ʔɑ"],          # hamza on alif
    "إ": ["ʔɪ"],          # hamza under alif
    "آ": ["ʔɑː"],         # alif madda (long a)
    "ب": ["b"],
    "ت": ["t"],
    "ث": ["θ"],
    "ج": ["dʒ"],
    "ح": ["ħ"],
    "خ": ["x"],
    "د": ["d"],
    "ذ": ["ð"],
    "ر": ["r"],
    "ز": ["z"],
    "س": ["s"],
    "ش": ["ʃ"],
    "ص": ["sˤ"],
    "ض": ["dˤ"],
    "ط": ["tˤ"],
    "ظ": ["ðˤ"],
    "ع": ["ʕ"],
    "غ": ["ɣ"],
    "ف": ["f"],
    "ق": ["q"],
    "ك": ["k"],
    "ل": ["l"],
    "م": ["m"],
    "ن": ["n"],
    "ه": ["h"],
    "و": ["w", "u"],      # consonantal /w/ or vowel /u/
    "ي": ["j", "i"],      # consonantal /j/ or vowel /i/
    "ء": ["ʔ"],           # hamza
    "ى": ["ɑː"],          # alif maqsurah
    "ة": ["h", "t"],       # taa marbuta, /t/ in construct
    "ﻻ": ["lɑː"],          # lam-alif ligature

    # Short vowel diacritics (harakat)
    "َ": ["a"],   # fatha
    "ُ": ["u"],   # damma
    "ِ": ["i"],   # kasra
    "ً": ["an"],  # tanwin fatha
    "ٌ": ["un"],  # tanwin damma
    "ٍ": ["in"],  # tanwin kasra
    "ْ": [""],    # sukun (no vowel)
    "ّ": ["geminate"], # shadda, handled as doubling consonant

    # Common digraphs / trigraphs (loanword conventions)
    "sh": ["ʃ"],  # ش
    "th": ["θ"],  # ث
    "dh": ["ð"],  # ذ
    "kh": ["x"],  # خ
    "gh": ["ɣ"],  # غ
    "ṣ": ["sˤ"],  # ص
    "ḍ": ["dˤ"],  # ض
    "ṭ": ["tˤ"],  # ط
    "ẓ": ["ðˤ"],  # ظ
    "'": ["ʔ"],   # hamza

    # Long vowels
    "ا": ["ɑː"], # long a
    "و": ["uː"], # long u
    "ي": ["iː"], # long i

    # Numerals (Arabic lexical IPA)
    "0": ["sˤɪfr"],   # صفر
    "1": ["wɑːħɪd"], # واحد
    "2": ["ɪθnɑːn"], # اثنان
    "3": ["θalɑːθa"], # ثلاثة
    "4": ["ʔɑrbɑːʕa"], # أربعة
    "5": ["χɑmsa"],   # خمسة
    "6": ["sitta"],   # ستة
    "7": ["sˤɑbaʕa"], # سبعة
    "8": ["θamɑːnɪja"], # ثمانية
    "9": ["tisʕa"],   # تسعة

    # Context-sensitive / optional transliterations
    "al": ["ɑl"],     # definite article lam-alif prefix
}
FA_MAPPING = {
    **BASE_AR,
    # Consonants (isolated forms)
    "ا": ["ɑ"],  # alef, long a
    "ب": ["b"],
    "پ": ["p"],
    "ت": ["t"],
    "ث": ["s"],  # often merges with /s/
    "ج": ["dʒ"],
    "چ": ["tʃ"],
    "ح": ["h"],  # voiceless pharyngeal fricative, sometimes /h/
    "خ": ["x"],
    "د": ["d"],
    "ذ": ["z"],
    "ر": ["ɾ"],
    "ز": ["z"],
    "ژ": ["ʒ"],
    "س": ["s"],
    "ش": ["ʃ"],
    "ص": ["sˤ"],
    "ض": ["zˤ", "dˤ"],  # classical emphatics
    "ط": ["tˤ"],
    "ظ": ["zˤ"],
    "ع": ["ʔ", "ʕ"],  # glottal stop / voiced pharyngeal
    "غ": ["ɣ"],
    "ف": ["f"],
    "ق": ["ɣ", "q"],  # voiced uvular / velar approximant in modern Persian
    "ک": ["k"],
    "گ": ["ɡ"],
    "ل": ["l"],
    "م": ["m"],
    "ن": ["n"],
    "و": ["v", "u", "o"],  # consonantal /v/, vowel /u/ or /o/
    "ه": ["h"],
    "ی": ["j", "i"],  # consonantal /j/, vowel /i/

    # Short vowels (diacritics)
    "َ": ["æ"],  # fatha / a
    "ِ": ["e"],  # kasra / e
    "ُ": ["o"],  # damma / u
    "ً": ["ɑ̃"],  # tanwin a, rare in Persian
    "ٌ": ["ũ"],  # tanwin u, rare
    "ٍ": ["ẽ"],  # tanwin i, rare
    "ّ": [""],  # tashdid (gemination, handled in context)
    "ْ": [""],  # sukun (no vowel)

    # Common digraphs / trigraphs (modern usage)
    "چه": ["tʃe"],
    "خه": ["xe"],
    "شی": ["ʃi"],
    "ای": ["iː"],
    "او": ["uː"],
    "اوو": ["uː"],  # for elongation
    "می": ["mi"],  # prefix for present tense
    "نا": ["nɑ"],  # negative prefix
    "پر": ["pæɾ"],  # common word-internal cluster

    # Loanword or frequent trigraphs
    "تس": ["ts"],  # loanwords
    "تچ": ["tʃ"],  # loanwords
    "پژ": ["pʒ"],  # loanwords
    "ژو": ["ʒu"],  # e.g., ژوئیه (July)

    # Common suffixes / prefixes (treated as sequences)
    "ها": ["hɑ"],  # plural marker
    "تر": ["tæɾ"],  # comparative
    "ترین": ["tæɾin"],  # superlative
    "ان": ["ɑn"],  # plural or collective
    "یی": ["ji"],  # possessive or adjective-forming

    # Digits (Persian / Farsi numerals)
    "۰": ["seɾo"],  # 0
    "۱": ["jek"],  # 1
    "۲": ["do"],  # 2
    "۳": ["se"],  # 3
    "۴": ["tʃɑhɑr"],  # 4
    "۵": ["panʤ"],  # 5
    "۶": ["ʃeʃ"],  # 6
    "۷": ["hæft"],  # 7
    "۸": ["hæʃt"],  # 8
    "۹": ["nuh"],  # 9
}

HI_MAPPING = {
    **BASE_DEVAN,
    # Independent vowels
    "अ": ["ə"],       # short a
    "आ": ["aː"],      # long a
    "इ": ["ɪ"],       # short i
    "ई": ["iː"],      # long i
    "उ": ["ʊ"],       # short u
    "ऊ": ["uː"],      # long u
    "ऋ": ["ɾɪ"],      # vocalic r
    "ॠ": ["ɾiː"],     # long vocalic r
    "ए": ["eː"],      # long e
    "ऐ": ["ɛː"],      # ai
    "ओ": ["oː"],      # long o
    "औ": ["ɔː"],      # au
    "अं": ["ə̃"],      # anusvara
    "अः": ["h"],      # visarga
    "ँ": ["̃"],        # chandrabindu, nasalization

    # Consonants
    "क": ["k"], "ख": ["kʰ"], "ग": ["ɡ"], "घ": ["ɡʰ"], "ङ": ["ŋ"],
    "च": ["tʃ"], "छ": ["tʃʰ"], "ज": ["dʒ"], "झ": ["dʒʰ"], "ञ": ["ɲ"],
    "ट": ["ʈ"], "ठ": ["ʈʰ"], "ड": ["ɖ"], "ढ": ["ɖʰ"], "ण": ["ɳ"],
    "त": ["t̪"], "थ": ["t̪ʰ"], "द": ["d̪"], "ध": ["d̪ʰ"], "न": ["n̪"],
    "प": ["p"], "फ": ["pʰ"], "ब": ["b"], "भ": ["bʰ"], "म": ["m"],
    "य": ["j"], "र": ["ɾ"], "ल": ["l"], "व": ["ʋ"],
    "श": ["ʃ"], "ष": ["ʂ"], "स": ["s"], "ह": ["ɦ"],

    # Common conjuncts / trigraphs
    "क्ष": ["kʃ"],      # k + ṣa
    "त्र": ["t̪ɾ"],      # t + ra
    "ज्ञ": ["dʒɲ"],     # j + ña

    # Vowel diacritics (matras, attach to consonant)
    "ा": ["aː"],  # ā
    "ि": ["ɪ"],   # i (preposed)
    "ी": ["iː"],  # ī
    "ु": ["ʊ"],   # u
    "ू": ["uː"],  # ū
    "ृ": ["ɾɪ"],  # ṛ
    "ॄ": ["ɾiː"], # ṝ
    "े": ["eː"],  # e
    "ै": ["ɛː"],  # ai
    "ो": ["oː"],  # o
    "ौ": ["ɔː"],  # au
    "ं": ["̃"],    # anusvara
    "ः": ["h"],   # visarga

    # Halant / virama
    "्": [""],     # cancels inherent vowel

    # Digraph/trigraph consonant conjuncts (expandable list)
    "क्त": ["kt̪"],   # example: k + t
    "द्र": ["d̪ɾ"],  # d + r
    "स्त्र": ["st̪ɾ"], # s + t + r
    "ञ्ज": ["ɲdʒ"],  # common conjunct
    "श्र": ["ʃɾ"],   # sh + r
    "स्र": ["sɾ"],   # s + r
    "त्व": ["t̪ʋ"],  # t + v
    "क्र": ["kɾ"],   # k + r
    "त्र्य": ["t̪ɾj"], # extended trigraph

    # Digits in Hindi lexical IPA
    "0": ["ʃuːnɪj"],   # शून्य
    "1": ["ek"],        # एक
    "2": ["d̪o"],       # दो
    "3": ["t̪iːn"],     # तीन
    "4": ["t̪ʃɑːr"],    # चार
    "5": ["pə̃tʃ"],     # पाँच
    "6": ["ɡəː"],       # छह
    "7": ["sət̪"],      # सात
    "8": ["ɑːt̪ʃ"],     # आठ
    "9": ["nɔː"],       # नौ
}

KR_MAPPING = {
    # --- Consonants (Choseong/Initial + Jongseong/Final) ---
    # Plosives / Stops
    "ㄱ": ["k", "ɡ"],       # g/k initial; velar stop
    "ㄲ": ["k͈"],            # tense k
    "ㄴ": ["n"],
    "ㄷ": ["t", "d"],        # d/t initial; voicing varies
    "ㄸ": ["t͈"],            # tense t
    "ㄹ": ["ɾ", "l"],        # tap in onset, lateral in coda
    "ㅁ": ["m"],
    "ㅂ": ["p", "b"],
    "ㅃ": ["p͈"],            # tense p
    "ㅅ": ["s", "tɕ"],       # s → [tɕ] before i
    "ㅆ": ["s͈", "tɕ͈"],     # tense s
    "ㅇ": ["ŋ", ""],         # silent in onset, nasal in coda
    "ㅈ": ["tɕ", "dʑ"],      # affricate
    "ㅉ": ["tɕ͈"],           # tense affricate
    "ㅊ": ["tɕʰ"],           # aspirated affricate
    "ㅋ": ["kʰ"],            # aspirated
    "ㅌ": ["tʰ"],
    "ㅍ": ["pʰ"],
    "ㅎ": ["h", "ɦ"],        # h/voiced fricative depending on context

    # --- Vowels (Jungseong / Medials) ---
    "ㅏ": ["a"],
    "ㅐ": ["ɛ"],
    "ㅑ": ["ja"],
    "ㅒ": ["jɛ"],
    "ㅓ": ["ʌ"],
    "ㅔ": ["e"],
    "ㅕ": ["jʌ"],
    "ㅖ": ["je"],
    "ㅗ": ["o"],
    "ㅘ": ["wa"],
    "ㅙ": ["wɛ"],
    "ㅚ": ["ø", "we"],        # /ø/ or glide
    "ㅛ": ["jo"],
    "ㅜ": ["u"],
    "ㅝ": ["wʌ"],
    "ㅞ": ["we"],
    "ㅟ": ["y", "wi"],        # front rounded or glide
    "ㅠ": ["ju"],
    "ㅡ": ["ɯ"],
    "ㅢ": ["ɯi", "i"],       # can be realized as [i] in casual speech
    "ㅣ": ["i"],

    # --- Common final consonants (batchim / Jongseong) ---
    "ㄱᆨ": ["k"], "ㄲᆩ": ["k͈"], "ㄳ": ["ks"], "ㄴᆫ": ["n"], "ㄵ": ["ntɕ"], "ㄶ": ["nh"],
    "ㄷᆮ": ["t"], "ㄹᆯ": ["l"], "ㄺ": ["lk"], "ㄻ": ["lm"], "ㄼ": ["lb"], "ㄽ": ["ls"], "ㄾ": ["lt"], "ㄿ": ["lp"], "ㅀ": ["lh"],
    "ㅁᆷ": ["m"], "ㅂᆸ": ["p"], "ㅄ": ["ps"], "ㅅᆺ": ["t"], "ㅆᆻ": ["t͈"], "ㅇᆼ": ["ŋ"],
    "ㅈᆽ": ["tɕ"], "ㅊᆾ": ["tɕʰ"], "ㅋᆿ": ["kʰ"], "ㅌᆺ": ["tʰ"], "ㅍᇁ": ["pʰ"], "ㅎᇂ": ["h"],

    # --- Common digraph/trigraph effects ---
    # liaison effects (optional for fuzzy matching)
    "ㄱㄴ": ["ŋn"],  # example: syllable-final ㄱ + ㄴ onset
    "ㄹㄱ": ["lk"],  # coda + onset cluster
    "ㄹㄴ": ["ln"],
    "ㄹㅁ": ["lm"],
    "ㄹㅂ": ["lb"],

    # --- Digraphs / aspirated and tense consonants already included above ---
    # Include IPA variants for all contexts:
    # e.g., ㅂ → p/b; ㅍ → pʰ; ㅈ → tɕ/dʑ

    # --- Digraph vowels (already included in medial mapping above) ---
    # ㅘ, ㅙ, ㅚ, ㅝ, ㅞ, ㅟ, ㅢ, etc.

    # --- Digits (Korean numeric lexemes in IPA, Seoul dialect) ---
    "0": ["ɡʌŋ"],          # 영
    "1": ["ɪl"],           # 일
    "2": ["i"],            # 이
    "3": ["sam"],          # 삼
    "4": ["sa"],           # 사
    "5": ["o"],            # 오
    "6": ["juk"],          # 육
    "7": ["tɕʰil"],        # 칠
    "8": ["pʰal"],         # 팔
    "9": ["ku"],           # 구
}
JP_MAPPING = {
    # Hiragana - basic vowels
    "あ": ["a"], "い": ["i"], "う": ["ɯ"], "え": ["e"], "お": ["o"],
    # Hiragana - k-line
    "か": ["ka"], "き": ["ki"], "く": ["kɯ"], "け": ["ke"], "こ": ["ko"],
    "が": ["ɡa"], "ぎ": ["ɡi"], "ぐ": ["ɡɯ"], "げ": ["ɡe"], "ご": ["ɡo"],
    # Hiragana - s-line
    "さ": ["sa"], "し": ["ɕi"], "す": ["sɯ"], "せ": ["se"], "そ": ["so"],
    "ざ": ["za"], "じ": ["ʑi"], "ず": ["zɯ"], "ぜ": ["ze"], "ぞ": ["zo"],
    # Hiragana - t-line
    "た": ["ta"], "ち": ["tɕi"], "つ": ["tsɯ"], "て": ["te"], "と": ["to"],
    "だ": ["da"], "ぢ": ["dʑi"], "づ": ["dzɯ"], "で": ["de"], "ど": ["do"],
    # Hiragana - n-line
    "な": ["na"], "に": ["ɲi"], "ぬ": ["nɯ"], "ね": ["ne"], "の": ["no"],
    # Hiragana - h-line
    "は": ["ha"], "ひ": ["çi"], "ふ": ["ɸɯ"], "へ": ["he"], "ほ": ["ho"],
    "ば": ["ba"], "び": ["bi"], "ぶ": ["bɯ"], "べ": ["be"], "ぼ": ["bo"],
    "ぱ": ["pa"], "ぴ": ["pi"], "ぷ": ["pɯ"], "ぺ": ["pe"], "ぽ": ["po"],
    # Hiragana - m-line
    "ま": ["ma"], "み": ["mi"], "む": ["mɯ"], "め": ["me"], "も": ["mo"],
    # Hiragana - y-line
    "や": ["ja"], "ゆ": ["jɯ"], "よ": ["jo"],
    # Hiragana - r-line
    "ら": ["ɾa"], "り": ["ɾi"], "る": ["ɾɯ"], "れ": ["ɾe"], "ろ": ["ɾo"],
    # Hiragana - w-line
    "わ": ["wa"], "を": ["o"],   # particle pronounced [o]
    # Hiragana - nasal
    "ん": ["ɴ"],

    # Small kana (yōon) - used in digraphs/trigraphs
    "ゃ": ["ja"], "ゅ": ["jɯ"], "ょ": ["jo"],
    "ぁ": ["a"], "ぃ": ["i"], "ぅ": ["ɯ"], "ぇ": ["e"], "ぉ": ["o"],
    "っ": ["ː"],  # sokuon - geminate consonant marker, handled as doubling next consonant

    # Katakana - basic vowels
    "ア": ["a"], "イ": ["i"], "ウ": ["ɯ"], "エ": ["e"], "オ": ["o"],
    # Katakana - k-line
    "カ": ["ka"], "キ": ["ki"], "ク": ["kɯ"], "ケ": ["ke"], "コ": ["ko"],
    "ガ": ["ɡa"], "ギ": ["ɡi"], "グ": ["ɡɯ"], "ゲ": ["ɡe"], "ゴ": ["ɡo"],
    # Katakana - s-line
    "サ": ["sa"], "シ": ["ɕi"], "ス": ["sɯ"], "セ": ["se"], "ソ": ["so"],
    "ザ": ["za"], "ジ": ["ʑi"], "ズ": ["zɯ"], "ゼ": ["ze"], "ゾ": ["zo"],
    # Katakana - t-line
    "タ": ["ta"], "チ": ["tɕi"], "ツ": ["tsɯ"], "テ": ["te"], "ト": ["to"],
    "ダ": ["da"], "ヂ": ["dʑi"], "ヅ": ["dzɯ"], "デ": ["de"], "ド": ["do"],
    # Katakana - n-line
    "ナ": ["na"], "ニ": ["ɲi"], "ヌ": ["nɯ"], "ネ": ["ne"], "ノ": ["no"],
    # Katakana - h-line
    "ハ": ["ha"], "ヒ": ["çi"], "フ": ["ɸɯ"], "ヘ": ["he"], "ホ": ["ho"],
    "バ": ["ba"], "ビ": ["bi"], "ブ": ["bɯ"], "ベ": ["be"], "ボ": ["bo"],
    "パ": ["pa"], "ピ": ["pi"], "プ": ["pɯ"], "ペ": ["pe"], "ポ": ["po"],
    # Katakana - m-line
    "マ": ["ma"], "ミ": ["mi"], "ム": ["mɯ"], "メ": ["me"], "モ": ["mo"],
    # Katakana - y-line
    "ヤ": ["ja"], "ユ": ["jɯ"], "ヨ": ["jo"],
    # Katakana - r-line
    "ラ": ["ɾa"], "リ": ["ɾi"], "ル": ["ɾɯ"], "レ": ["ɾe"], "ロ": ["ɾo"],
    # Katakana - w-line
    "ワ": ["wa"], "ヲ": ["o"],   # particle
    # Katakana - nasal
    "ン": ["ɴ"],

    # Katakana small kana (yōon, vowel extensions)
    "ャ": ["ja"], "ュ": ["jɯ"], "ョ": ["jo"],
    "ァ": ["a"], "ィ": ["i"], "ゥ": ["ɯ"], "ェ": ["e"], "ォ": ["o"],
    "ッ": ["ː"],  # sokuon

    # Trigraphs/digraphs (yōon combinations) - common
    "きゃ": ["kʲa"], "きゅ": ["kʲɯ"], "きょ": ["kʲo"],
    "ぎゃ": ["ɡʲa"], "ぎゅ": ["ɡʲɯ"], "ぎょ": ["ɡʲo"],
    "しゃ": ["ɕa"], "しゅ": ["ɕɯ"], "しょ": ["ɕo"],
    "じゃ": ["ʑa"], "じゅ": ["ʑɯ"], "じょ": ["ʑo"],
    "ちゃ": ["tɕa"], "ちゅ": ["tɕɯ"], "ちょ": ["tɕo"],
    "にゃ": ["ɲa"], "にゅ": ["ɲɯ"], "にょ": ["ɲo"],
    "ひゃ": ["ça"], "ひゅ": ["çɯ"], "ひょ": ["ço"],
    "びゃ": ["bʲa"], "びゅ": ["bʲɯ"], "びょ": ["bʲo"],
    "ぴゃ": ["pʲa"], "ぴゅ": ["pʲɯ"], "ぴょ": ["pʲo"],
    "みゃ": ["mʲa"], "みゅ": ["mʲɯ"], "みょ": ["mʲo"],
    "りゃ": ["ɾʲa"], "りゅ": ["ɾʲɯ"], "りょ": ["ɾʲo"],

    # Prolonged sound marker (chōon) - Katakana long vowel
    "ー": ["ː"],

    # Digits - Japanese pronunciation
    "0": ["ɾeː"],      # zero / rei
    "1": ["iːtɕi"],    # ichi
    "2": ["ni"],        # ni
    "3": ["san"],       # san
    "4": ["ɕi", "yon"], # shi / yon
    "5": ["go"],        # go
    "6": ["ɾoku"],      # roku
    "7": ["ɕi.t͡ɕi", "nana"], # shichi / nana
    "8": ["ha.t͡ɕi"],   # hachi
    "9": ["kjuː"],      # kyū
}
ZH_MAPPING = {
    # pinyin pre-processing required

    # Initials (consonants)
    "b": ["p"], "p": ["pʰ"], "m": ["m"], "f": ["f"],
    "d": ["t"], "t": ["tʰ"], "n": ["n"], "l": ["l"],
    "g": ["k"], "k": ["kʰ"], "h": ["x"],
    "j": ["tɕ"], "q": ["tɕʰ"], "x": ["ɕ"],
    "zh": ["ʈʂ"], "ch": ["ʈʂʰ"], "sh": ["ʂ"], "r": ["ɻ"],
    "z": ["ts"], "c": ["tsʰ"], "s": ["s"],
    "y": ["j"], "w": ["w"],

    # Finals (vowels and vowel combinations)
    "a": ["a"], "o": ["o"], "e": ["ɤ", "ə"], "i": ["i"], "u": ["u"], "ü": ["y"],

    # Compound finals / common vowel combinations
    "ai": ["ai"], "ei": ["ei"], "ao": ["au"], "ou": ["ou"],
    "ia": ["ia"], "ie": ["ie"], "iao": ["iau"], "iou": ["iou"],  # iou is 'iu' in standard pinyin
    "ua": ["ua"], "uo": ["uɔ"], "uai": ["uai"], "ui": ["uei"],  # ui is 'uei'
    "üe": ["yɛ"], "üe": ["yɛ"], "iao": ["iau"], "iou": ["iou"],

    "an": ["an"], "en": ["ən"], "in": ["in"], "un": ["uən"], "ün": ["yn"],
    "ang": ["ɑŋ"], "eng": ["əŋ"], "ing": ["iŋ"], "ong": ["uŋ"], "iong": ["jʊŋ"],

    # Full trigraphs / finals for combined sounds
    "ian": ["i̯ɛn"], "uan": ["u̯an"], "üan": ["y̯an"],
    "iang": ["i̯ɑŋ"], "uang": ["u̯ɑŋ"],
    "ueng": ["u̯əŋ"],  # rare, only in some dialectal or loan syllables

    # Special finals (erhua)
    "er": ["ɑɻ"],

    # Tones - optional IPA marks
    "ā": ["a˥"], "á": ["a˧˥"], "ǎ": ["a˨˦"], "à": ["a˥˩"],
    "ē": ["ə˥"], "é": ["ə˧˥"], "ě": ["ə˨˦"], "è": ["ə˥˩"],
    "ī": ["i˥"], "í": ["i˧˥"], "ǐ": ["i˨˦"], "ì": ["i˥˩"],
    "ō": ["o˥"], "ó": ["o˧˥"], "ǒ": ["o˨˦"], "ò": ["o˥˩"],
    "ū": ["u˥"], "ú": ["u˧˥"], "ǔ": ["u˨˦"], "ù": ["u˥˩"],
    "ǖ": ["y˥"], "ǘ": ["y˧˥"], "ǚ": ["y˨˦"], "ǜ": ["y˥˩"],

    # Digits - Mandarin Chinese lexical IPA
    "0": ["lɪŋ"], "1": ["i˥"], "2": ["ɑɹ˧˥"], "3": ["san˥˩"], "4": ["sɨ˥˩"],
    "5": ["u˨˦"], "6": ["liu˨˦"], "7": ["tʂʰi˥"], "8": ["pa˥"], "9": ["tɕjɔʊ˨˦"],

    # Single characters (simplified, common examples)
    # Note: only a subset shown; full coverage requires a dictionary or database (CC-CEDICT or Unihan)
    "你": ["ni˧˥"],  # nǐ
    "好": ["xaʊ˧˥"],  # hǎo
    "我": ["wo˨˩˦"],  # wǒ
    "是": ["ʂɨ˥˩"],  # shì
    "的": ["tə˙"],  # de (neutral tone)
    "了": ["lɛ˦˨"],  # le / liǎo (context-dependent)
    "不": ["pu˥˩"],  # bù
    "在": ["tsai˥˧"],  # zài
    "人": ["ʐən˧˥"],  # rén
    "有": ["joʊ˨˩˦"],  # yǒu
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

    ffs = PhoneticFuzzySearch(EN_MAPPING, use_eudex=True)

    # Add terms
    ffs.add_term('hello world', 0)
    ffs.add_term('hello friend', 1)
    ffs.add_term('goodbye world', 2)
    ffs.add_term('greetings', 3)
    ffs.add_term('friendship', 4)
    ffs.add_term('yellow world', 5)
    ffs.add_term('hello carl', 6)
    ffs.add_term('yellow curl', 7)

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
