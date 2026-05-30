"""Example — how cluster_sensitivity trades precision for recall.

Run::

    python examples/03_sensitivity_tuning.py
"""
from phonematcher.clustering import PhoneticFuzzySearch, PT_MAPPING


def cluster_count(ffs: PhoneticFuzzySearch) -> int:
    return len(set(ffs.clusters.values()))


def main() -> None:
    terms = ["sapo na lagoa", "casa amarela", "zona azul"]
    query = "zapo na lagoa"

    for sensitivity in (0.3, 0.5, 0.6):
        ffs = PhoneticFuzzySearch(PT_MAPPING, cluster_sensitivity=sensitivity)
        for i, term in enumerate(terms):
            ffs.add_term(term, i)
        results = ffs.search(query)
        top = results[0].term if results else "no match"
        print(
            f"sensitivity={sensitivity}: "
            f"{cluster_count(ffs)} phone clusters, "
            f"{query!r} -> {top!r}"
        )

    print("\nlower = tighter clusters (precision); higher = broader (recall)")


if __name__ == "__main__":
    main()
