# Phonematcher

Phonematcher is a Python library for phonetic fuzzy search and segment-to-segment distance computation. It finds words that sound like a query by analyzing International Phonetic Alphabet (IPA) features instead of comparing raw text.

The library uses distinctive feature theory to calculate the articulatory distance between sounds. For example, it recognizes that "p" and "b" are more similar than "p" and "k". It clusters similar sounds to improve search recall.

## Features

* **Distinctive feature matrix**: maps IPA phones to 21 articulatory features (nasality, voicing, place of articulation, and more).
* **Weighted phonetic distance**: calculates similarity based on linguistic importance. Major class features, such as "syllabic," carry more weight than fine-grained features, such as "strident."
* **UPGMA clustering**: groups similar sounds into clusters, based on a configurable sensitivity threshold.
* **Fuzzy phonetic index**: uses a "Phonex" algorithm to generate phonetic variants, including deletions, for high-recall indexing.
* **Hybrid scoring**: combines phonetic candidate retrieval with Levenshtein edit-distance ranking.

## Installation

Install the required dependency, then install the library:

```bash
pip install rapidfuzz
pip install -e .
```

## Usage

### Phonetic distance

Compare two IPA symbols to see how linguistically similar they are:

```python
from phonematcher.distance import phonetic_distance

# Voiced vs. voiceless bilabial stops (very similar)
print(phonetic_distance('b', 'p'))  # ~0.043

# Bilabial vs. velar stops (less similar)
print(phonetic_distance('p', 'k'))  # ~0.348

# Vowel vs. consonant (maximal distance)
print(phonetic_distance('a', 'k'))  # 1.0
```

### Phonetic fuzzy search

The `PhoneticFuzzySearch` class indexes terms by their phonetic clusters:

```python
from phonematcher.clustering import PhoneticFuzzySearch, EN_MAPPING

# Initialize with a grapheme-to-phoneme mapping
ffs = PhoneticFuzzySearch(EN_MAPPING, cluster_sensitivity=0.5)

# Add terms to the index (id, term)
ffs.add_term('hello world', 0)
ffs.add_term('greetings', 1)
ffs.add_term('friendship', 2)

# Search with typos or phonetic variations
results = ffs.search('helo wrld')
for match in results:
    print(f"ID: {match.id}, Term: {match.term}, Score: {match.score}")
```

## How it works

### Feature vectorization

Every phone resolves to a vector of boolean or null values. For example, the phone `c` (voiceless palatal stop) has these feature values:

* **Consonantal**: `True`
* **Voice**: `False`
* **High**: `True`
* **Back**: `False`

### The search pipeline

1. **Phoneticization**: the library expands a word into all possible IPA sequences, based on the mapping.
2. **Clustering**: phones group into numeric cluster IDs. For example, `s`, `z`, and `ʃ` might fall into the same cluster.
3. **Variant generation**: to handle misspellings, the indexer generates "deletes" — versions of the phonetic sequence with one or two sounds removed.
4. **Retrieval**: the query converts to clusters and matches against the index.
5. **Ranking**: the resulting candidates rank by the Levenshtein distance of the original orthographic strings.

## Configuration

Tune the `cluster_sensitivity` parameter (default `0.5`):

* **Lower values**: create more specific clusters. Fewer matches, higher precision.
* **Higher values**: create broader clusters. More matches, higher recall.

## Understanding phonetic mappings

Orthography (spelling) varies across languages, so the library uses grapheme-to-IPA mappings to translate written words into spoken phonetic vectors.

Without a mapping, the library treats letters as arbitrary symbols. Mapping them to IPA (International Phonetic Alphabet) symbols lets the system use distinctive feature theory:

* **Linguistic accuracy**: the engine knows that "p" and "b" are both bilabial stops that differ only in voicing.
* **Weighted distance**: mappings let the algorithm compute distance based on articulatory features, such as nasality or place of articulation, instead of simple character replacement.
* **Cluster precision**: a word converts into a sequence of cluster IDs. Accurate mappings ensure that words which sound similar (for example, "frend" and "friend") produce the same or highly similar cluster sequences, which increases search recall.

A mapping is a Python dictionary. Its keys are graphemes (single letters or digraphs) and its values are lists of possible IPA realizations:

```python
# Example: mapping 'x' to its multiple sounds
"x": ["ʃ", "ks", "z", "s"]
```

The `PhoneticFuzzySearch` class uses a breadth-first search (BFS) substitution traversal to expand a single word into all possible phonetic sequences. For example, a word containing "x" generates several phonetic variants, so the index can find a match regardless of how the user perceives the sound.

### How to support a new language

To add support for a new language, follow these steps:

1. Create a dictionary that covers the phonology of the language. Inherit from `BASE_LATIN` to reuse the standard characters.

```python
MY_LANG_MAPPING = {
    **BASE_LATIN,
    "sh": ["ʃ"],  # digraph
    "aa": ["aː"], # long vowel
}
```

2. If a letter has multiple sounds (for example, "c" in English), include all of them in the list. The variant generator indexes every possibility, which produces a fuzzy phonetic match.
3. Pass the custom mapping into the `PhoneticFuzzySearch` constructor.

```python
from phonematcher.clustering import PhoneticFuzzySearch

ffs = PhoneticFuzzySearch(mapping=MY_LANG_MAPPING, cluster_sensitivity=0.4)
```

For a highly phonetic language (such as Spanish or Italian), keep `cluster_sensitivity` low (around 0.3). For a language with complex spelling-to-sound rules (such as English or French), a higher sensitivity (0.5-0.6) helps group divergent spellings into the same cluster.

## Documentation

See the [docs](docs/quickstart.md) directory for a quickstart guide, the API reference, advanced usage recipes, and the distinctive-feature matrix.

## Related projects

- [orthography2ipa](https://github.com/TigreGotico/orthography2ipa) — grapheme-to-IPA phonemization engine.
- [silabificador](https://github.com/TigreGotico/silabificador) — syllabification library.

## License

This project is adapted from `pyphone` and `fast_fuzzy_search` by [lingz](https://github.com/lingz), and is released under the MIT License.
