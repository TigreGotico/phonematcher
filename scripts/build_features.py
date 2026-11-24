"""Build phonematcher/data/features.json.

PanPhon (Mortensen et al. 2016, MIT) supplies the segments, the feature weights and the diacritic
rules. The Hayes (2009) feature tables as converted to CSV by Gorman (Apache-2.0, vendored in
``scripts/sources/``; tables 4.7 to 4.9 per Gorman) add [front], [tap] and [trill]. The vowel letters take their height,
backness and rounding from the IPA chart (``scripts/sources/ipa-vowel-chart.csv``). [atr], the
secondary articulations and the epiglottals are local features. ``phonematcher/data/overrides.json`` holds the other changes, each with its source.
Run after changing any input:

    uv pip install -e '.[build]'
    python scripts/build_features.py [--out PATH]

Without ``--out`` the script overwrites ``phonematcher/data/features.json``.
"""
import argparse
import csv
import importlib.metadata
import importlib.util
import json
import unicodedata
from pathlib import Path

import panphon
import yaml

_spec = importlib.util.spec_from_file_location(
    "scales", Path(__file__).resolve().parent.parent / "phonematcher" / "scales.py")
scales = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scales)

DATA = Path(panphon.__file__).parent / "data"
HERE = Path(__file__).resolve().parent.parent / "phonematcher" / "data"
HAYES = Path(__file__).resolve().parent / "sources" / "hayes2009-features.csv"
CHART = Path(__file__).resolve().parent / "sources" / "ipa-vowel-chart.csv"

#: Hayes's name for each feature this build takes from him.
HAYES_NAMES = {"hi": "high", "lo": "low", "front": "front", "back": "back", "round": "round",
               "tense": "tense", "lab": "LABIAL", "tap": "tap", "trill": "trill"}
VOWEL_FEATURES = ("hi", "lo", "front", "back", "round", "tense", "lab")
#: The seven height rows, close to open.
HEIGHTS = ("close", "near-close", "close-mid", "mid", "open-mid", "near-open", "open")
#: [h1] ... [h6]: a vowel is + for each step its height lies below close, so the number of
#: differing step features equals the number of height rows between two vowels.
STEPS = scales.STEPS
#: Secondary articulations, each a feature of its own beside the primary place.
SECONDARY = ("palatalized", "velarized", "labialized", "pharyngealized")
ADDED = {"front": 0.25, "tap": 0.25, "trill": 0.25, "atr": 0.25,
         **dict.fromkeys(STEPS, 0.125), **dict.fromkeys(SECONDARY, 0.125)}


BACKNESS = {"front": "+-", "central": "--", "back": "-+"}
#: Place of articulation, copied by a segment built "with the place of" another.
PLACE = ("ant", "cor", "distr", "lab", "hi", "lo", "back", "round", "front")


