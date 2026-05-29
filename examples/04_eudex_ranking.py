"""Example — the Eudex phonetic hash as a word-level sound comparator.

Run::

    python examples/04_eudex_ranking.py
"""
from phonematcher.eudex import Hash, eudex_hash, weighted_hamming_distance


def main() -> None:
    print("normalization folds case and punctuation:")
    print("  Hash('JAva') == Hash('jAva'):", Hash("JAva") == Hash("jAva"))
    print("  Hash('comp-uter') == Hash('computer'):",
          Hash("comp-uter") == Hash("computer"))

    print("\nsound-alike judgements:")
    for a, b in [("maier", "meyer"), ("java", "jiva"),
                 ("horse", "norse"), ("nice", "mice")]:
        diff = Hash(a) - Hash(b)
        print(f"  {a!r} vs {b!r}: similar={diff.similar()} dist={diff.dist()}")

    print("\nraw hash + weighted hamming distance:")
    h1, h2 = eudex_hash("through"), eudex_hash("thru")
    print(f"  eudex_hash('through') = {h1}")
    print(f"  eudex_hash('thru')    = {h2}")
    print(f"  weighted hamming      = {weighted_hamming_distance(h1, h2)}")


if __name__ == "__main__":
    main()
