# Search by sound
<!-- agent-hint
covers: how to search an index of IPA terms by sound, and how cluster_sensitivity changes the results
source: phonematcher/clustering.py:PhoneticFuzzySearch, benchmarks/results/retrieval-dev.json, benchmarks/prereg-2.md
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k search.md
see: compare-words.md, benchmarks.md
-->

This page builds a small index of Portuguese words, searches it with a spelling from another dialect, and shows what the `cluster_sensitivity` setting changes. The last step gives the benchmark numbers behind the default of 0.1.

## 1. Build an index and search it

An index holds IPA terms. Each term has an id. The words below are European Portuguese, in broad IPA. A grapheme-to-IPA library such as orthography2ipa writes IPA from text.

```python
from phonematcher import PhoneticFuzzySearch

WORDS = {
    "pois": "ˈpojʃ", "retirada": "ʁɨtiˈɾadɐ", "carro": "ˈkaʁu", "caro": "ˈkaɾu",
    "casa": "ˈkazɐ", "dia": "ˈdiɐ", "mesa": "ˈmezɐ", "porta": "ˈpɔɾtɐ",
    "ponte": "ˈpõtɨ", "pote": "ˈpɔtɨ", "bote": "ˈbɔtɨ",
}

def index(sensitivity):
    search = PhoneticFuzzySearch(cluster_sensitivity=sensitivity)
    for word, ipa in WORDS.items():
        search.add_term(ipa, word)
    return search

search = index(0.1)
```

The query is the word `carro` as a Rio de Janeiro speaker says it. The index has the European reading, with `ʁ`. The query has `χ`.

```python
results = search.search("ˈkaχu")
[(m.id, round(m.score, 3)) for m in results]   # [('carro', 0.115), ('caro', 0.544), ('casa', 0.779)]
```

`search` returns the terms nearest first. Each `Match` has the id, the readings of the term and a score. The score is the word distance of [Compare two words](compare-words.md). The word `carro` is at 0.115: one near substitution, `χ` for `ʁ`.

## 2. Query by several readings

A term may have several readings, and a query may have several. The score is the smallest distance between a query reading and a term reading:

```python
two = PhoneticFuzzySearch()
two.add_term(["ˈpojʃ", "ˈpojs"], "pois")
[(m.id, m.score) for m in two.search("ˈpojs")]   # [('pois', 0.0)]
```

The first reading is at 0.199 from the query and the second is at 0. The score is 0.

## 3. See what a sensitivity groups

The search does not compare the query with every term. It groups the IPA letters into clusters of near sounds, and it finds the terms whose cluster sequence matches the query. Adjacent sounds of one cluster merge into one. The search may drop up to two clusters from the query word and up to two from the term word before it compares them. `cluster_sensitivity` sets how far apart two sounds may be and still share a cluster. A higher value makes larger clusters.

The dropping lets a query find a term that has no near sounds in common with it. The query `lumaki` finds the term `lumano`, because the query drops `k` and `i`, the term drops `n` and `o`, and both words become `luma`. The score is high:

```python
odd = PhoneticFuzzySearch()
odd.add_term("lumano", "lumano")
[(m.id, round(m.score, 3)) for m in odd.search("lumaki")]   # [('lumano', 0.904)]
```

```python
from phonematcher.clustering import phone_clusters

PAIRS = [("p", "b"), ("ʁ", "χ"), ("s", "ʃ"), ("e", "ɛ"), ("a", "ɐ"), ("p", "t"), ("ʁ", "k"), ("e", "o")]

for sensitivity in (0.0, 0.1, 0.2):
    clusters = phone_clusters(sensitivity)
    together = " ".join(a + b for a, b in PAIRS if clusters[a] == clusters[b])
    print(sensitivity, len(set(clusters.values())), "clusters;", together or "no pair")
```

```text
0.0 135 clusters; no pair
0.1 22 clusters; pb ʁχ sʃ eɛ aɐ
0.2 5 clusters; pb ʁχ sʃ eɛ aɐ pt ʁk eo
```

At 0.0 every letter is alone. At 0.1, voicing pairs and near vowels share a cluster, and `p t` and `e o` do not. At 0.2 only 5 clusters remain, and `p t`, `ʁ k` and `e o` share one.

## 4. See the effect on a search

Search the index of step 1 for `dia` as a speaker from Rio de Janeiro says it, with `d͡ʒ` before `i`. Count the terms that come back at each sensitivity:

```python
for sensitivity in (0.0, 0.1, 0.2):
    found = index(sensitivity).search("ˈd͡ʒiɐ", n_results=20)
    print(sensitivity, len(found), [m.id for m in found[:3]])
```

```text
0.0 1 ['dia']
0.1 4 ['dia', 'bote', 'ponte']
0.2 9 ['dia', 'casa', 'mesa']
```

The word `dia` comes first at every value. A higher sensitivity returns more candidates, and the search computes an edit distance for each one. The candidates are ranked by that distance, so the nearest word stays first.

## 5. Read the benchmark numbers

The retrieval benchmark searches an index of one dialect with the words of another. It uses WikiPron pairs of dialects. The development results are in `benchmarks/results/retrieval-dev.json`. Run the block from the root of a clone of the repository. It reads the Portuguese pair at each sensitivity:

```python
import json

pairs = json.load(open("benchmarks/results/retrieval-dev.json"))["pairs"]
rows = {r["sensitivity"]: r for r in pairs["pt-PT-BR"]["fuzzy_search"]}
levels = (0.0, 0.05, 0.1, 0.15, 0.2)

[rows[s]["recall@1"] for s in levels]                        # [0.428, 0.737, 0.806, 0.851, 0.851]
[rows[s]["candidate_recall"] for s in levels]                # [0.486, 0.84, 0.924, 0.988, 0.99]
[round(rows[s]["mean_candidates"], 1) for s in levels]       # [9.0, 58.8, 188.6, 2220.3, 5359.5]
```

The first list is the share of queries whose first result is the right word. The second is the share of queries whose right word is among the candidates. The third is the mean number of candidates per query. Neither recall value falls as the sensitivity rises, and the candidate count rises faster. The mean of recall at 1 over the four pairs of the benchmark (English, Portuguese, Spanish and Armenian dialects) is:

```python
[round(sum(p["fuzzy_search"][i]["recall@1"] for p in pairs.values()) / len(pairs), 4) for i in range(5)]   # [0.7051, 0.8318, 0.8521, 0.8663, 0.8663]
```

## 6. Choose a sensitivity

The default is 0.1. A rule fixed before the test run chooses it. The rule is in `benchmarks/prereg-2.md`, and it applies to the development results after the test run. Of the values 0.0, 0.05, 0.1, 0.15 and 0.2, take the one with the highest mean recall at 1 among the values whose mean candidate count is at most 5% of the index pronunciations in every pair.

The values 0.15 and 0.2 have the highest recall. Their candidate counts are too large. This block gives the largest share of the index that a query returns, over the four pairs, and then the share at 0.15 in each pair:

```python
share = lambda p, i: p["fuzzy_search"][i]["mean_candidates"] / p["counts"]["index_prons"]
[round(max(share(p, i) for p in pairs.values()), 4) for i in range(5)]   # [0.0027, 0.0051, 0.0146, 0.1055, 0.2582]
[round(share(p, 3), 3) for p in pairs.values()]                        # [0.106, 0.077, 0.052, 0.095]
```

At 0.1 the largest share is 1.5%. At 0.15 every pair is above 5%, so the rule picks 0.1.

[Index](index.md) · Previous: [Tones](tones.md) · Next: [Add a segment](add-a-segment.md)
