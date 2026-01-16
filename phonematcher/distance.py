"""
adapted from: https://github.com/lingz/pyphone - MIT License

Distinctive-feature matrix for IPA phones used by PyPhone.

This table encodes a hybrid SPE/IPA feature system for segment-to-segment
distance computation and classification. Each phone maps to a vector of
21 features. Features are boolean where applicable; `None` denotes that
a feature is not defined for a particular phone.

Feature index layout (0–20):

0  syllabic              — Major-class feature
1  sonorant              — Major-class feature
2  consonantal           — Major-class feature
3  continuant            — Manner feature
4  delayed_release       — Affrication feature
5  lateral               — Lateral airflow
6  nasal                 — Nasality
7  strident              — Sibilance/noise
8  voice                 — Voicing
9  spread_glottis        — Aspiration
10 constricted_glottis   — Ejective/creaky articulation
11 anterior              — Coronal place (dental/alveolar)
12 coronal               — Coronal major place
13 distributed           — Blade vs tip distinction
14 labial                — Labial place (bilabial/labiodental)
15 high                  — High vowel/glide or palatal consonant
16 low                   — Low vowel or pharyngealization
17 back                  — Back vowel or dorsal consonant
18 round                 — Lip rounding or labiovelar articulation
19 tense                 — Vowel tenseness
20 long                  — Length mark (ː)

The feature system aligns with features used in generative phonology
and acoustic modeling, but values are hand-curated for each IPA symbol.
"""
from typing import List, Union

NUM_FEATURES = 21

# ---------------------------------------------------------------------------
# phone_features:
#   A mapping of IPA phones to a 21-element feature vector.
#
# Notes:
# - Values are manually derived from articulatory definitions in IPA
#   and standard distinctive-feature systems.
# - `None` indicates the feature is not defined for the phone's class.
# - Used internally for computing similarity/distance between phones.
# ---------------------------------------------------------------------------

