# API reference

Everything importable, with real signatures and return shapes. The two names
re-exported from the package root are the ones you will use most:

```python
from phonematcher import PhoneticFuzzySearch, phonetic_distance
```

---

## `phonematcher.clustering`

### `class PhoneticFuzzySearch`

Combined phonetic + edit-distance fuzzy search over a set of terms.

```python
PhoneticFuzzySearch(
    mapping: dict,
    cluster_sensitivity: float = 0.5,
    use_eudex: bool = False,
    eudex_threshold: int = 100,
)
```

| Parameter | Meaning |
| --- | --- |
| `mapping` | Grapheme → list of IPA phones. Use a shipped `*_MAPPING` or your own. |
| `cluster_sensitivity` | UPGMA merge threshold. Lower = more, tighter clusters (precision); higher = fewer, broader clusters (recall). |
| `use_eudex` | If `True`, rank candidates by Eudex weighted Hamming distance instead of Levenshtein. |
| `eudex_threshold` | Divisor applied to the Eudex score (only used when `use_eudex=True`). |

Construction is **not free**: the constructor clusters every phone in the
mapping by computing the full pairwise `phonetic_distance` matrix (O(n²)).
Build one instance and reuse it; do not rebuild per query.

Attributes set on the instance:

- `mapping` — the dict you passed in.
- `clusters: dict[str, int]` — phone → cluster ID, the result of clustering.
- `phone_set: set[str]` — unique phones extracted from `mapping`.
- `index: dict[tuple[int], set]` — cluster-tuple → set of term IDs.
- `library: dict` — ID → original term string.

#### `add_term(term, id) -> None`

Index a term under an external identifier. The term is split on whitespace;
each word is expanded into its phonetic cluster variants (including one- and
two-deletion variants for recall) and registered in the index.

```python
ffs.add_term("pão com queijo", 0)
```

`id` is any hashable value — an int, a string, a database key. It is what you
get back in results, so use it to look the original item up on your side.

#### `search(query, n_results=10) -> list[Result]`

Find fuzzy phonetic matches for `query`.

```python
results = ffs.search("pao com keijo", n_results=5)
# [Result(id=0, term='pão com queijo', score=3), ...]
```

Returns a list of `Result` namedtuples, sorted by `score` ascending (best
first), truncated to `n_results`. For a multi-word query, the ID sets of all
words are **intersected** — every query word must match the candidate. If no
candidate survives the intersection, an empty list is returned.

#### `Result` namedtuple

```python
Result(id, term, score)
```

(The class is bound to the name `Match` inside the module but constructs a
namedtuple typed `Result`, so `repr` reads `Result(...)`.) Fields:

- `id` — the identifier you passed to `add_term`.
- `term` — the original indexed string.
- `score` — Levenshtein edit distance (default) or scaled Eudex distance
  (`use_eudex=True`). Lower is closer.

#### Static helpers

- `PhoneticFuzzySearch.get_phone_set(mapping) -> set[str]` — every distinct
  phone a mapping can emit.

### Language mappings

Module-level dicts, grapheme → `list[str]` of IPA phones. Pass any of them as
`mapping`, or splat one into a new dict to extend it:

`BASE_LATIN`, `EN_MAPPING`, `PT_MAPPING`, `GL_MAPPING`, `ES_MAPPING`,
`CA_MAPPING`, `OC_MAPPING`, `FR_MAPPING`, `IT_MAPPING`, `NL_MAPPING`,
`DE_MAPPING`, `SV_MAPPING`, `DA_MAPPING`, `NO_MAPPING`, `EUS_MAPPING`,
`UK_MAPPING`, `RU_MAPPING`, `AR_MAPPING`, `FA_MAPPING`, `HI_MAPPING`,
`KR_MAPPING`, `JP_MAPPING`, `ZH_MAPPING`.

`BASE_LATIN` is the shared fallback table the language mappings build on.

---

## `phonematcher.distance`

The distinctive-feature engine. See [features.md](features.md) for what the
21 features mean.

### `phonetic_distance(phone_a, phone_b) -> float`

