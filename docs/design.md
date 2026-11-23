# Design choices and limits
<!-- agent-hint
covers: why the feature table, the tone model and the word costs are as they are, and what does not read
source: docs/features.md, phonematcher/distance.py, phonematcher/tone.py, benchmarks/results/*.json, benchmarks/prereg-2.md
generated: no; the numbers are checked against the result files by tests/test_design.py
verify: pytest --import-mode=importlib tests/test_design.py
see: features.md, benchmarks.md, api.md
-->

This page lists the choices of phonematcher that a reader can contest. For each choice it names the alternatives, the one taken and the source or test behind it. It ends with what the library does not read and what the evidence does not show.

A source named here is one that was opened and read. Where a choice has no source, the page says that the choice is this table's own.

## Choices

### Vowel height as chart steps

PanPhon gives a vowel two height features, `hi` and `lo`, so it knows three heights. The IPA chart draws seven rows. The table keeps `hi` and `lo` and adds six step features, `h1` to `h6`. A vowel is + on `h1` when it lies below close, + on `h2` when it lies below near-close, and so on. Two vowels differ on as many steps as there are chart rows between them.

The alternatives are `hi` and `lo` alone, or one numeric height. Steps keep every feature a plus, a minus or a zero, as PanPhon does. The source is the IPA chart, which fixes the rows (`docs/features.md`, "Vowels").

The evidence is thin. On the Hillenbrand vowel confusions, the weighted table scores 0.5610. The same table with zero weight on the steps scores 0.5340. The 22 features of PanPhon 0.22.2 score 0.4153. The intervals of the three overlap, and the data was seen during the work. On the six cognate test sets, under the C0 word costs (gap 1, linear substitutions), the variant with zero weight on the steps differs from the shipped table by -0.0002, with an interval from -0.0013 to +0.0008. On the development split, under the shipped word costs (gap 0.5, square-root substitutions), the cognate AP of the variant with zero weight on the steps is 0.7725 and the shipped table's is 0.7727. The steps are kept because the chart has seven rows, not because a test showed that they help cognate detection.

The table keeps both codings, a trade-off that was measured. A form with one encoding sets `hi` and `lo` to 0 on every vowel, so the steps alone carry height and the distance stays a weighted L1 over fixed vectors. It is a metric. On the development split it changed the paired cognate AP by -0.0006, with an interval from -0.0012 to -0.0001, and the alignment PAS by +0.0039, with an interval from +0.0011 to +0.0066. On the Hillenbrand confusions it lowered the Spearman correlation from 0.5610 to 0.5474. The rule for changes made after the test run refuses a change when the interval of any development task lies wholly below 0, and the cognate interval does.

A second form drops `hi` and `lo` only when both segments are vowels. It breaks the triangle inequality on 875 of the 400,995 triples of table base letters. For `b`, `e` and `ɪ`, the feature distance of `b` and `ɪ` is 0.486842, and the way through `e` costs 0.460526 + 0.013158 = 0.473684, which is 0.013158 less. The cause is that `hi` still separates `b` from `ɪ`, and the two vowels no longer differ on it. A cost that is not a metric is not used.

The cognate, alignment and Hillenbrand numbers are in `benchmarks/results/ablations/vowel-height-dev.json` and `vowel-height-seen.json`, and `tests/test_design.py` ties this page to them. These development numbers use the shipped word costs. The paired test-set numbers on this page use the C0 costs, and `benchmarks/results/ablations-dev.json` holds the development ablations at the shipped costs. The triple count and the distances of the second form are not in a result file. They come from a run of the check on the development tree of version 1.0.0a3 (commit `ecde385`) over every unordered triple of the 135 base letters.

### Pharyngealization is its own feature

The mark `◌ˤ` and the mark `◌̙` (retracted tongue root) both involve the tongue root. One alternative reads them as one articulation, so `iˤ` equals `i̙`. The other adds a feature `pharyngealized`, and `◌ˤ` sets it, besides `atr` −. The table takes the second. `iˤ` and `i̙` share `atr` − and differ in `pharyngealized` alone.

Sources. McCarthy (1994, pp. 218–219) writes that the emphatics have a constriction in the upper pharynx, and that the so-called pharyngealized consonants of Arabic "should really be called uvularized". Hermes et al. (2017, p. 204) find a clear difference in place between pharyngeal and pharyngealized consonants. Al-Solami (2017, p. 25) reports tongue root and tongue dorsum retraction for emphatics, with inconsistent tongue root retraction. Casali (2007, p. 2) writes that expansion or contraction of the pharyngeal cavity measures [ATR] better than tongue root position alone, at least in languages like Akan (Lindau 1979). In Ateso, [ATR] is mainly tongue body raising. Retraction of the root is thus part of both marks, and the place of the main constriction is not the same.

The shared `atr` − encodes the overlap. The separate feature encodes the difference. No source read for this table shows one language that contrasts `iˤ` with `i̙`, so the choice rests on the two descriptions of the articulation and not on a contrast in one language. A test asserts that the two segments differ in `pharyngealized` and in no other feature.

### Marks that move a vowel along a scale

The marks `◌̝ ◌̞ ◌̟ ◌̠ ◌̈ ◌̽ ◌̹ ◌̜` move a vowel along the height, backness or rounding scale. PanPhon has no rule for most of them. The alternative is to read them as the bare letter. The table takes a rule for each mark, because the IPA chart names each mark and says what it moves. The size of the step, one chart row or column, is this table's own.

The rules change no score that the benchmarks measure. Under the C0 word costs (gap 1, linear substitutions), the variant with no scale shifts differs from the shipped table by less than 0.0001 in the paired cognate difference on the test sets. On the development split, under the shipped word costs, the cognate AP of that variant is 0.7726 and the shipped table's is 0.7727. The rules stay for the sake of the chart's meaning, and the benchmarks do not support them or oppose them.

### A mark reads only on the bases a chart prints it on

`k̃`, `m̃`, `aʰ` and `ʉʰ` do not read. The alternative is to apply every mark to every base. The table applies a mark only to the class of base that a chart prints it on, and `vectorize_phones` raises `ValueError` for any other base. The rule widens only when a chart prints the mark on the new class. A name in a code chart with no base does not widen it. The source is the IPA chart and the extIPA chart. The cost is lower coverage, listed below. The gain is that no reading is a guess.

### A diphthong is two segments

A diphthong written whole, as `ai`, has no vector. `segments` splits `a͡i` into `a` and `i`. The alternatives are one segment with a start vector and an end vector, one segment compared by its nucleus only, and one segment aligned against two. The table takes two segments, because the word distance needs no new rule: a diphthong costs as two segments, and `a͡i` against `a` costs one deletion. The choice follows Nerbonne and Heeringa (1997, p. 11), who found that "two-phone representations of diphthongs provide a more satisfactory base" for dialect distance. The sources do not agree. Heeringa (2004, p. 188) found that "it seems to make no difference whether diphthongs are represented as two segments or as one segment". Rubehn et al. (2024, p. 209) take the other choice: "feature vectors for diphthongs are based on their initial segments", so a diphthong is one segment.

### Tone is its own segment

PanPhon has two tone columns, `hitone` and `hireg`, and this table does not use them. A tone is one segment of tone letters after the syllable that carries it. `má` and `ma˦` both give `m`, `a`, `˦`. The alternatives are a tone feature on the vowel, and dropping tones. A segment keeps the feature table free of pitch and lets the edit distance align a tone with a tone. The tone letters and diacritics, and the readings of the diacritics as letters, come from the box "Tones and word accents" of the IPA chart.

### A tone against a phone costs 1

A tone and a phone have no feature in common, so no feature distance exists. The substitution cost of a tone and a phone is 1. A deletion and an insertion cost 0.5 each, so the substitution ties with a deletion plus an insertion. `align` prefers the substitution on a tie, so it can pair a tone with a phone, at the same total cost, as [Tones](tones.md) shows for `ma˥` and `mab`. A missing tone costs the same as a missing sound. This is a choice of this table, and a test asserts the two equal costs.

### The tone distance

The tone distance is experimental. On the one tone data set that exists for it, it does not beat a baseline that compares only direction (issue [#68](https://github.com/TigreGotico/phonematcher/issues/68)). A word distance that holds tones uses it, so treat the cost of a tone against a tone as a first model and not as a measured one.

Two tones are compared by their pitch at the start, the middle and the end of the syllable. The distance is the mean difference divided by four, the range of the five levels, and the substitution cost is its square root.

This is a limit, not a result. The benchmark has 15 tone pairs of Cantonese. It correlates the negative distance with the rate at which listeners confuse the two tones. The tone distance scores a Spearman 0.2475, with an interval from -0.3167 to 0.7396. A baseline that compares only the direction of the contour (rising, falling or level) scores 0.7817, with an interval from 0.4554 to 0.8860. With the alternative Chao values, the tone distance scores 0.3579. The intervals overlap, so 15 pairs do not show that the baseline is better. They show that the tone distance does not beat it. The two most confused pairs, T3 with T6 and T1 with T3, are level tones one or two steps apart. The data was seen, and no other tone data was tested.

### Two letters never share a vector

No two base letters of the table are at distance 0. A pair at distance 0 would be a synonym or a missing contrast. `tests/test_same_vector.py` reads 135 letters and fails when two letters share a vector, or when a collision is not reported as a group. The smallest distance between two letters is 0.0132. It is one feature of weight 0.125 out of a total of 9.5, and it separates `a` from `æ` on the step `h6`.

### PanPhon weights by name

PanPhon's weight file names `tense 0.25`, `long 0.125` and `velaric 0.25`. PanPhon's `FeatureTable` reads the numbers without the names and gives them in its own feature order, which ends `velaric, tense, long`. A PanPhon distance thus applies 0.25 to `velaric`, 0.125 to `tense` and 0.25 to `long`. The table takes the weights by the names in the file. The ablation that uses the weights PanPhon applies agrees with PanPhon on the 123256 pairs of segments whose 22 values equal PanPhon's, and differs on none of them. On all 727821 pairs that both systems read, 556665 differ, because the table changes some of PanPhon's values.

### An unread segment is at distance 1

A segment that cannot be read is at distance 1 from every other segment, and a word that holds one has no feature cost for it. The benchmarks score the unread pairs at distance 1 as the main view, and report a second view on the items that every system reads. The alternative is to drop the unread items. Dropping them would let a system that reads little score well on what it reads, so the main view charges for what a system cannot read.

The two views differ. On 12716 allophone items, the main view scores 0.8959. The view that skips the 224 items with an unread segment scores 0.9097 on the remaining 12492.

An unread segment costs as much as a missing one: its substitution against any other segment costs 1, the price of a deletion plus an insertion, and its insertion or deletion costs 0.5. Nothing signals that a segment went unread. Pass `strict=True` to `ipa_distance`, `edit_distance`, `align` or `PhoneticFuzzySearch` to get a `ValueError` that names the segment and the input:

```python
from phonematcher import ipa_distance

ipa_distance("ma", "maʅ")                  # 0.5
ipa_distance("ʅ", "a")                     # 1.0
try:
    ipa_distance("ma", "maʅ", strict=True)
except ValueError as error:
    print(error)
```

```text
cannot read the segment 'ʅ' in 'maʅ'
```

### The word costs

The edit distance prices a deletion and an insertion at 0.5. It prices a substitution at the square root of the segment distance. The alternatives came from a pre-registered test, [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md). Six candidates ran once on test data that no one had scored. C0 is the earlier rule: the table's weights, a gap cost of 1 and linear substitutions. C1 gives every feature weight 1. C2 also gives the vowel steps, backness and rounding one unit per dimension. C3 is C2 with a higher weight on the major-class features. P4 is C0 with a gap cost of 0.5. P5 is P4 with square-root substitutions. A candidate had to pass constraint K1 first: every pair of chart vowels is nearer than any chart vowel and any of `p b t d k ɡ q ʔ f v s z ʃ ʒ x χ h`. It then had to beat C0 on cognates and on retrieval, and not lose on alignment. The values are the paired differences from C0.

| Candidate | K1 | Cognates, AP | Alignment, PAS | Retrieval, R@1 |
|---|---|---|---|---|
| C1 | no | -0.0066 | -0.0205 | +0.0009 |
| C2 | no | -0.0066 | -0.0359 | -0.0035 |
| C3 | yes | -0.0061 | -0.0205 | -0.0039 |
| P4 | yes | +0.0289 | +0.0256 | +0.0255 |
| P5 | yes | +0.0709 | +0.0564 | +0.0696 |

P5 beat C0 on all three tasks and had the largest cognate difference, so the library uses it. The candidates P4 and P5 came from dev results, so only the test could decide between them and C0. The square root also keeps the cost a metric.

### One segment cost and a relative sensitivity

`substitution_cost` is the one cost of replacing a segment by another. The edit distance, the alignment and the clusters of the search all use it. `feature_distance` is the linear feature distance under its own name, and `phonetic_distance` stays as a deprecated alias of it.

The search clusters phones on the price that ranks its candidates, so one pair of sounds has one price. The sensitivity is a share from 0 to 1: the merge threshold is that quantile of the segment costs over all pairs of letters in the table, so a value keeps its meaning when the costs change.

This change came after the test run, and it was measured on the development split only. The default was chosen again by rule 7 of [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md) over the shares 0.01, 0.02, 0.03, 0.05, 0.08 and 0.12. The values 0.08 and 0.12 tie at a mean recall at 1 of 0.8521 over the four dialect pairs, and the rule does not name a tie-break, so the lower share won with fewer candidates. The change had to pass the acceptance rule that applies to every change after the test run: no development task may show a paired difference whose interval lies wholly below 0. Against the earlier library at 0.1, the mean recall at 1 differs by 0.0000, with an interval from 0.0000 to 0.0000 (1,000 resamples, seed 0, 500 queries in each of four pairs), and every query scores the same. A query returns from 1% to 23% fewer candidates, depending on the pair. The costs of the word distance, the alignment and the cognate task do not depend on the clusters, so they did not change.

### The feature weights stay

The weights of the 22 features in the data of PanPhon 0.22.2 are PanPhon's. The PanPhon paper counts 21 features (Mortensen et al. 2016, p. 3477); the 22 are the columns of the weight file of version 0.22.2. Fits of the weights to perceptual confusions did not transfer from one data set to the next, and the candidates C1 to C3 that changed the weights did not beat C0. No change to the feature weights passed a clean test; the test that changed the word costs kept the weights. The weights stay.

## What does not read

`vectorize_phones` raises `ValueError` for a segment it cannot read. The table counts the distinct segments (types) of three corpora and the occurrences (tokens) of those segments. The counts come from one run, recorded in `benchmarks/results/coverage-seen.json`. The run was made on a tree with uncommitted changes, and the results were committed as `4a31c7f`.

| Corpus | Distinct segments | Read | Unread | Share of tokens read |
|---|---|---|---|---|
| PHOIBLE 2.0 | 4158 | 3765 | 393 | 0.9944 |
| WikiPron | 3604 | 2594 | 1010 | 0.9939 |
| orthography2ipa | 2569 | 2168 | 401 | 0.9889 |

Most unread segments are rare. The kinds of segment that do not read are these.

| Kind | Example | Reason |
|---|---|---|
| A diphthong written whole | `ai` | A diphthong is two segments. |
| A mark with no chart meaning | `ˁ`, `ʳ`, `ᵊ` | No chart states what the mark means. |
| A superscript letter after a vowel | `eˣ` | The charts give the letter only as a form of the base letter. |
| A mark on a base the charts do not print it on | `k̃`, `m̃`, `aʰ`, `ʉʰ` | The rule applies only to the bases that a chart prints. |
| A mark that no feature encodes | `↓` | Ingressive airflow has no feature. |
| A letter with no row | `ʅ` | The table has no row for the letter. |

A test asserts that each example raises `ValueError`.

## What the evidence does not show

- The cognate test puts the library below plain edit distance and below SCA. The mean average precision of the shipped costs is 0.8035. Plain edit distance scores 0.8234 and SCA scores 0.8835.
- The data for the tone model, the weights and the coverage counts was seen during the work. The scores on it describe the library. They do not test it.
- The step features, the scale marks and the pharyngealized feature rest on the chart and on descriptions of the articulation. The benchmarks do not show that they help.
- The coverage counts are of three corpora. A segment outside them may not read.

[Index](index.md) · Previous: [The feature table](features.md) · Next: [API reference](api.md)
