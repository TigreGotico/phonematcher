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
# Phone mapping - LLM Generated
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
NL_MAPPING = {
    # Consonants
    "b": ["b"],
    "d": ["d"],
    "g": ["ɣ"],        # Dutch voiced velar fricative
    "h": ["h"],
    "j": ["j"],
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "p": ["p"],
    "r": ["r"],
    "s": ["s"],
    "t": ["t"],
    "v": ["v"],
    "w": ["ʋ"],        # Dutch approximant
    "z": ["z"],
    "ch": ["x"],       # Dutch voiceless velar fricative
    "sch": ["sx"],     # Dutch "sch" pronounced [sx]
    "sj": ["ʃ"],       # Dutch "sj" as in loanwords
    "tsj": ["tʃ"],     # Dutch "tsj" as in "tsja"
    "f": ["f"],

    # Vowels
    "a": ["ɑ"],        # short 'a' as in 'kat'
    "aa": ["aː"],      # long 'aa' as in 'maan'
    "e": ["ɛ"],        # short 'e' as in 'pet'
    "ee": ["eː"],      # long 'ee' as in 'been'
    "i": ["ɪ"],        # short 'i' as in 'vis'
    "ie": ["iː"],      # long 'ie' as in 'fiet'
    "o": ["ɔ"],        # short 'o' as in 'pot'
    "oo": ["oː"],      # long 'oo' as in 'boom'
    "u": ["ʏ"],        # short 'u' as in 'put'
    "uu": ["yː"],      # long 'uu' as in 'muur'
    "ei": ["ɛi"],      # as in 'meid'
    "ij": ["ɛi"],      # same as 'ei'
    "ai": ["ɛi"],      # less common, same diphthong
    "au": ["ɑu"],      # as in 'mauw'
    "ou": ["ɑu"],      # as in 'koud'
    "eu": ["øː"],      # as in 'neus'
    "ui": ["œy"],      # as in 'huis'
    "oe": ["u"],       # as in 'boek'
    "ieuw": ["iu"],    # as in 'nieuw'
    "ieu": ["iu"],     # variant

    # Other vowel combos
    "aai": ["aːi"],    # as in 'paai'
    "ooi": ["oːi"],    # as in 'kooi'
    "aou": ["ɑu"],     # uncommon

    # Suffixes
    "ng": ["ŋ"],
    "nk": ["ŋk"],
}
DE_MAPPING = {
    # Consonants
    "b": ["b"],
    "d": ["d"],
    "g": ["ɡ"],
    "j": ["j"],      # "ja" = /ja/
    "v": ["f", "v"], # "vater" = /f/, "von" = /f/ or /v/ depending
    "w": ["v"],      # German 'w' pronounced like English 'v'
    "z": ["ts"],     # "zeit" = /tsaɪt/
    "s": ["z", "s"], # word-initial 's' /z/, otherwise /s/
    "ß": ["s"],       # sharp S
    "c": ["k", "ts"], # usually 'c' = /k/, 'ce' /tsɛ/
    "ch": ["x", "ç"], # 'ach' /ax/, 'ich' /iç/
    "sch": ["ʃ"],    # 'schön' /ʃøːn/
    "sp": ["ʃp"],    # word-initial
    "st": ["ʃt"],    # word-initial
    "pf": ["pf"],    # 'Pferd' /pferd/
    "th": ["t"],     # archaic; mostly /t/
    "r": ["r"],      # alveolar/trilled
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "ng": ["ŋ"],
    "h": ["h"],
    "x": ["ks"],

    # Vowels
    "a": ["a"],        # short /a/ as in "Mann"
    "aa": ["aː"],      # long /aː/ as in "Saat"
    "ä": ["ɛ"],        # short /ɛ/ as in "Mädchen"
    "äh": ["eː"],      # long /eː/ as in "ähnlich"
    "e": ["ɛ"],        # short /ɛ/ as in "Bett"
    "ee": ["eː"],      # long /eː/ as in "Seele"
    "i": ["ɪ"],        # short /ɪ/ as in "mit"
    "ie": ["iː"],      # long /iː/ as in "Liebe"
    "o": ["ɔ"],        # short /ɔ/ as in "Sonne"
    "oo": ["oː"],      # long /oː/ as in "Boot"
    "u": ["ʊ"],        # short /ʊ/ as in "Mutter"
    "uu": ["uː"],      # long /uː/ as in "Schule"
    "ü": ["y"],        # short /y/ as in "Müll"
    "üh": ["yː"],      # long /yː/ as in "fühlen"
    "ö": ["ø"],        # short /ø/ as in "schön"
    "öh": ["øː"],      # long /øː/ as in "Höhle"
    "au": ["aʊ"],      # diphthong
    "ei": ["aɪ"],      # diphthong
    "ai": ["aɪ"],      # diphthong
    "eu": ["ɔʏ"],      # diphthong
    "äu": ["ɔʏ"],      # diphthong
    "ou": ["oʊ"],      # loanwords
    "oi": ["ɔɪ"],      # rare loanwords

    # Special endings
    "er": ["ɐ"],       # unstressed /ɐ/
    "el": ["əl"],      # unstressed /əl/
    "en": ["ən"],      # unstressed /ən/
}
DA_MAPPING = {
    # Consonants
    "b": ["b"],
    "d": ["d", "ð"],  # soft /d/ often realized as /ð/ medially
    "g": ["ɡ", "ɡ̊"],  # sometimes devoiced at word-end
    "j": ["j"],  # /j/ as in "ja"
    "f": ["f", "v"],  # final /v/ in some positions
    "h": ["h"],
    "k": ["k", "g̊"],  # /g̊/ for soft /g/ sometimes
    "p": ["p"],
    "r": ["r", "ɐ˞"],  # alveolar/trilled or uvular
    "s": ["s", "z"],  # voiced between vowels
    "t": ["t"],
    "v": ["v", "f"],  # sometimes devoiced
    "w": ["v"],  # borrowed words
    "z": ["s", "z"],  # mostly in loanwords
    "c": ["k", "s"],  # depending on word
    "x": ["ks"],
    "q": ["k"],
    "ng": ["ŋ"],
    "ch": ["k", "tʃ"],  # borrowed
    "th": ["t", "θ"],  # borrowed words

    # Common vowel letters
    "a": ["ɑ", "æ"],  # short/long variation
    "aa": ["ɔ"],  # modern /å/
    "e": ["ɛ", "ə", "e"],  # varies by position
    "i": ["i", "ɪ"],
    "o": ["ɔ", "o", "u"],
    "u": ["u", "ʉ", "y"],  # front rounded in some contexts
    "y": ["y", "ʏ"],
    "æ": ["ɛ"],
    "ø": ["ø", "œ"],
    "å": ["ɔ", "ɒ"],

    # Digraphs / vowel combinations
    "au": ["ɔu"],
    "ei": ["ai", "ɛi"],
    "oi": ["ɔi"],
    "ai": ["ɛi"],
    "øy": ["øy"],
    "ou": ["au"],
    "ie": ["iə"],  # borrowed words
    "ei": ["ai"],
    "au": ["ɔu"],

    # Silent letters / specific endings
    "e": ["ə"],  # often unstressed final 'e'
    "r": ["ɐ˞", "r"],  # soft /r/
    "ld": ["l"],  # final 'd' often silent
    "nd": ["n"],  # final 'd' often silent
    "st": ["sd"],  # assimilated cluster
    "rt": ["ɐ˞t"],  # common realization

    # Loanwords / borrowed spellings
    "ph": ["f"],
    "th": ["t", "θ"],
    "sh": ["ʃ"],
    "ch": ["tʃ", "k"],

    # Word endings
    "er": ["ɐ"],  # common in weak endings
    "en": ["ən"],  # definite ending or weak syllable
    "et": ["ət"],  # definite neuter ending
    "te": ["tə"],  # past tense ending

    # Others
    "ou": ["au"],
    "oo": ["u"],
    "øy": ["øy"],
}
NO_MAPPING = {
    "b": ["b"],
    "d": ["d"],
    "g": ["ɡ", "j"],  # g soft / hard
    "j": ["j"],
    "f": ["f"],
    "h": ["h"],
    "y": ["y"],
    "c": ["k", "s"],  # loanwords
    "k": ["k"],
    "q": ["k"],
    "ck": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "ng": ["ŋ"],
    "p": ["p"],
    "r": ["r"],  # alveolar trill
    "s": ["s"],
    "sj": ["ʃ"],  # sj-sound
    "skj": ["ʃ"],
    "tj": ["tʃ"],  # t + j clusters
    "t": ["t"],
    "v": ["v"],
    "w": ["v"],  # often pronounced like 'v'
    "x": ["ks"],
    "z": ["s"],
    "æ": ["æ"],
    "ø": ["ø"],
    "å": ["oː"],
    "a": ["ɑ", "aː"],
    "e": ["e", "ɛ"],
    "i": ["i"],
    "o": ["u", "oː"],
    "u": ["ʉ", "uː"],
    "au": ["ɔu"],
    "ei": ["æi"],
    "øy": ["øy"],
    "ei": ["ei"],
    "ie": ["iə"],
    "ai": ["ɑi"],
    "øy": ["øi"],
    "ei": ["ei"],
    "y": ["y"],
    "øy": ["øy"],
    "å": ["oː"],
    "ar": ["ɑr"],
    "or": ["oːr"],
    "er": ["ɛr"],
    "ir": ["ir"],
    "ur": ["ʉr"],
    "år": ["oːr"],
    "eir": ["eir"],
    "eir": ["eːr"],
    "en": ["ɛn"],
    "el": ["ɛl"],
    "om": ["ɔm"],
    "on": ["ɔn"],
    "un": ["ʉn"],
    "in": ["in"],
    "inn": ["in"],
    "ett": ["et"],
    "ikk": ["ik"],
    # common consonant clusters
    "sk": ["sk"],
    "sp": ["sp"],
    "st": ["st"],
    "tr": ["tr"],
    "dr": ["dr"],
    "kr": ["kr"],
}
SV_MAPPING = {
    # Consonants
    "b": ["b"],
    "d": ["d"],
    "g": ["ɡ", "ɡj"],      # g hard/soft
    "j": ["j"],             # y-sound /j/
    "f": ["f"],
    "h": ["h"],
    "k": ["k", "ɕ"],        # k before front vowels -> /ɕ/
    "ck": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n", "ŋ"],        # ng
    "ng": ["ŋ"],
    "p": ["p"],
    "r": ["r"],             # rolled or tapped
    "s": ["s"],
    "sj": ["ɧ"],            # sj-sound
    "sk": ["ɧ"],            # before front vowels
    "stj": ["ɧ"],
    "tj": ["ɕ"],            # tj-sound
    "t": ["t"],
    "v": ["v"],
    "w": ["v"],             # Swedish often pronounces w as v
    "z": ["s"],             # z pronounced as s
    "x": ["ks"],
    # Vowels
    "a": ["ɑ", "aː"],       # short vs long
    "å": ["oː"],            # long o
    "ä": ["ɛ", "ɛː"],       # short/long e
    "e": ["ɛ", "eː"],       # short/long e
    "i": ["ɪ", "iː"],
    "o": ["ɔ", "uː"],       # o short/long
    "ö": ["ø", "øː"],
    "u": ["ʉ", "ʉː"],
    "y": ["y", "yː"],
    "ei": ["eːi"],
    "eu": ["øːu"],
    "au": ["ʊ"],            # rare diphthong
    "oi": ["ɔɪ"],
    # Common suffixes and clusters
    "ar": ["ɑr"],           # e.g., "klar"
    "er": ["ɛr"],           # e.g., "katter"
    "or": ["uːr"],          # e.g., "stor"
    "ur": ["ʉr"],
    "ir": ["ɪr"],
    "ör": ["øːr"],
    "åre": ["oːrɛ"],        # specific endings
    "ie": ["iːɛ"],           # e.g., "serie"
    "tion": ["ʃɔn"],        # loanwords from English/French
    "skj": ["ɧ"],
    "tj": ["ɕ"],
    "dj": ["ɟ"],            # some loanwords
    # Diphthongs / common vowel combos
    "ai": ["aɪ"],           # rare
    "ay": ["aɪ"],
    "ey": ["eːy"],
    "au": ["ɔu"],
    "ou": ["uː"],
    "oi": ["ɔɪ"],
    # Special sequences
    "ch": ["ɧ"],             # often in loanwords
    "ph": ["f"],             # loanwords
    "sh": ["ɧ"],             # loanwords
}

