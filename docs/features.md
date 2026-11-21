# The feature table

Each IPA segment has a vector of 36 distinctive features. A value is `True` (+), `False` (−) or `None` (0, the feature does not apply). The table is in `phonematcher/data/features.json`. The script `scripts/build_features.py` builds it from PanPhon, Hayes (2009), the IPA vowel chart and a file of cited changes.

## The 36 features, in order

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
| 25 | `atr` | advanced tongue root: + for `◌̘`, − for `◌̙` and `◌ˤ`, otherwise 0 | 0.25 | Casali (2007) |
| 26–31 | `h1` … `h6` | vowel height steps: on a chart vowel, + for each row it lies below close and − for the rest; 0 on other segments | 0.125 each | the chart |
| 32 | `palatalized` | a secondary raising of the tongue body toward the palate: `◌ʲ`, `◌ᶣ` | 0.125 | Clements and Hume (1995) |
| 33 | `velarized` | a secondary raising of the tongue body toward the velum: `◌ˠ`; 0 for `◌̴` | 0.125 | Clements and Hume (1995) |
| 34 | `labialized` | a secondary rounding of the lips: `◌ʷ`, `◌ᶣ` | 0.125 | Clements and Hume (1995) |
| 35 | `pharyngealized` | a secondary constriction in the upper pharynx: `◌ˤ`; 0 for `◌̴` | 0.125 | McCarthy (1994); Hermes et al. (2017) |

`front` and `back` together give three positions. A front vowel is [+front, −back]. A central vowel is [−front, −back]. A back vowel is [−front, +back].

## Sources

| Source | What it gives |
|---|---|
| PanPhon (Mortensen, Littell, Bharadwaj, Goyal, Dyer and Levin 2016, "PanPhon: A Resource for Mapping IPA Segments to Articulatory Feature Vectors", *Proceedings of COLING 2016*, pp. 3475–3484, MIT licence) | 6,367 segments, features 0 to 21, their weights and the rules for diacritics. Its two tone features are not used. |
| Hayes (2009, *Introductory Phonology*, Wiley-Blackwell), through the CSV conversion by Kyle Gorman (github.com/kylebgorman/hayes2009, Apache-2.0), in `scripts/sources/` | `front`, `tap` and `trill` for consonants |
| The IPA chart (International Phonetic Association, revised to 2015), whose vowel quadrilateral is in `scripts/sources/ipa-vowel-chart.csv` | the height, backness and rounding of the 28 vowel letters |
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
| `◌̈` centralized | no change | `front` −, `back` − | the IPA chart names it; the reading is this table's |
| `◌̝` raised, `◌̞` lowered | no change | one chart row up or down | the IPA chart names them; the reading is this table's |
| `◌̟` advanced, `◌̠` retracted | no change | on a vowel, one chart column front or back | the IPA chart names them; the reading is this table's |
| `◌̹` more rounded, `◌̜` less rounded | no rule | on a vowel, one step on the rounding scale −, 0, + | the IPA chart names them; the reading is this table's |
| `◌̽` mid-centralized | no rule | on a vowel, the central column and one row nearer mid | the IPA chart names it; the reading is this table's |
| `◌̥` voiceless | `voi` −, only on voiced sonorants | `voi` − on any base | the IPA chart |
| `◌̬` voiced | no rule | `voi` + on any base | the IPA chart |
| `◌ˑ` half-long | no rule | `long` 0, between short and long | the IPA chart names it; the reading is this table's |
| `◌̚` no audible release | no rule | read; no change | the IPA chart |
| `◌ʱ` breathy-voiced release | no rule | on a voiced base, `sg` +, as `◌̤`: `bʱ` equals `b̤` and `bʰ` | this table's reading; the chart lists `ʰ` and `◌̤` only |
| `◌̘` advanced tongue root | `tense` + | `atr` +, `tense` kept | Casali (2007) |
| `◌̙` retracted tongue root | `tense` − | `atr` −, `tense` kept | Casali (2007) |
| `◌ʲ` palatalized | `hi` +, `back` − | `palatalized` + | Clements and Hume (1995) |
| `◌ᶣ` labio-palatalized | `hi` +, `back` −, `round` + | `palatalized` +, `labialized` + | Clements and Hume (1995) |
| `◌ʷ` labialized | `hi` +, `back` +, `round` + | `labialized` + | Clements and Hume (1995) |
| `◌ˠ` velarized | `hi` +, `back` + | `velarized` + | Clements and Hume (1995) |
| `◌̴` velarized or pharyngealized | `hi` +, `back` + | `velarized` 0, `pharyngealized` 0 | the IPA chart |
| `◌ˤ` pharyngealized | `lo` +, `back` + | `pharyngealized` +, `atr` − | McCarthy (1994); Hermes et al. (2017); Al-Solami (2017) |
| `◌˞` rhoticity | `hi` +, `round` +, `ant` − | `ant` − only | the IPA chart names it; the reading is this table's |

