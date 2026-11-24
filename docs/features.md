# The feature table
<!-- agent-hint
covers: the feature table: its 36 features, weights, sources, diacritic rules and the distance formula
source: phonematcher/data/features.json, phonematcher/data/overrides.json, scripts/build_features.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k features.md
see: add-a-segment.md, compare-sounds.md, api.md
-->

Each IPA segment has a vector of 36 distinctive features. A value is `True` (+), `False` (−) or `None` (0, the feature does not apply). The table is in `phonematcher/data/features.json`. The script `scripts/build_features.py` builds it from PanPhon, the Hayes (2009) feature tables as converted to CSV by Gorman, the IPA vowel chart and a file of cited changes.

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
| 22 | `front` | front: the tongue body is pushed forward | 0.25 | Hayes (2009) CSV and the chart for vowels |
| 23 | `tap` | tap: one fast contact, as in `ɾ` | 0.25 | Hayes (2009) CSV |
| 24 | `trill` | trill: repeated contacts, as in `r` and `ʀ` | 0.25 | Hayes (2009) CSV |
| 25 | `atr` | advanced tongue root: + for `◌̘`, − for `◌̙` and `◌ˤ`, otherwise 0 | 0.25 | the IPA chart names the marks, and Casali (2007) |
| 26–31 | `h1` … `h6` | vowel height steps: on a chart vowel, + for each row it lies below close and − for the rest; 0 on other segments | 0.125 each | the chart |
| 32 | `palatalized` | a secondary raising of the tongue body toward the palate: `◌ʲ`, `◌ᶣ` | 0.125 | the IPA chart names `◌ʲ`, and the feature is this table's |
| 33 | `velarized` | a secondary raising of the tongue body toward the velum: `◌ˠ`; 0 for `◌̴` | 0.125 | the IPA chart names `◌ˠ`, and the feature is this table's |
| 34 | `labialized` | a secondary rounding of the lips: `◌ʷ`, `◌ᶣ` | 0.125 | the IPA chart names `◌ʷ`, and the feature is this table's |
| 35 | `pharyngealized` | a secondary constriction in the upper pharynx: `◌ˤ`; 0 for `◌̴` | 0.125 | McCarthy (1994); Hermes et al. (2017) |

`front` and `back` together give three positions. A front vowel is [+front, −back]. A central vowel is [−front, −back]. A back vowel is [−front, +back].

## Sources

| Source | What it gives |
|---|---|
| PanPhon (Mortensen, Littell, Bharadwaj, Goyal, Dyer and Levin 2016, "PanPhon: A Resource for Mapping IPA Segments to Articulatory Feature Vectors", *Proceedings of COLING 2016*, pp. 3475–3484, MIT licence) | 6,367 segments, features 0 to 21, their weights and the rules for diacritics. Its two tone features are not used. |
| The CSV conversion by Kyle Gorman (github.com/kylebgorman/hayes2009, Apache-2.0, in `scripts/sources/`) of the feature tables of Hayes (2009, *Introductory Phonology*, Wiley-Blackwell). Gorman's `hayes2009.py` names them as tables 4.7 to 4.9, section 4.10. | `front`, `tap` and `trill` for consonants, and the value changes in "Other changes" |
| The IPA chart (International Phonetic Association; the footer reads "IPA Chart revised to 2015/2005"), whose vowel quadrilateral is in `scripts/sources/ipa-vowel-chart.csv` | the height, backness and rounding of the 28 vowel letters |
| The extIPA chart (International Clinical Phonetics and Linguistics Association; "Revised to 2015"), the Unicode Standard 18.0 code charts U0300 and U02B0, and Chang (2007) | the meaning of the marks in `◌͈ ◌͉ ◌̪ ◌̢ ◌͇ ◌̣ ◌̭ ◌̊` and `˔ ˕ ˖ ˗` |
| `phonematcher/data/overrides.json` | every other change, each with its source and reason |

The works cited on this page are in `docs/references.bib`, with their pages.

A segment that no source gives a value for gets `front` 0, `tap` −, `trill` −, `atr` 0 and the step features 0.

## Vowels

The 28 vowel letters take their values from their place on the IPA chart, not from a feature table. The chart defines what each symbol means, so it is the first authority.