phone_features = {
    # Example (one phone explained as template):
    #
    # "c": [
    #   False,  # 0 syllabic — stops are not syllabic
    #   False,  # 1 sonorant — stops are not sonorant
    #   True,   # 2 consonantal — major-class consonant
    #   False,  # 3 continuant — plosive stops are non-continuant
    #   False,  # 4 delayed_release — not an affricate
    #   False,  # 5 lateral — not lateral
    #   False,  # 6 nasal — not nasal
    #   None,   # 7 strident — stridency undefined for non-fricative stops
    #   False,  # 8 voice — voiceless
    #   False,  # 9 spread_glottis — not aspirated
    #   False,  # 10 constricted_glottis — no ejective/creaky state
    #   False,  # 11 anterior — velars not coronal/anterior
    #   False,  # 12 coronal — velars are dorsal, not coronal
    #   None,   # 13 distributed — irrelevant for dorsals
    #   False,  # 14 labial — not labial
    #   True,   # 15 high — dorsal place implies [+high] in SPE terms
    #   False,  # 16 low — not low
    #   False,  # 17 back — front velar [c] is [-back]
    #   False,  # 18 round — not rounded
    #   None,   # 19 tense — undefined for consonants
    #   False,  # 20 long — not lengthened
    # ],
    #
    # All other entries follow the same feature-index ordering.
    # -----------------------------------------------------------------------
    "c": [False, False, True, False, False, False, False, None, False, False, False, False, False, None, False, True,
          False, False, False, None, False],
    "ɡ": [False, False, True, False, False, False, False, None, True, False, False, False, False, None, False, True,
          False, True, False, None, False],
    "k": [False, False, True, False, False, False, False, None, False, False, False, False, False, None, False, True,
          False, True, False, None, False],
    "q": [False, False, True, False, False, False, False, None, False, False, False, False, False, None, False, False,
          False, True, False, None, False],
    "ɖ": [False, False, True, False, False, False, False, None, True, False, False, False, True, False, False, False,
          False, False, False, None, False],
    "ɟ": [False, False, True, False, False, False, False, None, True, False, False, False, False, None, False, True,
          False, False, False, None, False],
    "ɠ": [False, False, True, False, False, False, False, None, True, False, True, False, False, None, False, True,
          False, True, False, None, False],
    "ɢ": [False, False, True, False, False, False, False, None, True, False, False, False, False, None, False, False,
          False, True, False, None, False],
    "ʄ": [False, False, True, False, False, False, False, None, True, False, True, False, False, None, False, True,
          False, False, False, None, False],
    "ʈ": [False, False, True, False, False, False, False, False, False, False, False, False, True, False, False, False,
          False, False, False, None, False],
    "ʛ": [False, False, True, False, False, False, False, None, True, False, True, False, False, None, False, False,
          False, True, False, None, False],
    "b": [False, False, True, False, False, False, False, None, True, False, False, True, False, None, True, False,
          False, False, False, None, False],
    "d": [False, False, True, False, False, False, False, False, True, False, False, True, True, False, False, False,
          False, False, False, None, False],
    "p": [False, False, True, False, False, False, False, None, False, False, False, True, False, None, True, False,
          False, False, False, None, False],
    "t": [False, False, True, False, False, False, False, False, False, False, False, True, True, False, False, False,
          False, False, False, None, False],
    "ɓ": [False, False, True, False, False, False, False, None, True, False, True, True, False, None, True, False,
          False, False, False, None, False],
    "ɗ": [False, False, True, False, False, False, False, False, True, False, True, True, True, False, False, False,
          False, False, False, None, False],
    "x": [False, False, True, True, False, False, False, None, False, False, False, False, False, None, False, True,
          False, True, False, None, False],
    "ç": [False, False, True, True, False, False, False, None, False, False, False, False, False, None, False, True,
          False, False, False, None, False],
    "ħ": [False, False, True, True, False, False, False, None, False, False, False, False, False, None, False, False,
          True, True, False, None, False],
    "ɣ": [False, False, True, True, False, False, False, None, True, False, False, False, False, None, False, True,
          False, True, False, None, False],
    "ʁ": [False, False, True, True, False, False, False, None, True, False, False, False, False, None, False, False,
          False, True, False, None, False],
    "ʂ": [False, False, True, True, False, False, False, True, False, False, False, False, True, False, False, False,
          False, False, False, None, False],
    "ʃ": [False, False, True, True, False, False, False, True, False, False, False, False, True, True, False, False,
          False, False, False, None, False],
    "ʐ": [False, False, True, True, False, False, False, True, True, False, False, False, True, False, False, False,
          False, False, False, None, False],
    "ʒ": [False, False, True, True, False, False, False, True, True, False, False, False, True, True, False, False,
          False, False, False, None, False],
    "ʕ": [False, False, True, True, False, False, False, None, True, False, False, False, False, None, False, False,
          True, True, False, None, False],
    "ʝ": [False, False, True, True, False, False, False, None, True, False, False, False, False, None, False, True,
          False, False, False, None, False],
    "χ": [False, False, True, True, False, False, False, None, False, False, False, False, False, None, False, False,
          False, True, False, None, False],
    "f": [False, False, True, True, False, False, False, None, False, False, False, True, False, None, True, False,
          False, False, False, None, False],
    "s": [False, False, True, True, False, False, False, True, False, False, False, True, True, False, False, False,
          False, False, False, None, False],
    "v": [False, False, True, True, False, False, False, None, True, False, False, True, False, None, True, False,
          False, False, False, None, False],
    "z": [False, False, True, True, False, False, False, True, True, False, False, True, True, False, False, False,
          False, False, False, None, False],
    "ð": [False, False, True, True, False, False, False, False, True, False, False, True, True, True, False, False,
          False, False, False, None, False],
    "ɸ": [False, False, True, True, False, False, False, None, False, False, False, True, False, None, True, False,
          False, False, False, None, False],
    "β": [False, False, True, True, False, False, False, None, True, False, False, True, False, None, True, False,
          False, False, False, None, False],
    "θ": [False, False, True, True, False, False, False, False, False, False, False, True, True, True, False, False,
          False, False, False, None, False],
    "ɧ": [False, False, True, True, True, False, False, None, False, False, False, False, True, True, False, True,
          False, None, False, None, False],
    "ɕ": [False, False, True, True, True, False, False, True, False, False, False, True, True, True, False, True, False,
          False, False, None, False],
    "ɬ": [False, False, True, True, True, True, False, False, False, False, False, True, True, False, False, None, None,
          None, False, None, False],
    "ɮ": [False, False, True, True, True, True, False, False, True, False, False, True, True, False, False, None, None,
          None, False, None, False],
    "ʑ": [False, False, True, True, True, False, False, True, True, False, False, True, True, True, False, True, False,
          False, False, None, False],
    "ɱ": [False, True, True, False, None, False, True, None, True, False, False, True, False, None, True, None, None,
          None, False, None, False],
    "ʔ": [False, True, False, False, False, False, False, None, False, False, True, False, False, None, False, False,
          False, False, False, None, False],
    "ŋ": [False, True, True, False, False, False, True, None, True, False, False, False, False, None, False, True,
          False, True, False, None, False],
    "ɳ": [False, True, True, False, False, False, True, False, True, False, False, False, True, None, False, False,
          False, False, False, None, False],
    "ɴ": [False, True, True, False, False, False, True, None, True, False, False, False, False, None, False, False,
          False, True, False, None, False],
    "m": [False, True, True, False, False, False, True, None, True, False, False, True, False, None, True, False, False,
          False, False, None, False],
    "n": [False, True, True, False, False, False, True, False, True, False, False, True, True, False, False, False,
          False, False, False, None, False],
    "ɲ": [False, True, True, False, False, False, True, False, True, False, False, True, False, None, False, True,
          False, False, False, None, False],
    "ɥ": [False, True, False, True, None, False, False, None, True, False, False, None, False, None, True, True, False,
          False, True, True, False],
    "ɰ": [False, True, False, True, None, False, False, None, True, False, False, None, False, None, False, True, False,
          None, False, True, False],
    "ʋ": [False, True, False, True, None, False, False, None, True, False, False, True, False, None, True, None, None,
          None, False, None, False],
    "ʀ": [False, True, True, True, None, False, False, None, True, False, False, None, False, None, False, False, False,
          True, False, None, False],
    "ʙ": [False, True, True, True, None, False, False, None, True, False, False, True, False, None, True, None, None,
          None, False, None, False],
    "ʟ": [False, True, True, True, None, True, False, None, True, False, False, None, False, None, False, True, False,
          None, False, None, False],
    "ɭ": [False, True, True, True, None, True, False, False, True, False, False, False, True, False, False, None, None,
          None, False, None, False],
    "ɽ": [False, True, True, True, None, False, False, False, True, False, False, False, True, False, False, None, None,
          None, False, None, False],
    "ʎ": [False, True, True, True, None, True, False, None, True, False, False, False, True, True, False, True, False,
          False, False, None, False],
    "r": [False, True, True, True, None, False, False, False, True, False, False, True, True, False, False, None, None,
          None, False, None, False],
    "ɫ": [False, True, True, True, None, True, False, False, True, False, False, True, True, False, False, False, False,
          True, False, None, False],
    "ɺ": [False, True, True, True, None, True, False, False, True, False, False, True, True, False, False, None, None,
          None, False, None, False],
    "ɾ": [False, True, True, True, None, False, False, False, True, False, False, True, True, False, False, None, None,
          None, False, None, False],
    "ʍ": [False, True, False, True, False, False, False, None, False, False, False, False, False, None, True, True,
          False, True, True, None, False],
    "h": [False, True, True, True, False, False, False, False, False, False, False, False, False, None, False, False,
          False, False, False, None, False],
    "j": [False, True, False, True, False, False, False, None, True, False, False, False, False, None, False, True,
          False, False, False, None, False],
    "w": [False, True, False, True, False, False, False, None, True, False, False, False, False, None, True, True,
          False, True, True, None, False],
    "ɹ": [False, True, False, True, False, False, False, False, True, False, False, False, True, False, False, True,
          False, True, True, None, False],
    "ɻ": [False, True, False, True, False, False, False, False, True, False, False, False, True, False, False, False,
          False, False, False, None, False],
    "l": [False, True, True, True, False, True, False, False, True, False, False, True, True, False, False, False,
          False, False, False, None, False],
    "ɦ": [False, True, True, True, False, False, False, None, False, False, False, False, False, None, False, False,
          False, False, False, None, False],
    "ɑ": [True, True, False, True, None, False, False, None, True, False, False, False, False, False, False, False,
          True, True, False, True, False],
    "ɘ": [True, True, False, True, None, False, False, None, True, False, False, False, False, False, False, False,
          False, False, False, True, False],
    "ɞ": [True, True, False, True, None, False, False, None, True, False, False, False, False, False, True, False,
          False, False, True, False, False],
    "ɤ": [True, True, False, True, None, False, False, None, True, False, False, False, False, False, False, False,
          False, True, False, True, False],
    "ɵ": [True, True, False, True, None, False, False, None, True, False, False, False, False, False, True, False,
          False, False, True, True, False],
    "ʉ": [True, True, False, True, None, False, False, None, True, False, False, False, False, False, True, True, False,
          False, True, True, False],
    "a": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          True, True, False, True, False],
    "e": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, False, False, True, False],
    "i": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, True,
          False, False, False, True, False],
    "o": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, True, True, True, False],
    "u": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, True, True,
          False, True, True, True, False],
    "y": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, True, True,
          False, False, True, True, False],
    "æ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          True, False, False, True, False],
    "ø": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, False, True, True, False],
    "œ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, False, True, False, False],
    "ɒ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          True, True, True, True, False],
    "ɔ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, True, True, False, False],
    "ə": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, True, False, False, False],
    "ɜ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, True, False, True, False],
    "ɛ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, False, False, False, False],
    "ɨ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, True,
          False, True, False, True, False],
    "ɪ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, True,
          False, False, False, False, False],
    "ɯ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, True,
          False, True, False, False, False],
    "ɶ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          True, False, True, True, False],
    "ʊ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, True,
          False, True, True, False, False],
    "ɐ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, True, False, True, False],
    "ʌ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, False,
          False, True, False, True, False],
    "ʏ": [True, True, False, True, False, False, False, None, True, False, False, False, False, False, False, True,
          False, False, True, False, False],
}

