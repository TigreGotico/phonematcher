# Tones
<!-- agent-hint
covers: how phonematcher reads a tone as its own segment and prices a tone against a tone, a phone or nothing
source: phonematcher/tone.py, phonematcher/distance.py:substitution_cost
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k tones.md
see: compare-words.md, features.md
-->

This page shows how a tone enters a word distance. A tone is a segment of its own, not a feature of its vowel.

The tone distance is experimental. On the 15 Cantonese tone pairs of the benchmark it ranks tone confusions worse than a baseline that compares only the direction of the contour (issue [#68](https://github.com/TigreGotico/phonematcher/issues/68)). The numbers come from `benchmarks/results/tone-seen.json`. Run this block from the root of a clone of the repository, because the file is not in the installed package:

```python
import json

scored = json.load(open("benchmarks/results/tone-seen.json"))["scored"]["main"]
round(scored["phonematcher"]["score"], 4)                                  # 0.2475
[round(scored["phonematcher"]["interval"][k], 4) for k in ("low", "high")]  # [-0.3167, 0.7396]
round(scored["direction_baseline"]["score"], 4)                            # 0.7817
[round(scored["direction_baseline"]["interval"][k], 4) for k in ("low", "high")]  # [0.4554, 0.886]
```

The data was seen during the work, and the 15 pairs do not show that the baseline is better. They show that the tone distance does not beat it.

## 1. Write a tone

A tone is a run of tone letters after its syllable. Each letter is a pitch level from 1 (`˩`, extra low) to 5 (`˥`, extra high). The tone letters, the tone diacritics and the superscript digits give the same segments:

```python
from phonematcher import segments

segments("ma˦")      # ['m', 'a', '˦']
segments("má")       # ['m', 'a', '˦']
segments("ma⁴")      # ['m', 'a', '˦']
segments("ma˧˥")     # ['m', 'a', '˧˥']
segments("ma²¹⁴")    # ['m', 'a', '˨˩˦']
```

A rising tone is two letters in one segment. A word without a tone has no tone segment:

```python
segments("ma")       # ['m', 'a']
```

## 2. Compare two tones

Two tones are compared by their pitch at the start, the middle and the end of the syllable. `tone_distance` is the mean difference of the three pitches, divided by four, the range from `˩` to `˥`.

```python
from phonematcher.tone import tone_distance

tone_distance("˥", "˦")      # 0.25
tone_distance("˥", "˩")      # 1.0
tone_distance("˧˥", "˥˩")    # 0.583
```

A word distance uses the square root of the tone distance, as it does for two phones:

```python
from phonematcher import ipa_distance

ipa_distance("ma˥", "ma˦")     # 0.5
ipa_distance("ma˥", "ma˩")     # 1.0
ipa_distance("ma˧˥", "ma˥˩")   # 0.764
ipa_distance("ma˥", "ma˥")     # 0.0
```

## 3. A tone against a sound, or against nothing

A tone against a phone costs 1, the largest cost of a substitution. It is the same as deleting one segment and inserting the other (2 × 0.5):

```python
from phonematcher.distance import substitution_cost

substitution_cost("˥", "˦")    # 0.5
substitution_cost("˥", "a")    # 1.0
```

When two pairings cost the same, `align` prefers the substitution. It pairs the tone with the phone, and the distance is the same either way:

```python
from phonematcher import align, segments

align(segments("ma˥"), segments("mab"))      # [('m', 'm'), ('a', 'a'), ('˥', 'b')]
ipa_distance("ma˥", "mab")                   # 1.0
```

A missing tone costs 0.5, as a missing sound does:

```python
ipa_distance("ma˥", "ma")      # 0.5
```

## 4. Tones in a search

The search index ignores tones, so a query finds a word with any tone. The score still ranks the same tone first:

```python
from phonematcher import PhoneticFuzzySearch

search = PhoneticFuzzySearch()
search.add_term("ma˥", "mother")
search.add_term("ma˩˥", "hemp")
[(m.id, round(m.score, 3)) for m in search.search("ma˥")]   # [('mother', 0.0), ('hemp', 0.707)]
```

## Marks that are not read

Downstep `ꜜ`, upstep `ꜛ`, global rise `↗`, global fall `↘` and the neutral-tone numeral `⁰` change the pitch of a phrase, not of one syllable. `segments` drops them, as it drops stress marks:

```python
segments("ma⁰")      # ['m', 'a']
```

[The feature table](features.md#tone) gives the chart name of each tone diacritic.

[Index](index.md) · Previous: [Compare two words](compare-words.md) · Next: [Search by sound](search.md)