| Row or column | Features |
|---|---|
| close, near-close | `hi` + |
| close-mid, mid, open-mid | `hi` −, `lo` − |
| near-open, open | `lo` + |
| front | `front` +, `back` − |
| central | `front` −, `back` − |
| back | `front` −, `back` + |
| rounded | `round` +, `lab` + |

`hi` and `lo` give only three heights. The chart prints four height labels (close, close-mid, open-mid, open) and draws `ɪ ʏ ʊ`, `ə` and `æ ɐ` between them. This table counts these seven rows and names the three between the labels near-close, mid and near-open. The step features `h1` to `h6` give all seven in order. A vowel is + on `h1` if it is below close, + on `h2` if it is below near-close, and so on. Two vowels thus differ on as many step features as there are chart rows between them, and the distance between vowels grows with every row.

| Height | Letters | `h1` … `h6` |
|---|---|---|
| close | `i y ɨ ʉ ɯ u` | − − − − − − |
| near-close | `ɪ ʏ ʊ` | + − − − − − |
| close-mid | `e ø ɘ ɵ ɤ o` | + + − − − − |
| mid | `ə` | + + + − − − |
| open-mid | `ɛ œ ɜ ɞ ʌ ɔ` | + + + + − − |
| near-open | `æ ɐ` | + + + + + − |
| open | `a ɶ ɑ ɒ` | + + + + + + |

The chart prints three column labels: front, central and back. It draws `ɪ ʏ` between the front and central columns and `ʊ` between the central and back columns. The features give three columns, so `ɪ ʏ` count as front and `ʊ` as back. Their lower height keeps them apart from `i y u`.

The chart draws `a` at the open front corner and `ɐ` in the central column, between open-mid and open. The chart states that of a pair of symbols, the one to the right is rounded, so `a`, drawn left of `ɶ`, is unrounded. The chart draws `ɐ` alone, so this table reads it as unrounded without a source. A transcription that means open central can write `ä`, `a` with the mark the chart names "Centralized".

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
| `◌̘` advanced tongue root | `tense` + | `atr` +, `tense` kept | the IPA chart names it, and Casali (2007) |
| `◌̙` retracted tongue root | `tense` − | `atr` −, `tense` kept | the IPA chart names it, and Casali (2007) |
| `◌ʲ` palatalized | `hi` +, `back` − | `palatalized` + | the IPA chart names it, and the feature is this table's |
| `◌ᶣ` labio-palatalized | `hi` +, `back` −, `round` + | `palatalized` +, `labialized` + | the IPA chart names `◌ʷ` and `◌ʲ`, and the combined mark and the features are this table's |
| `◌ʷ` labialized | `hi` +, `back` +, `round` + | `labialized` + | the IPA chart names it, and the feature is this table's |
| `◌ˠ` velarized | `hi` +, `back` + | `velarized` + | the IPA chart names it, and the feature is this table's |
| `◌̴` velarized or pharyngealized | `hi` +, `back` + | `velarized` 0, `pharyngealized` 0 | the IPA chart |
| `◌ˤ` pharyngealized | `lo` +, `back` + | `pharyngealized` +, `atr` − | the IPA chart names it, and McCarthy (1994), Hermes et al. (2017) and Al-Solami (2017) describe it |
| `◌˞` rhoticity | `hi` +, `round` +, `ant` − | `ant` − only | the IPA chart names it; the reading is this table's |
| `◌̩` syllabic | `syl` +, only on a continuant without delayed release or on a sonorant | the same, and on any fricative | the Unicode chart (U0250): `ɿ` is "IPA spelling - 007A z 0329" |
| `◌̃` nasalized | `nas` +, only on a voiced base | `nas` + on a voiced base or on a vowel, voiced or not | the IPA chart prints it on the vowel in `ẽ` and ties it to no voicing |
| `◌̊` ring above | no rule | `voi` − on any base, as `◌̥` | the IPA chart prints `ŋ̊`, the ring of "Voiceless" above a descender |
| `◌̪` dental | no rule | `distr` + on a coronal | the IPA chart and the Unicode chart ("IPA: dental"); PanPhon's eight dental segments differ from their letters in `distr` alone |
| `◌̢` retroflexion | no rule | `ant` − on a coronal | the Unicode chart ("IPA: retroflexion"); the reading is this table's |
| `◌͇` equals sign below | no rule | `ant` + on a coronal | the Unicode chart ("IPA: alveolar"); the reading is this table's |
| `◌̣` dot below | no rule | on a vowel, one chart row closer | the Unicode chart ("IPA: closer variety of vowel"); the one-row step is this table's |
| `◌̭` circumflex below | no rule | as `◌̟` | the Unicode chart gives both "fronted articulation" |
| `◌͈` strong articulation | no rule | read; no change | the extIPA chart |
| `◌͉` weak articulation | no rule | read; no change | the extIPA chart |
| `˔` `˕` `˖` `˗` | no rule | as `◌̝` `◌̞` `◌̟` `◌̠` | the Unicode chart names each as the spacing form of its combining mark |

