from phonematcher.clustering import Match, PhoneticFuzzySearch
from phonematcher.distance import GAP_COST, align, edit_distance, ipa_distance, segments, substitution_cost
from phonematcher.features import FEATURES, WEIGHTS, feature_distance, is_vowel_phone, phonetic_distance, vectorize_phones
from phonematcher.tone import is_tone, tone_distance, tone_levels
from phonematcher.version import VERSION_STR as __version__

__all__ = [
    "FEATURES",
    "GAP_COST",
    "WEIGHTS",
    "Match",
    "PhoneticFuzzySearch",
    "align",
    "edit_distance",
    "feature_distance",
    "ipa_distance",
    "is_tone",
    "is_vowel_phone",
    "phonetic_distance",
    "segments",
    "substitution_cost",
    "tone_distance",
    "tone_levels",
    "vectorize_phones",
]
