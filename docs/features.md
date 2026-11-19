# The feature table

Each IPA segment has a vector of 25 distinctive features. A value is `True` (+), `False` (−) or `None` (0, the feature does not apply). The table is in `phonematcher/data/features.json`. The script `scripts/build_features.py` builds it from three inputs: PanPhon, Hayes (2009) and a file of cited overrides.

## The 25 features, in order

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
| 14 | `lab` | labial: made with the lips, rounded vowels included | 0.25 | PanPhon, Hayes for vowels |
| 15 | `hi` | high: the tongue body is raised | 0.25 | PanPhon, Hayes for vowels |
| 16 | `lo` | low: the tongue body is lowered | 0.25 | PanPhon, Hayes for vowels |
| 17 | `back` | back: the tongue body is retracted | 0.25 | PanPhon, Hayes for vowels |
| 18 | `round` | round: the lips are rounded | 0.25 | PanPhon, Hayes for vowels |
| 19 | `tense` | tense: the higher vowel of a pair such as `i`/`ɪ` or `e`/`ɛ` | 0.25 | PanPhon, Hayes for vowels |
| 20 | `long` | long: the length mark `ː` | 0.125 | PanPhon |
| 21 | `velaric` | velaric airstream: clicks | 0.25 | PanPhon |
| 22 | `front` | front: the tongue body is pushed forward | 0.25 | Hayes |
| 23 | `tap` | tap: one fast contact, as in `ɾ` | 0.25 | Hayes |
| 24 | `trill` | trill: repeated contacts, as in `r` and `ʀ` | 0.25 | Hayes |

`front` and `back` together give three positions. A front vowel is [+front, −back]. A central vowel is [−front, −back]. A back vowel is [−front, +back].

## Sources

**PanPhon** (Mortensen et al. 2016, "PanPhon: A Resource for Mapping IPA Segments to Articulatory Feature Vectors", COLING, MIT licence) is the base. It gives 6,367 segments, features 0 to 21, their weights and the rules for diacritics. Its two tone features are not used.

**Hayes** (2009, *Introductory Phonology*, Wiley-Blackwell) gives features 22 to 24 and the vowel values. The data comes from the CSV conversion by Kyle Gorman (github.com/kylebgorman/hayes2009, Apache-2.0 licence), vendored in `scripts/sources/`. For each vowel letter in Hayes's table, his values replace PanPhon's for `hi`, `lo`, `front`, `back`, `round`, `tense` and `lab`. A segment that Hayes does not list gets `front` 0, `tap` − and `trill` −.

**`phonematcher/data/overrides.json`** holds the local changes. Each entry names its source and its reason.

### Why Hayes for vowels

PanPhon has `back` but no `front`. It cannot tell a central vowel from a front one. These pairs have the same vector in PanPhon:

| Pair | Why they must differ |
|---|---|
| `e` / `ɐ` | close-mid front against near-open central |
| `ə` / `ɜ` | mid central against open-mid central |
| `r` / `ɾ` | trill against tap |

PanPhon also marks `u` and `y` labial, but not `o`, `ɔ` and `ʊ`, although all five are rounded. Hayes marks every rounded vowel labial.

### The one shared vector

`ə` and `ɜ` keep one vector. Hayes does not list `ɜ`, and PHOIBLE (Moran and McCloy) gives the two letters the same values. No published table separates them, so this table does not separate them. Every other IPA letter has its own vector, and a test checks this.

### Overrides

| Segment | Feature | Value | Source |
|---|---|---|---|
| `ɹ` | `hi` | 0 | Hayes (2009) |
| `ɹ` | `round` | − | Hayes (2009) |
| `ɐ` | `lo` | + | PHOIBLE |
| `ɐ` | `front` | − | PHOIBLE |
| `ɜ` | `front` | − | PHOIBLE |
| `ɜ` | `back` | − | PHOIBLE |
| `◌̈` (centralized) | `front`, `back` | −, − | IPA Handbook (1999) |

PHOIBLE also marks `ɐ` rounded. This table keeps `ɐ` unrounded, because the IPA chart gives the symbol no rounding.

To add an override, add an entry to `overrides.json` and run the build. Then add a test that fails without the entry.

## Diacritics

PanPhon lists many segments with diacritics, such as `ɐ̃` and `ɤˤ`. The build gives each one the vector of its base letter, with the Hayes values and the overrides. Then it adds each feature where PanPhon's row for the segment differs from PanPhon's row for the base. Thus `ɐ̃` is the overridden `ɐ` with `nas` +, and `ɤˤ` is the Hayes `ɤ` with `lo` + and `back` +.

`vectorize_phones` reads a segment that the table does not list as its longest listed base plus the diacritics after it. Each diacritic sets the features of its PanPhon rule, if the base meets the rule's conditions. For example, `ɐ̥` is `ɐ` with `voi` −.

Some marks come before their base. `ⁿ`, `ᵐ` and `ᵑ` before a stop make a prenasalized stop, as in `ⁿd`. `ʰ` before a stop makes a preaspirated stop, as in `ʰt`. Each takes the PanPhon rule of the same mark after a base.

A tie bar joins two symbols into one segment. `t͡ʃ` and `t͜ʃ` are the same affricate. Without a tie bar, `tʃ` is two segments.

## Distance

`phonetic_distance(a, b)` compares two segments feature by feature. The values count as + = 1, 0 = 0 and − = −1. Each feature adds its weight times half the difference of the two values:

| Values | Cost of the feature |
|---|---|
| same | 0 |
| 0 against + or − | half the weight |
| + against − | the full weight |

The total is divided by the sum of all weights, so the result is from 0 to 1. A segment that cannot be read is at distance 1 from all other segments.

The weights of features 0 to 21 are PanPhon's. `front`, `tap` and `trill` have weight 0.25, the same as `back` and `delrel`. The weights are not tuned to one language. A variant pair can thus be farther apart than a contrast: `ʁ`/`ʀ` is 0.188 but `ʁ`/`k` is 0.141, because a trill and a fricative differ in manner.

## Rebuilding

```
uv pip install panphon==0.22.2 pyyaml
python scripts/build_features.py
```

The build prints the number of segments in and out, the number of overrides and the number of PanPhon diacritic rules. It stops if an override's recorded old value does not match the table. With PanPhon 0.22.2, the output is the same, byte for byte, as the committed `features.json`.