PT_MAPPING = {
    # Consonants
    "b": ["b"],
    "c": ["k"],          # default hard; soft c handled via "ce", "ci"
    "ç": ["s"],          # cedilla
    "d": ["d"],
    "f": ["f"],
    "g": ["ɡ"],          # hard g; soft g handled below
    "h": [""],           # silent in BP
    "j": ["ʒ"],          # e.g., "jogo"
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "p": ["p"],
    "q": ["k"],
    "r": ["ʁ"],          # initial R or after consonant
    "rr": ["ʁ"],         # strong R between vowels
    "s": ["s"],          # default S; soft S handled below
    "ss": ["s"],         # unvoiced S
    "v": ["v"],
    "w": ["w"],
    "x": ["ʃ"],          # default for 'x' at start, middle: see exceptions
    "z": ["z"],

    # Soft consonants / digraphs
    "ch": ["ʃ"],         # chocolate
    "lh": ["ʎ"],         # palatal L
    "nh": ["ɲ"],         # palatal N
    "gu": ["ɡ"],         # before 'a','o','u'; silent before 'e','i'
    "qu": ["k"],         # before 'e','i'

    # Vowels (oral)
    "a": ["a"],
    "e": ["e", "ɛ"],      # 'e' can be closed/open
    "é": ["e"],           # stressed
    "ê": ["ɛ"],           # closed
    "i": ["i"],
    "o": ["o", "ɔ"],      # closed/open
    "ó": ["o"],
    "ô": ["ɔ"],
    "u": ["u"],

    # Vowels (nasal)
    "ã": ["ɐ̃"],
    "ão": ["ɐ̃w̃"],
    "õe": ["õj̃e"],
    "em": ["ẽ"],          # nasalized e before m/n at end of syllable
    "en": ["ẽ"],
    "im": ["ĩ"],
    "in": ["ĩ"],
    "om": ["õ"],
    "on": ["õ"],

    # Diphthongs
    "ai": ["ai"],
    "ei": ["ei"],
    "oi": ["oi"],
    "ui": ["ui"],
    "au": ["aw"],
    "ou": ["ow"],

    # Common combinations / suffixes
    "sc": ["s"],          # before 'e','i'
    "sç": ["s"],
    "gue": ["ɡe"],        # soft e
    "gui": ["ɡi"],
    "ge": ["ʒe"],         # soft g
    "gi": ["ʒi"],
}
GL_MAPPING = {
    # Consonants
    "b": ["b"],
    "v": ["b", "v"],  # Galician v is often pronounced like b
    "c": ["k", "s"],  # c before e/i is /s/, else /k/
    "ç": ["s"],       # sometimes used historically
    "ch": ["tʃ"],     # loanwords
    "d": ["d"],
    "f": ["f"],
    "g": ["ɡ", "ɣ"],  # g before e/i: /ʒ/ in some regions
    "gu": ["ɡ"],      # before e/i to keep hard g
    "h": [],          # silent in Galician
    "j": ["ʒ"],       # borrowed words
    "l": ["l", "ʎ"],  # l and palatalized ll
    "m": ["m"],
    "n": ["n", "ɲ"],  # n and palatalized ñ
    "ñ": ["ɲ"],
    "ng": ["ŋ"],      # mostly in loanwords
    "p": ["p"],
    "q": ["k"],       # always followed by u
    "r": ["ɾ", "r"],  # single vs trilled
    "s": ["s", "z"],  # voicing intervocalic
    "t": ["t"],
    "x": ["ʃ", "ks"], # x pronounced /ʃ/ or /ks/ depending on position
    "z": ["θ"],        # in some areas; often /s/
    "lh": ["ʎ"],       # palatal lateral
    "nh": ["ɲ"],       # palatal nasal

    # Vowels
    "a": ["a"],
    "á": ["a"],
    "e": ["ɛ", "e"],
    "é": ["ɛ"],
    "i": ["i"],
    "í": ["i"],
    "o": ["o", "ɔ"],
    "ó": ["o"],
    "u": ["u"],
    "ú": ["u"],

    # Common vowel combinations
    "ai": ["aj"],  # ai diphthong
    "ei": ["ej"],
    "oi": ["oj"],
    "au": ["aw"],
    "ou": ["ow"],

    # Common endings / sequences
    "ar": ["ar"],
    "er": ["ɛr"],
    "ir": ["ir"],
    "ur": ["ur"],
    "or": ["or"],
    "as": ["as"],
    "es": ["es"],
    "os": ["os"],
    "is": ["is"],

    # Others / loanwords
    "ph": ["f"],
    "th": ["t"],     # usually simplified
    "wh": ["w"],     # rare
}
ES_MAPPING = {
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
CA_MAPPING = {
    # Consonants
    "b": ["b"],
    "v": ["v"],  # /v/ or /b/ depending on context, simplified as /v/
    "c": ["k"],  # hard c
    "ç": ["s"],  # c cedilla
    "d": ["d"],
    "g": ["ɡ", "ʒ"],  # /ɡ/ before a, o, u; /ʒ/ before e, i
    "j": ["ʒ"],
    "ll": ["ʎ"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "ny": ["ɲ"],
    "p": ["p"],
    "q": ["k"],
    "r": ["r"],  # tapped /r/
    "rr": ["r"],  # trilled /r/
    "s": ["s"],
    "ss": ["s"],
    "t": ["t"],
    "x": ["ʃ", "ks"],  # /ʃ/ or /ks/ depending on context
    "z": ["z"],  # used rarely
    "f": ["f"],
    "h": [],  # silent
    "ch": ["tʃ"],  # borrowed words
    "gu": ["ɡ"],  # hard g before e, i (silent u)
    "gü": ["ɡw"],  # explicit u
    "qu": ["k"],  # hard q
    "w": ["w"],  # foreign
    # Vowels
    "a": ["a"],
    "à": ["a"],
    "e": ["ə", "ɛ"],  # unstressed /ə/, stressed /ɛ/
    "é": ["ɛ"],
    "è": ["ɛ"],
    "i": ["i"],
    "í": ["i"],
    "o": ["ɔ", "o"],  # stressed /ɔ/, unstressed /o/
    "ó": ["o"],
    "ò": ["ɔ"],
    "u": ["u"],
    "ú": ["u"],
    "ü": ["y"],  # front rounded
    # Diphthongs and common vowel combinations
    "ai": ["aj"],
    "au": ["aw"],
    "ei": ["ej"],
    "eu": ["ew"],
    "oi": ["oj"],
    "ou": ["ow"],
    "ia": ["ja"],
    "ie": ["je"],
    "io": ["jo"],
    "iu": ["ju"],
    "ua": ["wa"],
    "ue": ["we"],
    "ui": ["wi"],
    "uo": ["wo"],
    "uy": ["wi"],  # rare
    # Common endings
    "ig": ["tʃ"],  # final ig pronounced /tʃ/ in Catalan
    "rt": ["rt"],
    "nt": ["nt"],
    "ct": ["kt"],
    "sc": ["s"],  # before e, i
}
FR_MAPPING = {
    # Consonants
    "b": ["b"],
    "c": ["k"],          # default hard c
    "ç": ["s"],          # soft c
    "d": ["d"],
    "f": ["f"],
    "g": ["ɡ"],          # default hard g
    "gu": ["ɡ"],         # hard g before e/i
    "j": ["ʒ"],
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "p": ["p"],
    "q": ["k"],
    "r": ["ʁ"],
    "s": ["s"],
    "t": ["t"],
    "v": ["v"],
    "w": ["w"],
    "x": ["ks", "gz"],    # depending on context
    "y": ["j", "i"],      # sometimes consonant j or vowel i
    "z": ["z"],

    # Digraphs / special consonants
    "ch": ["ʃ"],
    "gn": ["ɲ"],
    "ph": ["f"],
    "th": ["t"],          # French 'th' is usually just 't'
    "qu": ["k"],

    # Vowels
    "a": ["a"],
    "à": ["a"],
    "â": ["ɑ"],
    "e": ["ə", "ɛ"],      # schwa or open e
    "é": ["e"],
    "è": ["ɛ"],
    "ê": ["ɛ"],
    "ë": ["ə"],
    "i": ["i"],
    "î": ["i"],
    "ï": ["i"],
    "o": ["o", "ɔ"],
    "ô": ["o"],
    "u": ["y"],
    "ù": ["y"],
    "û": ["y"],
    "ü": ["y"],

    # Nasal vowels
    "an": ["ɑ̃"],
    "en": ["ɑ̃"],
    "in": ["ɛ̃"],
    "ain": ["ɛ̃"],
    "aim": ["ɛ̃"],
    "on": ["ɔ̃"],
    "om": ["ɔ̃"],
    "un": ["œ̃"],
    "um": ["œ̃"],

    # Diphthongs / vowel combinations
    "ai": ["ɛ"],
    "au": ["o"],
    "eau": ["o"],
    "eu": ["ø", "œ"],
    "ou": ["u"],
    "oi": ["wa"],
    "oy": ["wa"],

    # Endings
    "ent": ["ɑ̃"],  # silent in many verbs except 3rd person plural
    "er": ["e"],    # infinitive verbs
    "ez": ["e"],    # imperative / 2nd person
    "es": ["ɛ"],    # plural or 2nd person singular
    "et": ["ɛ"],
    "ette": ["ɛt"],

    # Misc
    "le": ["lə", "l"],  # depending on position
    "la": ["la"],
    "les": ["le", "lez"],
    "des": ["de", "dez"],
}
IT_MAPPING = {
    # Consonants
    "b": ["b"],
    "c": ["k"],           # default hard 'c'
    "ch": ["k"],          # always hard 'c' before e/i
    "ci": ["tʃ"],         # soft 'c' before i
    "ce": ["tʃ"],         # soft 'c' before e
    "d": ["d"],
    "f": ["f"],
    "g": ["ɡ"],           # hard 'g' default
    "gh": ["ɡ"],          # hard 'g' before e/i
    "gi": ["dʒ"],         # soft 'g' before i
    "ge": ["dʒ"],         # soft 'g' before e
    "h": [""],            # silent in Italian
    "l": ["l"],
    "gl": ["ɡl"],         # 'gli' simplified; see below
    "gli": ["ʎ"],         # palatal lateral
    "m": ["m"],
    "n": ["n"],
    "gn": ["ɲ"],          # palatal nasal
    "p": ["p"],
    "q": ["k"],           # always followed by 'u'
    "qu": ["kw"],         # 'qu' sequence
    "r": ["r"],           # trilled
    "s": ["s"],           # default voiceless
    "z": ["ts", "dz"],    # Italian 'z' can be voiced or voiceless

    # Vowels
    "a": ["a"],
    "e": ["e", "ɛ"],      # closed/open e
    "i": ["i"],
    "o": ["o", "ɔ"],      # closed/open o
    "u": ["u"],

    # Vowel combinations / diphthongs
    "ai": ["ai"],
    "au": ["au"],
    "ei": ["ei"],
    "oi": ["oi"],
    "ia": ["ja"],
    "ie": ["je"],
    "io": ["jo"],
    "iu": ["ju"],
    "ua": ["wa"],
    "ue": ["we"],
    "uo": ["wo"],
    "ui": ["wi"],

    # Special sequences
    "qu": ["kw"],
    "sc": ["ʃ"],          # 'sc' before e/i
    "sce": ["ʃe"],
    "sci": ["ʃi"],
    "sch": ["sk"],         # 'sch' before e/i
    "che": ["ke"],
    "chi": ["ki"],
    "gli": ["ʎ"],         # palatal lateral
    "gn": ["ɲ"],          # palatal nasal
    "ci": ["tʃ"],         # soft c
    "ce": ["tʃ"],         # soft c
    "ge": ["dʒ"],         # soft g
    "gi": ["dʒ"],         # soft g
}

EUS_MAPPING = {
    "a": ["a"],
    "b": ["b"],
    "d": ["d"],
    "e": ["e"],
    "f": ["f"],
    "g": ["ɡ"],
    "h": ["h"],
    "i": ["i"],
    "j": ["ʝ"],      # j in Basque is like Spanish "y"
    "k": ["k"],
    "l": ["l"],
    "m": ["m"],
    "n": ["n"],
    "ñ": ["ɲ"],      # nasal palatal
    "o": ["o"],
    "p": ["p"],
    "r": ["r"],      # trilled
    "rr": ["r"],     # long trill
    "s": ["s"],
    "t": ["t"],
    "u": ["u"],
    "x": ["ʃ"],      # Basque x is like English "sh"
    "z": ["s"],      # z in Basque is /s/ in the north, /θ/ in some dialects
    "tz": ["ts"],    # affricate
    "tx": ["tʃ"],    # affricate like English "ch"
    "ts": ["ts"],
    "dɡ": ["dʒ"],    # less common, mostly loanwords
    "ll": ["ʎ"],     # palatal lateral
    "ai": ["ai"],
    "ei": ["ei"],
    "oi": ["oi"],
    "au": ["au"],
    "eu": ["eu"],
    "ia": ["ia"],
    "ie": ["ie"],
    "io": ["io"],
    "iu": ["iu"],
    "ua": ["ua"],
    "ue": ["ue"],
    "uo": ["uo"],
    "ui": ["ui"],
}

AR_MAPPING = {
    # Consonants
    "ا": ["ɑ"],       # Alif (long a)
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
    "و": ["w", "u"],  # Consonant or long vowel
    "ي": ["j", "i"],  # Consonant or long vowel

    # Hamza and glottal stop
    "ء": ["ʔ"],
    "ئ": ["ʔi"],
    "ؤ": ["ʔu"],

    # Short vowels
    "َ": ["a"],   # Fatha
    "ُ": ["u"],   # Damma
    "ِ": ["i"],   # Kasra

    # Long vowels (already covered by Alif, Waw, Ya)
    "ى": ["ɑ"],   # Alif Maqsura

    # Tanween (final vowels with 'n')
    "ً": ["an"],
    "ٌ": ["un"],
    "ٍ": ["in"],

    # Shadda (gemination) – handled as double consonant
    "ّ": [],

    # Sukun (no vowel)
    "ْ": [],

    # Common combinations / digraphs
    "ال": ["al"],   # Definite article
    "لا": ["la"],   # Lam-Alef ligature
}
HI_MAPPING = {
    # Vowels
    "a": ["ə"],       # अ
    "aa": ["ɑ"],      # आ
    "i": ["i"],       # इ
    "ii": ["iː"],     # ई
    "u": ["u"],       # उ
    "uu": ["uː"],     # ऊ
    "e": ["eː"],      # ए
    "ai": ["ɛː"],     # ऐ
    "o": ["oː"],      # ओ
    "au": ["ɔː"],     # औ

    # Consonants (basic)
    "k": ["k"],       # क
    "kh": ["kʰ"],     # ख
    "g": ["ɡ"],       # ग
    "gh": ["ɡʰ"],     # घ
    "ng": ["ŋ"],      # ङ

    "c": ["tʃ"],      # च
    "ch": ["tʃʰ"],    # छ
    "j": ["dʒ"],      # ज
    "jh": ["dʒʰ"],    # झ
    "ny": ["ɲ"],      # ञ

    "t": ["ʈ"],       # ट
    "th": ["ʈʰ"],     # ठ
    "d": ["ɖ"],       # ड
    "dh": ["ɖʰ"],     # ढ
    "n": ["ɳ"],       # ण

    "t2": ["t"],      # त
    "th2": ["tʰ"],    # थ
    "d2": ["d"],      # द
    "dh2": ["dʰ"],    # ध
    "n2": ["n"],      # न

    "p": ["p"],       # प
    "ph": ["pʰ"],     # फ
    "b": ["b"],       # ब
    "bh": ["bʰ"],     # भ
    "m": ["m"],       # म

    "y": ["j"],       # य
    "r": ["r"],       # र
    "l": ["l"],       # ल
    "v": ["ʋ"],       # व
    "sh": ["ʃ"],      # श
    "s": ["s"],       # स
    "h": ["ɦ"],       # ह

    # Additional consonants
    "sh2": ["ɕ"],     # ष
    "ksh": ["kʃ"],    # क्ष
    "tr": ["t̪ɾ"],    # त्र
    "gy": ["ɡj"],     # ज्ञ
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
