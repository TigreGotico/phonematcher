# Phonematcher

**Phonematcher** is a Python library for phonetic fuzzy searching and segment-to-segment distance computation. It allows you to find words that "sound like" a query by analyzing International Phonetic Alphabet (IPA) features rather than just comparing raw text.

By leveraging **Distinctive Feature Theory**, the library can calculate the articulatory distance between sounds (e.g., recognizing that 'p' and 'b' are more similar than 'p' and 'k') and cluster them to improve search recall.

---

## 🚀 Features

* **Distinctive Feature Matrix:** Maps IPA phones to 21 articulatory features (nasality, voicing, place of articulation, etc.).
* **Weighted Phonetic Distance:** Calculates similarity based on linguistic importance (e.g., major class features like "syllabic" carry more weight than "strident").
* **UPGMA Clustering:** Automatically groups similar sounds into clusters based on a configurable sensitivity threshold.
* **Fuzzy Phonetic Index:** Uses a "Phonex" algorithm to generate phonetic variants (including deletions) for high-recall indexing.
* **Hybrid Scoring:** Combines phonetic candidate retrieval with Levenshtein edit-distance ranking.

---

## 📦 Installation

Ensure you have the required dependencies:

```bash
pip install rapidfuzz

```

---

## 🛠 Usage

### 1. Phonetic Distance

You can compare two IPA symbols to see how linguistically similar they are.

```python
from phonematcher.distance import phonetic_distance

# Comparing voiced vs voiceless bilabial stops (very similar)
print(phonetic_distance('b', 'p'))  # ~0.043

# Comparing bilabial vs velar stops (less similar)
print(phonetic_distance('p', 'k'))  # ~0.348

# Vowel vs Consonant mismatch (maximal distance)
print(phonetic_distance('a', 'k'))  # 1.0

```

### 2. Phonetic Fuzzy Search

The `PhoneticFuzzySearch` class indexes terms based on their phonetic clusters.

```python
from phonematcher.clustering import PhoneticFuzzySearch, EN_MAPPING

# Initialize with a Grapheme-to-Phoneme mapping
ffs = PhoneticFuzzySearch(EN_MAPPING, cluster_sensitivity=0.5)

# Add terms to your index (id, term)
ffs.add_term('hello world', 0)
ffs.add_term('greetings', 1)
ffs.add_term('friendship', 2)

# Search with typos or phonetic variations
results = ffs.search('helo wrld')
for match in results:
    print(f"ID: {match.id}, Term: {match.term}, Score: {match.score}")

```

---

## 🧬 How it Works

### Feature Vectorization

Every phone is resolved into a vector of boolean or null values. For example, the phone `c` (voiceless palatal stop) is represented by features like:

* **Consonantal:** `True`
* **Voice:** `False`
* **High:** `True`
* **Back:** `False`

### The Search Pipeline

1. **Phoneticization:** The library expands a word into all possible IPA sequences based on your mapping.
2. **Clustering:** Phones are grouped into numeric IDs (e.g., `s`, `z`, and `ʃ` might all fall into Cluster 5).
3. **Variant Generation:** To handle misspellings, the indexer generates "deletes"—versions of the phonetic sequence with one or two sounds removed.
4. **Retrieval:** The query is converted to clusters and matched against the index.
5. **Ranking:** The resulting candidates are ranked using the Levenshtein distance of the original orthographic strings.

---

## ⚙️ Configuration

You can tune the `cluster_sensitivity` (default `0.5`):

* **Lower values:** Create more specific clusters (fewer matches, higher precision).
* **Higher values:** Create broader clusters (more matches, higher recall).

---

## 📜 License

This project is adapted from `pyphone` and `fast_fuzzy_search` by [lingz](https://github.com/lingz) and is released under the **MIT License**.