The extIPA chart (revised to 2015) prints `◌͈` as "strong articulation" and `◌͉` as "weak articulation", and gives neither a feature. Both marks read and change no feature.

Korean fortis obstruents are written with `◌͈`, as `k͈ s͈ t͈`. Chang (2007, *UC Berkeley PhonLab Annual Report* 3(3), pp. 1 and 3) writes that the fortis series is "associated with glottal adduction and stiffening". The chart does not link the mark to that setting, and other languages write the mark too (Ewe `f͈` and `v͈`). So `k͈ s͈ t͈` read the same as `k s t`, and the fortis contrast is lost.

### Marks that stay unread

A mark reads only if a chart states its meaning. These marks occur in PHOIBLE, WikiPron or orthography2ipa and have no statement, so they do not read.

| Mark | What the charts say |
|---|---|
| `ˁ` | The Unicode chart calls it a "typographical alternate for 02BF ʿ", the transliteration of Arabic ain. It does not name `ˤ`. |
| `ʳ` `ʶ` | "r-coloring or r-offglides": the chart does not say which of the two a transcription means. |
| `ˢ` `ˣ` `ᵡ` `ᶲ` `ᵏ` `ᵍ` | Only "≈ superscript" of the letter. A note under `ˠ` says that such modifier letters are "occasionally used in transcription of affricates". The reading is a tied affricate, which needs a reader change and not a diacritic rule, and in Finnish `eˣ` follows a vowel. |
| `ᵊ` `ᵝ` `ᵘ` `ᶢ` | Only "≈ superscript" of the letter. |
| `ᶬ` `ᶮ` `ᶯ` `ᶰ` `ᵑ` | Only "≈ superscript" of the nasal letter. `ᵐ`, `ⁿ` and `ᵑ` read as prenasalization by the rule of `◌ⁿ`; the others have no such statement. |
| `◌̍` | "this is not the Greek tonos", "Marshallese". The IPA chart marks a syllabic consonant with `◌̩`. |
| `◌̵` `◌͓` `◌͠` | The Unicode chart gives no annotation. |
| `↓` | The extIPA chart prints "ingressive airflow", which no feature of the table encodes. |

### Marks that a base refuses

A rule applies a mark only to the bases a chart prints it on. A base outside that class makes `vectorize_phones` raise `ValueError`, and the segment is at distance 1 from every other. A rule widens when a chart prints the mark on the new class of base, as the IPA chart does for `◌̃` on a vowel. The Unicode chart gives a mark a name and no base, so a name alone does not widen a rule.

| Mark | What the charts print | Bases that stay refused |
|---|---|---|
| `◌̃` | `ẽ`, a vowel | consonants: `k̃ f̃ h̃`; a nasal: `m̃` |
| `◌ʰ` | `tʰ dʰ` (IPA chart), `ʰp` (extIPA chart) | vowels `aʰ`, nasals `m̥ʰ`, liquids `lʰ`, glides `jʰ`, `ʔʰ` |
| `◌ⁿ` | `dⁿ` | vowels `aⁿ`, fricatives `ⁿs`, liquids and glides `ⁿl ⁿw` |
| `◌ʷ` `◌ʲ` | `tʷ dʷ`, `tʲ dʲ` | vowels `uʷ ʊʷ`, `iʲ` |
| `◌ˡ` | `dˡ`, a coronal stop | `nˡ`, `pˡ` |
| `◌̰` | `b̰ a̰`, both voiced | voiceless bases `p̰ k̰ t̰` |
| `◌̩` | `n̩`, a nasal; the Unicode chart spells `ɿ` as `z̩`, so a fricative takes it too | vowels `a̩`, stops `ɟ̰̩` |
| `◌̆` | `ĕ`, a vowel | `ɭ̆`, `ĭ̯` |
| `◌̞` | `β̞`, a fricative | stops `ɡ̞ k̞ʰ` |
| `◌ʱ` | a name only (Unicode chart: "breathy voiced, murmured") | voiceless clicks `ǃʱ ǀʱ` |
| `◌̼` `◌̻` | `t̼ d̼`, `t̻ d̻` | labial bases `m̼ p̼`, `m̻` |
| `◌ˀ` `◌ː` `◌̈` `◌ʼ` | `ː` once, `ë`, `p’ t’ k’ s’` | `ɑ̰ˀ`, `kːː`, `ẅ`, `ʎʼ` |
| `ᵡ` | "≈ superscript" of `χ` | after an affricate: `ʦᵡ ʣᵡʼ` |

