"""Find words from readings of another variety.

The index holds European Portuguese readings; the queries are Rio de Janeiro readings.
This example needs orthography2ipa (``uv pip install orthography2ipa``).

Run::

    python examples/02_search_portuguese.py
"""
from orthography2ipa import transcribe

from phonematcher import PhoneticFuzzySearch

search = PhoneticFuzzySearch()
for word in ["pois", "retirada", "carro", "caro", "casa", "dia"]:
    search.add_term(transcribe(word, "pt-PT"), word)

for word in ["pois", "carro", "dia"]:
    ipa = transcribe(word, "pt-BR-x-rj")
    best = search.search(ipa)[0]
    print(f"{word:6} {ipa:8} -> {best.id} ({best.score:.3f})")