Normalized articulatory distance between two IPA phones, in `[0.0, 1.0]`.

```python
phonetic_distance("b", "p")   # 0.043
phonetic_distance("p", "k")   # 0.348
phonetic_distance("a", "k")   # 1.0
```

Rules: a vowel paired with a consonant is always `1.0`; a space `" "` matches
only itself; otherwise the value is a weighted sum of feature mismatches,
normalized by total weight, with consonants scaled more heavily than vowels.

### `vectorize_phones(phones) -> list[bool | None]`

Resolve a phone (optionally with diacritic modifiers) into its
`NUM_FEATURES`-long feature vector. Each entry is `True`, `False`, or `None`
(unknown/irrelevant).

```python
from phonematcher.distance import vectorize_phones
vectorize_phones("a")     # base vowel vector
vectorize_phones("aː")    # same vowel, feature[20] (long) forced True
```

Raises `ValueError` for an empty or unrecognized phone. Modifiers (length `ː`,
rhoticization `˞`, etc.) overwrite specific feature positions on top of the
merged base.

### `is_vowel_phone(phone) -> bool`

`True` if the phone's feature[0] is set (vowel), else `False`. Never raises —
unknown phones return `False`.

### `phone_features`

The master table: `dict[str, list[bool | None]]` mapping each base IPA phone to
its `NUM_FEATURES`-element vector. This is the hand-curated data the whole
distance model reads.

### `NUM_FEATURES`

`int` — the feature-vector length (`21`). Every vector in `phone_features` and
every return of `vectorize_phones` has exactly this length.

---

## `phonematcher.phonex`

Grapheme-to-cluster expansion, the bridge between raw text and the index.

### `phonex(word, mapping, clusters) -> list[tuple[int]]`

Map a word to every possible sequence of cluster IDs, given a grapheme→phone
`mapping` and a phone→cluster-ID `clusters` dict (the
`PhoneticFuzzySearch.clusters` attribute).

```python
from phonematcher.phonex import phonex
ffs = PhoneticFuzzySearch(PT_MAPPING)
phonex("queijo", ffs.mapping, ffs.clusters)   # [(...cluster ids...), ...]
```

### `_phoneticize(word, mapping) -> set[tuple[str]]`

The lower-level expansion: BFS grapheme substitution producing every IPA phone
sequence a word can realize, with consecutive duplicates stripped.

---

## `phonematcher.eudex`

A Python port of the Rust `eudex` phonetic hash — an alternative ranking
backend, selected with `use_eudex=True`.

### Functions

- `eudex_hash(word: str) -> int` — 64-bit phonetic hash. `""` and whitespace
  hash to `0`; equal words hash equal.
- `weighted_hamming_distance(h1: int, h2: int) -> int` — per-byte weighted
  Hamming distance between two hashes.
- `similar(h1: int, h2: int, threshold: int = 200) -> bool` — whether two
  hashes fall within `threshold`.

### `class Hash`

```python
Hash(string: str)
```

Wraps a phonetic hash. Supports:

- `int(h)` — the underlying 64-bit value.
- `h1 - h2` → `Difference`.
- `h1 == h2` — equality against another `Hash` or a raw int.
- `repr(h)` → `Hash(<hex>)`.

Normalization folds case and punctuation: `Hash("JAva") == Hash("jAva")`,
`Hash("comp-uter") == Hash("computer")`.

### `class Difference`

Returned by `Hash.__sub__`. Methods:

- `dist() -> int` — graduated (Fibonacci-weighted) per-byte distance.
- `hamming() -> int` — flat bit-count distance.
- `xor_val() -> int` — raw XOR.
- `similar() -> bool` — whether the two are close enough to call alike.

Distance is symmetric: `(Hash("a") - Hash("b")).dist() == (Hash("b") - Hash("a")).dist()`.

## Where next

- [quickstart.md](quickstart.md) — the five-minute tour
- [advanced.md](advanced.md) — custom mappings, Eudex ranking, gotchas
- [features.md](features.md) — the distinctive-feature matrix
