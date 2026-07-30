# The distinctive-feature matrix

Every articulatory judgment `phonematcher` makes traces back to one table:
`phonematcher.distance.phone_features`. It maps each IPA phone to a vector
of `NUM_FEATURES` (21) distinctive features. This page explains what those
slots mean and how `phonetic_distance` reads them.

## Why features instead of letters

Distinctive-feature theory describes a sound not as an atom, but as a
bundle of binary articulatory properties: is it voiced, is it nasal, where
in the mouth is it made. Two sounds that share most features sound similar.
By comparing feature vectors rather than symbols, the library knows that
`p` and `b` differ only in voicing, while `a` and `k` share almost nothing.

## The 21 features, in order

Each vector position is `True`, `False`, or `None` (the feature does not
apply to that phone's class).

| # | Feature | Meaning |
| --- | --- | --- |
| 0 | syllabic | forms a syllable nucleus (vowels) |
| 1 | sonorant | produced without turbulent airflow |
| 2 | consonantal | major-class consonant |
| 3 | continuant | airflow not fully blocked (fricatives yes, stops no) |
| 4 | delayed_release | affricate-style release |
| 5 | lateral | air flows around the sides of the tongue |
| 6 | nasal | air escapes through the nose |
| 7 | strident | high-amplitude noise (sibilants) |
| 8 | voice | vocal folds vibrate |
| 9 | spread_glottis | aspiration |
| 10 | constricted_glottis | ejective or creaky |
| 11 | anterior | constriction at or in front of the alveolar ridge |
| 12 | coronal | made with the tongue tip or blade |
| 13 | distributed | constriction extended along the airflow |
| 14 | labial | involves the lips |
| 15 | high | tongue body raised |
| 16 | low | tongue body lowered |
| 17 | back | tongue body retracted |
| 18 | round | lips rounded |
| 19 | tense | tense vs. lax (vowels) |
| 20 | long | lengthened |

## Reading a vector

`vectorize_phones` returns the vector for a phone, and applies any
diacritic modifiers on top of the base:

```python
from phonematcher.distance import vectorize_phones, NUM_FEATURES

vec = vectorize_phones("a")
len(vec) == NUM_FEATURES        # True, always 21 entries

long_a = vectorize_phones("aː")
long_a[20] is True              # length mark sets feature 20 (long)
```

Modifiers overwrite specific slots. A length mark `ː` sets feature 20.
Rhoticization `˞` rewrites the anterior, high, and round positions. Unknown
phones raise `ValueError`:

```python
vectorize_phones("???")   # ValueError: Unrecognized phone '?'
```

## How distance uses the vectors

`phonetic_distance` does not weight all 21 features equally. It separates
vowels from consonants (a vowel-vs-consonant pair is hard-coded to `1.0`),
picks the feature subset relevant to that class, sums the weighted
mismatches, and normalizes by the total possible weight, so the result
lands in `[0, 1]`. Major-class distinctions count for more than fine ones.
That is why a voicing flip is small and a place-of-articulation flip is
larger:

```python
from phonematcher.distance import phonetic_distance

phonetic_distance("b", "p")   # 0.043, only feature 8 (voice) differs
phonetic_distance("p", "k")   # 0.348, same manner, different place
phonetic_distance("a", "k")   # 1.0, vowel vs consonant
```

This is the metric `PhoneticFuzzySearch` clusters over. Phones whose
vectors sit within `cluster_sensitivity` of each other merge into one
cluster, and those cluster IDs are what the index actually stores.

## Extending the table

If a custom mapping needs a phone the table does not yet carry,
`vectorize_phones` raises before clustering can finish. Either add the
phone to `phone_features` with a correct 21-element vector, register a
normalization alias in `_bad_phones` that points it at an existing phone,
or emit an already-supported phone from the mapping instead. Validate a
mapping against the table before building a search over it. See
[Custom mappings for a new language](advanced.md#custom-mappings-for-a-new-language).

---
[← Quickstart](quickstart.md) · [Home](../README.md) · [API reference →](api.md)