# ---------------------------------------------------------------------------
# vowel_features / consonant_features:
#   Feature index sets used when computing similarity metrics.
#   They define which features contribute to vowel or consonant distance.
# ---------------------------------------------------------------------------

vowel_features = {
    0,  # syllabic
    1,  # sonorant
    3,  # continuant
    8,  # voice
    14,  # labial (relevant for rounding/labiality in vowels)
    15,  # high
    16,  # low
    17,  # back
    18,  # round
    19,  # tense
    20,  # long
}

consonant_features = {
    1, 2, 3, 4, 5, 6, 7, 8, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19
}

# ---------------------------------------------------------------------------
# modifiers:
#   IPA diacritics that flip or assign features.
#   Each dictionary maps a feature index to the updated boolean value.
# ---------------------------------------------------------------------------

modifiers = {
    "ː": {20: True},  # length mark: [+long]

    " ̻": {13: True},  # laminal articulation: [+distributed]

    "ˤ": {  # pharyngealization: typically [+back, +low]
        16: True,
        17: True,
    },

    "˞": {  # rhoticization
        11: False,  # rhotics are non-anterior
        15: True,  # raised/tighter tongue position
        18: True,  # lip rounding (common in approximant rhotics)
    },
}

# ---------------------------------------------------------------------------
# Weights used for feature-distance scoring.
# feature_weights[i] gives the weight of feature index i.
#
# Values are hand-tuned. Higher weights correspond to major-class features.
# ---------------------------------------------------------------------------

