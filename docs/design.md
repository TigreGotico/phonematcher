# Design choices and limits
<!-- agent-hint
covers: why the feature table, the tone model and the word costs are as they are, and what does not read
source: docs/features.md, phonematcher/distance.py, phonematcher/tone.py, benchmarks/results/*.json, benchmarks/prereg-2.md
generated: no; the numbers are checked against the result files by tests/test_design.py
verify: pytest --import-mode=importlib tests/test_design.py
see: features.md, benchmarks.md, api.md
-->

This page lists the choices of phonematcher that a reader can contest. For each choice it names the alternatives, the one taken and the source or test behind it. It ends with what the library does not read and what the evidence does not show.

Where a choice has no source, the page says that the choice is this table's own.

## Choices

### Vowel height as chart steps

PanPhon gives a vowel two height features, `hi` and `lo`, so it knows three heights. The IPA chart draws seven rows. The table keeps `hi` and `lo` and adds six step features, `h1` to `h6`, which [The feature table](features.md#vowels) defines.

The alternatives are `hi` and `lo` alone, or one numeric height. Steps keep every feature a plus, a minus or a zero, as PanPhon does. The source is the IPA chart, which fixes the rows (`docs/features.md`, "Vowels").

The evidence is thin. On the Hillenbrand vowel confusions, the weighted table scores 0.5610. The same table with zero weight on the steps scores 0.5340. The 22 features of PanPhon 0.22.2 score 0.4153. The intervals of the three overlap, and the data was seen while the library was built. On the six cognate test sets, under the C0 word costs (gap 1, linear substitutions), the variant with zero weight on the steps differs from the shipped table by -0.0002, with an interval from -0.0013 to +0.0008. On the development split, under the shipped word costs (gap 0.5, square-root substitutions), the cognate AP of the variant with zero weight on the steps is 0.7872 and the shipped table's is 0.7876. The steps are kept because the chart has seven rows, not because a test showed that they help cognate detection.

The table keeps both codings, a trade-off that was measured. A form with one encoding sets `hi` and `lo` to 0 on every vowel, so the steps alone carry height and the distance stays a weighted L1 over fixed vectors. It is a metric. On the development split it changed the paired cognate AP by -0.0006, with an interval from -0.0012 to -0.0001, and the alignment PAS by +0.0039, with an interval from +0.0011 to +0.0066. On the Hillenbrand confusions it lowered the Spearman correlation from 0.5610 to 0.5474. The acceptance rule refuses a change when the interval of any development task lies wholly below 0, and the cognate interval does.

A second form drops `hi` and `lo` only when both segments are vowels. It breaks the triangle inequality on 875 of the 400,995 triples of table base letters. For `b`, `e` and `ɪ`, the feature distance of `b` and `ɪ` is 0.486842, and the way through `e` costs 0.460526 + 0.013158 = 0.473684, which is 0.013158 less. The cause is that `hi` still separates `b` from `ɪ`, and the two vowels no longer differ on it. A cost that is not a metric is not used.

The cognate, alignment and Hillenbrand numbers are in `benchmarks/results/ablations/vowel-height-dev.json` and `vowel-height-seen.json`, and `tests/test_design.py` ties this page to them. These development numbers use the shipped word costs. The paired test-set numbers on this page use the C0 costs, and `benchmarks/results/ablations-dev.json` holds the development ablations at the shipped costs. The triple count and the distances of the second form come from a check over every unordered triple of the 135 base letters. No result file holds them, and [whitepaper.md](../whitepaper.md#9-reproducibility) names the run.

### Pharyngealization is its own feature

The mark `◌ˤ` and the mark `◌̙` (retracted tongue root) both involve the tongue root. One alternative reads them as one articulation, so `iˤ` equals `i̙`. The other adds a feature `pharyngealized`, and `◌ˤ` sets it, besides `atr` −. The table takes the second. `iˤ` and `i̙` share `atr` − and differ in `pharyngealized` alone.

Sources. McCarthy (1994, "The phonetics and phonology of Semitic pharyngeals", in Keating (ed.), *Phonological Structure and Phonetic Form: Papers in Laboratory Phonology III*, Cambridge University Press, pp. 218–219) reports that emphatics "have a constriction in the upper pharynx". He writes: "The so-called pharyngealized consonants of Arabic should really be called uvularized." Real-time MRI shows that this constriction is at a different place from that of the pharyngeals `ħ ʕ` (Hermes, Barlaz, Shosted, Liang and Sutton 2017, Interspeech, pp. 201–205; p. 204 finds a clear difference in place). Ultrasound shows "tongue root and tongue dorsum retraction with inconsistent tongue root retraction" (Al-Solami 2017, *Canadian Acoustics* 45(1), pp. 25–35). Casali (2007, "Some observations on the phonetics of [ATR] contrasts", lecture, University of Education, Winneba, section 2, p. 2) writes that expansion or contraction of the pharyngeal cavity is a better measure of the [ATR] contrast than tongue root position alone, at least in languages such as Akan (Lindau 1979). He also writes that it is "probably not possible to give a single invariant articulatory definition of [ATR] that applies to all ATR harmony languages". In Ateso, [ATR] is mainly tongue body raising. Retraction of the root is thus part of both marks, and the place of the main constriction is not the same. The table gives [ATR] a feature of its own and does not read it as vowel height, so `◌̘` and `◌̙` keep `tense` as the base has it.

The shared `atr` − encodes the overlap. The separate feature encodes the difference. No source read for this table shows one language that contrasts `iˤ` with `i̙`, so the choice rests on the two descriptions of the articulation and not on a contrast in one language. A test asserts that the two segments differ in `pharyngealized` and in no other feature.

### Marks that move a vowel along a scale

The marks `◌̝ ◌̞ ◌̟ ◌̠ ◌̈ ◌̽ ◌̹ ◌̜` move a vowel along the height, backness or rounding scale. PanPhon has no rule for most of them. The alternative is to read them as the bare letter. The table takes a rule for each mark, because the IPA chart names each mark and says what it moves. The size of the step, one chart row or column, is this table's own. On a consonant, `◌̝` and `◌̞` follow the chart's own examples instead: `ɹ̝` is a fricative and `β̞` is an approximant (`docs/features.md`).

The rules change no score that the benchmarks measure. Under the C0 word costs (gap 1, linear substitutions), the variant with no scale shifts differs from the shipped table by less than 0.0001 in the paired cognate difference on the test sets. On the development split, under the shipped word costs, the cognate AP of that variant is 0.7875 and the shipped table's is 0.7876. The rules stay for the sake of the chart's meaning, and the benchmarks do not support them or oppose them.

### A mark reads only on the bases its rule accepts

`k̃`, `m̃`, `aʰ` and `ʉʰ` do not read. The alternative is to apply every mark to every base. The table applies a mark only to the bases that the conditions of its rule accept, and `vectorize_phones` raises `ValueError` for any other base. The conditions are PanPhon's, unless `overrides.json` changes them with a source. Thus the class is often wider than the bases a chart prints. `◌̃` reads on any voiced base that is not nasal (`b̃ z̃ w̃`), although the IPA chart prints it only in `ẽ`. `◌ˤ` reads on any base (`iˤ`), and `◌ˠ` on any base that is not a high back vowel (`aˠ`), although the chart prints `tˤ dˤ` and `tˠ dˠ`. `◌̥` devoices any base (`å ḁ`), although the chart prints `n̥ d̥`. A rule widens only when a chart prints the mark on a base that the rule refuses, as the IPA chart does for `◌̃` on a vowel, and Ladefoged and Maddieson (1996) do for `◌̃` on a voiceless continuant (`h̃`). A name in a code chart with no base does not widen it. The cost is lower coverage, listed below.

### A diphthong is two segments

A diphthong written whole, as `ai`, has no vector. `segments` splits `a͡i` into `a` and `i̯`, the same segments as `ai̯`. [The feature table](features.md#diphthongs) gives the reading and the distances. A plain `ai` reads as two vowels, because the string does not say whether it is a diphthong or a hiatus. That is a limit of the transcription, and a spec that wants the diphthong reading writes ◌̯. The alternatives are one segment with a start vector and an end vector, one segment compared by its nucleus only, and one segment aligned against two. The table takes two segments, because the word distance needs no new rule: a diphthong costs as two segments, and `a͡i` against `a` costs one deletion of `i̯`. The choice follows Nerbonne and Heeringa (1997, pp. 11-13), who compared one-symbol and two-symbol diphthongs with feature vectors on 40 Dutch dialects and found that "two-phone representations of diphthongs provide a more satisfactory base" for dialect distance. Anderson et al. (2018, p. 33) define a diphthong in CLTS as two vowels: "Diphthongs are thus defined by two vowels". The sources do not agree. Heeringa (2004, p. 188) found that "it seems to make no difference whether diphthongs are represented as two segments or as one segment". Rubehn et al. (2024, p. 209) take the other choice: "feature vectors for diphthongs are based on their initial segments", so a diphthong is one segment.

### Tone is a feature of its vowel

A tone is four features of the segment that carries it, which [The feature table](features.md#tone) defines. They are the four values of the tone block of phoonnx (`phoonnx_train/features_json.py`), so a TTS voice and a word distance read a tone the same way. The alternative is a tone as a segment of its own. A tone with no vowel before it stays such a segment, and the alignment then stays one segment against one segment, so a tone differs by a scale step, as a vowel height does.

PanPhon has two tone columns, `hitone` and `hireg`, and this table does not use them. The tone letters and diacritics, and the readings of the diacritics as letters, come from the box "Tones and word accents" of the IPA chart.

### A tone adds to the distance

The feature distance divides by 9.5, the weight of the 36 segment features, and not by the weight of all 40 ([Distance](features.md#distance)). So a pair of segments with no tone keeps the distance it has with no tone features. On 3,000 word pairs with no tone mark from the training word lists of the cognate task, `ipa_distance` gives the same 3,000 values, bit for bit, as with no tone features.

### The tone weights

The four weights were chosen on the dev split. `tone_is` weighs 0.25, and each of the three pitches weighs 0.125, the weight of one height step. So one Chao level costs 0.09375 of the 9.5, a little less than one height step, and `˥` against `˩` costs 0.375 of the 9.5. The three pitches weigh the same, as in the tone distance, because 15 seen tone pairs cannot support another shape. With equal pitch weights, the tone task ranks the 15 pairs as the tone distance does, so its score does not depend on the weights.

The weights come from the cognate task on its dev split, the six training word lists, where Bai and Chinese write tones. The mean average precision and the mean B-cubed F-score over the six lists were these, with the tone weights as `tone_is` and pitch:

| Tone weights | Average precision | B-cubed F | Chinese average precision |
|---|---|---|---|
| tone as a segment of its own | 0.7736 | 0.8268 | 0.5485 |
| 0 and 0: the tone is read and not priced | 0.7867 | 0.8383 | 0.6297 |
| 0.25 and 0.0625 | 0.7876 | 0.8385 | 0.6308 |
| 0.25 and 0.125, chosen | 0.7875 | 0.8384 | 0.6286 |
| 0.5 and 0.125 | 0.7875 | 0.8384 | 0.6288 |
| 0.25 and 0.25 | 0.7869 | 0.8378 | 0.6236 |
| 0.5 and 0.5 | 0.7854 | 0.8358 | 0.6135 |
| 1 and 1 | 0.7817 | 0.8321 | 0.5928 |

Nearly all of the gain over the segment model comes from carrying the tone onto its vowel, and not from the weights: with both weights at 0, the scores are already 0.7867 and 0.8383. The chosen weights add about 0.001 to that, on two tonal lists only. The row 0.25 and 0.0625 scores 0.0001 higher than the chosen row, which is less than the dev split can separate. The scores are flat up to a pitch weight of 0.125 and fall above it. The table takes the largest pitch weight in that flat range, so that a tone still separates two words, and the dev split does not show that this weight is better than a smaller one. No claim about tone weights holds beyond Bai, Chinese and the 15 Cantonese tone pairs. The test split was not run.

### The tone distance

The tone distance is experimental. On the one tone data set that exists for it, it does not beat a baseline that compares only direction ([the tracking issue](https://github.com/TigreGotico/phonematcher/issues/68)). With equal weights on the three pitches, the feature distance of two toned vowels ranks tone pairs as the tone distance does, so the same limit holds for both.

This is a limit, not a result. The benchmark has 15 tone pairs of Cantonese. It correlates the negative distance with the rate at which listeners confuse the two tones. The tone distance scores a Spearman 0.2475, with an interval from -0.3167 to 0.7396. A baseline that compares only the direction of the contour (rising, falling or level) scores 0.7817, with an interval from 0.4554 to 0.8860. With the alternative Chao values, the tone distance scores 0.3579. The intervals overlap, so 15 pairs do not show that the baseline is better. They show that the tone distance does not beat it. The two most confused pairs, T3 with T6 and T1 with T3, are level tones one or two steps apart. The data was seen while the library was built, and no other tone data was tested.

### Two letters never share a vector

No two base letters of the table are at distance 0. A pair at distance 0 would be a synonym or a missing contrast. `tests/test_same_vector.py` reads 135 letters and fails when two letters share a vector, or when a collision is not reported as a group. The smallest distance between two letters is 0.0132. It is one feature of weight 0.125 out of a total of 9.5, and it separates `a` from `æ` on the step `h6`.

### PanPhon weights by name

PanPhon's weight file names `tense 0.25`, `long 0.125` and `velaric 0.25`. PanPhon's `FeatureTable` reads the numbers without the names and gives them in its own feature order, which ends `velaric, tense, long`. A PanPhon distance thus applies 0.25 to `velaric`, 0.125 to `tense` and 0.25 to `long`. The table takes the weights by the names in the file. The ablation that uses the weights PanPhon applies agrees with PanPhon on the 115921 pairs of segments whose 22 values equal PanPhon's, and differs on none of them. On all 727821 pairs that both systems read, 561318 differ, because the table changes some of PanPhon's values.

### An unread segment is at distance 1

A segment that cannot be read is at distance 1 from every other segment, and a word that holds one has no feature cost for it. The benchmarks score the unread pairs at distance 1 as the main view, and report a second view on the items that every system reads. The alternative is to drop the unread items. Dropping them would let a system that reads little score well on what it reads, so the main view charges for what a system cannot read.

The two views differ. On 12716 allophone items, the main view scores 0.8988. The view that skips the 199 items with an unread segment scores 0.9110 on the remaining 12517.

The substitution of such a segment against any other segment costs 1, the price of a deletion plus an insertion, and its insertion or deletion costs 0.5. The first time such a segment is priced against another segment, phonematcher issues one `UserWarning` that names the segment and its code points. Each segment warns once per process, also when several threads price it at the same time.

The warning comes from the feature distance, so some inputs stay silent. An unread segment does not warn when it meets only gaps, tones or spaces. A gap costs 0.5 for any segment, and a tone or a space against a phone costs 1 before the features are read. Use `strict=True` to catch every unread segment.

The table does not read every valid IPA segment (see [What does not read](#what-does-not-read)). Strict mode cannot catch a spelling that uses the ASCII letters `c`, `y`, `j` and `r`. These are also IPA letters, so the spelling is read as IPA and gives a wrong score with no error.

The first warning uses up the segment's one warning, even when nobody sees it. A first pricing under an "ignore" filter records the segment, so a later call with warnings on is silent. Under `-W error` or an "error" filter, the first pricing raises the warning as an exception instead of returning 1, and later calls return 1 with no warning.

To silence the warning, use the standard `warnings` filter:

```python
import warnings

warnings.filterwarnings("ignore", message="Unrecognized phone", category=UserWarning)
```

Pass `strict=True` to `ipa_distance`, `edit_distance`, `align` or `PhoneticFuzzySearch` to get a `ValueError` that names the segment and the input:

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

The edit distance prices a deletion and an insertion at 0.5. It prices a substitution at the square root of the segment distance. The alternatives came from a pre-registered test, [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md). Six candidates ran once on test data that no one had scored. C0 is the starting rule: the table's weights, a gap cost of 1 and linear substitutions. C1 gives every feature weight 1. C2 also gives the vowel steps, backness and rounding one unit per dimension. C3 is C2 with a higher weight on the major-class features. P4 is C0 with a gap cost of 0.5. P5 is P4 with square-root substitutions. A candidate had to pass constraint K1 first: every pair of chart vowels is nearer than any chart vowel and any of `p b t d k ɡ q ʔ f v s z ʃ ʒ x χ h`. It then had to beat C0 on cognates and on retrieval, and not lose on alignment. The values are the paired differences from C0.

| Candidate | K1 | Cognates, AP | Alignment, PAS | Retrieval, R@1 |
|---|---|---|---|---|
| C1 | no | -0.0066 | -0.0205 | +0.0009 |
| C2 | no | -0.0066 | -0.0359 | -0.0035 |
| C3 | yes | -0.0061 | -0.0205 | -0.0039 |
| P4 | yes | +0.0289 | +0.0256 | +0.0255 |
| P5 | yes | +0.0709 | +0.0564 | +0.0696 |

P5 beat C0 on all three tasks and had the largest cognate difference, so the library uses it. The candidates P4 and P5 came from dev results, so only the test could decide between them and C0. The square root also keeps the cost a metric.

### One segment cost and a relative sensitivity

The edit distance, the alignment and the clusters of the search all use `substitution_cost` ([API reference](api.md)). The search clusters phones on the price that ranks its candidates, so one pair of sounds has one price. The sensitivity is a share and not a cost, so a value keeps its meaning when the costs change ([Search by sound](search.md#3-see-what-a-sensitivity-groups)).

The default share is 0.12. Rule 7 of [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md) chooses it on the development split, and [Search](search.md#6-choose-a-sensitivity) gives the rule and the values. The costs of the word distance, the alignment and the cognate task do not depend on the clusters.

### Feature values that follow their sources

Three groups of feature values follow a cited source and differ from the values that the test run scored. The marks `◌̝ ◌̞ ˔ ˕` on a consonant follow the chart examples `ɹ̝` and `β̞` (`docs/features.md`). In a tie of a click and its velar or uvular letter, the tie is the click with the voicing and nasality of that letter (`docs/features.md`). `h` and `ɦ` take [−son, −cons] and `ʔ` takes [−son, +cons] from the Hayes CSV, as `ɹ` does (`docs/features.md`). These values change some word distances. The test numbers describe the library that the test run scored. The development and seen result files are scored with these values.

The table compares the library of the test run with the shipped library on the development split. The "without" column is the result files of the test-run library. The paired difference comes from an audit run that scores each unit with the library at `cd2996a` (without) and at `4f254da` (with). The "with" column holds every change since `cd2996a`: these values, the tone features, and the later fixes to the reading of marks. The audit uses the benchmark code of `100ff08` for "without" and of `4f254da` for "with". Its units are the 977 cognate concepts, the 4575 alignment pairs that phonematcher reads, and the 500-query sample of each of the four retrieval pairs; its interval uses 1,000 resamples with seed 0. `benchmarks/results/ablations/corrections-dev.json` holds every number of the table.

| Task | Without | With | Paired difference [95% interval] |
|---|---|---|---|
| Cognates, AP | 0.7727 | 0.7875 | +0.0148 [+0.0122, +0.0176] |
| Alignment, PAS | 0.8315 | 0.8315 | +0.0002 [-0.0007, +0.0011] |
| Retrieval, recall@1 | 0.8801 | 0.8802 | +0.0002 [+0.0000, +0.0008] |

The audit ran at `4f254da`. The click ties and the marks after a tone that came later move the cognate AP of the shipped library from 0.7875 to 0.7876 and leave the alignment score at 0.8315 on the development split. The paired intervals were not computed again.

The rule for a change that corrects a value is to adopt it unless a paired interval on the development split lies wholly below 0. No interval lies below 0, so the library keeps its values.

### The feature weights stay

The weights of the 22 features in the data of PanPhon 0.22.2 are PanPhon's. The PanPhon paper counts 21 features (Mortensen et al. 2016, p. 3477); the 22 are the columns of the weight file of version 0.22.2. Fits of the weights to perceptual confusions did not transfer from one data set to the next, and the candidates C1 to C3 that changed the weights did not beat C0. No change to the feature weights passed a clean test; the test that changed the word costs kept the weights. The weights stay.

## What does not read

`vectorize_phones` raises `ValueError` for a segment it cannot read. The table counts the distinct segments (types) of three corpora and the occurrences (tokens) of those segments. The counts come from one run, recorded in `benchmarks/results/coverage-seen.json`.

| Corpus | Distinct segments | Read | Unread | Share of tokens read |
|---|---|---|---|---|
| PHOIBLE 2.0 | 4158 | 3783 | 375 | 0.9947 |
| WikiPron | 3604 | 2639 | 965 | 0.9940 |
| orthography2ipa | 2519 | 2299 | 220 | 0.9953 |

Most unread segments are rare. The kinds of segment that do not read are these.

| Kind | Example | Reason |
|---|---|---|
| A diphthong written whole | `ai` | A diphthong is two segments. |
| A mark with no chart meaning | `ˁ`, `ʳ`, `ᵊ` | No chart states what the mark means. |
| A superscript letter after a vowel | `eˣ` | The charts give the letter only as a form of the base letter. |
| A mark on a base the charts do not print it on | `k̃`, `m̃`, `aʰ`, `ʉʰ` | The rule applies only to the bases that a chart prints. |
| A mark that no feature encodes | `↓` | The IPA chart prints the mark as "Downstep" and the extIPA chart as "ingressive airflow". No feature encodes either meaning. |
| A click with a breathy or glottalic mark before or on its rear letter | `ǃ͡ɢʱ`, `ᵏʼǃ` | No source writes the click that way. |
| A letter with no row | `ʅ` | The table has no row for the letter. |

A test asserts that each example raises `ValueError`.

## What the evidence does not show

- The cognate test puts the library below plain edit distance and below SCA. The mean average precision of the shipped costs is 0.8035. Plain edit distance scores 0.8234 and SCA scores 0.8835.
- The data for the tone model, the weights and the coverage counts was seen while the library was built. The scores on it describe the library. They do not test it.
- The step features, the scale marks and the pharyngealized feature rest on the chart and on descriptions of the articulation. The benchmarks do not show that they help.
- The coverage counts are of three corpora. A segment outside them may not read.

[Index](index.md) · Previous: [The feature table](features.md) · Next: [API reference](api.md)
