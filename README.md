# phonematcher

phonematcher measures how far apart two IPA sounds are, and finds terms that sound like a query. It works on IPA only. To get IPA from text, use a grapheme-to-IPA library such as [orthography2ipa](https://github.com/TigreGotico/orthography2ipa).

Every distance comes from distinctive features. The feature table starts from PanPhon (Mortensen et al. 2016), takes the vowels from the IPA chart, and lists every other change with its source. [docs/features.md](docs/features.md) explains the table.

## Install

```
uv pip install phonematcher
```

phonematcher has no runtime dependencies.

## Distance between sounds

```python
from phonematcher import phonetic_distance, ipa_distance, segments

phonetic_distance("ʁ", "χ")       # 0.013: uvular fricatives that differ only in voice
phonetic_distance("ʁ", "k")       # 0.118: a different manner and place
segments("ˈt͡ʃɐ̃w̃")              # ['t͡ʃ', 'ɐ̃', 'w̃']
ipa_distance("ˈpojʃ", "ˈpojs")   # 0.039: one near substitution
```

`phonetic_distance` compares two segments, from 0 to 1. `ipa_distance` compares two IPA strings: an edit distance where a substitution costs the feature distance and an insertion or deletion costs 1.

## Search by sound

```python
from orthography2ipa import transcribe
from phonematcher import PhoneticFuzzySearch

search = PhoneticFuzzySearch()
for word in ["pois", "retirada", "carro", "caro", "casa", "dia"]:
    search.add_term(transcribe(word, "pt-PT"), word)

query = transcribe("carro", "pt-BR-x-rj")   # 'ˈkaχu'
best = search.search(query)[0]
best.id, best.term, round(best.score, 3)   # ('carro', ('ˈkaʁu',), 0.013)
```

A term may have several readings: `search.add_term(["ˈpojʃ", "ˈpojs"], "pois")`.

## Documentation

- [docs/quickstart.md](docs/quickstart.md): first steps.
- [docs/features.md](docs/features.md): the feature table, its sources and the distance.
- [docs/api.md](docs/api.md): every public name.

## Licence

MIT. The feature table derives from PanPhon (MIT) and from Hayes (2009) through the CSV conversion by Kyle Gorman (Apache-2.0).

To cite phonematcher, use [CITATION.cff](CITATION.cff).
