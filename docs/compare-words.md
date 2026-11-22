# Compare two words
<!-- agent-hint
covers: how to measure the distance between two IPA strings, align them and normalize the result
source: phonematcher/distance.py:ipa_distance, phonematcher/distance.py:align, phonematcher/distance.py:segments
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k compare-words.md
see: compare-sounds.md, tones.md, search.md, benchmarks.md
-->

This page measures the distance between two IPA strings, shows which sound matches which, and scales the result by word length.

## 1. Split a word into segments

`segments` cuts an IPA string into sounds. A diacritic stays with its base letter, and a tie bar joins two symbols into one affricate. Stress marks are dropped.

```python
from phonematcher import segments

segments("ˈkaza")      # ['k', 'a', 'z', 'a']
segments("ˈt͡ʃɐ̃w̃")   # ['t͡ʃ', 'ɐ̃', 'w̃']
```

## 2. Measure one change

The strings `ˈkaza` and `ˈkasa` differ in one sound, `z` against `s`:

```python
from phonematcher import ipa_distance

ipa_distance("ˈkaza", "ˈkasa")   # 0.115
```

The cost of a substitution is the square root of the feature distance of the two sounds. Here `feature_distance("z", "s")` is 0.013, and its square root is 0.115:

```python
from phonematcher import feature_distance

feature_distance("z", "s")        # 0.013
feature_distance("z", "s") ** 0.5  # 0.115
```

A change to a vowel costs the same way. `a` against `ɐ` is a near substitution:

```python
ipa_distance("ˈmesa", "ˈmesɐ")   # 0.199
```

## 3. Measure an extra or a missing sound

An insertion costs 0.5, and so does a deletion. The cost does not depend on the sound:

```python
ipa_distance("kasa", "kasas")   # 0.5
ipa_distance("kasa", "kasa")    # 0.0
```

A substitution costs at most 1. It never costs more than a deletion plus an insertion.

## 4. See which sound matches which

`align` returns the least-cost pairing of the segments of two words. `None` marks a gap.

```python
from phonematcher import align

align(segments("kat"), segments("kaʃt"))   # [('k', 'k'), ('a', 'a'), (None, 'ʃ'), ('t', 't')]
```

The sound `ʃ` has no partner in `kat`, so it is a gap. Two words that differ in more places show the pairing better:

```python
pairs = align(segments("ˈkaza"), segments("ˈpoʁtɐ"))
pairs   # [('k', 'p'), ('a', 'o'), (None, 'ʁ'), ('z', 't'), ('a', 'ɐ')]
```

The cost of an alignment is the sum of the cost of each pair: 0.5 for a pair with a gap, and the substitution cost for the others. The sum is the distance that `ipa_distance` returns:

```python
from phonematcher.distance import GAP_COST, substitution_cost

total = sum(GAP_COST if None in pair else substitution_cost(*pair) for pair in pairs)
total                                   # 1.733
ipa_distance("ˈkaza", "ˈpoʁtɐ")        # 1.733
```

## 5. Scale by length

A distance of 0.5 is large for a word of two sounds and small for a word of ten. Pass `normalized=True` to divide the distance by the segment count of the longer word. The result is from 0 to 1.

```python
ipa_distance("kasa", "kasas")                   # 0.5
ipa_distance("kasa", "kasas", normalized=True)  # 0.1
ipa_distance("ˈkaza", "ˈpoʁtɐ", normalized=True)   # 0.347
ipa_distance("", "", normalized=True)           # 0.0
```

Two empty strings are at distance 0.

## Where the costs come from

The insertion and deletion cost of 0.5 and the square root of the feature distance for a substitution are the values that a pre-registered test chose. The test is `benchmarks/prereg-2.md`. Its results are in [Benchmarks](benchmarks.md).

[Index](index.md) · Previous: [Compare two sounds](compare-sounds.md) · Next: [Tones](tones.md)
