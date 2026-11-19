# The feature table

Each IPA segment has a vector of 35 distinctive features. A value is `True` (+), `False` (−) or `None` (0, the feature does not apply). The table is in `phonematcher/data/features.json`. The script `scripts/build_features.py` builds it from PanPhon, Hayes (2009), the IPA vowel chart and a file of cited changes.

## The 35 features, in order

| # | Feature | Meaning | Weight | Source |
|---|---|---|---|---|
| 0 | `syl` | syllabic: forms the nucleus of a syllable (vowels, syllabic consonants) | 1 | PanPhon |
| 1 | `son` | sonorant: air flows without a build-up of pressure (vowels, nasals, liquids, glides) | 1 | PanPhon |
| 2 | `cons` | consonantal: a major constriction in the vocal tract | 1 | PanPhon |
| 3 | `cont` | continuant: air keeps flowing through the mouth (fricatives yes, stops no) | 0.5 | PanPhon |
| 4 | `delrel` | delayed release: a stop that opens into a fricative (affricates) | 0.25 | PanPhon |
| 5 | `lat` | lateral: air flows past the sides of the tongue | 0.25 | PanPhon |
| 6 | `nas` | nasal: air flows through the nose | 0.25 | PanPhon |
| 7 | `strid` | strident: loud, high-frequency noise (sibilants) | 0.125 | PanPhon |
| 8 | `voi` | voice: the vocal folds vibrate | 0.125 | PanPhon |
| 9 | `sg` | spread glottis: aspiration and breathy voice | 0.125 | PanPhon |
| 10 | `cg` | constricted glottis: ejectives, glottal stop, creaky voice | 0.125 | PanPhon |
| 11 | `ant` | anterior: the constriction is at the alveolar ridge or in front of it | 0.25 | PanPhon |
| 12 | `cor` | coronal: made with the tip or the blade of the tongue | 0.25 | PanPhon |
| 13 | `distr` | distributed: a long constriction along the tongue (laminal, not apical) | 0.125 | PanPhon |
| 14 | `lab` | labial: made with the lips, rounded vowels included | 0.25 | PanPhon; the chart for vowels |
| 15 | `hi` | high: the tongue body is raised | 0.25 | PanPhon; the chart for vowels |
| 16 | `lo` | low: the tongue body is lowered | 0.25 | PanPhon; the chart for vowels |
| 17 | `back` | back: the tongue body is retracted | 0.25 | PanPhon; the chart for vowels |
| 18 | `round` | round: the lips are rounded | 0.25 | PanPhon; the chart for vowels |
| 19 | `tense` | tense: a consonant feature in PanPhon; 0 on the chart vowels, whose height the step features give | 0.25 | PanPhon |
| 20 | `long` | long: the length mark `ː` | 0.125 | PanPhon |
| 21 | `velaric` | velaric airstream: clicks | 0.25 | PanPhon |
| 22 | `front` | front: the tongue body is pushed forward | 0.25 | Hayes; the chart for vowels |
| 23 | `tap` | tap: one fast contact, as in `ɾ` | 0.25 | Hayes |
| 24 | `trill` | trill: repeated contacts, as in `r` and `ʀ` | 0.25 | Hayes |
| 25 | `atr` | advanced tongue root: + for `◌̘`, − for `◌̙`, otherwise 0 | 0.25 | Lindau (1978) |
| 26–31 | `h1` … `h6` | vowel height steps: + for each chart row the vowel lies below close, otherwise 0 | 0.125 each | the chart |
| 32 | `palatalized` | a secondary raising of the tongue body toward the palate: `◌ʲ`, `◌ᶣ` | 0.125 | Sagey (1986) |
| 33 | `velarized` | a secondary raising of the tongue body toward the velum: `◌ˠ`, `◌̴` | 0.125 | Sagey (1986) |
| 34 | `labialized` | a secondary rounding of the lips: `◌ʷ`, `◌ᶣ` | 0.125 | Sagey (1986) |

`front` and `back` together give three positions. A front vowel is [+front, −back]. A central vowel is [−front, −back]. A back vowel is [−front, +back].

## Sources

