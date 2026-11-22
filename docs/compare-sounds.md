# Compare two sounds
<!-- agent-hint
covers: how to measure the distance between two IPA segments and why it has that value
source: phonematcher/features.py:phonetic_distance, phonematcher/data/features.json
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k compare-sounds.md
see: compare-words.md, features.md
-->

This page measures the distance between two sounds, then shows where the number comes from. Each step prints its real result.

## 1. Ask for a distance

`phonetic_distance` takes two segments and returns a number from 0 to 1. Zero means the same features. One means the farthest.

```python
from phonematcher import phonetic_distance

phonetic_distance("p", "b")   # 0.013
phonetic_distance("p", "t")   # 0.059
phonetic_distance("i", "e")   # 0.053
phonetic_distance("i", "a")   # 0.132
phonetic_distance("k", "ʔ")   # 0.25
```

`p` and `b` differ only in voice, so they are close. `p` and `t` differ in place. `i` is nearer to `e` than to `a`. Two vowels differ on as many height steps (`h1` to `h6`) as there are chart rows between them. The next block lists the features that differ.

```python
from phonematcher.features import FEATURES, vectorize_phones

def differing(a, b):
    return [f for f, x, y in zip(FEATURES, vectorize_phones(a), vectorize_phones(b)) if x != y]

differing("i", "e")   # ['hi', 'h1', 'h2']
differing("e", "a")   # ['lo', 'h3', 'h4', 'h5', 'h6']
```

From `i` to `e` the chart has two rows, so two steps differ. From `e` to `a` it has four rows. The features `hi` and `lo` also change, because `i` is high and `a` is low.

## 2. Read the features behind a number

Each segment is a vector of 36 features. `vectorize_phones` returns it. Put the vectors of `p` and `b` side by side and keep the features that differ:

```python
from phonematcher.features import FEATURES, WEIGHTS, vectorize_phones

p, b = vectorize_phones("p"), vectorize_phones("b")
[(f, x, y, w) for f, x, y, w in zip(FEATURES, p, b, WEIGHTS) if x != y]   # [('voi', False, True, 0.125)]
```

One feature differs: voice (`voi`). Its weight is 0.125. All weights add up to 9.5, so the distance is the weight divided by that sum:

```python
sum(WEIGHTS)           # 9.5
0.125 / sum(WEIGHTS)   # 0.013
```

## 3. Count a feature that does not apply

A feature has three values: `True` (+), `False` (−) and `None` (0, it does not apply). A difference between + and − costs the full weight. A difference between 0 and + or − costs half the weight. The total is divided by the sum of all weights.

The vowel `a` and its nasal `ã` differ in the feature `nas` only. The nasal mark sets it from − to +:

```python
phonetic_distance("a", "ã")   # 0.026
phonetic_distance("a", "aː")  # 0.013
phonetic_distance("t", "tʰ")  # 0.013
```

`nas` weighs 0.25, so `a` and `ã` are at 0.25 / 9.5. The length mark and the aspiration mark each change a feature of weight 0.125, so those pairs are at 0.125 / 9.5.

## 4. A segment the table cannot read

`vectorize_phones` raises `ValueError` for a segment that is not in the table. `phonetic_distance` does not raise. It puts the segment at distance 1 from every other segment.

```python
try:
    vectorize_phones("ʞ")
except ValueError as error:
    print(error)

phonetic_distance("p", "ʞ")   # 1.0
```

```text
Unrecognized phone 'ʞ'
```

## Next

[The feature table](features.md) lists all 36 features with their weights and sources. [Compare two words](compare-words.md) uses this distance for whole words.

[Index](index.md) · Previous: [Quickstart](quickstart.md) · Next: [Compare two words](compare-words.md)
