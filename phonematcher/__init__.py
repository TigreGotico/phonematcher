from phonematcher.clustering import Match, PhoneticFuzzySearch
from phonematcher.distance import GAP_COST, align, edit_distance, ipa_distance, segments, substitution_cost
from phonematcher.features import FEATURES, WEIGHTS, feature_distance, phonetic_distance, vectorize_phones
from phonematcher.tone import is_tone, tone_distance
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
    "phonetic_distance",
    "segments",
    "substitution_cost",
    "tone_distance",
    "vectorize_phones",
]
