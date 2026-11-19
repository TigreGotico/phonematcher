# The feature table

Each IPA segment has a vector of 25 distinctive features. A value is `True` (+), `False` (−) or `None` (0: the feature does not apply). The table is in `phonematcher/data/features.json`, and `scripts/build_features.py` builds it from three inputs.

## Sources

1. **PanPhon** (Mortensen et al. 2016, "PanPhon: A Resource for Mapping IPA Segments to Articulatory Feature Vectors", COLING; MIT). It gives 6,367 segments, 22 features, the feature weights and the rules for diacritics.
2. **Hayes** (2009, *Introductory Phonology*, Wiley-Blackwell, ch. 4), through the CSV conversion by Kyle Gorman (github.com/kylebgorman/hayes2009, Apache-2.0), vendored in `scripts/sources/`. Hayes adds the features `front`, `tap` and `trill`. For every vowel that Hayes lists, his values replace PanPhon's for `hi`, `lo`, `front`, `back`, `round`, `tense` and `lab`.
3. **`phonematcher/data/overrides.json`**. Each entry changes one feature of one segment. It records the value before the change, the new value, the source and the reason.

### Why Hayes for vowels

PanPhon has `back` but no `front`. Thus it cannot tell a central vowel from a front one. In PanPhon, `e` and `ɐ` have the same vector, `ə` and `ɜ` have the same vector, `r` and `ɾ` have the same vector, and rounded vowels do not agree on `lab`. With Hayes's vowels and his `tap` and `trill`, every IPA letter has its own vector, except one pair.

### The one shared vector

`ə` (mid central) and `ɜ` (open-mid central) share a vector. Hayes does not list `ɜ`, and PHOIBLE (Moran and McCloy) gives the two identical values. No published table separates them, so the table does not separate them either.

### Overrides

| Segment | Feature | Value | Source |
|---|---|---|---|
| `ɹ` | `hi` | 0 | Hayes (2009) |
| `ɹ` | `round` | − | Hayes (2009) |
| `ɐ` | `lo` | + | PHOIBLE |
| `ɐ` | `front` | − | PHOIBLE |
| `ɜ` | `front` | − | PHOIBLE |
| `ɜ` | `back` | − | PHOIBLE |

`overrides.json` gives the reason for each change. To add an override, add an entry there, run the build, and add a test that fails without it.

## Diacritics

A segment that is not in the table is read as its longest listed base plus the diacritics after it. Each diacritic changes the features that PanPhon's rule for it names, if the rule's conditions hold for the base. For example, `ɐ̥` is `ɐ` with `voi` set to −.

A tie bar joins two symbols into one segment: `t͡ʃ` and `t͜ʃ` are the same affricate. Without a tie bar, `tʃ` is two segments.

## Distance

`phonetic_distance(a, b)` adds, for each feature, its weight times half the difference of the two values, with + = 1, 0 = 0 and − = −1. A +/− mismatch costs the full weight, and a 0 against + or − costs half the weight. The sum is divided by the total weight, so the result is between 0 and 1. A segment that cannot be read is at distance 1 from everything.

The weights are PanPhon's. The added features `front`, `tap` and `trill` have weight 0.25, the same as `back` and `delrel`.

## Rebuilding

```
uv pip install panphon pyyaml
python scripts/build_features.py
```

The build prints the number of segments in and out, and the number of overrides. It stops if an override's recorded old value does not match the table.
