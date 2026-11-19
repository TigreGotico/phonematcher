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

    with open(DATA / "ipa_all.csv", encoding="utf-8") as fh:
        panphon = {unicodedata.normalize("NFD", row["ipa"]): {f: row[f] for f in panphon_features}
                   for row in csv.DictReader(fh)}
    n_in = len(panphon)

    changes = json.loads((HERE / "overrides.json").read_text(encoding="utf-8"))
    overrides = changes["overrides"]
    unknown = {o["phone"] for o in overrides} - set(panphon)
    if unknown:
        raise SystemExit(f"overrides name segments PanPhon does not list: {sorted(unknown)}")

    def bare(letter: str) -> dict:
        """A bare letter: PanPhon's values, with Hayes's added features and vowel values."""
        vec = dict(panphon[letter])
        h = hayes.get(letter)
        vec.update({f: (h[HAYES_NAMES[f]] if h else "0" if f == "front" else "-")
                    for f in ADDED})
        if h and h["syllabic"] == "+" and vec["syl"] == "+":
            vec.update({f: h[HAYES_NAMES[f]] for f in VOWEL_FEATURES})
        for o in overrides:
            if unicodedata.normalize("NFD", o["phone"]) == letter:
                if vec[o["feature"]] != o["panphon"]:
                    raise SystemExit(f"{o['phone']} {o['feature']}: the table has "
                                     f"{vec[o['feature']]}, the override expects {o['panphon']}")
                vec[o["feature"]] = o["value"]
        return vec

    # A segment with diacritics is its base letter plus the difference PanPhon records between
    # the two, so a diacritic's effect survives the Hayes values of its base.
    phones = {}
    for seg, row in panphon.items():
        base = base_letter(seg)
        if base not in panphon:
            vec = bare(seg)
        else:
            vec = bare(base)
            vec.update({f: row[f] for f in panphon_features if row[f] != panphon[base][f]})
        phones[seg] = vec

    diacritics = yaml.safe_load((DATA / "diacritic_definitions.yml").read_text(encoding="utf-8"))
    for change in changes["diacritics"]:
        marker = unicodedata.normalize("NFD", change["marker"])
        for d in diacritics["diacritics"]:
            if unicodedata.normalize("NFD", d["marker"]) == marker:
                d["content"] = {**d.get("content", {}), **change["content"]}
        for seg, vec in phones.items():
            if marker in seg and vec["syl"] == "+":
                vec.update(change["content"])
    phones = {seg: "".join(vec[f] for f in features) for seg, vec in phones.items()}
    out = {
        "source": f"PanPhon {importlib.metadata.version('panphon')} (Mortensen et al. 2016, MIT); "
                  "vowel features, [front], [tap] and [trill] from Hayes (2009, Introductory "
                  f"Phonology); {len(overrides)} value and {len(changes['diacritics'])} diacritic "
                  "changes from overrides.json",
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
