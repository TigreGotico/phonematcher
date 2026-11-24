# API reference
<!-- agent-hint
covers: every public name of the package and what it returns
source: phonematcher/__init__.py, phonematcher/features.py, phonematcher/distance.py, phonematcher/tone.py, phonematcher/clustering.py, phonematcher/phonex.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k api.md
see: quickstart.md, features.md
-->

## Stable API

These names are the stable API. Each one is exported from the package root, so `from phonematcher import <name>` works, except `phonex`. The function `phonex` has the name of its module, so it is not exported from the root.

| Name | What it is | Module |
|---|---|---|
| `Match` | A search result: id, term readings, score. | `phonematcher.clustering` |
| `PhoneticFuzzySearch` | An index of IPA terms that finds terms by sound. | `phonematcher.clustering` |
| `align` | One least-cost alignment of two segment lists. | `phonematcher.distance` |
| `edit_distance` | The cost of the cheapest edit of one segment list into another. | `phonematcher.distance` |
| `ipa_distance` | The edit distance between two IPA strings. | `phonematcher.distance` |
| `segments` | The segments of an IPA string. | `phonematcher.distance` |
| `segment_spans` | The offsets of the segments in the input string. | `phonematcher.distance` |
| `substitution_cost` | The cost of replacing one segment by another. | `phonematcher.distance` |
| `GAP_COST` | The cost of an insertion or a deletion. | `phonematcher.distance` |
| `feature_distance` | The weighted feature distance of two segments. | `phonematcher.features` |
| `vectorize_phones` | The feature vector of one segment. | `phonematcher.features` |
| `is_vowel_phone` | True for a syllabic segment. | `phonematcher.features` |
| `FEATURES` | The feature names, read-only. | `phonematcher.features` |
| `WEIGHTS` | The feature weights, read-only. | `phonematcher.features` |
| `tone_distance` | The distance between two tones. Experimental. | `phonematcher.tone` |
| `is_tone` | True for a segment made only of tone letters. | `phonematcher.tone` |
| `tone_levels` | The Chao levels of a tone, in order. | `phonematcher.tone` |
| `phonex` | The cluster-id key of a word. Import it with `from phonematcher.phonex import phonex`. | `phonematcher.phonex` |

`phonematcher.__version__` is the version string of the installed package, such as `2.2.0a2`.

A stable name changes only in a major release, after one deprecation cycle with a warning. `phonetic_distance` is in that cycle: it is still exported from the package root, it warns, and it goes away in the next major version. Use `feature_distance` instead.

## Internal

Every other name is internal. It can change or go away in any release, with no warning. Do not import it in code that must keep working.

- `phonematcher.clustering`: `upgma`, `phone_clusters`, `merge_threshold`.
- `phonematcher.distance`: `check_readable`, `SUPRASEGMENTALS`, `NON_SYLLABIC`.
- `phonematcher.features`: `compose_tie`, `phone_features`, `NUM_FEATURES`, `SOURCE`, `SPELLINGS`, `PRE_DIACRITICS`, `POST_DIACRITICS`.
- `phonematcher.tone`: `LEVELS`, `DIACRITIC_TONES`, `NUMERALS`, `PHRASE_MARKS`.
- `phonematcher.scales`: the whole module.

The sections below describe the stable names first, then the internal names that the guides use.

## `phonematcher.features`


- `feature_distance(a, b) -> float`: the weighted feature distance between two segments, from 0 to 1. See [features.md](features.md).
- `phonetic_distance(a, b) -> float`: the old name of `feature_distance`. It returns the same value and raises a `DeprecationWarning` that names the version where it goes away, the next major version.
- `vectorize_phones(segment) -> tuple`: the feature vector of one segment, in the order of `FEATURES`. Raises `ValueError` for a segment it cannot read.
- `is_vowel_phone(segment) -> bool`: true when the segment reads and its `syl` feature is `+`: a vowel, a syllabic consonant such as `m̩`, or a rhotic vowel such as `ɚ`. It is false for a glide, a consonant, and a segment that cannot be read (it does not raise).
- `FEATURES`, `WEIGHTS`: the feature names and their weights, as tuples. Treat them as read-only.