feature_weights = [
    0.14285714285714285,  # 0 syllabic
    0.14285714285714285,  # 1 sonorant
    0.14285714285714285,  # 2 consonantal
    0.07142857142857142,  # 3 continuant
    0.03571428571428571,  # 4 delayed release
    0.03571428571428571,  # 5 lateral
    0.03571428571428571,  # 6 nasal
    0.017857142857142856,  # 7 strident
    0.017857142857142856,  # 8 voice
    0.017857142857142856,  # 9 spread_glottis
    0.017857142857142856,  # 10 constricted_glottis
    0.03571428571428571,  # 11 anterior
    0.03571428571428571,  # 12 coronal
    0.017857142857142856,  # 13 distributed
    0.03571428571428571,  # 14 labial
    0.03571428571428571,  # 15 high
    0.03571428571428571,  # 16 low
    0.03571428571428571,  # 17 back
    0.03571428571428571,  # 18 round
    0.03571428571428571,  # 19 tense
    0.017857142857142856,  # 20 long
]

total_vowel_weight = sum(feature_weights[i] for i in vowel_features)
total_consonant_weight = sum(feature_weights[i] for i in consonant_features)

standard_weights = [1 / 21] * 21
zero_weights = [0] * 21

# Cache for feature vectors of composite phones.
# Composite phones (like "ɜ˞") require merging multiple feature sets.
# Since merging costs time, we store results after first computation.
_phone_memory = {}

