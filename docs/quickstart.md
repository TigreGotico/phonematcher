# Quickstart

phonematcher takes IPA. This page goes from words to IPA with orthography2ipa, then measures and searches with phonematcher.

## 1. Install

```
uv pip install phonematcher orthography2ipa
```

orthography2ipa is used only in these examples. phonematcher does not need it.

## 2. Get IPA

```python
from orthography2ipa import transcribe

transcribe("carro", "pt-PT")        # 'ˈkaʁu'
transcribe("carro", "pt-BR-x-rj")   # 'ˈkaχu'
```

## 3. Compare two sounds

```python
from phonematcher import phonetic_distance

phonetic_distance("ʁ", "χ")   # 0.028
phonetic_distance("ʁ", "k")   # 0.124
```

The uvular fricatives differ in voice only, so they are near. The velar stop differs in manner and place, so it is farther.

## 4. Compare two words

```python
from phonematcher import ipa_distance, segments

segments("ˈt͡ʃɐ̃w̃")              # ['t͡ʃ', 'ɐ̃', 'w̃']
ipa_distance("ˈpojʃ", "ˈpojs")   # 0.055
```

`segments` keeps a diacritic with its base and joins tied symbols into one affricate. Stress and syllable marks are dropped.

## 5. Search

```python
from orthography2ipa import transcribe
from phonematcher import PhoneticFuzzySearch

search = PhoneticFuzzySearch()
for word in ["pois", "retirada", "carro", "caro", "casa", "dia"]:
    search.add_term(transcribe(word, "pt-PT"), word)

for word in ["pois", "carro", "dia"]:
    ipa = transcribe(word, "pt-BR-x-rj")
    print(word, ipa, search.search(ipa)[0].id)
```

```
pois ˈpojʃ pois
carro ˈkaχu carro
dia ˈd͡ʒiɐ dia
```

The index holds European Portuguese readings, and the queries are Rio de Janeiro readings. Each query finds its word, because `χ` is near `ʁ` and `d͡ʒ` is near `d`.