def read_chart() -> dict:
    with open(CHART, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    chart = {}
    for r in rows:
        front, back = BACKNESS[r["backness"]]
        level = HEIGHTS.index(r["height"])
        # PanPhon gives 22 of the 28 vowels [-delrel] and six of them 0; a vowel has no release,
        # so all take the majority value.
        height = {"tense": "0"}
        scales.set_height(height, level)
        chart[r["symbol"]] = {**height, "front": front, "back": back,
                              "round": r["rounded"], "lab": r["rounded"], "delrel": "-", "index": level}
    return chart


def read_hayes() -> dict:
    with open(HAYES, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    return {unicodedata.normalize("NFD", r[0]): dict(zip(head, r)) for r in rows[1:] if r[0]}


def base_letter(segment: str) -> str:
    letters = [ch for ch in segment if unicodedata.category(ch).startswith("L")
               and unicodedata.category(ch) != "Lm"]
    return letters[0] if len(letters) == 1 else ""


def validate(changes: dict, features: list) -> None:
    """Stop the build with a message naming the first entry of *changes* that is not well formed."""
    known = set(features)

    def check(kind: str, name: str, values: dict) -> None:
        for f, v in values.items():
            if f not in known:
                raise SystemExit(f"{kind} {name}: unknown feature {f!r}")
            if v not in ("+", "-", "0"):
                raise SystemExit(f"{kind} {name}: value {v!r} of {f} is not '+', '-' or '0'")

    for kind, key in (("overrides", "phone"), ("diacritics", "marker"), ("segments", "segment")):
        for entry in changes[kind]:
            if not entry.get("source"):
                raise SystemExit(f"{kind} entry {entry[key]} has no source")
    for o in changes["overrides"]:
        check("override", o["phone"], {o["feature"]: o["value"]})
        phone = unicodedata.normalize("NFD", o["phone"])
        if base_letter(phone) != phone:
            raise SystemExit(f"override {o['phone']}: the segment is not a bare table letter")
    for d in changes["diacritics"]:
        check("diacritic", d["marker"], d["content"])
        for reading in d.get("consonant", ()):
            check("diacritic", d["marker"], {**reading["when"], **reading["set"]})
    for s in changes["segments"]:
        check("segments entry", s["segment"], s["set"])


#: The tone features that end every vector, after the tone block of phoonnx_train/features_json.py,
#: and their weights, chosen on the dev split (docs/design.md, "The tone weights").
TONE = {"tone_is": 0.25, "tone_start": 0.125, "tone_mid": 0.125, "tone_end": 0.125}


def main(out_path: Path) -> None:
    with open(DATA / "feature_weights.csv", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    panphon_features = rows[0]
    features = panphon_features + list(ADDED)
    weights = [float(w) for w in rows[1]] + list(ADDED.values())
    hayes = read_hayes()
    chart = read_chart()

    with open(DATA / "ipa_all.csv", encoding="utf-8") as fh:
        # vectorize_phones reads ɫ as l̴, built by the rules, so PanPhon's ɫ rows are not taken.
        # Tone letters are tones, read by phonematcher.tone, not phones.
        panphon = {unicodedata.normalize("NFD", row["ipa"]): {f: row[f] for f in panphon_features}
                   for row in csv.DictReader(fh)
                   if "ɫ" not in row["ipa"] and not set(row["ipa"]) & set("˩˨˧˦˥")}
    n_in = len(panphon)

    changes = json.loads((HERE / "overrides.json").read_text(encoding="utf-8"))
    validate(changes, features)
    overrides = changes["overrides"]
    for s in changes["segments"]:
        missing = [s[k] for k in ("from", "place_of") if k in s and s[k] not in panphon]
        if missing:
            raise SystemExit(f"segments entry {s['segment']} names segments PanPhon does not list: {missing}")
        row = dict(panphon[s["from"]])
        row.update({f: panphon[s["place_of"]][f] for f in PLACE if f in row} if "place_of" in s else {})
        row.update({f: v for f, v in s["set"].items() if f in row})
        panphon[unicodedata.normalize("NFD", s["segment"])] = row
    unknown = {o["phone"] for o in overrides} - set(panphon)
    if unknown:
        raise SystemExit(f"overrides name segments PanPhon does not list: {sorted(unknown)}")

    def bare(letter: str) -> dict:
        """A bare letter: PanPhon's values, with Hayes's added features and vowel values."""
        vec = dict(panphon[letter])
        h = hayes.get(letter)
        vec.update({f: (h[HAYES_NAMES[f]] if h else "0" if f == "front" else "-")
                    for f in ("front", "tap", "trill")})
        vec.update({"atr": "0", **dict.fromkeys(STEPS, "0"), **dict.fromkeys(SECONDARY, "-")})
        if letter in chart:
            vec.update({f: v for f, v in chart[letter].items() if f != "index"})
        elif h and h["syllabic"] == "+" and vec["syl"] == "+":
            vec.update({f: h[HAYES_NAMES[f]] for f in VOWEL_FEATURES})
        for s in changes["segments"]:
            if unicodedata.normalize("NFD", s["segment"]) == letter:
                vec.update({f: v for f, v in s["set"].items() if f in ADDED})
        for o in overrides:
            if unicodedata.normalize("NFD", o["phone"]) == letter:
                if vec[o["feature"]] != o["panphon"]:
                    raise SystemExit(f"{o['phone']} {o['feature']}: the table has "
                                     f"{vec[o['feature']]}, the override expects {o['panphon']}")
                vec[o["feature"]] = o["value"]
        return vec

    # A diacritic change replaces PanPhon's rule for that mark: the features PanPhon's rule set
    # stay as the base has them, then the change's own values apply.
    diacritics = yaml.safe_load((DATA / "diacritic_definitions.yml").read_text(encoding="utf-8"))
    for change in changes["diacritics"]:
        marker = unicodedata.normalize("NFD", change["marker"])
        found = [d for d in diacritics["diacritics"]
                 if unicodedata.normalize("NFD", d["marker"]) == marker]
        if not found:
            found = [{"marker": marker, "position": "post", "conditions": [], "content": {}}]
            diacritics["diacritics"].append(found[0])
        for d in found:
            d["content"] = {**{f: v for f, v in d.get("content", {}).items()
                               if f not in change.get("restore", [])}, **change["content"]}
            if "conditions" in change:
                d["conditions"] = change["conditions"]
            if "shift" in change:
                d["shift"] = change["shift"]
            if "consonant" in change:
                d["consonant"] = change["consonant"]
    rules = {unicodedata.normalize("NFD", d["marker"]): d
             for d in diacritics["diacritics"] if d.get("position", "post") == "post"}

    def apply_rules(vec: dict, marks: str) -> dict:
        """The marks' rules in order, as vectorize_phones applies them; None if one does not
        apply. [+high, +low] is impossible, because the tongue body cannot be raised and lowered
        at once: a mark that adds one keeps the other as the base has it."""
        vec = dict(vec)
        for ch in marks:
            rule = rules[ch]
            if rule.get("conditions") and not any(
                    all(vec[f] == v for f, v in cond.items()) for cond in rule["conditions"]):
                return None
            before = dict(vec)
            vec.update(rule.get("content", {}))
            for reading in rule.get("consonant", ()):
                if all(vec[f] == v for f, v in reading["when"].items()):
                    vec.update(reading["set"])
                    break
            scales.shift(vec, rule.get("shift", {}))
            if vec["hi"] == vec["lo"] == "+":
                vec["lo" if before["hi"] == "+" else "hi"] = "-"
        return vec

    # A segment with diacritics is its base letter with each mark's rule applied in order, so a
    # listed stack equals the same stack read by vectorize_phones. A mark without a rule takes
    # the difference PanPhon records between the segment and its base.
    # The base is the longest listed prefix, as in vectorize_phones; shorter segments are built
    # first, so the base's own vector is final when a longer segment uses it.
    phones = {}
    for seg in sorted(panphon, key=len):
        row = panphon[seg]
        vec = None
        for end in range(len(seg) - 1, 0, -1):
            prefix, marks = seg[:end], seg[end:]
            if prefix in phones and all(ch in rules for ch in marks):
                vec = apply_rules(phones[prefix], marks)
                break
        base = base_letter(seg)
        if vec is None and base in panphon and base != seg:
            vec = bare(base)
            vec.update({f: row[f] for f in panphon_features if row[f] != panphon[base][f]})
        if vec is None:
            vec = bare(seg)
        phones[seg] = vec
    both = sorted(s for s, v in phones.items() if v["hi"] == "+" and v["lo"] == "+")
    if both:
        raise SystemExit(f"[+high, +low] in {len(both)} segments: {both}")
    phones = {seg: "".join(vec[f] for f in features) for seg, vec in phones.items()}
    out = {
        "source": f"PanPhon {importlib.metadata.version('panphon')} (Mortensen et al. 2016, MIT); "
                  "[front], [tap] and [trill] from the Hayes (2009) tables as converted to CSV by Gorman; vowel "
                  "letters from the IPA chart; "
                  f"{len(overrides)} value, {len(changes['diacritics'])} diacritic and "
                  f"{len(changes['segments'])} segment changes from overrides.json",
        "features": features,
        "weights": weights,
        "tone": {"features": list(TONE), "weights": list(TONE.values())},
        "phones": phones,
        "diacritics": [
            {"marker": unicodedata.normalize("NFD", d["marker"]),
             "position": d.get("position", "post"),
             "conditions": d.get("conditions", []),
             "content": d.get("content", {}),
             **({"shift": d["shift"]} if "shift" in d else {}),
             **({"consonant": d["consonant"]} if "consonant" in d else {})}
            for d in diacritics["diacritics"]
        ],
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"phones in {n_in} + {len(changes['segments'])} added, out {len(phones)}; "
          f"overrides {len(overrides)}; "
          f"diacritics {len(out['diacritics'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "features.json",
                        help="where to write the table")
    main(parser.parse_args().out)
