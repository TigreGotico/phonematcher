# API reference
<!-- agent-hint
covers: every public name of the package and what it returns
source: phonematcher/__init__.py, phonematcher/features.py, phonematcher/distance.py, phonematcher/tone.py, phonematcher/clustering.py, phonematcher/phonex.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k api.md
see: quickstart.md, features.md
-->

The package root exports `feature_distance`, `substitution_cost`, `vectorize_phones`, `segments`, `ipa_distance`, `edit_distance`, `align`, `PhoneticFuzzySearch` and `Match`. It also exports `phonetic_distance`, a deprecated alias of `feature_distance`.

## `phonematcher.features`

- `feature_distance(a, b) -> float`: the weighted feature distance between two segments, from 0 to 1. See [features.md](features.md).
- `phonetic_distance(a, b) -> float`: the old name of `feature_distance`. It returns the same value and raises a `DeprecationWarning` that names the version where it goes away, the next major version.
- `vectorize_phones(segment) -> tuple`: the feature vector of one segment, in the order of `FEATURES`. Raises `ValueError` for a segment it cannot read.
- `is_vowel_phone(segment) -> bool`: true for a syllabic segment.
- `FEATURES`, `WEIGHTS`, `NUM_FEATURES`: the feature names, their weights and their count.
- `SOURCE`: where the table comes from.
- `phone_features`: the table, segment (NFD) to vector.
- `POST_DIACRITICS`: the diacritics that follow their base.

## `phonematcher.distance`

- `segments(ipa) -> list[str]`: the segments of an IPA string. A diacritic stays with its base, a tie bar joins two symbols, a space between words becomes one `" "` segment, and stress, syllable and phrase-tone marks are dropped. A tone is one segment of tone letters after its syllable; a tone diacritic or a tone numeral is written as tone letters.
- `substitution_cost(a, b) -> float`: the one cost of replacing segment `a` by `b`: the square root of the tone distance of two tones, 1 for a tone and a phone, and the square root of the feature distance of two phones. `edit_distance`, `align`, `ipa_distance` and the clusters of `PhoneticFuzzySearch` use it.
- `edit_distance(a, b, *, strict=False) -> float`: the Levenshtein distance between two segment lists, where a substitution costs `substitution_cost` and an insertion or deletion costs 0.5. The costs are those of the pre-registered test in `benchmarks/prereg-2.md` and `docs/benchmarks.md`.
- `align(a, b, *, strict=False) -> list[tuple[str | None, str | None]]`: one least-cost alignment of two segment lists, as pairs of a left and a right segment. `None` marks a gap. The costs are those of `edit_distance`. The traceback starts at the end and prefers a substitution, then a deletion (a gap in `b`), then an insertion.
- `ipa_distance(a, b, normalized=False, *, strict=False) -> float`: `edit_distance` between two IPA strings. With `normalized=True` the distance is divided by the segment count of the longer string, so it falls between 0 and 1, and two empty strings give 0.0.
- `strict=True` on `ipa_distance`, `edit_distance` and `align`: a segment the feature table cannot read raises `ValueError` that names the segment and the input. Without it, an unread segment costs as much as a missing one. See [Design choices and limits](design.md#an-unread-segment-is-at-distance-1).

## `phonematcher.tone`

- `is_tone(segment) -> bool`: true for a segment made only of tone letters.
- `tone_levels(segment) -> tuple[int, ...] | None`: the pitch levels of a tone, 1 (extra low) to 5 (extra high).
- `tone_distance(a, b) -> float`: the distance between two tones, from 0 to 1. It is experimental: see [Tones](tones.md) and issue [#68](https://github.com/TigreGotico/phonematcher/issues/68). See [features.md](features.md#tone).

## `phonematcher.clustering`

### `PhoneticFuzzySearch(cluster_sensitivity=0.08, *, strict=False)`

An index of IPA terms. Phones are grouped into clusters of near sounds by UPGMA average linkage over `substitution_cost`. `cluster_sensitivity` is a share from 0 to 1, and a value outside that range raises `ValueError`. The merge threshold is that quantile of `substitution_cost` over all pairs of distinct IPA letters of the table. A higher share puts more phones in one cluster, so a search finds more candidates. At 0.08, voicing pairs (`p b`), `ʁ χ`, `s ʃ`, `e ɛ` and `a ɐ` share a cluster, and `p t`, `ʁ k` and `e o` do not. [Search by sound](search.md) shows the steps.

- `add_term(term, id)`: index `term`, one IPA string or a list of readings, under `id`. With `strict=True`, a reading that holds an unread segment raises `ValueError` and nothing is indexed.
- `search(query, n_results=10) -> list[Match]`: the terms that sound like `query`, nearest first. `query` is one IPA string or a list of readings. A candidate must match every word of one query reading, allowing up to two dropped sounds per word. Its score is the smallest `edit_distance` between a query reading and a term reading.
- With `strict=True`, `search` raises `ValueError` for a query that holds an unread segment.
- `cluster_of(segment) -> int`: the cluster of a segment. A segment outside the clustered letters takes the cluster of its nearest phone.

### `Match(id, term, score)`

A search result: the term's id, its readings as a tuple, and its score.

### `phone_clusters(share) -> dict`

The clusters of the IPA letters and tied affricates at the merge threshold of `share`, cached. Raises `ValueError` for a share outside 0 to 1.

### `merge_threshold(share) -> float`

The `share` quantile of `substitution_cost` over all pairs of distinct IPA letters and tied affricates, with linear interpolation between the two nearest costs.

## `phonematcher.phonex`

- `phonex(word, cluster_of) -> tuple[int, ...]`: the cluster ids of a word's segments, with repeats of one cluster collapsed.

[Index](index.md) · Previous: [Design choices and limits](design.md) · Next: [Benchmarks](benchmarks.md)