# Normalization table for irregular or ambiguous IPA symbols.
# When a phone appears in this map, it should be replaced with the canonical form.
_bad_phones = {
    "ɝ": "ɜ˞",
}


def vectorize_phones(phones: str) -> List[Union[bool, None]]:
    """
    Resolve a phone or phone-with-modifiers into a phonetic feature vector.

    Phones can be:
        - A single IPA symbol (e.g. "p", "a", "ʒ")
        - A composite sequence (e.g. "ɜ˞") where modifiers adjust features

    How this works:
        1. If the phone is known to require normalization, normalize it.
        2. If the phone consists of exactly one symbol:
              return its feature vector directly.
        3. If it contains multiple symbols:
              • Some symbols represent modifiers that override features.
              • Others represent base phones that contribute their features.
              • We merge the base features first.
              • Then we apply modifiers that overwrite specific features.

    Feature vector rules:
        - Each feature index holds True, False, or None (unknown/irrelevant).
        - When merging:
              • A True anywhere forces the feature True.
              • Otherwise, if any base phone sets False, keep False.
              • If all base phones leave a feature None, it remains None.
        - Modifiers overwrite final values for specific feature indices.
    """
    global _phone_memory

    if not phones:
        raise ValueError("Phone is empty or None.")

    # --- Step 1: normalize irregular phones ---
    if phones in _bad_phones:
        phones = _bad_phones[phones]

    # --- Step 2: fast path for simple phones ---
    if len(phones) == 1:
        try:
            return phone_features[phones]
        except KeyError:
            raise ValueError(f"Unrecognized phone '{phones}'")

    # --- Step 3: cached result for composite phones ---
    if phones in _phone_memory:
        return _phone_memory[phones]

    # --- Step 4: compute vector for composite phone ---
    try:
        # Start with an empty feature list (None = no information yet)
        vec = [None] * NUM_FEATURES

        # A list of modifier dicts that will be applied later
        new_modifiers = []

        # Merge all base phone feature contributions
        #
        # For every feature index, we scan all characters:
        #   - If character is a modifier, mark for later.
        #   - If character is a base phone, check its feature value.
        #
        # Merging logic:
        #   True dominates everything (immediate)
        #   False sets only if we have not seen a True
        #   None means "no influence" unless no other phones give a value
        #
        for f_idx in range(NUM_FEATURES):
            merged_val = None
            for p in phones:
                if p in modifiers:
                    new_modifiers.append(modifiers[p])
                    continue

                # Base phone feature lookup
                base_val = phone_features[p][f_idx]

                # Dominance rule: True > False > None
                if base_val is True:
                    merged_val = True
                    break
                elif base_val is False:
                    merged_val = False

            vec[f_idx] = merged_val

        # Apply modifiers, which can overwrite any feature position.
        # Modifiers represent diacritics or IPA secondary articulations.
        for mod in new_modifiers:
            for feature_idx, mod_val in mod.items():
                vec[feature_idx] = mod_val

        # Save result to cache
        _phone_memory[phones] = vec
        return vec

    except KeyError as e:
        raise ValueError(f"Unrecognized phone '{e.args[0]}'")


