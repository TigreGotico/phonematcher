"""Example — sound-alike search over Portuguese phrases despite misspellings.

Run::

    python examples/02_search_portuguese.py
"""
from phonematcher.clustering import PhoneticFuzzySearch, PT_MAPPING


def main() -> None:
    terms = [
        "pão com queijo",
        "coração batendo",
        "cachorro corre",
        "chocolate quente",
        "peixe no mar",
    ]
    ffs = PhoneticFuzzySearch(PT_MAPPING)
    for i, term in enumerate(terms):
        ffs.add_term(term, i)

    queries = [
        "pao com keijo",
        "corasao batendo",
        "kashoro kore",
        "shocolate kente",
        "peishe no mar",
    ]
    print("Portuguese phonetic search (query -> best match, score):")
    for q in queries:
        results = ffs.search(q)
        if results:
            top = results[0]
            print(f"  {q!r:24} -> {top.term!r} (score={top.score})")
        else:
            print(f"  {q!r:24} -> no match")


if __name__ == "__main__":
    main()
