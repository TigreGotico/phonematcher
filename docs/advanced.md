# Advanced usage

Recipes, tuning, and the sharp edges worth knowing before you build on
`phonematcher`.

## Build once, search many

Constructing a `PhoneticFuzzySearch` clusters every phone in the mapping by
computing the full pairwise `phonetic_distance` matrix, O(n²) in the
number of distinct phones. That work happens in `__init__`, not in
`search()`.

```python
from phonematcher.clustering import PhoneticFuzzySearch, PT_MAPPING

ffs = PhoneticFuzzySearch(PT_MAPPING)   # cluster once
for term, tid in [("pão com queijo", 0), ("coração", 1)]:
    ffs.add_term(term, tid)

ffs.search("pao")          # cheap
ffs.search("corasao")      # cheap
```

Treat the instance as a long-lived index. Rebuilding it per query throws
away the clustering work every time.

## Tuning `cluster_sensitivity`

The threshold controls how readily two phones merge into one cluster.

```python
precise = PhoneticFuzzySearch(PT_MAPPING, cluster_sensitivity=0.3)
recall  = PhoneticFuzzySearch(PT_MAPPING, cluster_sensitivity=0.6)
```

- Low (around 0.3): tight clusters, fewer false matches. Good for
  phonetically spelled languages (Portuguese, Spanish, Italian), where
  spelling already tracks sound.
- High (0.5-0.6): broad clusters, more recall. Good for English or French,
  where one sound is spelled many ways and you want those spellings to
  collide.

You can inspect the clustering directly to see what merged:

```python
ffs = PhoneticFuzzySearch(PT_MAPPING, cluster_sensitivity=0.5)
ffs.clusters["s"], ffs.clusters["z"]   # two phone-to-cluster-id lookups
```

## Custom mappings for a new language

A mapping is just `dict[str, list[str]]`: grapheme to candidate IPA
phones. Inherit `BASE_LATIN` for the common letters and override the parts
your language spells differently. Include every sound a grapheme can
make. The expander indexes all of them, which is what makes the match
fuzzy.

```python
from phonematcher.clustering import PhoneticFuzzySearch, BASE_LATIN

MY_LANG = {
    **BASE_LATIN,
    "sh": ["ʃ"],     # digraph
    "aa": ["aː"],    # long vowel
    "x":  ["ʃ", "ks", "z", "s"],   # one grapheme, several sounds
}

ffs = PhoneticFuzzySearch(mapping=MY_LANG, cluster_sensitivity=0.4)
```

Constraint: every phone your mapping emits must exist in the feature table
(`phonematcher.distance.phone_features`) or in its normalization aliases.
`vectorize_phones` raises `ValueError` on an unknown phone, and clustering
calls it for every phone in the set. Validate a candidate mapping up
front:

```python
from phonematcher.distance import vectorize_phones
from phonematcher.clustering import PhoneticFuzzySearch

for phone in sorted(PhoneticFuzzySearch.get_phone_set(MY_LANG)):
    if not phone:
        continue                      # empty string means "silent", allowed
    vectorize_phones(phone)           # raises ValueError if unsupported
```

## Eudex ranking

By default, candidates retrieved by the phonetic index rank by Levenshtein
edit distance. Switch the ranker to the Eudex phonetic hash when you want
the ranking, not just the retrieval, to be sound-aware:

```python
ffs = PhoneticFuzzySearch(EN_MAPPING, use_eudex=True, eudex_threshold=100)
ffs.add_term("through", 0)
ffs.search("thru")
```

`eudex_threshold` scales the raw Eudex score into the `score` field. Raise
it to compress scores, lower it to spread them. The Eudex primitives are
usable on their own for word-level sound comparison:

```python
from phonematcher.eudex import Hash

(Hash("maier") - Hash("meyer")).similar()    # True, sound alike
(Hash("horse") - Hash("norse")).similar()    # False, onset differs
(Hash("lizzard") - Hash("wizzard")).dist()   # graduated distance, int
```

## Phone distance as a standalone metric

You do not need the search class to use the articulatory distance. It is
a plain function over IPA symbols and is useful for any task that needs
"how close are these two sounds":

```python
from phonematcher.distance import phonetic_distance, is_vowel_phone

phonetic_distance("ʃ", "s")    # sibilants, close
phonetic_distance("m", "n")    # nasals, close
is_vowel_phone("a")            # True
is_vowel_phone("k")            # False
```

Because it is normalized to `[0, 1]`, you can drop it straight into a
clustering or nearest-neighbor routine of your own.

## Gotchas

- **Multi-word queries intersect.** `search("a b")` keeps only terms
  matched by both words. A single mistyped word that matches nothing drops
  the whole candidate. Search word-by-word if you want a union instead.
- **`score` direction.** Lower is better; results are sorted ascending. Do
  not treat `score` as a similarity. It is a distance.
- **`vectorize_phones` raises on unknown phones**, and clustering calls it
  for every phone in your mapping. A typo in a mapping fails loudly at
  construction time, which is the behavior you want. Validate as shown
  above.
- **`Result` namedtuple is typed `Result` but bound to `Match`** inside the
  module. Access by field name (`.id`, `.term`, `.score`) and the
  distinction never matters.

---
[← API reference](api.md) · [Home](../README.md)
