# Quickstart — sound-alike search in five minutes

`phonematcher` finds words that *sound like* a query instead of words that
*look like* it. It does this by turning letters into IPA phones, measuring how
close those phones are using distinctive-feature theory, and matching on the
resulting sound clusters rather than raw characters.

## 1. Install

```bash
pip install rapidfuzz   # the only runtime dependency
pip install -e .        # editable install of phonematcher itself
```

## 2. The one idea

A word is not a string of letters — it is a sequence of *sounds*. Two letters
can spell the same sound (`c` and `k`), and one letter can spell several
(`x` → `ʃ`, `ks`, `z`, `s`). `phonematcher` maps each grapheme to its possible
IPA phones, groups phones that are articulatorily close into numbered
**clusters**, and indexes a term by its cluster sequence. A misspelling that
*sounds* the same lands on the same clusters, so it still matches.

You drive this through one class — `PhoneticFuzzySearch` — fed a
grapheme-to-IPA `mapping` for the language you care about:

```python
from phonematcher.clustering import PhoneticFuzzySearch, PT_MAPPING

ffs = PhoneticFuzzySearch(PT_MAPPING)
ffs.add_term("pão com queijo", 0)
ffs.add_term("coração batendo", 1)

for match in ffs.search("pao com keijo"):
    print(match.id, match.term, match.score)
# 0 pão com queijo 3
```

`search()` returns a list of `Result(id, term, score)` namedtuples, lowest
`score` first. The phonetic index found the candidate; `score` is the
Levenshtein edit distance used to rank it.

## 3. The other half: phone distance

Underneath the search sits an articulatory distance between any two IPA phones.
It knows that a voiced/voiceless pair is nearly identical and a vowel/consonant
pair is maximally far apart:

```python
from phonematcher.distance import phonetic_distance

phonetic_distance("b", "p")   # 0.043  — same place, only voicing differs
phonetic_distance("p", "k")   # 0.348  — both stops, different place
phonetic_distance("a", "k")   # 1.0    — vowel vs consonant, maximal
```

Every value is normalized to `[0.0, 1.0]`. This is the metric the clusterer
runs over to decide which phones share a cluster.

## 4. Pick your language

`phonematcher.clustering` ships grapheme-to-IPA mappings for ~22 languages,
each a plain dict you can read and extend: `EN_MAPPING`, `PT_MAPPING`,
`ES_MAPPING`, `FR_MAPPING`, `DE_MAPPING`, `NL_MAPPING`, `IT_MAPPING`,
`RU_MAPPING`, `AR_MAPPING`, `ZH_MAPPING`, `JP_MAPPING`, and more, all built on a
shared `BASE_LATIN` table.

```python
from phonematcher.clustering import PhoneticFuzzySearch, EN_MAPPING

ffs = PhoneticFuzzySearch(EN_MAPPING)
ffs.add_term("knight in shining armor", 0)
print(ffs.search("nite in shinin armur")[0].term)
# knight in shining armor
```

## 5. Tune recall vs precision

One knob — `cluster_sensitivity` (default `0.5`) — decides how aggressively
phones merge into shared clusters:

```python
strict  = PhoneticFuzzySearch(PT_MAPPING, cluster_sensitivity=0.3)  # precise
relaxed = PhoneticFuzzySearch(PT_MAPPING, cluster_sensitivity=0.6)  # high recall
```

Highly phonetic spelling (Portuguese, Spanish, Italian) tolerates a low value;
languages with tangled spelling-to-sound rules (English, French) want it higher
so divergent spellings collapse into the same cluster.

## Where next

- [api.md](api.md) — every public class, function, kwarg, and return shape
- [advanced.md](advanced.md) — custom mappings, Eudex ranking, gotchas, recipes
- [features.md](features.md) — the distinctive-feature matrix that powers distance
