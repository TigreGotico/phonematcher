"""Build phonematcher/data/features.json.

PanPhon (Mortensen et al. 2016, MIT) supplies the segments, the feature weights and the diacritic
rules. Hayes (2009, Introductory Phonology; the CSV conversion by Gorman, Apache-2.0, vendored in
``scripts/sources/``) adds three features PanPhon lacks, [front], [tap] and [trill], and supplies
the vowel features (high, low, front, back, round, tense, labial) of every vowel it lists, because
PanPhon cannot tell central from front vowels. ``phonematcher/data/overrides.json`` then changes
single values, each with its source. Run after changing any input:

    uv pip install panphon pyyaml
    python scripts/build_features.py
"""
import csv
import importlib.metadata
import json
import unicodedata
from pathlib import Path

import panphon
import yaml

DATA = Path(panphon.__file__).parent / "data"
HERE = Path(__file__).resolve().parent.parent / "phonematcher" / "data"
HAYES = Path(__file__).resolve().parent / "sources" / "hayes2009-features.csv"

#: Hayes's name for each feature this build takes from him.
HAYES_NAMES = {"hi": "high", "lo": "low", "front": "front", "back": "back", "round": "round",
               "tense": "tense", "lab": "LABIAL", "tap": "tap", "trill": "trill"}
VOWEL_FEATURES = ("hi", "lo", "front", "back", "round", "tense", "lab")
ADDED = {"front": 0.25, "tap": 0.25, "trill": 0.25}


def read_hayes() -> dict:
    with open(HAYES, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    return {unicodedata.normalize("NFD", r[0]): dict(zip(head, r)) for r in rows[1:] if r[0]}


def base_letter(segment: str) -> str:
    letters = [ch for ch in segment if unicodedata.category(ch).startswith("L")
               and unicodedata.category(ch) != "Lm"]
    return letters[0] if len(letters) == 1 else ""


def main() -> None:
    with open(DATA / "feature_weights.csv", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    panphon_features = rows[0]
    features = panphon_features + list(ADDED)
    weights = [float(w) for w in rows[1]] + list(ADDED.values())
    hayes = read_hayes()

    phones = {}
    with open(DATA / "ipa_all.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            seg = unicodedata.normalize("NFD", row["ipa"])
            vec = {f: row[f] for f in panphon_features}
            h = hayes.get(base_letter(seg))
            vec.update({f: (h[HAYES_NAMES[f]] if h else "0" if f == "front" else "-")
                        for f in ADDED})
            if h and h["syllabic"] == "+" and row["syl"] == "+":
                vec.update({f: h[HAYES_NAMES[f]] for f in VOWEL_FEATURES})
            phones[seg] = "".join(vec[f] for f in features)
    n_in = len(phones)

    overrides = json.loads((HERE / "overrides.json").read_text(encoding="utf-8"))["overrides"]
    for o in overrides:
        key = unicodedata.normalize("NFD", o["phone"])
        i = features.index(o["feature"])
        vec = phones[key]
        if vec[i] != o["panphon"]:
            raise SystemExit(f"{o['phone']} {o['feature']}: PanPhon has {vec[i]}, "
                             f"the override expects {o['panphon']}")
        phones[key] = vec[:i] + o["value"] + vec[i + 1:]

    diacritics = yaml.safe_load((DATA / "diacritic_definitions.yml").read_text(encoding="utf-8"))
    out = {
        "source": f"PanPhon {importlib.metadata.version('panphon')} (Mortensen et al. 2016, MIT); "
                  "vowel features, [front], [tap] and [trill] from Hayes (2009, Introductory "
                  f"Phonology); {len(overrides)} changes from overrides.json",
        "features": features,
        "weights": weights,
        "phones": phones,
        "diacritics": [
            {"marker": unicodedata.normalize("NFD", d["marker"]),
             "position": d.get("position", "post"),
             "conditions": d.get("conditions", []),
             "content": d.get("content", {})}
            for d in diacritics["diacritics"]
        ],
    }
    (HERE / "features.json").write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n",
                                        encoding="utf-8")
    print(f"phones in {n_in}, out {len(phones)}; overrides {len(overrides)}; "
          f"diacritics {len(out['diacritics'])}")


if __name__ == "__main__":
    main()
