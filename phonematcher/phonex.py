"""
This module is adapted from:
https://github.com/lingz/pyphone
MIT License.
"""


def _tokenize(w):
    # Marks each character for stable substring replacement.
    return "".join(["_" + letter for letter in w])


def _strip_repeats(w):
    # Remove consecutive duplicate phonemes and strip leading tokens.
    stripped = []
    last_letter = None
    w = filter(None, w.split("$"))
    for letter in w:
        if letter != last_letter and not letter.startswith("_"):
            stripped.append(letter)
        last_letter = letter
    return tuple(stripped)


def _phoneticize(word, mapping) -> set:
    """
    Expand a raw orthographic word into all phonetic sequences using
    grapheme-to-phoneme mapping expansion.

    Returns:
        set[tuple[str]]:
            All deduplicated phoneme sequences after replacement and
            repeat-stripping.
    """
    tokenized = _tokenize(word.lower())
    next_words = {tokenized}
    results = set()

    # Precompute tokenized mapping keys for replacer.
    tokenized_mappings = {
        _tokenize(key): ["$" + ph for ph in mapping]
        for (key, mapping) in mapping.items()
    }

    # BFS-like substitution traversal.
    while next_words:
        next_word = next_words.pop()
        has_replacements = False

        for key, replacements in tokenized_mappings.items():
            if key in next_word:
                has_replacements = True
                for replacement in replacements:
                    # Replace only first occurrence each time to avoid collapse.
                    next_words.add(next_word.replace(key, replacement, 1))

        if not has_replacements:
            # Terminal form; strip repeats.
            results.add(_strip_repeats(next_word))

    return results


def phonex(word, mapping, clusters):
    """
    Map a word to all possible sequences of phone clusters.

    Returns:
        list[tuple[int]]:
            Each phonex tuple is a sequence of cluster IDs.
    """
    phone_variants = _phoneticize(word, mapping)
    results = []
    for phone_variant in phone_variants:
        try:
            phonex_variant = tuple(clusters[p] for p in phone_variant)
            results.append(phonex_variant)
        except:
            print('Error:', word, phone_variant)
            raise
    return results
