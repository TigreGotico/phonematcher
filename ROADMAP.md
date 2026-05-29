# Roadmap — phonematcher

A phonetic fuzzy-search and segment-distance library. Phones are resolved to
21-dimensional articulatory feature vectors, compared with a weighted distance
(major-class features weigh more than minor ones), clustered with UPGMA at a
configurable sensitivity, indexed with a Phonex delete-variant index, and ranked
with Levenshtein edit distance over the original orthography.

This is the phonetics stack's *retrieval/comparison* component rather than a G2P:
the other repos produce IPA, phonematcher measures how close two IPA strings sound.

## Phase 0 — Hardening

- Add the `OpenVoiceOS/gh-automations@dev` workflow set (build-tests, coverage,
  license_check, release_workflow, publish_stable, conventional-label) and run the
  existing `tests/` suite under `build-tests`.
- Migrate to `pyproject.toml`, add `LICENSE` (MIT, crediting `pyphone` /
  `fast_fuzzy_search`), set `description`, declare `pytest` as a test extra, add a
  `.gitignore`, and remove the committed `phonematcher.egg-info/`.

## Phase 1 — Correctness & coverage

- Replace / verify the LLM-generated phone-to-feature placeholders against a
  reference feature inventory; add tests asserting expected distance orderings
  (e.g. `d(p,b) < d(p,k) < d(p,a)`).
- Expand and document the bundled grapheme→IPA mappings, and add per-language
  fuzzy-search tests beyond English.
- Expose `cluster_sensitivity` tuning guidance as data/tests rather than prose.

## Phase 2 — Integration

- Consume IPA directly from the org phonemizers (`tugaphone`, `mwl_phonemizer`,
  `g2p_barranquenho`, `sotaque_forcado`) so fuzzy search can run on phonemized
  input, not just the built-in grapheme mappings.
- Reconcile the feature model with `orthography2ipa`'s `distance.py` / `feats.py`
  phonological-distance metrics so the two share one feature definition rather than
  maintaining parallel inventories; phonematcher then becomes the indexing/recall
  layer on top of `orthography2ipa`'s feature vectors.

## Phase 3 — Publishing

- Release to PyPI through the standard publish workflow after Phase 0.
- Optionally publish the validated feature table as a small reusable data artifact
  shared with `orthography2ipa`.
