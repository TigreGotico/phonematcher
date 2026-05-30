# phonematcher — agent guide

Python library for phonetic fuzzy search and IPA segment-to-segment distance: find words that "sound like" a query by analyzing distinctive features of International Phonetic Alphabet (IPA) phones.

## Setup

```bash
pip install rapidfuzz   # only runtime dependency
pip install -e .        # editable install of the package
```

## Test

```bash
pytest tests/
```

`pytest` is the test runner. Tests cover the distinctive-feature matrix, vectorization/modifier rules (`tests/test_phonematcher.py`), the Eudex port (`tests/test_eudex.py`), and per-language mappings (`tests/test_langs.py`). There is no pytest config file; invoke the directory directly.

## Lint/Typecheck

None configured.

## Layout

Package `phonematcher/` (single top-level package, no entry points — this is a plain library, not an OVOS/OPM plugin or skill):

- `distance.py` — distinctive-feature matrix: `phone_features` (IPA phone -> 21-element feature vector), `vectorize_phones`, `phonetic_distance`, `_bad_phones` normalization, `NUM_FEATURES`. The articulatory-distance core.
- `clustering.py` — `PhoneticFuzzySearch` (index + search), UPGMA average-link phone clustering, and the language grapheme->IPA mappings (`BASE_LATIN`, `EN_MAPPING`, `PT_MAPPING`, `ES_MAPPING`, `FR_MAPPING`, `DE_MAPPING`, `RU_MAPPING`, `AR_MAPPING`, `ZH_MAPPING`, `JP_MAPPING`, ~22 languages total). Largest module.
- `phonex.py` — `_phoneticize` (BFS grapheme-to-phoneme expansion) and `phonex` (word -> sequences of cluster IDs). Adapted from `pyphone`.
- `eudex.py` — Python port of the Rust `eudex` phonetic hash (`Hash`, `Difference`, `eudex_hash`, `weighted_hamming_distance`). Optional ranking backend (`use_eudex=True`).
- `__init__.py` — re-exports `phonetic_distance` and `PhoneticFuzzySearch`.
- `version.py` — version block; do not edit.

Data flow: word -> `_phoneticize` expands all IPA variants via mapping -> phones clustered into numeric IDs (UPGMA over `phonetic_distance`) -> `PhoneticFuzzySearch` indexes cluster tuples plus generated deletes -> query matched against index -> candidates ranked by Levenshtein (rapidfuzz) or Eudex distance.

## Conventions (org hard rules)

- Branches: `dev` (work) / `master` (stable). NEVER `main`.
- Never edit `version.py`; gh-automations bumps semver from conventional-commit prefixes (`feat:` / `fix:` / `feat!:`).
- New repos private by default.
- Commit identity: JarbasAi <jarbasai@mailfence.com>.
- CI is provided by OpenVoiceOS/gh-automations reusable workflows referenced at `@dev`.
- No Neon / `neon-*` references.
- No meta-commentary in docs/commits/code (no history, no dates; describe current state only).

## Gotchas

- `_cluster_phones()` recomputes the full pairwise phone distance matrix on every `PhoneticFuzzySearch` construction (O(n^2) `phonetic_distance` calls); reuse one instance rather than rebuilding per query.
- `vectorize_phones` raises `ValueError` on unrecognized phones; mappings must only emit phones present in `phone_features` (or in `_bad_phones`).
- The phone feature table carries an LLM-generated-placeholder marker in `clustering.py` (around line 295) flagged for review — values are hand-curated and may be imperfect.
- `setup.py` uses a bare `except:` in `phonex()` that re-raises after printing; not a clean error path.
- `phonematcher.egg-info/` is committed and should not be (build artifact).