The marks `◌̟ ◌̠ ◌̝ ◌̞ ◌̭ ˖ ˗ ˔ ˕` move a chart vowel along a scale. On a consonant that the rule accepts they read and change nothing: `ṱ` reads as `t`, and `r˔` reads as `r`. `◌̝ ◌̞ ˔ ˕` accept only a continuant.

PanPhon writes a secondary articulation with the features of primary place. The mark then overwrites the place of its base: in PanPhon, `kʲ` and `qʲ` share a vector. Here each mark sets a feature of its own, and the base keeps its place. Thus `kʲ` has the place of `k` and differs from `k` only in `palatalized`. The four feature names belong to this table.

Pharyngealized consonants, such as the Arabic emphatics, have a second constriction high in the pharynx. McCarthy (1994, "The phonetics and phonology of Semitic pharyngeals", in Keating (ed.), *Phonological Structure and Phonetic Form: Papers in Laboratory Phonology III*, Cambridge University Press, pp. 218–219) reports that emphatics "have a constriction in the upper pharynx". He writes: "The so-called pharyngealized consonants of Arabic should really be called uvularized." Real-time MRI shows that this constriction is at a different place from that of the pharyngeals `ħ ʕ` (Hermes, Barlaz, Shosted, Liang and Sutton 2017, Interspeech, pp. 201–205). Ultrasound shows "tongue root and tongue dorsum retraction with inconsistent tongue root retraction" (Al-Solami 2017, *Canadian Acoustics* 45(1), pp. 25–35). Thus `◌ˤ` sets `pharyngealized` + for the upper-pharynx constriction, and `atr` − for the part of it that retracts the tongue root. A pharyngealized vowel and a vowel with retracted tongue root share `atr` −, but differ in `pharyngealized`: `iˤ` is not `i̙`.

`◌̘` and `◌̙` set `atr`. Casali (2007, "Some observations on the phonetics of [ATR] contrasts", lecture, University of Education, Winneba, section 2, p. 2) writes that expansion or contraction of the pharyngeal cavity is a better measure of the [ATR] contrast than tongue root position alone, at least in languages such as Akan. He also writes that it is "probably not possible to give a single invariant articulatory definition of [ATR] that applies to all ATR harmony languages". This table gives [ATR] a feature of its own and does not read it as vowel height, so the mark keeps `tense` as the base has it.

Rhoticity `◌˞` colours a vowel. The IPA chart gives the mark a name and no features. PanPhon's rule made `ɚ` high and rounded. This table reads the mark as a colouring that keeps the vowel's height and rounding, and keeps PanPhon's `ant` −. The precomposed letters `ɚ` and `ɝ` read as `ə˞` and `ɜ˞`, and `ɫ`, the chart's example for `◌̴`, reads as `l̴`.

`hi` means a raised tongue body and `lo` a lowered one, so no segment is [+high, +low]. A mark that adds one keeps the other as the base has it. The build stops if a segment is [+high, +low].

### Scales and their ends

The chart's vowel quadrilateral gives three ordered scales: the seven height rows of this table, the three columns, and the rounding steps −, 0, +. A mark moves a vowel one step on its scale, so `e̞` lies between `e` and `ɛ`, and `ɔ̜` between `ɔ` and `ʌ`. A mark at the end of its scale changes nothing: `ɔ̹` equals `ɔ`, because `ɔ` is already rounded, and `ĕ` equals `e`, because `e` is already short. Two other marks also change nothing. `t̺` equals `t`, because PanPhon's `t` is already apical. `d̚` equals `d`, because no feature of the table encodes the release of a stop.

