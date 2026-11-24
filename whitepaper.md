# phonematcher: a sourced feature table for IPA distance and search
<!-- agent-hint
covers: the method and the evidence of phonematcher, as one paper: feature table, costs, search, the pre-registered test and its limits
source: benchmarks/results/*.json, benchmarks/render.py, benchmarks/prereg-2.md, docs/design.md
generated: partly; the tables between whitepaper markers come from benchmarks/render.py --whitepaper, and tests/test_whitepaper.py checks each number in the prose
verify: python benchmarks/render.py --check && pytest --import-mode=importlib tests/test_whitepaper.py
see: docs/design.md, docs/benchmarks.md, docs/features.md
-->

## Abstract

phonematcher gives the distance between two IPA segments or two IPA strings. It also finds the terms in an index that sound like a query. Each distance comes from a table of distinctive features. The table starts from PanPhon. Each change to PanPhon has a source.

We tested seven systems one time on held-out data. We wrote the rules of the test before the test. On word retrieval across dialects, phonematcher has the highest recall@1, 0.8777. On cognate detection, its mean average precision is 0.8035, below SCA at 0.8835 and below plain edit distance at 0.8234. On alignment, it is below SCA and ALINE, and the intervals overlap.

The same test chose the word costs. A gap costs 0.5. A substitution costs the square root of the feature distance. These numbers come from the candidate that won the test, so they have a selection effect. Some changes that the sources suggest did not improve a score. PanPhon's own features scored higher than our full table on test cognates. Our tone distance is not better than a baseline that uses only the direction of the contour.

## 1. Introduction

Many tasks must find out if two transcriptions sound alike. Some examples:

- A voice assistant compares a spoken name with a list of contacts.
- A dialect study compares one word in many regions.
- A historical study looks for cognates.

Each task needs a distance that is finer than "same" or "different".

phonematcher gives this distance for the International Phonetic Alphabet (IPA). It compares two segments. It compares two strings. It finds the terms in an index that are nearest to a query. It reads only IPA. To use text, change the text to IPA first.

Two rules control the library:

1. Each feature value has a source that we read. If a value has no source, the documentation says that the value is our choice.
2. The results come from one test. We wrote the rules of the test before we had a test result. We give all the results of that test, also the results where phonematcher is worse.

## 2. The feature table and its sources

A segment is a vector of 36 features. Each value is plus, minus or zero. Zero means that the feature does not apply.

The features come from these sources:

- 22 features and their weights come from PanPhon 0.22.2 (Mortensen et al. 2016). The PanPhon paper counts 21 features (Mortensen et al. 2016, p. 3477). Thus the count changes with the version.
- Three consonant features, `front`, `tap` and `trill`, come from Gorman (2022). This source is a CSV file of the feature tables in the textbook *Introductory Phonology* by Hayes. We did not read the book. Thus we cite only the CSV file.
- Six height steps, `h1` to `h6`, place a vowel on seven height rows. The IPA chart (International Phonetic Association 2015) prints four height labels: close, close-mid, open-mid and open. It draws `ɪ ʏ ʊ`, `ə` and `æ ɐ` between them, so the table counts seven rows. A vowel is + on one step for each row it lies below close.
- One feature, `atr`, gives the position of the tongue root. The marks `◌̘` and `◌̙` set it.
- Four features give a secondary articulation: palatalized, labialized, velarized and pharyngealized.

The total is 22 + 3 + 6 + 1 + 4 = 36.

The vowels follow the IPA chart, not a feature table. The chart defines each vowel symbol. The chart puts 28 vowel letters on seven height rows. PanPhon's `hi` and `lo` give only three heights. Thus we add six height steps. Two vowels differ on one step for each row between them.

In PanPhon, a secondary mark replaces the place of its base. Thus `kʲ` and `qʲ` have the same vector in PanPhon. In phonematcher, the base keeps its place. The mark sets its own feature.

The mark `ˤ` (pharyngealized) and the mark `◌̙` (retracted tongue root) both use the tongue root. The sources show that they are not the same articulation:

- McCarthy (1994, pp. 218–219) puts the constriction of the Arabic emphatics in the upper pharynx.
- Hermes et al. (2017, p. 204) find a clear difference in place between pharyngeal and pharyngealized consonants.
- Al-Solami (2017, p. 25) finds that the tongue root and the tongue dorsum move back. The tongue root does not always move back.
- Casali (2007, p. 2) writes that the size of the pharyngeal cavity measures [ATR] better than the position of the tongue root, at least in languages such as Akan.

Thus `ˤ` sets `atr` to minus, as `◌̙` does. It also sets its own feature. We know no language that has a contrast between `iˤ` and `i̙`. Thus this choice comes from the descriptions of the articulation, not from a contrast.

A script makes the table from four inputs: the PanPhon data, the CSV file, the vowel chart and a file of changes. Each change has a source. A test makes the table again. The result must be the same as the published file, byte for byte.

Coverage shows how much real transcription the table can read. We counted coverage in three collections: PHOIBLE 2.0 (Moran and McCloy 2019), WikiPron (Lee et al. 2020) and the phone lists of orthography2ipa. A type is one different segment. A token is one inventory in PHOIBLE, one occurrence in WikiPron and one language in orthography2ipa. We used these collections when we made the table. Thus the counts describe the table. They are not a test.

<!-- whitepaper:coverage:start -->
| Corpus | Segment types | Types read | Share of types | Share of tokens |
|---|---|---|---|---|
| PHOIBLE 2.0 | 4158 | 3765 | 0.9055 | 0.9944 |
| WikiPron | 3604 | 2605 | 0.7228 | 0.9939 |
| orthography2ipa | 2569 | 2184 | 0.8501 | 0.9898 |
<!-- whitepaper:coverage:end -->

Most segments that the table cannot read are rare. Thus the token share is much higher than the type share. The table cannot read these types of segment:

- a diphthong written as one unit;
- a mark that no chart defines;
- a mark on a base that no chart shows it on;
- a letter that has no row in the table.

## 3. Diacritics, ties, tone and the reading rules

A diacritic applies only to the bases that its rule accepts. The rule is PanPhon's, unless `overrides.json` changes it with a source. PanPhon's rule for nasalization accepts a voiced base that is not already nasal, so `b̃`, `z̃` and `w̃` read, and `k̃` and `m̃` do not. The IPA chart prints the mark on a vowel, as in `ẽ`, so the rule also accepts a voiceless vowel. Ladefoged and Maddieson (1996) print `h̃` among the nasalized continuants, so the rule also accepts a voiceless continuant, as in `h̃` and `f̃`. PanPhon's rule for aspiration accepts stops and voiceless fricatives. Thus `aʰ` does not read. Some rules accept any base: `iˤ`, `å` and `ḁ` read, and `aˠ` reads because `a` is not high. A refusal decreases coverage. A rule becomes wider only when a chart prints the mark on a base that the rule refuses.

Eight marks move a vowel on a scale of the chart:

- along height: raised and lowered;
- along backness: advanced, retracted, centralized and mid-centralized;
- along rounding: more rounded and less rounded.

PanPhon has no rule for most of these marks. We move the vowel one row, one column, or one step of rounding. The chart gives the name and the direction of each mark. The size of the step is our choice. A mark at the end of its scale changes nothing.

Two letters without a tie bar read as one tied segment if the tie is possible. For example, `ts` reads as `t͡s`. A tie combines its parts:

- A nasal before an obstruent gives a prenasalized stop.
- A stop before a fricative gives an affricate.
- Two stops or two nasals give a double articulation, as in `k͡p`.

Two vowels do not combine. Thus a diphthong is two segments. The sources do not agree on this point. Nerbonne and Heeringa (1997, p. 11) found better dialect distances with two segments. Heeringa (2004, p. 188) found no difference. Rubehn et al. (2024, p. 209) use one segment with the vector of its first part.

The tie rule increases coverage. This table gives the PHOIBLE types that read with three methods.

<!-- whitepaper:readings:start -->
| Reading of a PHOIBLE segment | Types read | Share of types |
|---|---|---|
| the segment as written | 2663 of 4158 | 0.6405 |
| as written, or with a tie bar between its pieces | 2692 of 4158 | 0.6474 |
| as the library reads a word: whole, split into segments, tones included | 3765 of 4158 | 0.9055 |
<!-- whitepaper:readings:end -->

A tone is its own segment. It comes after the syllable that has the tone. Tone letters, tone diacritics and superscript digits give the same segment. Thus `má`, `ma˦` and `ma⁴` all read as `m`, `a`, `˦`. We do not use the two tone features of PanPhon. We compare two tones by their pitch at the start, the middle and the end of the syllable. The distance is the mean difference, divided by the range of the five levels. Section 6 shows that this distance is not better than a simple baseline. Thus the tone distance is experimental.

A stress mark is not a segment. The library removes it. Thus `ˈio` and `io` are at distance 0.

## 4. Distances and search

The feature distance of two segments is a weighted city-block distance between their vectors. Plus against minus costs the full weight of the feature. Zero against plus or minus costs half the weight. We divide by the total weight, 9.5. Thus the distance is between 0 and 1. A segment that the table cannot read is at distance 1 from all other segments.

The word distance is an edit distance:

- A substitution costs the square root of the feature distance.
- A deletion or an insertion costs 0.5.
- A tone against a phone costs 1.

Thus a substitution never costs more than a deletion and an insertion. The square root of a metric is a metric. Thus the word distance is a metric. The normalized distance divides by the number of segments in the longer word. The test chose these costs (section 5.5). We call them the released costs.

The square root makes a small substitution more expensive, relative to a gap. The test also had a candidate with the same gap of 0.5 but no square root. The released costs gained more than that candidate on all three test tasks. This is true for the point estimates. No interval for the difference between the two exists.

The search does not compare the query with each term. The index puts the letters of the table into clusters. Each term goes into the index under its sequences of clusters. A query gets the terms that have the same cluster sequence. The edit distance then sorts these candidates. The clusters come from average-linkage clustering on the substitution cost.

The sensitivity controls the size of the clusters. It is a share between 0 and 1. The merge threshold is that quantile of the costs of all pairs of letters. Thus one share has the same meaning with different costs.

We chose the default share, 0.08, on the development data. We took the share with the best mean recall@1 that also kept the lists of candidates short. The shares 0.08 and 0.12 both have a mean recall@1 of 0.8521 over the four dialect pairs. We took the smaller share, because it gives fewer candidates.

A segment that phonematcher cannot read is at distance 1 from every other segment. The library gives no warning. With `strict=True`, the distance, alignment and search functions stop with an error. The error gives the segment. Strict mode cannot find the ASCII letters `c`, `y`, `j` and `r`, because they are also IPA letters.

## 5. Evaluation

### 5.1 One test, with rules written before the test

Before the test, we wrote the systems, the tasks, the metrics, the candidate costs and the rules that choose the winner. Then the test ran one time. Each result file records the commit of the test and a hash of the written rules. The rules permit a second run of a task only after a crash. Each pre-registered metric has a 95% bootstrap interval from 1000 resamples. A paired difference uses the same resamples for the two systems.

Alignment and retrieval use a hash of each item to divide the data. One item in five goes to the test. Cognate detection uses the published training and test sets of List, Greenhill and Gray (2017). We set the costs and the defaults on the development data. Some data has no test part, because we used it when we made the table and its weights. We call this data "seen". A development number or a seen number is never a test result.

### 5.2 Systems and tasks

Seven systems ran:

- Plain edit distance: each substitution costs 1.
- PanPhon, weighted and unweighted: feature edit distances (Mortensen et al. 2016).
- ALINE: alignment by multivalued features (Kondrak 2000).
- CLTS sound vectors: the feature vectors of Rubehn et al. (2024), made from the CLTS catalogue (Anderson et al. 2018).
- SCA: alignment by sound classes. List (2012) describes SCA as the alignment that LexStat uses.
- phonematcher at the time of the test, with its original costs: a gap of 1, and a substitution that costs the feature distance itself.

Five other sets of costs for phonematcher also ran (section 5.5). One of them is the released library.

There are three tasks:

- Cognate detection uses the six test sets of List, Greenhill and Gray (2017). The score is the mean average precision (AP) of "same cognate set" over the word pairs of each concept. A pair that a system cannot read is at distance 1.
- Alignment uses the gold alignments of List and Prokić (2014). The score is the share of pairs that a system aligns the same as the gold alignment (PAS). We use only the pairs that all aligning systems can read.
- Retrieval puts the WikiPron pronunciations of one dialect into an index. Then it finds each word from its pronunciation in a second dialect. There are four pairs of dialects. The score is recall@1: the share of queries that get the correct word first.

### 5.3 Results

The cognate table starts with the words that all systems can read. The all-words column is the planned main measure. A defect in our benchmark code changes this column on Romance (section 5.4).

On the common words, phonematcher has a lower average precision than SCA. It has a higher average precision than all other systems. These columns have no interval.

On all words, phonematcher is worse than SCA, and the intervals do not overlap. Plain edit distance also has the higher point estimate on this main measure, 0.8234 against 0.8035. The result files give the paired difference of each system to the original costs, not to the released costs. Thus we cannot calculate the interval of this difference. The overlap of the two separate intervals does not answer the question. The Romance defect decreases the all-words score of phonematcher, but not of plain edit distance.

We chose the common words after we saw the results. The common words do not include Chinese and Tujia, the two tonal sets. PanPhon and ALINE cannot read any of their words.

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
| phonematcher, original costs | 0.8381 | 0.8479 | 0.9647 | 0.7326 [0.7140, 0.7500] | 0.7609 |
| phonematcher, released costs | 0.9179 | 0.9198 | 0.9812 | 0.8035 [0.7874, 0.8186] | 0.7641 |
<!-- whitepaper:cognates:end -->

On alignment, phonematcher is below SCA and ALINE on the point estimate. The intervals overlap. ALINE reads few segments. Thus there are few common pairs, and the intervals are wide. phonematcher is clearly better than plain edit distance.

SCA ran one time on all the alignment pairs, also the test pairs. This run made sure that SCA agreed with its published settings. SCA has no tuning. Thus that run did not change a decision about phonematcher.

<!-- whitepaper:alignment:start -->
Test split. Every system is scored on the 195 pairs that all four aligning systems read.

| System | Pairs read | PAS, common pairs [95% interval] | Column score, common pairs |
|---|---|---|---|
| plain edit distance | 1459 of 1459 | 0.6154 [0.5487, 0.6872] | 0.7709 |
| ALINE | 195 of 1459 | 0.8923 [0.8513, 0.9333] | 0.9413 |
| SCA | 1459 of 1459 | 0.8974 [0.8564, 0.9385] | 0.9531 |
| phonematcher, original costs | 1163 of 1459 | 0.7949 [0.7436, 0.8513] | 0.8752 |
| phonematcher, released costs | 1163 of 1459 | 0.8513 [0.8051, 0.8974] | 0.9178 |
<!-- whitepaper:alignment:end -->

On retrieval, phonematcher has the highest recall@1 in three views: on all queries, on the queries that all systems read, and on the queries that all systems scored. SCA ran on a sample of 500 queries per pair. ALINE ran on the first 100 of those queries. Thus their all-queries scores use different queries from the other systems. There is no paired difference for SCA or ALINE. The column of shared queries compares all systems on the same queries. This column has no interval.

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
| phonematcher, original costs | 0.8324 | 0.8129 | 0.8082 [0.7999, 0.8168] | 1180/10815/712/2992 |
| phonematcher, released costs | 0.8503 | 0.8642 | 0.8777 [0.8706, 0.8851] | 1180/10815/712/2992 |
<!-- whitepaper:retrieval:end -->

### 5.4 The Romance defect

On Romance, the released library reached a B-cubed F of only 0.3631 at its training threshold, against 0.8660 for SCA.

The cause is in our benchmark code. The code did not read two types of token:

- a segment with a stress mark in front, for example `ˈa`;
- the boundary symbols `+` and `_` of the word lists.

The planned rule puts a pair that a system cannot read at distance 1. Thus 3544 of the 4853 Romance words, and 91479 of its 105702 word pairs, went to distance 1. These words could not join a cluster, and recall decreased very much.

The fault for the stress marks is only in the benchmark code, because the library removes a stress mark. The library also does not read `+` and `_`. But these symbols are word boundaries in the data, not sounds. Thus the benchmark code must remove them before it calculates the scores.

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

The corrected benchmark code reads the two types of token. Some smaller sets also lost words because of `_`. Chinese and Tujia lose words because of `⁰` and `∼`. The corrected code does not read these symbols.

We keep the recorded numbers. The rules permit a second run only after a crash. The correction changes no metric and no rule. A correct Romance number needs a second test. The rules do not permit a second test.

Thus the all-words column is not fair on Romance to all systems that use features. PanPhon and ALINE lose more Romance words than phonematcher. Thus the all-words order of the feature systems is also not a clean comparison. Only SCA and plain edit distance read all the words. The common words give the fair comparison. On the 1042 Romance words that all systems read, the released library scores an average precision of 0.9812 and SCA 0.9877.

### 5.5 How the test chose the word costs

Six sets of costs ran on the test data:

- original costs: PanPhon's weights, a gap of 1, and a substitution that costs the feature distance;
- equal weights: each feature weight is 1;
- one unit per dimension: as equal weights, but the height steps, backness and rounding have one unit together for each dimension;
- heavier major classes: as one unit per dimension, with a higher weight on the features syllabic, sonorant and consonantal;
- half gap: as the original costs, with a gap of 0.5;
- released costs: as half gap, with a substitution that costs the square root of the feature distance.

A candidate had to pass two rules:

1. Each pair of chart vowels must be nearer than any vowel and any obstruent of a fixed list.
2. The candidate must be better than the original costs on cognates and on retrieval, and not worse on alignment.

<!-- whitepaper:candidates:start -->
| Candidate | Passes the vowel rule | Cognates, AP minus original | Alignment, PAS minus original | Retrieval, recall@1 minus original |
|---|---|---|---|---|
| equal weights | no | -0.0066 [-0.0082, -0.0050] | -0.0205 [-0.0462, +0.0000] | +0.0009 [-0.0016, +0.0034] |
| one unit per dimension | no | -0.0066 [-0.0081, -0.0052] | -0.0359 [-0.0667, -0.0103] | -0.0035 [-0.0064, -0.0007] |
| heavier major classes | yes | -0.0061 [-0.0074, -0.0048] | -0.0205 [-0.0410, -0.0051] | -0.0039 [-0.0068, -0.0011] |
| half gap | yes | +0.0289 [+0.0254, +0.0322] | +0.0256 [+0.0051, +0.0513] | +0.0255 [+0.0219, +0.0294] |
| released costs | yes | +0.0709 [+0.0629, +0.0790] | +0.0564 [+0.0256, +0.0872] | +0.0696 [+0.0635, +0.0759] |
<!-- whitepaper:candidates:end -->

Equal weights and one unit per dimension do not pass the vowel rule. Heavier major classes is worse than the original costs on all three tasks. Half gap and the released costs are both better than the original costs. The released costs have the larger gain on cognates, so they won. No candidate that changed the feature weights passed. Thus the weights stay as PanPhon gives them. The two winning candidates came from development results. Thus only the test could choose between them and the original costs.

The Romance defect does not change this choice. All candidates used the same benchmark code and lost the same words. A paired difference compares two candidates on the same units.

## 6. What did not work

### 6.1 Tone

We compared our tone distance with the confusions of the six Cantonese tones (Wong, Cheng and Chen 2018). The tone distance is not better than a baseline that knows only if a contour goes up, goes down or stays level. There are 15 pairs. The intervals are wide and they overlap. Thus the data does not show that the baseline is better. But it shows that the tone distance is not better. The data is seen.

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

The height steps and the scale marks follow the chart. Neither improves a score. This table changes one thing at a time. The test columns use the original costs, as the test did. The development column uses the costs that we release.

<!-- whitepaper:ablations:start -->
| Variant | Test cognates, AP minus table (original costs) | Test alignment, PAS minus table (original costs) | Dev cognates, AP (released costs) |
|---|---|---|---|
| PanPhon's 22 features | +0.0058 [+0.0044, +0.0071] | +0.0000 [+0.0000, +0.0000] | 0.7742 |
| no height steps | -0.0002 [-0.0013, +0.0008] | +0.0000 [+0.0000, +0.0000] | 0.7725 |
| no scale marks | -0.0000 [-0.0000, -0.0000] | +0.0000 [+0.0000, +0.0000] | 0.7726 |
| every weight 1 | -0.0066 [-0.0082, -0.0050] | -0.0205 [-0.0462, +0.0000] | 0.7695 |
| the table (control) | - | - | 0.7727 |
<!-- whitepaper:ablations:end -->

Removing the scale marks changes each paired test score by less than 0.0001. It changes the development cognate score by one unit in the fourth decimal. We keep the marks because the chart gives them a meaning, not because they help. We did not measure their effect on coverage.

The height steps give no gain on test cognates. PanPhon's 22 features alone are better than our table on test cognates, and the interval is above zero. On development cognates with the released costs, the score almost does not change when we remove the steps or the scale marks. PanPhon's features again score higher. On the Hillenbrand vowel confusions, the full table has the higher point estimate. But this data is seen, and the intervals overlap.

<!-- whitepaper:confusions:start -->
Seen data, 66 vowel pairs. Spearman correlation of the negative segment distance with confusion.

| Feature set | Hillenbrand vowels [95% interval] |
|---|---|
| the table | 0.5610 [0.3800, 0.7126] |
| no height steps | 0.5340 [0.3463, 0.6964] |
| PanPhon's 22 features | 0.4153 [0.1984, 0.6171] |
<!-- whitepaper:confusions:end -->

### 6.3 One encoding of vowel height

The table gives height two times: in `hi` and `lo`, and in the steps. One possible correction sets `hi` and `lo` to zero on each vowel. Then only the steps give height. This correction keeps the distance a metric.

After the test, we accept a change only if no development task becomes worse with an interval fully below zero. Cognate detection became worse in this way. Thus we did not make the change.

<!-- whitepaper:vowel-height:start -->
Dev split, released costs. One height encoding minus the table.

| Task | Paired difference [95% interval] |
|---|---|
| Cognates, AP | -0.0006 [-0.0012, -0.0001] |
| Alignment, PAS | +0.0039 [+0.0011, +0.0066] |
| Retrieval, recall@1 | -0.0028 [-0.0067, +0.0010] |
<!-- whitepaper:vowel-height:end -->

A second possible correction removes `hi` and `lo` only when both segments are vowels. This correction breaks the triangle inequality. We checked the three inequalities of each triple of the 135 base letters, 1,202,985 inequalities over 400,995 triples, and found 875 violated. This check is an audit run. No result file has it. We did not score this correction.

### 6.4 Fitted weights

We fitted one weight for each feature on two of three confusion sets. Then we scored the third set. The weights did not transfer from one set to a different set: the Hillenbrand correlation rose from 0.5610 to 0.6394, the Mandarin one from 0.2927 to 0.3395, but the Miller and Nicely one fell from 0.3495 to 0.2981. These numbers come from an audit run on seen data. We used all three sets when we made the table. Thus the held-out scores are also not clean tests.

Lakretz et al. (2018) learn a perceptual metric from confusions. They compare it on two English data sets and one Hebrew data set. Nerbonne and Heeringa (1997, p. 11) found that weights did not help for dialect distance.

## 7. Findings about other tools

The PanPhon weight file gives `tense` 0.25, `long` 0.125 and `velaric` 0.25. The PanPhon feature table reads these numbers without their names. It gives them in its own feature order, which ends with `velaric`, `tense`, `long`. Thus a PanPhon distance gives 0.25 to `velaric`, 0.125 to `tense` and 0.25 to `long`. phonematcher reads the weights by name.

A control shows this. One variant of phonematcher has PanPhon's 22 features and the weights that PanPhon applies. This variant agrees with the weighted PanPhon distance on each pair of segments that has PanPhon's values. It differs on other pairs, because our table changes some values. 710 of the 1207 segments that both read have one or more changed values.

<!-- whitepaper:control:start -->
| Pairs | Count | Distance differs |
|---|---|---|
| segment pairs that both read | 727821 | 556665 |
| pairs whose 22 values equal PanPhon's | 123256 | 0 |
<!-- whitepaper:control:end -->

Two of our results agree with earlier work. Heeringa (2004, p. 185) found that methods with phones were better than methods with features, against perception. Sofroniev and Çöltekin (2018, p. 114) found PHOIBLE feature vectors below SCA on the same alignment benchmark.

## 8. Limits

We used the test data. We chose the released costs with the one test. We examined all changes after the test only on development data and seen data. There is no new test. The released library uses those costs.

On cognate detection, SCA scores higher than phonematcher on all words, and the intervals do not overlap. On the common words, SCA scores higher only on the point estimate. Plain edit distance also has the higher point estimate on the pre-registered measure. The files do not let us calculate an interval for that difference.

The numbers of the released library come from the candidate that won the same test. The scores of a winner on the data that chose it have a selection effect. No interval includes this effect.

We defined the common words of the cognate table after we saw the results. They do not include the two tonal sets, Chinese and Tujia. They keep only the words that the weakest reader can read.

Only the three test result files have a clean commit and the hash of the written rules. The development and seen results come from working trees. Most of these trees had changes that were not committed.

The alignment comparison uses few pairs. The retrieval comparison with SCA and ALINE uses samples.

The coverage counts come from three collections. A segment that is not in them possibly does not read. The height steps, the scale marks and the pharyngealized feature come from the chart and from descriptions of the articulation. No task shows that they help.

The tone model uses one small data set that we used before.

## 9. Reproducibility

The test ran at commit `f092f20c8bbe0aa49a6480946858c0354a2580a9` of `TigreGotico/phonematcher`. The written rules are in `benchmarks/prereg-2.md`. Their sha256 is `29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c`. The test code stops if the hash of the file is different.

The two audit runs of section 6 are not in the result files. The triangle check ran on the tree of commit `ecde385`. The weight fit ran `scripts/fit_weights.py` on the library at commit `9c0f5bf`. The script is not on `dev`. It is on the branch `feat/fit-weights`, at commit `3a134ef`.

The relative sensitivity and strict mode came after the test. They do not change a word distance. A test keeps a hash of many word distances, and this hash did not change. On the development queries, each query gives the same result at the share 0.08 as with the absolute threshold 0.1 of the tested version. The paired difference in mean recall at 1 is 0.0000, with an interval from 0.0000 to 0.0000 (1000 resamples, seed 0, 500 queries in each of four pairs). A query returns from 1% to 23% fewer candidates, depending on the pair. This comparison is an audit run. No result file has its scores for each query.

Some feature values of the released table differ from the values that the test scored. Each of them follows a cited source, and they change some word distances. The test numbers describe the tested library. `docs/design.md` lists these values and their sources.

`benchmarks/render.py` makes the tables of this paper from `benchmarks/results/`. `tests/test_whitepaper.py` checks each number in the text against those files. It connects each number to the system and the claim in its sentence. The five audit-run numbers of section 6 and the three of the sensitivity comparison above are typed, because no file has them.

The data and its licences:

- cognates: the word lists of List, Greenhill and Gray (2017), Zenodo record 192607, CC BY 4.0;
- alignment: `full.psa` and `covington.psa` of the alignment benchmark, from `github.com/SequenceComparison/SupplementaryMaterial` at a pinned commit. The repository gives no licence. Thus the benchmark downloads the files and does not distribute them;
- retrieval and coverage: the WikiPron files, Apache-2.0;
- coverage and allophones: PHOIBLE 2.0, CC BY 4.0;
- tone: the tables of Wong, Cheng and Chen (2018), CC BY 4.0;
- confusions: the four sets in `benchmarks/tasks/confusions.py`, each with its licence.

The feature table comes from PanPhon (MIT) and the CSV file of Gorman (Apache-2.0). SCA comes from LingPy, which has the GPL-3.0 licence. Thus SCA is in a separate optional dependency group.

To install the benchmarks, run the development and seen tasks again, and make sure that each table agrees with the result files, do these commands:

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

The test split runs only with `--final`, on a clean tree. The rules permit this run one time.

On Python before version 3.12, the clusters of the search changed with the hash seed. The cause was a floating-point sum over a set, which changed with the order. The search uses `math.fsum`. A test makes sure that the clusters are the same with two seeds.

## 10. References

- Al-Solami, M. 2017. Ultrasound study of emphatics, uvulars, pharyngeals and laryngeals in three Arabic dialects. *Canadian Acoustics* 45(1), pp. 25–35. <https://jcaa.caa-aca.ca/index.php/jcaa/article/download/2603/pdf>
- Anderson, C., Tresoldi, T., Chacon, T. C., Fehn, A.-M., Walworth, M., Forkel, R. and List, J.-M. 2018. A cross-linguistic database of phonetic transcription systems. *Yearbook of the Poznań Linguistic Meeting* 4, pp. 21–53. <https://pressto.amu.edu.pl/index.php/yplm/article/download/yplm-2018-0002/28347>
- Casali, R. F. 2007. Some observations on the phonetics of [ATR] contrasts. Lecture, University of Education, Winneba. <https://research.canil.ca/ATRLecture/Phonetics%20of%20ATR.pdf>
- Gorman, K. 2022. Hayes 2009 phonological feature tables (CSV conversion). <https://github.com/kylebgorman/hayes2009>
- Heeringa, W. 2004. *Measuring Dialect Pronunciation Differences using Levenshtein Distance*. PhD thesis, University of Groningen. <https://pure.rug.nl/ws/portalfiles/portal/9800656/thesis.pdf>
- Hermes, Z., Barlaz, M., Shosted, R., Liang, Z.-P. and Sutton, B. 2017. Phonetic correlates of pharyngeal and pharyngealized consonants in Saudi, Lebanese, and Jordanian Arabic: an rt-MRI study. *Proceedings of Interspeech 2017*, pp. 201–205. <https://www.isca-archive.org/interspeech_2017/hermes17_interspeech.pdf>
- International Phonetic Association. 2015. The International Phonetic Alphabet (chart, revised to 2015). <https://www.internationalphoneticassociation.org/IPAcharts/common_files/pdfs/pdfs_IPA_charts_E/IPA_Kiel.pdf>
- Kondrak, G. 2000. A new algorithm for the alignment of phonetic sequences. *Proceedings of NAACL 2000*, pp. 288–295. <https://aclanthology.org/A00-2038.pdf>
- Ladefoged, P. and Maddieson, I. 1996. *The Sounds of the World's Languages*. Oxford: Blackwell. ISBN 0-631-19815-6. <https://openlibrary.org/books/OL1122315M>
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
