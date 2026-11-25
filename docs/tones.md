# Tones
<!-- agent-hint
covers: how phonematcher reads a tone as four features of its vowel, and a tone with no vowel as a segment of its own
source: phonematcher/tone.py, phonematcher/features.py, phonematcher/distance.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k tones.md
see: compare-words.md, features.md
-->

This page shows how a tone enters a word distance. A tone is four features of the vowel that carries it.

The tone distance between two tones is experimental. On the 15 Cantonese tone pairs of the benchmark it ranks tone confusions worse than a baseline that compares only the direction of the contour ([tracked in an open issue](https://github.com/TigreGotico/phonematcher/issues/68)). The tone features rank the 15 pairs in the same order, so the same limit holds for them. [Design choices and limits](design.md#the-tone-distance) gives the reading of the numbers. They come from `benchmarks/results/tone-seen.json`. Run this block from the root of a clone of the repository, because the file is not in the installed package:

```python
import json

scored = json.load(open("benchmarks/results/tone-seen.json"))["scored"]["main"]
round(scored["phonematcher"]["score"], 4)                                  # 0.2475
round(scored["phonematcher_features"]["score"], 4)                         # 0.2475
[round(scored["phonematcher"]["interval"][k], 4) for k in ("low", "high")]  # [-0.3167, 0.7396]
round(scored["direction_baseline"]["score"], 4)                            # 0.7817
[round(scored["direction_baseline"]["interval"][k], 4) for k in ("low", "high")]  # [0.4554, 0.886]
```

## 1. Write a tone

A tone is a run of tone letters after its syllable. Each letter is a pitch level from 1 (`˩`, extra low) to 5 (`˥`, extra high). `segments` puts the tone on the vowel. The tone letters, the tone diacritics and the superscript digits give the same segments:

```python
from phonematcher import segments

segments("ma˦")      # ['m', 'a˦']
segments("má")       # ['m', 'a˦']
segments("ma⁴")      # ['m', 'a˦']
segments("ma˧˥")     # ['m', 'a˧˥']
segments("ma²¹⁴")    # ['m', 'a˨˩˦']
```

A tone after a coda goes to the vowel before the coda. A syllabic consonant carries a tone too:

```python
segments("tam˧˧")    # ['t', 'a˧˧', 'm']
segments("pz̩˥")      # ['p', 'z̩˥']
```

A tone with no vowel or syllabic consonant before it in its word stays a segment of tone letters:

```python
segments("˥˩")       # ['˥˩']
segments("ɡ˩a")      # ['ɡ', '˩', 'a']
```

A vowel carries one tone. Sandhi notation writes the underlying tone in tone letters and the surface tone after it in left-stem letters. The first tone goes onto the vowel, and the surface tone stays a tone segment of its own:

```python
segments("ni˨˩˦꜔꜒")  # ['n', 'i˨˩˦', '˧˥']
```

## 2. Read the tone features

The last four features of a vector are the tone. `tone_is` is `True` on a toned vowel. The three pitches are the start, the middle and the end of the syllable, each Chao level as (level − 3) / 2:

```python
from phonematcher import FEATURES, vectorize_phones

FEATURES[-4:]                    # ('tone_is', 'tone_start', 'tone_mid', 'tone_end')
vectorize_phones("a˧˥")[-4:]     # (True, 0.0, 0.5, 1.0)
vectorize_phones("a˨˩˦")[-4:]    # (True, -0.5, -1.0, 0.5)
vectorize_phones("a")[-4:]       # (None, None, None, None)
```

## 3. Compare two toned vowels

Two toned vowels are compared by all their features. Each pitch adds its weight times half the pitch difference:

```python
from phonematcher import feature_distance, ipa_distance

feature_distance("a˥", "a˦")     # 0.01
feature_distance("a˥", "a˩")     # 0.039
ipa_distance("ma˥", "ma˦")       # 0.099
ipa_distance("ma˥", "ma˩")       # 0.199
ipa_distance("ma˧˥", "ma˥˩")     # 0.152
ipa_distance("ma˥", "ma˥")       # 0.0
```

A missing tone costs `tone_is` at half its weight, plus each pitch at half its weight times its distance from 0, the middle level. A missing tone thus costs less than a missing sound:

```python
ipa_distance("ma˥", "ma")        # 0.181
ipa_distance("ma˧", "ma")        # 0.115
ipa_distance("ma", "m")          # 0.5
```

## 4. A tone segment of its own

A tone with no vowel stays a segment. Two such tones are compared by `tone_distance`, the mean pitch difference at the start, the middle and the end, divided by four:

```python
from phonematcher.tone import tone_distance

tone_distance("˥", "˦")      # 0.25
tone_distance("˥", "˩")      # 1.0
tone_distance("˧˥", "˥˩")    # 0.583
ipa_distance("˥", "˦")       # 0.5
```

A tone segment against a phone costs 1, the largest cost of a substitution. It is the same as deleting one segment and inserting the other (2 × 0.5):

```python
from phonematcher.distance import substitution_cost

substitution_cost("˥", "˦")    # 0.5
substitution_cost("˥", "a")    # 1.0
substitution_cost("˥", "a˥")   # 1.0
```

## 5. Tones in a search

The search index ignores tones, so a query finds a word with any tone. The score still ranks the same tone first:

```python
from phonematcher import PhoneticFuzzySearch

search = PhoneticFuzzySearch()
search.add_term("ma˥", "mother")
search.add_term("ma˩˥", "hemp")
[(m.id, round(m.score, 3)) for m in search.search("ma˥")]   # [('mother', 0.0), ('hemp', 0.14)]
```

## Marks that are not read

Downstep `ꜜ`, upstep `ꜛ`, global rise `↗`, global fall `↘` and the neutral-tone numeral `⁰` change the pitch of a phrase, not of one syllable. `segments` drops them, as it drops stress marks:

```python
segments("ma⁰")      # ['m', 'a']
```

[The feature table](features.md#tone) gives the chart name of each tone diacritic.

[Index](index.md) · Previous: [Compare two words](compare-words.md) · Next: [Search by sound](search.md)
