# API reference

The package root exports `phonetic_distance`, `vectorize_phones`, `segments`, `ipa_distance`, `edit_distance`, `align`, `PhoneticFuzzySearch` and `Match`.

## `phonematcher.features`

- `phonetic_distance(a, b) -> float`: the weighted feature distance between two segments, from 0 to 1. See [features.md](features.md).
- `vectorize_phones(segment) -> tuple`: the feature vector of one segment, in the order of `FEATURES`. Raises `ValueError` for a segment it cannot read.
- `is_vowel_phone(segment) -> bool`: true for a syllabic segment.
- `FEATURES`, `WEIGHTS`, `NUM_FEATURES`: the feature names, their weights and their count.
- `SOURCE`: where the table comes from.
- `phone_features`: the table, segment (NFD) to vector.
- `POST_DIACRITICS`: the diacritics that follow their base.

## `phonematcher.distance`

- `segments(ipa) -> list[str]`: the segments of an IPA string. A diacritic stays with its base, a tie bar joins two symbols, a space between words becomes one `" "` segment, and stress, syllable and phrase-tone marks are dropped. A tone is one segment of tone letters after its syllable; a tone diacritic or a tone numeral is written as tone letters.
- `substitution_cost(a, b) -> float`: the cost of replacing segment `a` by `b`: the tone distance of two tones, 1 for a tone and a phone, and the feature distance of two phones.
- `edit_distance(a, b) -> float`: the Levenshtein distance between two segment lists, where a substitution costs `substitution_cost` and an insertion or deletion costs 1.
- `align(a, b) -> list[tuple[str | None, str | None]]`: one least-cost alignment of two segment lists, as pairs of a left and a right segment. `None` marks a gap. The costs are those of `edit_distance`. The traceback starts at the end and prefers a substitution, then a deletion (a gap in `b`), then an insertion.
- `ipa_distance(a, b, normalized=False) -> float`: `edit_distance` between two IPA strings. With `normalized=True` the distance is divided by the segment count of the longer string, and two empty strings give 0.0.

## `phonematcher.tone`

- `is_tone(segment) -> bool`: true for a segment made only of tone letters.
- `tone_levels(segment) -> tuple[int, ...] | None`: the pitch levels of a tone, 1 (extra low) to 5 (extra high).
- `tone_distance(a, b) -> float`: the distance between two tones, from 0 to 1. See [features.md](features.md#tone).

## `phonematcher.clustering`

### `PhoneticFuzzySearch(cluster_sensitivity=0.1)`

An index of IPA terms. Phones are grouped into clusters of near sounds by UPGMA average linkage over `phonetic_distance`. A higher `cluster_sensitivity` puts more phones in one cluster, so a search finds more candidates. At 0.1, voicing pairs (`p b`), `ʁ χ`, `s ʃ`, `e ɛ` and `a ɐ` share a cluster, and `p t`, `ʁ k` and `e o` do not.

- `add_term(term, id)`: index `term`, one IPA string or a list of readings, under `id`.
- `search(query, n_results=10) -> list[Match]`: the terms that sound like `query`, nearest first. `query` is one IPA string or a list of readings. A candidate must match every word of one query reading, allowing up to two dropped sounds per word. Its score is the smallest `edit_distance` between a query reading and a term reading.
- `cluster_of(segment) -> int`: the cluster of a segment. A segment outside the clustered letters takes the cluster of its nearest phone.

### `Match(id, term, score)`

A search result: the term's id, its readings as a tuple, and its score.

### `phone_clusters(threshold) -> dict`

The clusters of the IPA letters and tied affricates at `threshold`, cached.

## `phonematcher.phonex`

- `phonex(word, cluster_of) -> tuple[int, ...]`: the cluster ids of a word's segments, with repeats of one cluster collapsed.