## Letters PanPhon does not list

| Letter | Name | Built as | Source |
|---|---|---|---|
| `ⱱ` | labiodental flap | the manner of `ɾ` with the place of `v` | the IPA chart |
| `ʜ` | voiceless epiglottal fricative | `ħ` with `trill` + | the IPA chart (Other Symbols) and Hassan et al. (2011) |
| `ʢ` | voiced epiglottal fricative | `ʕ` with `trill` + | the IPA chart (Other Symbols) and Hassan et al. (2011) |
| `ʡ` | epiglottal plosive | `ħ` with `cont` −, `voi` − | the IPA chart (Other Symbols) |
| `ȵ` | alveolo-palatal nasal | the manner of `n` with the place of `ɕ` | Unicode chart U+0235 (name), Wikipedia (sound), PHOIBLE 2.0 row |
| `ȶ` | alveolo-palatal plosive | the manner of `t` with the place of `ɕ` | Unicode chart U+0236 (name), Wikipedia (sound), PHOIBLE 2.0 row |
| `ȴ` | alveolo-palatal lateral | the manner of `l` with the place of `ɕ` | Unicode chart U+0234 (name), Wikipedia (sound), PHOIBLE 2.0 row |
| `ᶑ` | retroflex implosive | the manner of `ɗ` with the place of `ɖ` | Unicode chart U+1D91 (name), Wikipedia (sound), PHOIBLE 2.0 row |
| `ɿ` | apical dental vowel | the vector of `z̩` | Unicode chart U+027F: "IPA spelling - 007A z 0329" |
| `ʮ` | labialized apical dental vowel | `ɿ` with `round` + and `lab` +, as `y` has them | Unicode chart U+02AE |

The curl letters `ȵ ȶ ȴ` are Sinological symbols that the IPA does not contain. The Unicode chart gives only their names, under "Additions for Sinology", and Wikipedia states the sound. Their name says "WITH CURL", and the curl is the one of `ɕ` and `ʑ`. The place of `ɕ` is `ant` −, `cor` +, `distr` +, `hi` +, `lo` −, `back` − and `front` +. PHOIBLE 2.0 gives the same letters `anterior` +, where PanPhon's `ɕ` has `ant` −. The table keeps `ant` − so that `ȵ` and `ɕ` share one place, as `ɲ` and `ɕ` do in PanPhon. PHOIBLE agrees on every other place feature. For `ᶑ`, PHOIBLE gives `cg` −, because it codes the implosive with its own feature. PanPhon's `ɗ` has `cg` +, and the table keeps it, so `ᶑ` and `ɗ` differ only in place.

`ᴇ` (U+1D07) and `ᵻ` (U+1D7B) do not read. The Unicode chart gives no meaning for `ᴇ`. For `ᵻ` it says "used with different meanings by Americanists and Oxford dictionaries".

The IPA chart lists `ʜ`, `ʢ` and `ʡ` as the voiceless epiglottal fricative, the voiced epiglottal fricative and the epiglottal plosive. Hassan, Esling, Moisik and Crevier-Buchman (2011, "Aryepiglottic trilled variants of /ʕ, ħ/ in Iraqi Arabic", ICPhS XVII, pp. 831–834) write that "both pharyngeals and epiglottals occur at the aryepiglottic sphincter point of stricture" (p. 831, reporting Esling). They add that sounds heard as epiglottal "are associated either with AE trilled varieties of the simple fricative or approximant or with the default raised-larynx posture of the laryngeal sphincter" (p. 831). This table takes the first reading: `ʜ` and `ʢ` are `ħ` and `ʕ` with `trill` +.

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

## Letters with no tie bar

The IPA chart says: "Affricates and double articulations can be represented by two symbols joined by a tie bar if necessary." (Other Symbols, IPA chart revised to 2015/2005). So a transcription may leave the tie bar out when the two symbols are one segment. `vectorize_phones` reads such a segment as the one with the tie bar:

```python
from phonematcher import segments
from phonematcher.features import vectorize_phones

vectorize_phones("ts") == vectorize_phones("t͡s")   # True
vectorize_phones("kp") == vectorize_phones("k͡p")   # True
segments("ts")                                      # ['t', 's']
```

