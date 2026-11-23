# phonematcher: a sourced feature table for IPA distance and search
<!-- agent-hint
covers: the method and the evidence of phonematcher, as one paper: feature table, costs, search, the pre-registered test and its limits
source: benchmarks/results/*.json, benchmarks/render.py, benchmarks/prereg-2.md, docs/design.md
generated: partly; the tables between whitepaper markers come from benchmarks/render.py --whitepaper, and tests/test_whitepaper.py checks each number in the prose
verify: python benchmarks/render.py --check && pytest --import-mode=importlib tests/test_whitepaper.py
see: docs/design.md, docs/benchmarks.md, docs/features.md
-->

## Abstract

phonematcher measures how far apart two IPA segments or two IPA strings are, and finds the terms of an index that sound like a query. Each distance comes from a table of distinctive features. The table starts from PanPhon, and every change to it cites a source. We compared seven systems once on held-out data, under rules fixed before the run. On retrieval of a word across dialects, phonematcher has the highest recall@1, 0.8777. On cognate detection its mean average precision is 0.8035, below SCA at 0.8835 and below plain edit distance at 0.8234. On alignment it is below SCA and ALINE, with overlapping intervals. The same run chose the word costs: a gap of 0.5 and substitutions at the square root of the feature distance, so these figures come from the winning candidate and carry a selection effect. Several refinements that the sources suggest did not improve a score, and PanPhon's own features beat our full table on test cognates. Our tone distance does not beat a baseline that compares only the direction of the contour.

## 1. Introduction

Many tasks need to know whether two transcriptions sound alike. A voice assistant matches a spoken name against a contact list. A dialectologist compares pronunciations of one word across regions. A historical linguist looks for cognate candidates. Each task needs a distance between sounds that is finer than "same or different".

phonematcher gives that distance for transcriptions in the International Phonetic Alphabet. It compares two segments, compares two strings, and searches an index for the terms nearest to a query. It reads IPA only, so text must first pass through a grapheme-to-IPA converter.

Two rules shape the library. First, every feature value has a source that we opened and read, or the documentation says that the value is our own choice. Second, the claims about performance come from one test run whose rules we wrote down before any test result existed. We report every row of that run, including the tasks where phonematcher is behind.

## 2. The feature table and its sources

A segment is a vector of 36 features. Each value is plus, minus or zero, and zero means that the feature does not apply. The first 22 features, with their weights, are those of PanPhon 0.22.2 (Mortensen et al. 2016). The PanPhon paper counts 21 features (Mortensen et al. 2016, p. 3477), so the count depends on the version. Three consonant features, `front`, `tap` and `trill`, come from Gorman (2022), a CSV version of the feature tables in Hayes's textbook *Introductory Phonology*. We did not read the book itself, so we cite the CSV.

Vowels follow the IPA chart (International Phonetic Association 2015), not a feature table, because the chart defines what each vowel symbol means. The chart places 28 vowel letters on seven height rows. PanPhon's `hi` and `lo` give only three heights, so we add six step features. Two vowels then differ on as many steps as there are rows between them.

One feature, `atr`, records the tongue-root position that the marks `◌̘` and `◌̙` set. Four more features mark a secondary articulation: palatalized, labialized, velarized and pharyngealized. That makes 22 from PanPhon, three from the CSV, six height steps, `atr` and four secondary features, 36 in all. In PanPhon such a mark overwrites the place of its base, so `kʲ` and `qʲ` get the same vector. In phonematcher the base keeps its place and the mark sets a feature of its own.

Pharyngealization needs a word of its own. The mark `ˤ` and the mark for a retracted tongue root both involve the tongue root, and one could read them as the same articulation. The sources point the other way. McCarthy (1994, pp. 218–219) places the constriction of the Arabic emphatics in the upper pharynx. Hermes et al. (2017, p. 204) find a clear difference in place between pharyngeal and pharyngealized consonants. Al-Solami (2017, p. 25) reports retraction of both the tongue root and the tongue dorsum, the root inconsistently. Casali (2007, p. 2) writes that the size of the pharyngeal cavity measures [ATR] better than the position of the tongue root alone, at least in languages such as Akan. So `ˤ` sets `atr` to minus, as `◌̙` does, and also sets its own feature. We know of no language that contrasts `iˤ` with `i̙`, so this choice rests on the descriptions of the articulation and not on a contrast.

The table is built by a script from four inputs: the PanPhon data, the Gorman CSV, the vowel chart and a file of overrides with a source for each entry. A test rebuilds the table and requires the result to equal the published file byte for byte.

Coverage tells how much real transcription the table can read. We counted it on three collections: PHOIBLE 2.0 (Moran and McCloy 2019), WikiPron (Lee et al. 2020) and the phone inventories of the orthography2ipa converter. A type is a distinct segment. A token is an inventory in PHOIBLE, an occurrence in WikiPron and a language specification in orthography2ipa. We looked at these collections while we built the table, so the counts describe the table; they do not test it.

<!-- whitepaper:coverage:start -->
| Corpus | Segment types | Types read | Share of types | Share of tokens |
|---|---|---|---|---|
| PHOIBLE 2.0 | 4158 | 3765 | 0.9055 | 0.9944 |
| WikiPron | 3604 | 2594 | 0.7198 | 0.9939 |
| orthography2ipa | 2569 | 2168 | 0.8439 | 0.9889 |
<!-- whitepaper:coverage:end -->

Most segments that the table cannot read are rare, which is why the token shares are so much higher than the type shares. The unread types fall into a few kinds: a diphthong written as one unit, a mark that no chart defines, a mark on a kind of base that no chart shows it on, and a letter that the table has no row for.

## 3. Diacritics, ties, tone and the reading rules

A diacritic applies only to the kind of base that a chart prints it on. The chart shows nasalization on a vowel, as in `ẽ`, so `k̃` does not read. It shows aspiration on stops, as in `tʰ`, so `aʰ` does not read. This costs some coverage, but no reading is a guess. A rule widens only when a chart prints the mark on a new kind of base.

Eight marks move a vowel along a scale of the chart: raised and lowered along height; advanced, retracted, centralized and mid-centralized along backness; more and less rounded along rounding. PanPhon has no rule for most of them. We move the vowel one row or one column, or one step on the rounding scale. The chart names each mark and its direction. The size of the step is our choice. A mark at the end of its scale changes nothing.

Letters written side by side without a tie bar read as a tied segment when the tie makes sense: `ts` reads as `t͡s`. A tie combines its parts. A nasal before an obstruent makes a prenasalized stop. A stop before a fricative makes an affricate. Two stops or two nasals make a double articulation, as in `k͡p`. Two vowels do not combine, so a diphthong is two segments. The literature is divided here. Nerbonne and Heeringa (1997, p. 11) found that two-segment diphthongs gave the better dialect distances. Heeringa (2004, p. 188) found no difference. Rubehn et al. (2024, p. 209) treat a diphthong as one segment with the vector of its first part.

The tie rule matters for coverage. The table below counts the PHOIBLE types that read under three readings.

<!-- whitepaper:readings:start -->
| Reading of a PHOIBLE segment | Types read | Share of types |
|---|---|---|
| the segment as written | 2534 of 4158 | 0.6094 |
| as written, or with a tie bar between its pieces | 2692 of 4158 | 0.6474 |
| as the library reads a word: whole, split into segments, tones included | 3765 of 4158 | 0.9055 |
<!-- whitepaper:readings:end -->

A tone is a segment of its own and follows the syllable that carries it. Tone letters, tone diacritics and superscript digits give the same segment, so `má`, `ma˦` and `ma⁴` all read as `m`, `a`, `˦`. We do not use PanPhon's two tone features. Two tones are compared by their pitch at the start, middle and end of the syllable. Their distance is the mean difference, scaled by the range of the five levels. Section 6 shows that this distance does not beat a simple baseline, and we mark it as experimental.

A stress mark is not a segment. The reader drops it, so `ˈio` and `io` are at distance 0.

## 4. Distances and search

The feature distance of two segments is a weighted city-block distance between their vectors. A plus against a minus costs the full weight of the feature, and a zero against either costs half. Dividing by the total weight, 9.5, puts the distance between 0 and 1. A segment that cannot be read is at distance 1 from everything.

Word distance is an edit distance. A substitution costs the square root of the feature distance. A deletion or an insertion costs 0.5. A tone against a phone costs 1. So a substitution never costs more than a deletion plus an insertion, and since the square root of a metric is a metric, the word distance stays a metric. The normalized distance divides by the segment count of the longer word. These costs are the candidate P5, which the test run selected (section 5).

The square root makes a small substitution dearer relative to a gap. P5, which adds the square root to P4, gained more than P4 on all three test tasks, on the point estimate; no interval for the difference between the two exists (section 5.5).

Search would be slow if every query were compared with every term, so the index groups the letters of the table into clusters and files each term under its sequences of clusters. A query retrieves the terms that share a cluster sequence, and these candidates are ranked by edit distance. The clusters come from average-linkage clustering on the substitution cost. The sensitivity sets how coarse the clusters are. It is a share between 0 and 1: the merge threshold is that quantile of the costs over all pairs of letters, so a given share means the same thing whatever the costs are.

The default share, 0.08, came from the development data. We took the share with the best mean recall@1 among those that keep the candidate lists short. The shares 0.08 and 0.12 tie at 0.8521 over the four dialect pairs, and we took the smaller one, because it returns fewer candidates.

A segment that cannot be read costs as much as a missing one, and nothing warns the user. With `strict=True`, the distance, alignment and search functions raise an error that names the segment instead. Strict mode cannot catch the ASCII letters `c`, `y`, `j` and `r`, because they are valid IPA letters as well.

The relative sensitivity and strict mode were added after the test run. Neither changes a word distance, and a test pins a hash of many word distances to keep it so. On the development queries, every query also gives the same result at the share 0.08 as under the absolute threshold of the tested version, in an audit run whose per-query scores are not published.

## 5. Evaluation

### 5.1 One test run, fixed in advance

Before the test, we wrote down the systems, the tasks, the metrics, the candidate costs and the rules that would pick a winner. The test then ran once. Each result file records the commit of the run and a hash of the written rules. The rules allow a task to run again only after a crash. Each pre-registered metric has a 95% bootstrap interval from 1000 resamples, and a paired difference uses the same resamples for both systems.

Alignment and retrieval items were split by a hash of each item, one item in five going to test. Cognate detection uses the published training and test sets of List, Greenhill and Gray (2017). We tuned costs and defaults on the development part. Some data has no test part, because we had already looked at it while building the table and its weights. We call that data "seen". A development or seen number is never a test result.

### 5.2 Systems and tasks

Seven systems ran. Plain edit distance gives every substitution the cost 1. PanPhon offers a weighted and an unweighted feature edit distance (Mortensen et al. 2016). ALINE aligns words by multivalued features (Kondrak 2000). CLTS sound vectors are the feature vectors of Rubehn et al. (2024), built on the CLTS catalogue (Anderson et al. 2018). SCA aligns words by sound classes. List (2012) describes it as the alignment that LexStat builds on. The seventh system is phonematcher as it stood at the test, with the costs we call C0: a gap of 1 and linear substitutions. The candidate costs ran beside them, and P5 is the library as it ships.

Cognate detection uses the six test sets of List, Greenhill and Gray (2017). The score is the mean average precision of "same cognate set" over the word pairs of each concept, with unreadable pairs at distance 1. Alignment uses the gold alignments of List and Prokić (2014), and scores the share of pairs that a system aligns exactly as the gold does, on the pairs that every aligning system can read. Retrieval indexes the WikiPron pronunciations of one dialect and looks each word up by its pronunciation in another dialect, for four pairs of dialects. The score is recall@1 over all queries.

### 5.3 Results

On cognates, the first columns use only the words that every system can read. The all-words column, which was the planned main measure, is distorted on Romance by a defect in our benchmark code (section 5.4). On the common words, phonematcher has a lower average precision than SCA and a higher one than every other system, though these columns have no interval. On all words, phonematcher is clearly behind SCA, whose interval does not overlap. Plain edit distance also has the higher point estimate on this main measure, 0.8234 against 0.8035. The result files store each system's paired difference to C0, not to P5, so the interval of that difference cannot be computed, and the overlap of the two separate intervals does not settle it. The Romance defect lowers phonematcher's all-words score but not that of plain edit distance. The common words were chosen after we saw the results, and they leave out Chinese and Tujia, the two tonal sets, because PanPhon and ALINE read none of their words.

<!-- whitepaper:cognates:start -->
Test split. The common words are the 5497 words that every system reads, in Bahnaric, Huon, Romance, Uralic; Chinese and Tujia have no word that every system reads. The common columns have no interval. The all-words column is the pre-registered main metric, with unread pairs at distance 1.

| System | AP, common words | B-cubed F, common words | Romance AP, common words | AP, all words [95% interval] | Romance AP, all words |
|---|---|---|---|---|---|
| plain edit distance | 0.8935 | 0.9142 | 0.9760 | 0.8234 [0.8108, 0.8363] | 0.9105 |
| PanPhon, weighted | 0.8832 | 0.8782 | 0.9772 | 0.6361 [0.6151, 0.6565] | 0.7512 |
| PanPhon, Hamming | 0.8425 | 0.8480 | 0.9650 | 0.6462 [0.6242, 0.6663] | 0.7576 |
| ALINE | 0.9060 | 0.9132 | 0.9833 | 0.6130 [0.5903, 0.6359] | 0.7559 |
| CLTS sound vectors | 0.8283 | 0.8469 | 0.9634 | 0.7399 [0.7224, 0.7561] | 0.7820 |
| SCA | 0.9239 | 0.9209 | 0.9877 | 0.8835 [0.8718, 0.8949] | 0.9558 |
| phonematcher, starting weights (C0) | 0.8381 | 0.8479 | 0.9647 | 0.7326 [0.7140, 0.7500] | 0.7609 |
| phonematcher, shipped library (P5) | 0.9179 | 0.9198 | 0.9812 | 0.8035 [0.7874, 0.8186] | 0.7641 |
<!-- whitepaper:cognates:end -->

On alignment, phonematcher is behind SCA and ALINE on the point estimate, but the intervals overlap. ALINE reads few segments, which leaves few common pairs and wide intervals. phonematcher is clearly ahead of plain edit distance. SCA was once run over all the alignment pairs, test pairs included, to check that it matched its published settings. SCA is an untuned baseline, so that run affected no decision about phonematcher.

<!-- whitepaper:alignment:start -->
Test split. Every system is scored on the 195 pairs that all four aligning systems read.

| System | Pairs read | PAS, common pairs [95% interval] | Column score, common pairs |
|---|---|---|---|
| plain edit distance | 1459 of 1459 | 0.6154 [0.5487, 0.6872] | 0.7709 |
| ALINE | 195 of 1459 | 0.8923 [0.8513, 0.9333] | 0.9413 |
| SCA | 1459 of 1459 | 0.8974 [0.8564, 0.9385] | 0.9531 |
| phonematcher, starting weights (C0) | 1163 of 1459 | 0.7949 [0.7436, 0.8513] | 0.8752 |
| phonematcher, shipped library (P5) | 1163 of 1459 | 0.8513 [0.8051, 0.8974] | 0.9178 |
<!-- whitepaper:alignment:end -->

On retrieval, phonematcher has the highest recall@1, on all queries, on the queries every system reads, and on the queries that every system scored. SCA ran on a sample of 500 queries per pair and ALINE on the first 100 of those. Their all-queries scores therefore come from different queries than the others', and there is no paired difference against them. The shared-queries column compares every system on the same queries, without an interval.

<!-- whitepaper:retrieval:start -->
Test split, mean recall@1 over the four dialect pairs (en-US-UK, pt-PT-BR, es-ES-LA, hy-E-W). The common queries are the 223 queries that every system reads and scores. The shared queries are the 400 queries of the ALINE sample, which every system scores. These two columns have no interval.

| System | Common queries (223) | Shared queries (400) | All queries [95% interval] | Queries per pair |
|---|---|---|---|---|
| plain edit distance | 0.6592 | 0.6783 | 0.6861 [0.6763, 0.6956] | 1180/10815/712/2992 |
| PanPhon, weighted | 0.8183 | 0.7754 | 0.7765 [0.7675, 0.7856] | 1180/10815/712/2992 |
| PanPhon, Hamming | 0.7968 | 0.7504 | 0.7623 [0.7531, 0.7719] | 1180/10815/712/2992 |
| ALINE | 0.7270 | 0.4150 | 0.4150 [0.3742, 0.4550] | 100/100/100/100 |
| CLTS sound vectors | 0.8157 | 0.7971 | 0.7929 [0.7844, 0.8017] | 1180/10815/712/2992 |
| SCA | 0.7780 | 0.7995 | 0.7925 [0.7773, 0.8086] | 500/500/500/500 |
| phonematcher, starting weights (C0) | 0.8324 | 0.8129 | 0.8082 [0.7999, 0.8168] | 1180/10815/712/2992 |
| phonematcher, shipped library (P5) | 0.8503 | 0.8642 | 0.8777 [0.8706, 0.8851] | 1180/10815/712/2992 |
<!-- whitepaper:retrieval:end -->

### 5.4 The Romance defect

On Romance, P5 reached a B-cubed F of only 0.3631 at its training threshold, against 0.8660 for SCA. Our benchmark code treated two kinds of token as unreadable: a segment with a stress mark in front, such as `ˈa`, and the boundary symbols `+` and `_` of the word lists. Under the planned rule, an unreadable pair counts as distance 1. That put 3544 of the 4853 Romance words, and 91479 of its 105702 word pairs, at distance 1. Those words could join no cluster, and recall collapsed. For the stress marks the fault lies in the benchmark code alone, because the library drops a stress mark. The library does not read `+` and `_` either, but they mark word boundaries in the data, not sounds, so the benchmark code should have removed them before scoring.

<!-- whitepaper:romance:start -->
Test split. Words that each system cannot read; both PanPhon systems read the same words.

| Test set | Words | phonematcher | PanPhon | ALINE | CLTS sound vectors | plain edit distance | SCA |
|---|---|---|---|---|---|---|---|
| Bahnaric | 4546 | 242 | 282 | 2334 | 182 | 0 | 0 |
| Chinese | 3653 | 786 | 3653 | 3653 | 300 | 0 | 0 |
| Huon | 1668 | 42 | 172 | 202 | 42 | 0 | 0 |
| Romance | 4853 | 3544 | 3658 | 3811 | 2892 | 0 | 0 |
| Tujia | 513 | 62 | 513 | 513 | 62 | 0 | 0 |
| Uralic | 1401 | 22 | 193 | 624 | 22 | 0 | 0 |
<!-- whitepaper:romance:end -->

The corrected benchmark code reads both kinds of token. Smaller sets lost words to `_` in the same way. Chinese and Tujia lose words to `⁰` and `∼`, which remain unread.

We keep the recorded numbers. The rules allowed a second run only after a crash, and the fix changes no metric and no rule. A corrected Romance number would need a second test run, which the rules do not allow. The all-words column is therefore biased on Romance against every feature-based system in the benchmark. PanPhon and ALINE lose even more Romance words than phonematcher, so the all-words order among the feature systems is not a clean comparison either. Only SCA and plain edit distance read every word. The common words are the fair comparison. On the 1042 Romance words that every system reads, P5 scores an average precision of 0.9812 and SCA 0.9877.

### 5.5 Choosing the word costs

Six candidate costs ran on the test data. C0 kept PanPhon's weights with a gap of 1 and linear substitutions. C1 set every feature weight to 1. C2 also gave the height steps, backness and rounding one unit per dimension. C3 raised the weight of the major-class features in C2. P4 was C0 with a gap of 0.5, and P5 was P4 with square-root substitutions. A candidate first had to keep every pair of chart vowels nearer than any vowel and any obstruent of a fixed list. It then had to beat C0 on cognates and on retrieval without losing on alignment.

<!-- whitepaper:candidates:start -->
| Candidate | K1 holds | Cognates, AP minus C0 | Alignment, PAS minus C0 | Retrieval, recall@1 minus C0 |
|---|---|---|---|---|
| C1 | no | -0.0066 [-0.0082, -0.0050] | -0.0205 [-0.0462, +0.0000] | +0.0009 [-0.0016, +0.0034] |
| C2 | no | -0.0066 [-0.0081, -0.0052] | -0.0359 [-0.0667, -0.0103] | -0.0035 [-0.0064, -0.0007] |
| C3 | yes | -0.0061 [-0.0074, -0.0048] | -0.0205 [-0.0410, -0.0051] | -0.0039 [-0.0068, -0.0011] |
| P4 | yes | +0.0289 [+0.0254, +0.0322] | +0.0256 [+0.0051, +0.0513] | +0.0255 [+0.0219, +0.0294] |
| P5 | yes | +0.0709 [+0.0629, +0.0790] | +0.0564 [+0.0256, +0.0872] | +0.0696 [+0.0635, +0.0759] |
<!-- whitepaper:candidates:end -->

C1 and C2 fail the vowel constraint. C3 is worse than C0 on all three tasks. P4 and P5 both beat C0, and P5 wins on the larger cognate gain. No candidate that changed the feature weights passed, so the weights stay as PanPhon gives them, and the word costs became P5. P4 and P5 were suggested by development results, which is why only the test could decide between them and C0.

The Romance defect does not touch this choice. Every candidate went through the same benchmark code and lost the same words, and a paired difference compares two candidates on the same units.

## 6. What did not work

### 6.1 Tone

Our tone distance ranks the confusions of the six Cantonese tones (Wong, Cheng and Chen 2018) no better than a baseline that knows only whether a contour rises, falls or stays level. There are 15 pairs, and the intervals are wide and overlap, so the data cannot show that the baseline is better. It does show that the tone distance is not better. The data is seen.

<!-- whitepaper:tone:start -->
Seen data, 15 Cantonese tone pairs.

| System | Tone values | Spearman [95% interval] |
|---|---|---|
| tone distance | main Chao values | 0.2475 [-0.3167, 0.7396] |
| direction baseline | main Chao values | 0.7817 [0.4554, 0.8860] |
| tone distance | alternative Chao values | 0.3579 [-0.2042, 0.8279] |
| direction baseline | alternative Chao values | 0.7817 [0.4554, 0.8860] |
<!-- whitepaper:tone:end -->

### 6.2 Height steps, scale marks and PanPhon's own features

The height steps and the scale marks follow the chart, but neither improves a score. The table below changes one thing at a time. The test columns use the C0 costs, as the test run did; the development column uses the shipped costs.

<!-- whitepaper:ablations:start -->
| Variant | Test cognates, AP minus table (C0 costs) | Test alignment, PAS minus table (C0 costs) | Dev cognates, AP (P5 costs) |
|---|---|---|---|
| PanPhon's 22 features | +0.0058 [+0.0044, +0.0071] | +0.0000 [+0.0000, +0.0000] | 0.7742 |
| no height steps | -0.0002 [-0.0013, +0.0008] | +0.0000 [+0.0000, +0.0000] | 0.7725 |
| no scale marks | -0.0000 [-0.0000, -0.0000] | +0.0000 [+0.0000, +0.0000] | 0.7726 |
| every weight 1 | -0.0066 [-0.0082, -0.0050] | -0.0205 [-0.0462, +0.0000] | 0.7695 |
| the table (control) | - | - | 0.7727 |
<!-- whitepaper:ablations:end -->

Removing the scale marks changes each paired test score by less than 0.0001, and the development cognate score by one unit in the fourth decimal. We keep the marks because the chart gives them a meaning, not because they help. We did not measure what they add to coverage.

The height steps give no gain on test cognates either. PanPhon's 22 features alone do better there than our table, by a margin whose interval lies above zero. On development cognates at the shipped costs, removing the steps or the scale marks leaves the score almost unchanged, and PanPhon's features again score higher. On the Hillenbrand vowel confusions the full table has the higher point estimate, but that data is seen and the intervals overlap.

<!-- whitepaper:confusions:start -->
Seen data, 66 vowel pairs. Spearman correlation of the negative segment distance with confusion.

| Feature set | Hillenbrand vowels [95% interval] |
|---|---|
| the table | 0.5610 [0.3800, 0.7126] |
| no height steps | 0.5340 [0.3463, 0.6964] |
| PanPhon's 22 features | 0.4153 [0.1984, 0.6171] |
<!-- whitepaper:confusions:end -->

### 6.3 One encoding of vowel height

The table encodes height twice: in `hi` and `lo`, and in the steps. One fix sets `hi` and `lo` to zero on every vowel, so that the steps alone carry height. It keeps the distance a metric. After the test run, we accept a change only if no development task gets worse with an interval wholly below zero. Cognate detection did, so we kept the table as it is.

<!-- whitepaper:vowel-height:start -->
Dev split, P5 costs. One height encoding minus the table.

| Task | Paired difference [95% interval] |
|---|---|
| Cognates, AP | -0.0006 [-0.0012, -0.0001] |
| Alignment, PAS | +0.0039 [+0.0011, +0.0066] |
| Retrieval, recall@1 | -0.0028 [-0.0067, +0.0010] |
<!-- whitepaper:vowel-height:end -->

A second fix drops `hi` and `lo` only when both segments are vowels. It breaks the triangle inequality. A check of the three inequalities of every triple of the 135 base letters, 1,202,985 inequalities over 400,995 triples, found 875 violated, in an audit run that is not published as a result file. We did not score it.

### 6.4 Fitted weights

Weights fitted to listeners' confusions did not carry over from one data set to another. We fitted one weight per feature on two of three confusion sets and scored the third. The Hillenbrand correlation rose from 0.5610 to 0.6394 and the Mandarin one from 0.2927 to 0.3395, but the Miller and Nicely one fell from 0.3495 to 0.2981. These numbers come from an audit run on seen data: we had looked at all three sets while building the table, so even the held-out scores are not clean tests. Lakretz et al. (2018) learn a perceptual metric from confusions and compare it across two English data sets and one Hebrew one. Nerbonne and Heeringa (1997, p. 11) found weighting of no use for dialect distance.

## 7. Findings about other tools

PanPhon's weight file gives `tense` 0.25, `long` 0.125 and `velaric` 0.25. PanPhon's feature table reads these numbers without their names and assigns them in its own feature order, which ends with `velaric`, `tense`, `long`. A PanPhon distance therefore gives 0.25 to `velaric`, 0.125 to `tense` and 0.25 to `long`. phonematcher reads the weights by name.

A control confirms this. A variant of phonematcher with PanPhon's 22 features and the weights PanPhon actually applies agrees with PanPhon's weighted distance on every pair of segments whose values match PanPhon's. It differs elsewhere because our table changes some values: 710 of the 1207 segments that both read have at least one changed value.

<!-- whitepaper:control:start -->
| Pairs | Count | Distance differs |
|---|---|---|
| segment pairs that both read | 727821 | 556665 |
| pairs whose 22 values equal PanPhon's | 123256 | 0 |
<!-- whitepaper:control:end -->

Two of our results match earlier work. Heeringa (2004, p. 185) found that phone-based methods beat feature-based ones against perception. Sofroniev and Çöltekin (2018, p. 114) found PHOIBLE feature vectors below SCA on the same alignment benchmark.

## 8. Limits

The test data is spent. P5 was chosen on the one test run, and every change after it was judged on development and seen data. The shipped library is P5 plus changes that leave every word distance as it was.

On cognate detection, SCA scores higher than phonematcher on all words, with intervals that do not overlap. On the common words it scores higher on the point estimate only. Plain edit distance also has the higher point estimate on the pre-registered measure, and the files do not allow an interval for that difference.

The P5 numbers come from the candidate that won on the same test run. A winner's scores on the data that chose it carry a selection effect, and no interval covers it.

The common-word columns of the cognate table were defined after the results were seen. They drop the two tonal sets, Chinese and Tujia, and keep the words that the weakest reader can read.

Only the three test result files carry a clean commit and the hash of the written rules. The development and seen results were made on working trees, most of them with uncommitted changes.

The alignment comparison rests on few pairs, and the retrieval comparison with SCA and ALINE on samples.

The coverage counts come from three collections, and a segment outside them may not read. The height steps, the scale marks and the pharyngealized feature rest on the chart and on descriptions of articulation; no task shows that they help.

The tone model rests on one small data set that we had already seen.

## 9. Reproducibility

The test ran at commit `f092f20c8bbe0aa49a6480946858c0354a2580a9` of `TigreGotico/phonematcher`. The written rules are `benchmarks/prereg-2.md`, with sha256 `29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c`. The test code stops when the file's hash differs.

The two audit runs of section 6 are outside the result files. The triangle check ran on the tree of commit `ecde385`. The weight fit ran `scripts/fit_weights.py` from commit `3a134ef` on the library at commit `9c0f5bf`. The tables of this paper are rendered from `benchmarks/results/` by `benchmarks/render.py`, and `tests/test_whitepaper.py` checks each number in the text against those files, bound to the system and the claim in its sentence. The five audit-run numbers of section 6 are typed, because no file holds them.

The data and its licences:

- cognates: the word lists of List, Greenhill and Gray (2017), Zenodo record 192607, CC BY 4.0;
- alignment: `full.psa` and `covington.psa` of the alignment benchmark, from `github.com/SequenceComparison/SupplementaryMaterial` at a pinned commit; the repository states no licence, so the files are downloaded and never redistributed;
- retrieval and coverage: the WikiPron files, Apache-2.0;
- coverage and allophones: PHOIBLE 2.0, CC BY 4.0;
- tone: the tables of Wong, Cheng and Chen (2018), CC BY 4.0;
- confusions: the four sets listed in `benchmarks/tasks/confusions.py`, each with its licence.

The feature table derives from PanPhon (MIT) and the Gorman CSV (Apache-2.0). SCA comes from LingPy, which is GPL-3.0, and sits in a separate optional dependency group.

To install the benchmarks, rerun the development and seen tasks, and check that every table here matches the result files:

```bash
uv venv
uv pip install --prerelease=allow -e '.[test,build,bench,bench-copyleft]'
python benchmarks/run.py --task cognates --system all --split dev
python benchmarks/run.py --task alignment --system all --split dev
python benchmarks/run.py --task retrieval --system all --split dev
python benchmarks/run.py --task coverage --system all --split seen
python benchmarks/final.py decide
python benchmarks/render.py --check
pytest --import-mode=importlib tests
```

The test split runs only with `--final`, on a clean tree, and the rules allow it once.

On Python versions before 3.12, the clusters of the search depended on the hash seed, because a floating-point sum over a set changed with the order. The search uses `math.fsum`, and a test pins the clusters under two seeds.

## 10. References

- Al-Solami, M. 2017. Ultrasound study of emphatics, uvulars, pharyngeals and laryngeals in three Arabic dialects. *Canadian Acoustics* 45(1), pp. 25–35. <https://jcaa.caa-aca.ca/index.php/jcaa/article/download/2603/pdf>
- Anderson, C., Tresoldi, T., Chacon, T. C., Fehn, A.-M., Walworth, M., Forkel, R. and List, J.-M. 2018. A cross-linguistic database of phonetic transcription systems. *Yearbook of the Poznań Linguistic Meeting* 4, pp. 21–53. <https://pressto.amu.edu.pl/index.php/yplm/article/download/yplm-2018-0002/28347>
- Casali, R. F. 2007. Some observations on the phonetics of [ATR] contrasts. Lecture, University of Education, Winneba. <https://research.canil.ca/ATRLecture/Phonetics%20of%20ATR.pdf>
- Gorman, K. 2022. Hayes 2009 phonological feature tables (CSV conversion). <https://github.com/kylebgorman/hayes2009>
- Heeringa, W. 2004. *Measuring Dialect Pronunciation Differences using Levenshtein Distance*. PhD thesis, University of Groningen. <https://pure.rug.nl/ws/portalfiles/portal/9800656/thesis.pdf>
- Hermes, Z., Barlaz, M., Shosted, R., Liang, Z.-P. and Sutton, B. 2017. Phonetic correlates of pharyngeal and pharyngealized consonants in Saudi, Lebanese, and Jordanian Arabic: an rt-MRI study. *Proceedings of Interspeech 2017*, pp. 201–205. <https://www.isca-archive.org/interspeech_2017/hermes17_interspeech.pdf>
- International Phonetic Association. 2015. The International Phonetic Alphabet (chart, revised to 2015). <https://www.internationalphoneticassociation.org/IPAcharts/common_files/pdfs/pdfs_IPA_charts_E/IPA_Kiel.pdf>
- Kondrak, G. 2000. A new algorithm for the alignment of phonetic sequences. *Proceedings of NAACL 2000*, pp. 288–295. <https://aclanthology.org/A00-2038.pdf>
- Lakretz, Y., Chechik, G., Cohen, E.-G., Treves, A. and Friedmann, N. 2018. Metric learning for phoneme perception. arXiv:1809.07824. <https://arxiv.org/pdf/1809.07824>
- Lee, J. L., Ashby, L. F. E., Garza, M. E., Lee-Sikka, Y., Miller, S., Wong, A., McCarthy, A. D. and Gorman, K. 2020. Massively multilingual pronunciation mining with WikiPron. *Proceedings of LREC 2020*, pp. 4223–4228. <https://aclanthology.org/2020.lrec-1.521.pdf>
- List, J.-M. 2012. LexStat: automatic detection of cognates in multilingual wordlists. *Proceedings of the EACL 2012 Joint Workshop of LINGVIS and UNCLH*, pp. 117–125. <https://aclanthology.org/W12-0216.pdf>
- List, J.-M. and Prokić, J. 2014. A benchmark database of phonetic alignments in historical linguistics and dialectology. *Proceedings of LREC 2014*, pp. 288–294. <http://www.lrec-conf.org/proceedings/lrec2014/pdf/299_Paper.pdf>
- List, J.-M., Greenhill, S. J. and Gray, R. D. 2017. The potential of automatic word comparison for historical linguistics. *PLOS ONE* 12(1): e0170046. <https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0170046&type=printable>
- McCarthy, J. J. 1994. The phonetics and phonology of Semitic pharyngeals. In P. A. Keating (ed.), *Phonological Structure and Phonetic Form: Papers in Laboratory Phonology III*, pp. 191–233. Cambridge University Press. <https://hdl.handle.net/20.500.14394/32543>
- Moran, S. and McCloy, D. (eds.) 2019. PHOIBLE 2.0. Max Planck Institute for the Science of Human History, Jena. <https://phoible.org/>
- Mortensen, D. R., Littell, P., Bharadwaj, A., Goyal, K., Dyer, C. and Levin, L. 2016. PanPhon: a resource for mapping IPA segments to articulatory feature vectors. *Proceedings of COLING 2016*, pp. 3475–3484. <https://aclanthology.org/C16-1328.pdf>
- Nerbonne, J. and Heeringa, W. 1997. Measuring dialect distance phonetically. *Computational Phonology: Third Meeting of the ACL SIGPHON*, pp. 11–18. <https://aclanthology.org/W97-1102.pdf>
- Rubehn, A., Nieder, J., Forkel, R. and List, J.-M. 2024. Generating feature vectors from phonetic transcriptions in Cross-Linguistic Data Formats. *Proceedings of SCiL 2024*, pp. 205–216. <https://aclanthology.org/2024.scil-1.19.pdf>
- Sofroniev, P. and Çöltekin, Ç. 2018. Phonetic vector representations for sound sequence alignment. *Proceedings of SIGMORPHON 2018*, pp. 111–116. <https://aclanthology.org/W18-5812.pdf>
- Wong, P., Cheng, S. T. and Chen, F. 2018. Cantonese tone identification in three temporal cues in quiet, speech-shaped noise and two-talker babble. *Frontiers in Psychology* 9:1604. <https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2018.01604/pdf>