| Source | What it gives |
|---|---|
| PanPhon (Mortensen et al. 2016, "PanPhon: A Resource for Mapping IPA Segments to Articulatory Feature Vectors", COLING, MIT licence) | 6,367 segments, features 0 to 21, their weights and the rules for diacritics. Its two tone features are not used. |
| Hayes (2009, *Introductory Phonology*, Wiley-Blackwell), through the CSV conversion by Kyle Gorman (github.com/kylebgorman/hayes2009, Apache-2.0), in `scripts/sources/` | `front`, `tap` and `trill` for consonants |
| The IPA vowel chart (International Phonetic Association 1999, *Handbook of the International Phonetic Association*), in `scripts/sources/ipa-vowel-chart.csv` | the height, backness and rounding of the 28 vowel letters |
| `phonematcher/data/overrides.json` | every other change, each with its source and reason |

A segment that no source gives a value for gets `front` 0, `tap` −, `trill` −, `atr` 0 and the step features 0.

## Vowels

The 28 vowel letters take their values from their place on the IPA chart, not from a feature table. The chart defines what each symbol means, so it is the first authority.

| Chart value | Features |
|---|---|
| close, near-close | `hi` + |
| close-mid, mid, open-mid | `hi` −, `lo` − |
| near-open, open | `lo` + |
| front | `front` +, `back` − |
| central | `front` −, `back` − |
| back | `front` −, `back` + |
| rounded | `round` +, `lab` + |

`hi` and `lo` give only three heights, but the chart has seven. The step features `h1` to `h6` give all seven in order. A vowel is + on `h1` if it is below close, + on `h2` if it is below near-close, and so on. Two vowels thus differ on as many step features as there are chart rows between them, and the distance between vowels grows with every row.

| Height | Letters | `h1` … `h6` |
|---|---|---|
| close | `i y ɨ ʉ ɯ u` | − − − − − − |
| near-close | `ɪ ʏ ʊ` | + − − − − − |
| close-mid | `e ø ɘ ɵ ɤ o` | + + − − − − |
| mid | `ə` | + + + − − − |
| open-mid | `ɛ œ ɜ ɞ ʌ ɔ` | + + + + − − |
| near-open | `æ ɐ` | + + + + + − |
| open | `a ɶ ɑ ɒ` | + + + + + + |

The chart has five columns, and the features give three. Near-front `ɪ ʏ` count as front and near-back `ʊ` as back. Their lower height keeps them apart from `i y u`.

The chart places `a` open front and `ɐ` near-open central. Both are unrounded. Many descriptions write the open central vowel as `a`. A transcription that means open central can write `ä`.

PanPhon gives 6 of the 28 vowels `delrel` 0 and the rest `delrel` −. A vowel has no release, so all 28 take −.

## Changes to PanPhon's diacritic rules

| Mark | PanPhon | Here | Source |
|---|---|---|---|
| `◌̈` centralized | no change | `front` −, `back` − | IPA Handbook (1999) |
| `◌̝` raised, `◌̞` lowered | no change | one chart row up or down | IPA Handbook (1999) |
| `◌̘` advanced tongue root | `tense` + | `atr` +, `tense` kept | Lindau (1978), "Vowel features", *Language* 54, who names the feature [expanded] |
| `◌̙` retracted tongue root | `tense` − | `atr` −, `tense` kept | Lindau (1978) |
| `◌ʲ` palatalized | `hi` +, `back` − | `palatalized` + | Sagey (1986); Clements and Hume (1995) |
| `◌ᶣ` labio-palatalized | `hi` +, `back` −, `round` + | `palatalized` +, `labialized` + | Sagey (1986) |
| `◌ʷ` labialized | `hi` +, `back` +, `round` + | `labialized` + | Sagey (1986) |
| `◌ˠ` `◌̴` velarized | `hi` +, `back` + | `velarized` + | Sagey (1986) |
| `◌ˤ` pharyngealized | `lo` +, `back` + | `atr` − | McCarthy (1994) |
| `◌˞` rhoticity | `hi` +, `round` +, `ant` − | `ant` − only | IPA Handbook (1999); Ladefoged and Maddieson (1996) |

PanPhon writes a secondary articulation with the features of primary place. The mark then overwrites the place of its base: in PanPhon, `kʲ` and `qʲ` share a vector. In feature geometry a secondary articulation is a feature of its own, beside the primary place (Sagey 1986, *The Representation of Features and Relations in Non-linear Phonology*, MIT dissertation; Clements and Hume 1995, "The internal organization of speech sounds", in *The Handbook of Phonological Theory*). Here each mark sets its own feature, and the base keeps its place. The names `palatalized`, `velarized` and `labialized` belong to this table. Neither work uses them. Thus `kʲ` has the place of `k`, and differs from `k` only in `palatalized`.

