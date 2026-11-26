# Add a segment
<!-- agent-hint
covers: how to add an IPA segment to the feature table, with its source, the rebuild and the test
source: phonematcher/data/overrides.json, scripts/build_features.py, tests/test_features.py
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k add-a-segment.md
see: features.md, compare-sounds.md
-->

This page adds a segment that the feature table does not read. The table is built, never edited by hand. A segment enters through `phonematcher/data/overrides.json`, with its source. The worked example is the labiodental flap `ⱱ`, which PanPhon does not list.

## 1. Check that the table lacks the segment

A segment that is not in the table raises `ValueError`. The letter `ʞ` is such a segment:

```python
from phonematcher.features import vectorize_phones

try:
    vectorize_phones("ʞ")
except ValueError as error:
    print(error)
```

```text
Unrecognized phone 'ʞ' (U+029E). A word distance or a search takes strict=True to raise on such a segment instead of costing it 1
```

The table reads `ⱱ`, because its entry is already in `overrides.json`. The next steps show that entry.

## 2. Write the entry

Each entry in the `segments` list of `overrides.json` has these fields:

```python
import json

entries = json.load(open("phonematcher/data/overrides.json", encoding="utf-8"))["segments"]
flap = next(e for e in entries if e["segment"] == "ⱱ")
sorted(flap)   # ['from', 'name', 'place_of', 'reason', 'segment', 'set', 'source']
```

The values for `ⱱ`:

| Field | Value |
|---|---|
| `segment` | `ⱱ` |
| `name` | voiced labiodental flap |
| `from` | `ɾ`, a segment PanPhon lists. The added segment starts as a copy of its row. |
| `place_of` | `v`. The place features of this segment replace the copied ones. |
| `set` | `tap` +, `trill` −. Features set by hand. |
| `source` | The page of the source that names the segment and its sound. The IPA chart, row Tap or Flap, column Labiodental. |
| `reason` | One sentence: why the table gives these values. |

The `source` field is required. A change to the table needs a source and a test that fails without it.

## 3. Rebuild the table

The build needs PanPhon and PyYAML. It writes `phonematcher/data/features.json`:

```
uv pip install -e '.[build]'
python scripts/build_features.py
```

```text
phones in 6307 + 10 added, out 6317; overrides 8; diacritics 50
```

The line says how many segments PanPhon lists, how many `segments` entries were added, how many segments the table holds, how many value changes `overrides` holds, and how many diacritic rules the build read. The build stops with a message that names the entry if its `from` or `place_of` is a segment that PanPhon does not list, and if an `overrides` entry names such a segment. Commit `overrides.json` and `features.json` together. A test rebuilds the table and compares it with `features.json` byte for byte, so a change to one file without the other fails.

## 4. Check the vector

The distances to the two source segments show where the vector sits. It differs from `ɾ` in place features and from `v` in manner features:

```python
from phonematcher import feature_distance

feature_distance("ⱱ", "ɾ")   # 0.086
feature_distance("ⱱ", "v")   # 0.158
```

## 5. Write the test

The test lives in `tests/test_features.py`. Its expected values come from the IPA chart, not from the table. For `ⱱ` the chart puts the flap in the labiodental column, so one test compares its place features with those of `v`:

```python
def test_labiodental_flap_has_the_place_of_v():
    for f in ("lab", "ant", "cor"):
        assert feature("ⱱ", f) is feature("v", f)
```

Run it, then the whole suite:

```
pytest --import-mode=importlib tests/
```

A test for an added segment must fail without the entry. Remove the entry, rebuild, run the test, and see it fail. Put the entry back and rebuild.

[Index](index.md) · Previous: [Use with scikit-learn](scikit-learn.md) · Next: [The feature table](features.md)
