# TODO — phonematcher

A library for phonetic fuzzy search and segment-to-segment distance over IPA.
It maps IPA phones to 21 articulatory features (Distinctive Feature Theory),
computes weighted phonetic distance, clusters phones via UPGMA, builds a Phonex
fuzzy index, and ranks candidates with Levenshtein edit distance.

## Hardening (CI / packaging / hygiene)

- [ ] Add the standard `OpenVoiceOS/gh-automations@dev` workflows: `build-tests`, `coverage`, `license_check`, `release_workflow`, `publish_stable`, `conventional-label`. The repo has no `.github/workflows/`.
- [ ] Migrate packaging to `pyproject.toml`; keep the `version.py` block untouched by humans.
- [ ] Fill in package metadata: `license` and `description` are empty. The README declares MIT (adapted from `pyphone` / `fast_fuzzy_search`); add a `LICENSE` file and set the metadata accordingly.
- [ ] Remove the committed build artifact `phonematcher.egg-info/` and add a `.gitignore` (egg-info, `__pycache__`, build/dist).
- [ ] Declare the test dependency: `requirements.txt` lists only `rapidfuzz`; `pytest` should be a test extra, and the existing `tests/` suite should run in `build-tests`.
- [ ] Add lint/type configuration to match the org standard.

## Correctness gaps

- [ ] Audit the LLM-generated phone-to-feature placeholder mappings against a reference feature inventory (e.g. PHOIBLE / Hayes features); incorrect feature vectors silently distort distance and clustering.
- [ ] The built-in grapheme→IPA mappings (`EN_MAPPING`, `BASE_LATIN`) are coarse; document their intended coverage and validate per-language behaviour against the test corpus.

## Code TODOs

- [ ] `phonematcher/clustering.py:295` — review the LLM-generated phone-mapping placeholders.
