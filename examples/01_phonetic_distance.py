"""Example — articulatory distance between IPA phones.

Run::

    python examples/01_phonetic_distance.py
"""
from phonematcher.distance import phonetic_distance, is_vowel_phone


def main() -> None:
    pairs = [
        ("b", "p"),   # same place, voicing only
        ("p", "k"),   # both stops, different place
        ("m", "n"),   # two nasals
        ("ʃ", "s"),   # two sibilants
        ("a", "k"),   # vowel vs consonant -> maximal
    ]
    print("phone-pair distances (0.0 = same, 1.0 = maximal):")
    for a, b in pairs:
        print(f"  {a!r} vs {b!r}: {phonetic_distance(a, b):.3f}")

    print("\nvowel check:")
    for ph in ("a", "i", "k", "ʃ"):
        print(f"  is_vowel_phone({ph!r}) = {is_vowel_phone(ph)}")


if __name__ == "__main__":
    main()
