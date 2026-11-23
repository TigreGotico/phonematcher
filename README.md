# phonematcher
<!-- agent-hint
covers: what phonematcher is, how to install it, and one distance and one search example
source: phonematcher/__init__.py, phonematcher/features.py, phonematcher/distance.py, phonematcher/clustering.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k README.md
see: docs/index.md, docs/quickstart.md
-->

phonematcher measures how far apart two IPA sounds are, and finds terms that sound like a query. It works on IPA only. To get IPA from text, use a grapheme-to-IPA library such as [orthography2ipa](https://github.com/TigreGotico/orthography2ipa).

Every distance comes from distinctive features. The feature table starts from PanPhon (Mortensen et al. 2016), takes the vowels from the IPA chart, and lists every other change with its source. [docs/features.md](docs/features.md) explains the table.

## Install

```
uv pip install phonematcher
```

The library has no runtime dependencies. The "Search by sound" example below also needs orthography2ipa: `uv pip install phonematcher orthography2ipa`.

## Distance between sounds

```python
from phonematcher import feature_distance, ipa_distance, segments, substitution_cost

feature_distance("ʁ", "χ")       # 0.013: uvular fricatives that differ only in voice
feature_distance("ʁ", "k")       # 0.118: a different manner, place and voice
substitution_cost("ʁ", "χ")      # 0.115: the square root of the feature distance
segments("ˈt͡ʃɐ̃w̃")              # ['t͡ʃ', 'ɐ̃', 'w̃']
ipa_distance("ˈpojʃ", "ˈpojs")   # 0.199: one near substitution
```

`feature_distance` compares two segments, from 0 to 1. `substitution_cost` is the one cost of replacing a segment by another. It is the square root of the feature distance. `ipa_distance` compares two IPA strings: an edit distance where a substitution costs `substitution_cost` and an insertion or deletion costs 0.5. A substitution costs at most 1, so it never costs more than a deletion plus an insertion. The search groups sounds with the same cost. The costs are the ones that the pre-registered test in [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md) selected.

A segment that phonematcher cannot read is at distance 1 from every other segment. With `strict=True`, a distance, an alignment or a search raises `ValueError` for such a segment. The table does not read every valid IPA segment. Strict mode cannot catch a spelling that uses the ASCII letters `c`, `y`, `j` and `r`. These are also IPA letters, so the spelling is read as IPA and gives a wrong score with no error.

## Search by sound

```python
from orthography2ipa import transcribe
from phonematcher import PhoneticFuzzySearch

search = PhoneticFuzzySearch()
for word in ["pois", "retirada", "carro", "caro", "casa", "dia"]:
    search.add_term(transcribe(word, "pt-PT"), word)

query = transcribe("carro", "pt-BR-x-rj")   # 'ˈkaχu'
best = search.search(query)[0]
best.id, best.term, round(best.score, 3)   # ('carro', ('ˈkaʁu',), 0.115)
```

A term may have several readings: `search.add_term(["ˈpojʃ", "ˈpojs"], "pois")`.

## How it compares

<!-- benchmark-table:start -->
Test split, run once under [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md). Each cell is the estimate with its 95% interval. The best value in each column is in bold. A dash means that the system does not run the task. SCA ran retrieval on a sample of 500 queries per pair and ALINE on the first 100 of those, so these two retrieval cells are not on the same queries as the other rows. The shipped library is the P5 candidate, with its test numbers. [docs/benchmarks.md](docs/benchmarks.md) holds every result.

| System | Cognates, mean AP | Alignment, PAS on common pairs | Retrieval, mean recall@1 |
|---|---|---|---|
| plain edit distance | 0.8234 [0.8108, 0.8363] | 0.6154 [0.5487, 0.6872] | 0.6861 [0.6763, 0.6956] |
| PanPhon, weighted | 0.6361 [0.6151, 0.6565] | — | 0.7765 [0.7675, 0.7856] |
| PanPhon, Hamming | 0.6462 [0.6242, 0.6663] | — | 0.7623 [0.7531, 0.7719] |
| ALINE | 0.6130 [0.5903, 0.6359] | 0.8923 [0.8513, 0.9333] | 0.4150 [0.3742, 0.4550] |
| CLTS sound vectors | 0.7399 [0.7224, 0.7561] | — | 0.7929 [0.7844, 0.8017] |
| SCA | **0.8835 [0.8718, 0.8949]** | **0.8974 [0.8564, 0.9385]** | 0.7925 [0.7773, 0.8086] |
| phonematcher, starting weights (C0) | 0.7326 [0.7140, 0.7500] | 0.7949 [0.7436, 0.8513] | 0.8082 [0.7999, 0.8168] |
| phonematcher, shipped library (P5) | 0.8035 [0.7874, 0.8186] | 0.8513 [0.8051, 0.8974] | **0.8777 [0.8706, 0.8851]** |
<!-- benchmark-table:end -->

## Documentation

- [docs/index.md](docs/index.md): every page, in reading order.
- [docs/quickstart.md](docs/quickstart.md): first steps.
- [docs/features.md](docs/features.md): the feature table, its sources and the distance.
- [docs/api.md](docs/api.md): every public name.
- [whitepaper.md](whitepaper.md): the method and the evidence as one paper, with the pre-registered test and its limits.

## Licence

MIT. The feature table derives from PanPhon (MIT) and from Hayes (2009) through the CSV conversion by Kyle Gorman (Apache-2.0).

To cite phonematcher, use [CITATION.cff](CITATION.cff).