PanPhon writes a secondary articulation with the features of primary place. The mark then overwrites the place of its base: in PanPhon, `kʲ` and `qʲ` share a vector. Clements and Hume (1995, "The internal organization of speech sounds", in Goldsmith (ed.), *The Handbook of Phonological Theory*, Blackwell, ch. 7, section 3.5.1) treat a secondary articulation as a set of minor features linked under the C-place node. It adds to the primary place and does not replace it. Here each mark sets a feature of its own, and the base keeps its place. Thus `kʲ` has the place of `k` and differs from `k` only in `palatalized`. The four feature names belong to this table.

Pharyngealized consonants, such as the Arabic emphatics, have a second constriction high in the pharynx. McCarthy (1994, "The phonetics and phonology of Semitic pharyngeals", in Keating (ed.), *Phonological Structure and Phonetic Form: Papers in Laboratory Phonology III*, Cambridge University Press, pp. 218–219) reports "a constriction in the upper pharynx" and writes that these sounds "should really be called uvularized". Real-time MRI shows that this constriction is at a different place from that of the pharyngeals `ħ ʕ` (Hermes, Barlaz, Shosted, Liang and Sutton 2017, Interspeech, pp. 201–205). Ultrasound shows "tongue root and tongue dorsum retraction with inconsistent tongue root retraction" (Al-Solami 2017, *Canadian Acoustics* 45(1), pp. 25–35). Thus `◌ˤ` sets `pharyngealized` + for the upper-pharynx constriction, and `atr` − for the part of it that retracts the tongue root. A pharyngealized vowel and a vowel with retracted tongue root share `atr` −, but differ in `pharyngealized`: `iˤ` is not `i̙`.

`◌̘` and `◌̙` set `atr`. Advanced tongue root is a contrast in the size of the pharyngeal cavity, not in vowel height (Casali 2007, "Some observations on the phonetics of [ATR] contrasts", lecture, University of Education, Winneba, section 2, after Lindau 1979, "The feature expanded", *Journal of Phonetics* 7). Thus the mark keeps `tense` as the base has it.

Rhoticity `◌˞` colours a vowel. The IPA chart gives the mark a name and no features. PanPhon's rule made `ɚ` high and rounded. This table reads the mark as a colouring that keeps the vowel's height and rounding, and keeps PanPhon's `ant` −. The precomposed letters `ɚ` and `ɝ` read as `ə˞` and `ɜ˞`, and `ɫ`, the chart's example for `◌̴`, reads as `l̴`.

`hi` means a raised tongue body and `lo` a lowered one, so no segment is [+high, +low]. A mark that adds one keeps the other as the base has it. The build stops if a segment is [+high, +low].

### Scales and their ends

The chart's vowel quadrilateral gives three ordered scales: seven heights, three columns, and the rounding steps −, 0, +. A mark moves a vowel one step on its scale, so `e̞` lies between `e` and `ɛ`, and `ɔ̜` between `ɔ` and `ʌ`. A mark at the end of its scale changes nothing: `ɔ̹` equals `ɔ`, because `ɔ` is already rounded, and `ĕ` equals `e`, because `e` is already short. Two other marks also change nothing. `t̺` equals `t`, because PanPhon's `t` is already apical. `d̚` equals `d`, because no feature of the table encodes the release of a stop.

## Letters PanPhon does not list

| Letter | Name | Built as | Source |
|---|---|---|---|
| `ⱱ` | labiodental flap | the manner of `ɾ` with the place of `v` | the IPA chart |
| `ʜ` | voiceless epiglottal fricative | `ħ` with `trill` + | Hassan et al. (2011) |
| `ʢ` | voiced epiglottal fricative | `ʕ` with `trill` + | Hassan et al. (2011) |
| `ʡ` | epiglottal plosive | `ħ` with `cont` −, `voi` − | the IPA chart (Other Symbols) |