The reader puts a tie bar between each two base letters and reads the result. A tie that `compose_tie` has no reading for stays unread: `ab`, `ɑi`, and the three-letter `bvf` and `dzs`, because a fricative tied to a fricative has no reading. For the same reason `ʧ͡f` and `ʤ͡v` stay unread.

A letter that repeats the one before it is a geminate, not a tie: `nn` and `tt` stay unread. A click after a velar or uvular letter (`k ɡ ŋ q ɢ ɴ`) is that letter tied to the click: `kǀ` is `k͡ǀ`. The IPA Handbook says: "Since any click involves a velar or uvular closure, it is possible to symbolize factors such as voicelessness, voicing, or nasality of the click by combining the click symbol with the appropriate velar or uvular symbol" (section 2.5, p. 10). A click after any other letter stays unread.

Only a segment given whole is read this way. `segments` keeps `ts` in running text as two segments, `t` and `s`, because the same two letters are two sounds in many words. Use `segments("t͡s")` or write the tie bar to make one.

A mark before such a segment applies to it as to a listed one. `ʰts` is `t͡s` with `sg` +, and `ᵐɡb` is `ɡ͡b` with `nas` +. `ⁿ`, `ᵐ` and `ᵑ` before an affricate, tied or not, add `nas` + to it, as a nasal tied before it does: `ⁿd͡z` and `ⁿdz` equal `n͡d͡z`. The mark's own rule still decides elsewhere: `ⁿs` and `ⁿʃ` stay unread, because `◌ⁿ` applies to a stop.

## Other changes

| Segment | Feature | Value | Source |
|---|---|---|---|
| `ɹ` | `hi` | 0 | Hayes (2009) CSV |
| `ɹ` | `round` | − | Hayes (2009) CSV |
| `h` `ɦ` | `son` | − | Hayes (2009) CSV |
| `h` `ɦ` | `cons` | − | Hayes (2009) CSV |
| `ʔ` | `son` | − | Hayes (2009) CSV |
| `ʔ` | `cons` | + | Hayes (2009) CSV |

PanPhon gives `h` and `ɦ` [+son, +cons] and `ʔ` [+son, −cons]. With those values, `h` is nearer `ʀ` than `x`, and `ʔ` is nearer `j` than `k`. The Hayes CSV values put the three letters with the obstruents. Because `ʔ` is [−son], the rule of `◌̩` refuses `ʔ̩`, as it refuses the other syllabic stops. As a stop, `ʔ` before another stop takes the rule for two stops: `ʔt` reads as `ʔ͡t`.

Every IPA letter has its own vector, and a test checks this. To add a change, add an entry to `overrides.json` and run the build. Then add a test that fails without the entry.

## Diacritics

`vectorize_phones` reads a segment that the table does not list as its longest listed base plus the diacritics after it. Each diacritic sets the features of its rule, in order, if the base meets the rule's conditions. For example, `ɐ̥` is `ɐ` with `voi` −.

PanPhon lists 6,367 segments, many with diacritics, such as `ɐ̃` and `kʷʰ`. The table takes all of them except the 50 stacks on `ɫ`, which `vectorize_phones` reads as `l̴` with the same marks, and the 10 tone rows (the five tone letters `˩ ˨ ˧ ˦ ˥`, each also with `ˤ`), which `phonematcher.tone` reads. It adds the ten letters above: 6,317 segments. The build reads each listed segment in the same way: its longest listed base, then the rules of its marks. A listed stack thus has the same vector as an unlisted one, and a test checks this for every listed stack. A mark that has no rule takes the difference that PanPhon records between the segment and its base letter.

Some marks come before their base. `ⁿ`, `ᵐ` and `ᵑ` before a stop make a prenasalized stop, as in `ⁿd`. `ʰ` before a stop makes a preaspirated stop, as in `ʰt`. Each takes the rule of the same mark after a base.

A tie bar joins two symbols into one segment. `t͡ʃ` and `t͜ʃ` are the same affricate. Without a tie bar, `tʃ` is two segments.

PanPhon lists 23 tied pairs, such as `t͡ʃ`, `k͡p` and `ɡ͡b`, each with its diacritic stacks. A tied segment that is not listed is built from its parts, right to left:

| Parts | Result | Example |
|---|---|---|
| a nasal, then an obstruent | the obstruent with `nas` +, as `ᵐb` | `m͡b` equals `ᵐb` |
| a stop, then a fricative | the fricative with `cont` −, `delrel` +, and `sg` or `cg` + if either part has it | `t̠͡ʃ` equals `t͡ʃ` |
| two stops or two nasals | a double articulation: a feature one part leaves at 0 takes the other's value, an articulator (`lab`, `cor`, `hi`, `back`) either part uses is +, and other features the parts set apart are 0 | `ŋ͡m͡ɡ͡b` equals `ᵑɡ͡b` |

The rule gives the listed vector for 18 of PanPhon's 23 pairs. For `b͡β`, `p͡ɸ`, `ɖ͡ʐ` and `ʈ͡ʂ`, PanPhon sets `hi` and `lo` to 0, but its fricatives have −. For `ɟ͡ʝ`, PanPhon sets `cor` + and `distr` +, and `front` 0, but `ʝ` has `cor` −, `distr` 0 and `front` +. The listed rows of these five stay as PanPhon has them.

Other ties raise `ValueError`. Two sonorants, such as `l͡j`, and a fricative before a stop have no reading here.

### Diphthongs

`segments` splits a tie between two vowels into the two vowels: `a͡i` gives `a` and `i`, and `ei̯` gives `e` and `i̯`. A tie between two consonants still joins them, so `t͡ʃa͡i` gives `t͡ʃ`, `a` and `i`. A diphthong thus costs as two segments in a word distance, and `ai` and `a͡i` are at distance 0. Against `a` the distance is 0.5, one deletion of `i`.

Nerbonne and Heeringa (1997, pp. 11-13) compared one-symbol and two-symbol diphthongs on 40 Dutch dialects with feature vectors. The two-symbol form gave the better dialect distances. Anderson et al. (2018, p. 33) define a diphthong in CLTS as two vowels: "Diphthongs are thus defined by two vowels". A diphthong has no vector of its own, so `vectorize_phones` raises `ValueError` for `ai`, `a͡i` and `ei̯`:

| Input | Result | Reason |
|---|---|---|
| `a͡i`, `ai`, `ei̯` as one segment | `ValueError` | a diphthong is two segments; read `a` and `i` alone |

## Distance

`feature_distance(a, b)` compares two segments feature by feature. The values count as + = 1, 0 = 0 and − = −1. Each feature adds its weight times half the difference of the two values:

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

The IPA chart prints each tone diacritic beside a drawing of a tone letter or a contour. This table reads each diacritic as the tone letters that match the drawing:

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

Superscript digits are tone numerals: the digit is the level, so `²¹⁴` is `˨˩˦`. The left-stem tone letters `꜒` to `꜖` have the levels of `˥` to `˩`. A run of tone letters is one tone, also after a tone diacritic: `má˥` has the tone `˦˥`.

Some marks are not read and are dropped like stress marks. The chart lists downstep `ꜜ` and upstep `ꜛ` with the level tones, but they change the pitch of the tones after them, and a tone here is the contour of one syllable only. Global rise `↗` and global fall `↘` belong to the intonation of a phrase. The neutral-tone numeral `⁰` has no level.

Two tones are compared by their contours. Each tone gives its pitch at the start, the middle and the end of the syllable, by linear steps between its levels. The tone distance is the mean difference of the three pitches, divided by four, the range from `˩` to `˥`. Thus `˥` and `˩` are at 1, `˥` and `˦` at 0.25, and `˧˥` and `˩˥` at 0.25. A tone against a phone costs 1, so a tone costs no less than deleting one segment and inserting the other (see [Tones](tones.md)), and a missing tone costs 0.5, like a missing sound.

The scale of one quarter per level is linear and not fitted to perception data. The search index ignores tones, so a query finds a word with any tone, and the score ranks the same tone first.

## Rebuilding

```
uv pip install panphon==0.22.2 pyyaml
python scripts/build_features.py
```

The build prints the number of segments in, added and out, the number of value changes and the number of diacritic rules. It stops if a change's recorded old value does not match the table, or if a segment is [+high, +low].

[Index](index.md) · Previous: [Add a segment](add-a-segment.md) · Next: [Design choices and limits](design.md)
