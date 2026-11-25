# phonematcher: agent guide

phonematcher measures distinctive-feature distances between IPA segments and finds terms that sound like a query. It takes IPA only and never converts text to IPA.

## Setup and test

```bash
uv venv
uv pip install --prerelease=allow -e '.[test,build,bench]'
pytest --import-mode=importlib tests/
```

The `bench-copyleft` extra adds the SCA system. Its tests, `benchmarks/test_sca.py`, do not run in CI. [`benchmarks/README.md`](benchmarks/README.md) covers the harness.

## Map

- `phonematcher/features.py`: loads `data/features.json`. It holds `vectorize_phones`, `feature_distance`, `is_vowel_phone`, `PhoneFeatures` and the deprecated alias `phonetic_distance`.
- `phonematcher/distance.py`: `segments`, `segment_spans`, `substitution_cost`, `edit_distance`, `align`, `ipa_distance`, `pairwise_distances`.
- `phonematcher/tone.py`: tone letters, levels and `tone_distance`.
- `phonematcher/clustering.py`: `PhoneticFuzzySearch` and the UPGMA clustering of phones. `phonematcher/phonex.py` turns a word into cluster ids.
- `phonematcher/scales.py`: the ordered vowel scales that some marks move a vowel along.
- `phonematcher/data/features.json`: built, never hand-edited. `scripts/build_features.py` rebuilds it from `scripts/sources/` and `data/overrides.json`.
- `phonematcher/data/overrides.json`: changes to the built table, each with its source and reason. `data/spellings.json` maps spellings that are not IPA to IPA.
- `scripts/sources/`: the Hayes (2009) feature table as a CSV conversion by Kyle Gorman (Apache-2.0), and the height, backness and rounding of the 28 vowel letters of the IPA chart.
- `benchmarks/`: the harness, outside the wheel. `benchmarks/render.py` writes `docs/benchmarks.md` and the README table.
- `docs/index.md`: every documentation page in reading order. `whitepaper.md` is the method and the evidence as one paper.

## Rules

- Every feature value comes from PanPhon, the Hayes (2009) CSV, the IPA chart or a cited change in `overrides.json`. A change to a value needs a source and a test that fails without it. See [The feature table](docs/features.md) and [Add a segment](docs/add-a-segment.md).
- `features.json` and `overrides.json` change together. A test rebuilds the table and compares it with `features.json` byte for byte.
- The stable API is the set of names in [the API reference](docs/api.md). `tests/test_api.py` ties `__all__` to that page.
- Every example in the README and the docs runs, and each `# value` comment is the computed value. `tests/test_docs.py` checks this, the agent hint and the footer of each page.
- The numbers in [Design choices and limits](docs/design.md) equal the result files. `tests/test_design.py` checks this.
- Never edit `version.py`. Releases bump it from conventional-commit prefixes.
- Work on `dev`. `master` holds the stable release.

## Before a push

```bash
pytest --import-mode=importlib tests/
python benchmarks/render.py --check
```