The pharyngeals and the epiglottals have one place of articulation and differ in manner. Hassan, Esling, Moisik and Crevier-Buchman (2011, "Aryepiglottic trilled variants of /ʕ, ħ/ in Iraqi Arabic", ICPhS XVII, pp. 831–834) write that "both pharyngeals and epiglottals occur at the aryepiglottic sphincter point of stricture". Sounds heard as epiglottal "are associated either with AE trilled varieties" of the pharyngeals.

## Spellings that are not IPA

Some transcriptions use a symbol that the IPA chart does not contain. The reader treats each one as the IPA letter it stands for, before it looks up any feature. `vectorize_phones("ʤ")` returns the vector of `d͡ʒ`, and `segments("ʤ")` returns `["d͡ʒ"]`. So `ipa_distance("ɡato", "gato")` is 0.0.

| Spelling | Reads as | Unicode chart annotation |
|---|---|---|
| `g` (U+0067) | `ɡ` | cross reference "→ 0261 ɡ latin small letter script g"; U+0261 is "voiced velar stop" |
| `ʦ` (U+02A6) | `t͡s` | "voiceless dental affricate" |
| `ʣ` (U+02A3) | `d͡z` | "voiced dental affricate" |
| `ʧ` (U+02A7) | `t͡ʃ` | "voiceless postalveolar affricate" |
| `ʤ` (U+02A4) | `d͡ʒ` | "voiced postalveolar affricate" |
| `ʨ` (U+02A8) | `t͡ɕ` | "voiceless alveolo-palatal affricate" |
| `ʥ` (U+02A5) | `d͡ʑ` | "voiced alveolo-palatal affricate" |

The annotations come from the Unicode code charts for U+0000 and U+0250. Chapter 7 of the Unicode Standard says that `ʦ` "is a transcription for the sound that could also be transcribed in IPA as [ t͜s ] ... or [ t͡s ]". The chart calls `ʦ` and `ʣ` dental, and the table's `s` and `z` are alveolar. The reading follows the common IPA pairing, not the place word. The full rows, with their sources, are in `phonematcher/data/spellings.json`. To add a spelling, add a row there with the chart annotation as its source, and add its pair to `tests/test_spellings.py`.

## Other changes

| Segment | Feature | Value | Source |
|---|---|---|---|
| `ɹ` | `hi` | 0 | Hayes (2009) |
| `ɹ` | `round` | − | Hayes (2009) |

Every IPA letter has its own vector, and a test checks this. To add a change, add an entry to `overrides.json` and run the build. Then add a test that fails without the entry.

## Diacritics

`vectorize_phones` reads a segment that the table does not list as its longest listed base plus the diacritics after it. Each diacritic sets the features of its rule, in order, if the base meets the rule's conditions. For example, `ɐ̥` is `ɐ` with `voi` −.

PanPhon lists 6,367 segments, many with diacritics, such as `ɐ̃` and `kʷʰ`. The table takes all of them except the 50 stacks on `ɫ`, which `vectorize_phones` reads as `l̴` with the same marks, and adds the four letters above: 6,321 segments. The build reads each listed segment in the same way: its longest listed base, then the rules of its marks. A listed stack thus has the same vector as an unlisted one, and a test checks this for every listed stack. A mark that has no rule takes the difference that PanPhon records between the segment and its base letter.

Some marks come before their base. `ⁿ`, `ᵐ` and `ᵑ` before a stop make a prenasalized stop, as in `ⁿd`. `ʰ` before a stop makes a preaspirated stop, as in `ʰt`. Each takes the rule of the same mark after a base.

A tie bar joins two symbols into one segment. `t͡ʃ` and `t͜ʃ` are the same affricate. Without a tie bar, `tʃ` is two segments.

PanPhon lists 23 tied pairs, such as `t͡ʃ`, `k͡p` and `ɡ͡b`, each with its diacritic stacks. A tied segment that is not listed is built from its parts, right to left:

| Parts | Result | Example |
|---|---|---|
| a nasal, then an obstruent | the obstruent with `nas` +, as `ᵐb` | `m͡b` equals `ᵐb` |
| a stop, then a fricative | the fricative with `cont` −, `delrel` +, and `sg` or `cg` + if either part has it | `t̠͡ʃ` equals `t͡ʃ` |
| two stops or two nasals | a double articulation: a feature one part leaves at 0 takes the other's value, an articulator (`lab`, `cor`, `hi`, `back`) either part uses is +, and other features the parts set apart are 0 | `ŋ͡m͡ɡ͡b` equals `ᵑɡ͡b` |

The rule gives the listed vector for 18 of PanPhon's 23 pairs. For `b͡β`, `p͡ɸ`, `ɖ͡ʐ` and `ʈ͡ʂ`, PanPhon sets `hi` and `lo` to 0, but its fricatives have −. For `ɟ͡ʝ`, PanPhon sets `cor` + and `distr` +, and `front` 0, but `ʝ` has `cor` −, `distr` 0 and `front` +. The listed rows of these five stay as PanPhon has them.

Other ties raise `ValueError`. Two vowels are two segments: `a͡i` is not read, because one vector cannot keep the order of `a` and `i`. Two sonorants, such as `l͡j`, and a fricative before a stop have no reading here.

## Distance

`phonetic_distance(a, b)` compares two segments feature by feature. The values count as + = 1, 0 = 0 and − = −1. Each feature adds its weight times half the difference of the two values:

| Values | Cost of the feature |
|---|---|
| same | 0 |
| 0 against + or − | half the weight |
| + against − | the full weight |

The total is divided by the sum of all weights, so the result is from 0 to 1. A segment that cannot be read is at distance 1 from all other segments.

The weights of features 0 to 21 are PanPhon's. Two chart vowels are always nearer to each other than a vowel is to a stop or a fricative. The weights are not tuned to one language. A variant pair can thus be farther apart than a contrast: `ʁ`/`ʀ` is 0.158 but `ʁ`/`k` is 0.118, because a trill and a fricative differ in manner.

## Tone

A tone is not a feature of its vowel. It is a segment of its own, a sequence of pitch levels from 1 (extra low) to 5 (extra high), written after its syllable:

```python
segments("má")       # ['m', 'a', '˦']
segments("ma˦")      # ['m', 'a', '˦']
segments("ma²¹⁴")    # ['m', 'a', '˨˩˦']
```

The IPA chart gives the tone letters and the tone diacritics side by side, and each diacritic reads as the letters beside it:

| Diacritic | Tone letters | Chart name |
|---|---|---|
| `◌̋` | `˥` | Extra high |
| `◌́` | `˦` | High |
| `◌̄` | `˧` | Mid |
| `◌̀` | `˨` | Low |
| `◌̏` | `˩` | Extra low |
| `◌̌` | `˩˥` | Rising |
| `◌̂` | `˥˩` | Falling |
| `◌᷄` | `˧˥` | High rising |
| `◌᷅` | `˩˧` | Low rising |
| `◌᷈` | `˧˦˨` | Rising-falling |

Superscript digits are Chao tone numerals: the digit is the level, so `²¹⁴` is `˨˩˦`. The left-stem tone letters `꜒` to `꜖` have the levels of `˥` to `˩`. A run of tone letters is one tone, also after a tone diacritic: `má˥` has the tone `˦˥`.

Some marks are not read and are dropped like stress marks. The chart lists downstep `ꜜ` and upstep `ꜛ` with the level tones, but they change the pitch of the tones after them, and a tone here is the contour of one syllable only. Global rise `↗` and global fall `↘` belong to the intonation of a phrase. The neutral-tone numeral `⁰` has no level.

Two tones are compared by their contours. Each tone gives its pitch at the start, the middle and the end of the syllable, by linear steps between its levels. The tone distance is the mean difference of the three pitches, divided by four, the range from `˩` to `˥`. Thus `˥` and `˩` are at 1, `˥` and `˦` at 0.25, and `˧˥` and `˩˥` at 0.25. A tone against a phone costs 1, so a tone never replaces a sound, and a missing tone costs 1, like a missing sound.

The scale of one quarter per level is linear and not fitted to perception data. The search index ignores tones, so a query finds a word with any tone, and the score ranks the same tone first.

## Rebuilding

```
uv pip install panphon==0.22.2 pyyaml
python scripts/build_features.py
```

The build prints the number of segments in, added and out, the number of value changes and the number of diacritic rules. It stops if a change's recorded old value does not match the table, or if a segment is [+high, +low].