Pharyngealization is a retraction of the tongue root (McCarthy 1994, "The phonetics and phonology of Semitic pharyngeals", in Keating (ed.), *Phonological Structure and Phonetic Form: Papers in Laboratory Phonology III*, pp. 191–233). McCarthy writes it as a Pharyngeal place feature. This table writes it as `atr` −, so `kˤ`, `tˤ` and `sˤ` keep their place and differ from `k`, `t` and `s` in the tongue root. On a vowel, pharyngealization and retracted tongue root are thus one articulation: `iˤ` equals `i̙`.

Rhoticity `◌˞` colours a vowel without moving it on the chart. PanPhon's rule made `ɚ` high and rounded. Here the mark keeps the vowel's height and rounding and sets only `ant` −, for the retroflex or bunched tongue. The precomposed letters `ɚ` and `ɝ` read as `ə˞` and `ɜ˞`.

The tongue body cannot be high and low at once (Chomsky and Halle 1968, *The Sound Pattern of English*). No segment is [+high, +low], and the build stops if one is.

## Letters PanPhon does not list

| Letter | Name | Built as | Source |
|---|---|---|---|
| `ⱱ` | labiodental flap | the manner of `ɾ` with the place of `v` | the IPA chart |
| `ʜ` | voiceless epiglottal fricative | `ħ` with `trill` + | Esling (2005), *Canadian Journal of Linguistics* 50 |
| `ʢ` | voiced epiglottal fricative | `ʕ` with `trill` + | Esling (2005) |
| `ʡ` | epiglottal plosive | `ħ` with `cont` −, `voi` − | Esling (2005) |

Esling describes the epiglottal sounds as made at the pharyngeal place by the aryepiglottic folds, often with trilling.

## Other changes

| Segment | Feature | Value | Source |
|---|---|---|---|
| `ɹ` | `hi` | 0 | Hayes (2009) |
| `ɹ` | `round` | − | Hayes (2009) |

Every IPA letter has its own vector, and a test checks this. To add a change, add an entry to `overrides.json` and run the build. Then add a test that fails without the entry.

## Diacritics

`vectorize_phones` reads a segment that the table does not list as its longest listed base plus the diacritics after it. Each diacritic sets the features of its rule, in order, if the base meets the rule's conditions. For example, `ɐ̥` is `ɐ` with `voi` −.

PanPhon lists 6,367 segments, many with diacritics, such as `ɐ̃` and `kʷʰ`. The build reads each listed segment in the same way: its longest listed base, then the rules of its marks. A listed stack thus has the same vector as an unlisted one, and a test checks this for every listed stack. A mark that has no rule takes the difference that PanPhon records between the segment and its base letter.

Some marks come before their base. `ⁿ`, `ᵐ` and `ᵑ` before a stop make a prenasalized stop, as in `ⁿd`. `ʰ` before a stop makes a preaspirated stop, as in `ʰt`. Each takes the rule of the same mark after a base.

A tie bar joins two symbols into one segment. `t͡ʃ` and `t͜ʃ` are the same affricate. Without a tie bar, `tʃ` is two segments.

## Distance

`phonetic_distance(a, b)` compares two segments feature by feature. The values count as + = 1, 0 = 0 and − = −1. Each feature adds its weight times half the difference of the two values:

| Values | Cost of the feature |
|---|---|
| same | 0 |
| 0 against + or − | half the weight |
| + against − | the full weight |

The total is divided by the sum of all weights, so the result is from 0 to 1. A segment that cannot be read is at distance 1 from all other segments.

The weights of features 0 to 21 are PanPhon's. Two chart vowels are always nearer to each other than a vowel is to a stop or a fricative. The weights are not tuned to one language. A variant pair can thus be farther apart than a contrast: `ʁ`/`ʀ` is 0.160 but `ʁ`/`k` is 0.120, because a trill and a fricative differ in manner.

## Tone

The table has no tone features. A tone mark is not read as part of its vowel.

## Rebuilding

```
uv pip install panphon==0.22.2 pyyaml
python scripts/build_features.py
```

The build prints the number of segments in, added and out, the number of value changes and the number of diacritic rules. It stops if a change's recorded old value does not match the table, or if a segment is [+high, +low].
