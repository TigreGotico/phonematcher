"""Example — extend BASE_LATIN into a small custom grapheme-to-IPA mapping.

Run::

    python examples/05_custom_mapping.py
"""
from phonematcher.clustering import PhoneticFuzzySearch, BASE_LATIN
from phonematcher.distance import vectorize_phones


def main() -> None:
    # Inherit the shared Latin table, override a few graphemes.
    overrides = {
        "sh": ["ʃ"],            # digraph -> single sound
        "x": ["ʃ", "ks", "s"],  # one grapheme, several sounds
    }
    my_lang = {**BASE_LATIN, **overrides}

    # Validate the phones our overrides emit before building the index:
    # every one must resolve in the distinctive-feature table.
    bad = []
    for phones in overrides.values():
        for phone in phones:
            if not phone:
                continue  # empty string = silent, allowed
            try:
                vectorize_phones(phone)
            except ValueError:
                bad.append(phone)
    print("unsupported phones in overrides:", bad or "none")

    ffs = PhoneticFuzzySearch(mapping=my_lang, cluster_sensitivity=0.4)
    ffs.add_term("ship shape", 0)
    ffs.add_term("extra exit", 1)

    for q in ("schip schape", "ekstra eksit"):
        results = ffs.search(q)
        top = results[0].term if results else "no match"
        print(f"  {q!r} -> {top!r}")


if __name__ == "__main__":
    main()
