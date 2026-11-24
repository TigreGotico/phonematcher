# Search by sound
<!-- agent-hint
covers: how to search an index of IPA terms by sound, and how cluster_sensitivity changes the results
source: phonematcher/clustering.py:PhoneticFuzzySearch, benchmarks/results/retrieval-dev.json, benchmarks/prereg-2.md
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k search.md
see: compare-words.md, benchmarks.md
-->

This page builds a small index of Portuguese words, searches it with a spelling from another dialect, and shows what the `cluster_sensitivity` setting changes. The last step gives the benchmark numbers behind the default of 0.08.

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

search = index(0.08)
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

The search does not compare the query with every term. It groups the IPA letters into clusters of near sounds, and it finds the terms whose cluster sequence matches the query. Adjacent sounds of one cluster merge into one. The search may drop up to two clusters from the query word and up to two from the term word before it compares them.

`cluster_sensitivity` is a share from 0 to 1. It sets how far apart two sounds may be and still share a cluster, in four steps:

1. Take the IPA letters and tied affricates of the feature table. There are 135, so there are 9,045 pairs of two different letters.
2. Price each pair with `substitution_cost`, the cost that `ipa_distance` uses, and sort the prices.
3. Read the price at the position that the share names, in the sorted list of 9,045 prices. A share of 0.08 reads the price at 8% of the way along the list. That price is the merge threshold.
4. Start with one cluster per letter. Merge the two nearest clusters while the mean price between them is at most the merge threshold.

A share keeps its meaning when the prices change, because it counts pairs and not units of cost. Many pairs have equal prices, so the share of pairs below the threshold is near the share but not equal to it. The block does the first three steps:

```python
from itertools import combinations

from phonematcher import substitution_cost
from phonematcher.clustering import merge_threshold, phone_clusters

letters = sorted(phone_clusters(0.0))
costs = sorted(substitution_cost(a, b) for a, b in combinations(letters, 2))
threshold = merge_threshold(0.08)

len(letters)                                  # 135
len(costs)                                    # 9045
round(threshold, 4)                           # 0.2924
sum(c < threshold for c in costs) / len(costs)   # 0.0737
```

A share outside 0 to 1 raises `ValueError`. The block below groups the letters at four shares and lists which of eight pairs of sounds share a cluster:

```python
PAIRS = [("p", "b"), ("ʁ", "χ"), ("s", "ʃ"), ("e", "ɛ"), ("a", "ɐ"), ("p", "t"), ("ʁ", "k"), ("e", "o")]

for sensitivity in (0.0, 0.08, 0.2, 0.5):
    clusters = phone_clusters(sensitivity)
    together = " ".join(a + b for a, b in PAIRS if clusters[a] == clusters[b])
    print(sensitivity, len(set(clusters.values())), "clusters;", together or "no pair")
```

```text
0.0 98 clusters; pb ʁχ
0.08 28 clusters; pb ʁχ sʃ eɛ aɐ
0.2 10 clusters; pb ʁχ sʃ eɛ aɐ pt eo
0.5 3 clusters; pb ʁχ sʃ eɛ aɐ pt ʁk eo
```

At 0.0 only the nearest pairs share a cluster, `p b` and `ʁ χ`. At 0.08, voicing pairs and near vowels share a cluster, and `p t` and `e o` do not. At 0.2 `p t` and `e o` share one. At 0.5 only 3 clusters remain.

The dropping lets a query find a term that has no near sounds in common with it. The query `lumaki` finds the term `lumano`, because the query drops `k` and `i`, the term drops `n` and `o`, and both words become `luma`. The score is high:

```python
odd = PhoneticFuzzySearch()
odd.add_term("lumano", "lumano")
[(m.id, round(m.score, 3)) for m in odd.search("lumaki")]   # [('lumano', 0.904)]
```

## 4. See the effect on a search

Search the index of step 1 for `dia` as a speaker from Rio de Janeiro says it, with `d͡ʒ` before `i`. Count the terms that come back at each sensitivity:

```python
for sensitivity in (0.0, 0.08, 0.2, 0.5):
    found = index(sensitivity).search("ˈd͡ʒiɐ", n_results=20)
    print(sensitivity, len(found), [m.id for m in found[:3]])
```

```text
0.0 1 ['dia']
0.08 1 ['dia']
0.2 8 ['dia', 'casa', 'bote']
0.5 10 ['dia', 'casa', 'mesa']
```

The word `dia` comes first at every value. A higher sensitivity returns more candidates, and the search computes an edit distance for each one. The candidates are ranked by that distance, so the nearest word stays first.

## 5. Read the benchmark numbers

The retrieval benchmark searches an index of one dialect with the words of another. It uses WikiPron pairs of dialects. The development results are in `benchmarks/results/retrieval-dev.json`. Run the block from the root of a clone of the repository. It reads the Portuguese pair at each sensitivity:

```python
import json

pairs = json.load(open("benchmarks/results/retrieval-dev.json"))["pairs"]
rows = {r["sensitivity"]: r for r in pairs["pt-PT-BR"]["fuzzy_search"]}
levels = (0.01, 0.02, 0.03, 0.05, 0.08, 0.12)

[rows[s]["recall@1"] for s in levels]                        # [0.452, 0.678, 0.737, 0.737, 0.749, 0.806]
[rows[s]["candidate_recall"] for s in levels]                # [0.512, 0.768, 0.84, 0.84, 0.858, 0.924]
[round(rows[s]["mean_candidates"], 1) for s in levels]       # [14.7, 45.4, 58.8, 60.4, 139.4, 170.1]
```

The first list is the share of queries whose first result is the right word. The second is the share of queries whose right word is among the candidates. The third is the mean number of candidates per query. Neither recall value falls as the sensitivity rises, and the candidate count rises faster. The mean of recall at 1 over the four pairs of the benchmark (English, Portuguese, Spanish and Armenian dialects) is:

```python
[round(sum(p["fuzzy_search"][i]["recall@1"] for p in pairs.values()) / len(pairs), 4) for i in range(6)]   # [0.7601, 0.8166, 0.8323, 0.8323, 0.8348, 0.8521]
```

## 6. Choose a sensitivity

The default is 0.08. A rule chooses it on the development results. The rule is rule 7 of [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md), applied to these six values: 0.01, 0.02, 0.03, 0.05, 0.08 and 0.12. Take the value with the highest mean recall at 1 among the values whose mean candidate count is at most 5% of the index pronunciations in every pair. The test data played no part in the choice.

This block gives, for each value, the largest share of the index that a query returns over the four pairs:

```python
share = lambda p, i: p["fuzzy_search"][i]["mean_candidates"] / p["counts"]["index_prons"]
[round(max(share(p, i) for p in pairs.values()), 4) for i in range(6)]   # [0.0038, 0.0045, 0.0057, 0.0057, 0.0134, 0.0162]
```

Every value stays below 5%, so the cap removes none. The values 0.08 and 0.12 share the highest mean recall at 1, 0.8521. The rule does not name a tie-break. The lower share wins, because it returns fewer candidates for the same recall: at 0.08 the largest share is 1.4%, and at 0.12 it is 1.6%.

[Index](index.md) · Previous: [Tones](tones.md) · Next: [Add a segment](add-a-segment.md)
