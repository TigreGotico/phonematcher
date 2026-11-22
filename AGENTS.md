# phonematcher: agent guide

Distinctive-feature distances between IPA segments, and phonetic fuzzy search over IPA.

The library takes IPA only. It never converts text to IPA.

## Setup and test

```bash
uv venv
uv pip install --prerelease=allow -e '.[test]'
pytest --import-mode=importlib tests/
```

## Layout

- `phonematcher/features.py`: loads `data/features.json` and gives `vectorize_phones`, `feature_distance` (and the deprecated alias `phonetic_distance`), `is_vowel_phone`.
- `phonematcher/distance.py`: `segments`, `substitution_cost` (the one segment cost), `edit_distance`, `ipa_distance`.
- `phonematcher/clustering.py`: `PhoneticFuzzySearch`, UPGMA clustering of phones.
- `phonematcher/phonex.py`: a word as its sequence of cluster ids.
- `phonematcher/data/features.json`: built, never hand-edited. Rebuild with `scripts/build_features.py` (needs `panphon` and `pyyaml`).
- `phonematcher/data/overrides.json`: single-value changes to the built table, each with its source and reason.
- `benchmarks/`: the benchmark harness, outside the wheel; see `benchmarks/README.md`. Its tests are `tests/test_bench_harness.py` (extra `bench`) and `benchmarks/test_sca.py` (extra `bench-copyleft`, not run in CI).
- `scripts/sources/hayes2009-features.csv`: Hayes (2009) feature table, CSV conversion by Kyle Gorman (Apache-2.0).
- `scripts/sources/ipa-vowel-chart.csv`: height, backness and rounding of the 28 vowel letters of the IPA chart.

## Rules

- Every feature value comes from PanPhon, the Hayes (2009) CSV, the IPA chart or a cited change in `overrides.json`. A change to a value needs a source in `overrides.json` and a test that fails without it.
- Branches: `dev` (work) and `master` (stable).
- Never edit `version.py`. Releases bump it from conventional-commit prefixes.
- Commit identity: JarbasAi <jarbasai@mailfence.com>.