def is_vowel_phone(phone: str) -> bool:
    """
    Return True if the phone is a vowel, else False.

    Convention:
        The data model places the vowel/consonant flag in feature[0].
        A True at feature[0] means vowel.
    """
    try:
        return vectorize_phones(phone)[0]
    except:
        return False


def phonetic_distance(phone_a: str, phone_b: str) -> float:
    """
    Compute a normalized phonetic distance between two IPA phones.

    Key rules:
        - Space ' ' is considered a phone but can only match itself.
        - Vowel ↔ consonant mismatches always yield distance = 1.0.
        - Otherwise, distance is computed from weighted feature mismatches.
        - The mismatch sum is normalized by a precomputed total weight.
        - Consonants are scaled by factor 2.0; vowels by 1.0.

    Algorithm:
        1. Handle special case: if either phone is a space.
        2. If one is vowel and the other is consonant → return 1.0.
        3. Determine if phones are vowels or consonants.
        4. Select feature subset and normalization constants:
              vowels → smaller set, factor 1
              consonants → larger set, factor 2
        5. Retrieve feature vectors.
        6. Compare only the relevant feature indices:
              if vecA[i] != vecB[i], add weight[i] to difference sum.
        7. Normalize difference sum:
              distance = (difference_sum / total_weight) * factor

    Result Range:
        • For vowels: 0 → 1
        • For consonants: 0 → 2 (due to factor 2)
    """
    # --- Step 1: special-case for space phones ---
    if phone_a == ' ' or phone_b == ' ':
        # Identical spaces match with distance 0, else fully dissimilar
        return 0.0 if phone_a == phone_b else 1.0

    # --- Step 2: vowel/consonant mismatch ---
    vowel = is_vowel_phone(phone_a)
    if vowel != is_vowel_phone(phone_b):
        return 1.0

    # --- Step 3: choose feature subset and scaling factor ---
    if vowel:
        # Vowels use a limited feature set and factor = 1
        total_weights = total_vowel_weight
        feature_indices = vowel_features
        factor = 1.0
    else:
        # Consonants use more features and factor = 2
        total_weights = total_consonant_weight
        feature_indices = consonant_features
        factor = 2.0

    # --- Step 4: retrieve merged feature vectors ---
    try:
        vecA = vectorize_phones(phone_a)
        vecB = vectorize_phones(phone_b)
    except:
        return 3.0

    # --- Step 5: accumulate weighted mismatches ---
    diff_sum = 0.0
    for idx in feature_indices:
        # Any inequality counts as a mismatch
        if vecA[idx] != vecB[idx]:
            diff_sum += feature_weights[idx]

    # --- Step 6: normalize & scale ---
    return (diff_sum / total_weights) * factor

