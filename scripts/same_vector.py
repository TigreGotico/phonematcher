"""Print every group of two or more base letters that share one feature vector.

    python scripts/same_vector.py

The letters are the ones ``phone_clusters`` clusters: single letters and tied affricates of the
table. Letters in one group are at distance 0 from each other.
"""
import unicodedata
from collections import defaultdict
from typing import List

from phonematcher import vectorize_phones
from phonematcher.features import phone_features


def base_letters() -> List[str]:
    """The IPA letters and tied affricates of the table."""
    return sorted(p for p in phone_features
                  if (len(p) == 1 and unicodedata.category(p).startswith("L"))
                  or (len(p) == 3 and p[1] in "͜͡"))


def same_vector_groups() -> List[List[str]]:
    """Groups of two or more base letters with identical vectors, in sorted order."""
    by_vector = defaultdict(list)
    for letter in base_letters():
        by_vector[vectorize_phones(letter)].append(letter)
    return sorted(g for g in by_vector.values() if len(g) > 1)


def main() -> None:
    letters = base_letters()
    groups = same_vector_groups()
    print(f"{len(letters)} letters in, {len(groups)} groups with {sum(map(len, groups))} letters")
    for group in groups:
        print(" ".join(f"{c} U+{ord(c[0]):04X}" if len(c) == 1 else c for c in group))


if __name__ == "__main__":
    main()
