"""Distances between IPA segments and between IPA strings.

Run::

    python examples/01_phonetic_distance.py
"""
from phonematcher import ipa_distance, feature_distance, segments

for a, b in [("ʁ", "χ"), ("ʁ", "k"), ("e", "ɛ"), ("e", "o"), ("ɐ", "a"), ("t", "t͡ʃ")]:
    print(f"{a} {b} {feature_distance(a, b):.3f}")

print(segments("ˈt͡ʃɐ̃w̃"))
print(f"{ipa_distance('ˈpojʃ', 'ˈpojs'):.3f}")