## `phonematcher.distance`

- `segments(ipa) -> list[str]`: the segments of an IPA string. A diacritic stays with its base, a tie bar joins two symbols, a space between words becomes one `" "` segment, and stress, syllable and phrase-tone marks are dropped. A tone is one segment of tone letters after its syllable; a tone diacritic or a tone numeral is written as tone letters. A tie bar with nothing before it in its word is dropped, and format characters such as U+200B and U+FEFF are dropped.
- `segment_spans(text) -> list[tuple[int, int]]`: the `(start, end)` offsets of the segments in `text`, in order, so `[text[s:e] for s, e in segment_spans(text)]` gives each segment as it is written in `text`. A spelling keeps its form and nothing is normalized: `segment_spans("ˈʧa")` gives `[(1, 2), (2, 3)]`, the substrings `ʧ` and `a`, where `segments` gives `t͡ʃ` and `a`. The characters that `segments` drops (stress, syllable and phrase-tone marks, format characters) and the spaces between words fall in the gaps between spans. A mark that `segments` drops between the parts of one segment stays inside its span, so `ɲaⁿˈdu` puts the stress mark inside the span of `ⁿd`, and the `segments` of that span are still `ⁿd`. A tone diacritic stays in the span of the letter it is written on, because a precomposed letter such as `á` is one character. Two segments that share a character share one span, so the tie bar of `a͡i` puts `a` and `i̯` in one span. So, for well-formed IPA, the `segments` of each span, in turn, are the `segments` of `text` without its `" "` entries.
- `substitution_cost(a, b) -> float`: the one cost of replacing segment `a` by `b`: the square root of the tone distance of two tones, 1 for a tone and a phone, and the square root of the feature distance of two phones. `edit_distance`, `align`, `ipa_distance` and the clusters of `PhoneticFuzzySearch` use it.
- `edit_distance(a, b, *, strict=False, substitution=substitution_cost, gap=GAP_COST) -> float`: the Levenshtein distance between two segment lists, where a substitution costs `substitution_cost` and an insertion or deletion costs 0.5. `substitution` and `gap` replace these two costs. The costs are those of the pre-registered test in [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md) and [`docs/benchmarks.md`](https://github.com/TigreGotico/phonematcher/blob/dev/docs/benchmarks.md).
- `align(a, b, *, strict=False, substitution=substitution_cost, gap=GAP_COST) -> list[tuple[str | None, str | None]]`: one least-cost alignment of two segment lists, as pairs of a left and a right segment. `None` marks a gap. The costs are those of `edit_distance`. The traceback starts at the end and prefers a substitution, then a deletion (a gap in `b`), then an insertion.
- `edit_distance` takes lists of segments. A string is also accepted, and each character is then one segment, so `edit_distance("ka", "kb")` compares the two characters of each string. A diacritic or a tie bar is a character of its own in that case. Call `segments` first to split a string as IPA.
- A wrong type raises `TypeError` that names the function, the argument and the type: `ipa_distance` and `tone_distance` take strings (a string that is not a tone raises `ValueError`), `edit_distance` and `align` take lists of segments.
- The cost of `ipa_distance`, `edit_distance` and `align` grows with the product of the two segment counts: see [Split long input](compare-words.md#6-split-long-input).
- `ipa_distance(a, b, normalized=False, *, strict=False) -> float`: `edit_distance` between two IPA strings. With `normalized=True` the distance is divided by the segment count of the longer string, so it falls between 0 and 1, and two empty strings give 0.0.
- `GAP_COST`: the cost of an insertion or a deletion in `edit_distance` and `align`, 0.5.
- `strict=True` on `ipa_distance`, `edit_distance` and `align`: a segment that phonematcher cannot read raises `ValueError` that names the segment and the input. Without it, such a segment is at distance 1 from every other segment, and the first time it is priced against another segment it issues one `UserWarning` per process. The warning names the segment and its code points. A segment that meets only gaps, tones or spaces does not warn. A first warning that a filter ignores or turns into an error still uses up the segment's one warning. Silence it with `warnings.filterwarnings("ignore", message="Unrecognized phone", category=UserWarning)`. See [Design choices and limits](design.md#an-unread-segment-is-at-distance-1).

## `phonematcher.tone`

- `is_tone(segment) -> bool`: true for a segment made only of tone letters.
- `tone_levels(tone) -> tuple[int, ...]`: the Chao levels of a tone, in order, from 1 (extra low) to 5 (extra high), so `tone_levels("˧˦˧")` gives `(3, 4, 3)`. It takes tone letters, superscript tone numerals (`²¹⁴`) and left-stem tone letters (U+A712 to U+A716). A string that is not a tone raises `ValueError`, and a value that is not a string raises `TypeError`.
- `tone_distance(a, b) -> float`: the distance between two tones, from 0 to 1. It is experimental: see [Tones](tones.md) and issue [#68](https://github.com/TigreGotico/phonematcher/issues/68). See [features.md](features.md#tone).

## `phonematcher.clustering`

### `PhoneticFuzzySearch(cluster_sensitivity=0.08, *, strict=False)`

An index of IPA terms. Phones are grouped into clusters of near sounds by UPGMA average linkage over `substitution_cost`. `cluster_sensitivity` is a share from 0 to 1, and a value outside that range raises `ValueError`. A value that is not a number raises `TypeError`. The merge threshold is that quantile of `substitution_cost` over all pairs of distinct IPA letters of the table. A higher share puts more phones in one cluster, so a search finds more candidates. At 0.08, voicing pairs (`p b`), `ʁ χ`, `s ʃ`, `e ɛ` and `a ɐ` share a cluster, and `p t`, `ʁ k` and `e o` do not. [Search by sound](search.md) shows the steps. A `PhoneticFuzzySearch` is not thread-safe while terms are added: do not call `search` from one thread while another thread calls `add_term`.

- `add_term(term, id)`: index `term`, one IPA string or a list of readings, under `id`. With `strict=True`, a reading that holds an unread segment raises `ValueError` and nothing is indexed. `id` of `None` raises `ValueError`, and a `term` that is not a string or a list of strings raises `TypeError`. An empty reading, or an empty list of readings, is stored and never found. A second call with the same `id` replaces the first: a search for a reading that only the first call held no longer finds the id.
- `search(query, n_results=10) -> list[Match]`: the terms that sound like `query`, nearest first. `n_results` is an `int` of 1 or more, or `None` for every match; a smaller value raises `ValueError`, and a bool, a float or any other type raises `TypeError`. Matches with the same score are ordered by the type name of the id, then by the id as text, so the order is the same in every run. `query` is one IPA string or a list of readings. A candidate must match every word of one query reading, allowing up to two dropped sounds per word. Its score is the smallest `edit_distance` between a query reading and a term reading.
- With `strict=True`, `search` raises `ValueError` for a query that holds an unread segment.
- `cluster_of(segment) -> int`: the cluster of a segment. A segment outside the clustered letters takes the cluster of its nearest phone.

### `Match(id, term, score)`

A search result: the term's id, its readings as a tuple, and its score.

## `phonematcher.phonex`

- `phonex(word, cluster_of) -> tuple[int, ...]`: the cluster ids of a word's segments, with repeats of one cluster collapsed.

## Internal reference

These names can change in any release.

- `phonematcher.features.NUM_FEATURES`: the feature count.
- `phonematcher.features.SOURCE`: where the table comes from.
- `phonematcher.features.phone_features`: the table, segment (NFD) to vector.
- `phonematcher.features.POST_DIACRITICS`: the diacritics that follow their base.

### `phonematcher.clustering.phone_clusters(share) -> dict`

The clusters of the IPA letters and tied affricates at the merge threshold of `share`, cached. Raises `ValueError` for a share outside 0 to 1.

### `phonematcher.clustering.merge_threshold(share) -> float`

The `share` quantile of `substitution_cost` over all pairs of distinct IPA letters and tied affricates, with linear interpolation between the two nearest costs.

[Index](index.md) · Previous: [Design choices and limits](design.md) · Next: [Benchmarks](benchmarks.md)
