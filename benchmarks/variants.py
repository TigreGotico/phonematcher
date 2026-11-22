"""Ablations of phonematcher, each a ``System``, built without changing the package.

Every variant reads the segments phonematcher reads and keeps its tone distance. Each one changes
a single thing in the segment distance or the edit distance:

=====================  ==================================================================
``pm-panphon22``       PanPhon's 22 features, each with the weight in PanPhon's own file
``pm-no-height``       every feature but the vowel height steps ``h1`` to ``h6``
``pm-flat-diacritics`` marks apply their content only; no mark moves a vowel along a scale
``pm-uniform``         all 36 features at weight 1
``pm-indel-0.5``       deletion and insertion cost 0.5
``pm-indel-1.5``       deletion and insertion cost 1.5
=====================  ==================================================================

The feature distance is the package's: the weighted sum of half the value differences, over the
sum of the weights that the variant keeps. A variant is a diagnostic; none is a candidate.

Each variant exists under two cost rules. The ``pm-`` names keep the C0 costs: gap 1 and linear
substitutions, the rule of the pre-registered test run. The ``pm-p5-`` names keep the shipped P5
costs: gap 0.5 and substitutions at the square root of the feature distance. ``phonematcher`` is
on the P5 costs, so it is compared with the ``pm-p5-`` names, and the ``pm-`` names are compared
with each other. ``pm-p5-indel-0.5`` is the shipped costs again and serves as a control.

    python benchmarks/variants.py control --cache DIR

prints the control: ``pm-panphon22`` against ``panphon-weighted`` on every PHOIBLE segment both read.
"""
import argparse
import csv
import importlib.util
import io
import sys
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phonematcher import features
from phonematcher.tone import tone_distance
from systems import PhoneMatcher, System, edit_alignment, edit_distance, per_length  # noqa: E402

NAMES = ["pm-panphon22", "pm-no-height", "pm-flat-diacritics", "pm-uniform", "pm-indel-0.5", "pm-indel-1.5"]
#: the same variants on the shipped P5 costs
P5_NAMES = [f"pm-p5-{name.removeprefix('pm-')}" for name in NAMES]
#: the weight candidates of ``prereg-2.md``; C0 is the ``phonematcher`` system
CANDIDATES = ["pm-C1", "pm-C2", "pm-C3", "pm-P4", "pm-P5"]
HEIGHT_STEPS = tuple(f"h{k}" for k in range(1, 7))
HALF_WEIGHT = ("front", "back", "round", "lab")
MAJOR_CLASS = ("syl", "son", "cons")
#: vowel chart of constraint K1, and the obstruents it keeps apart from every chart vowel
CHART = Path(__file__).resolve().parent.parent / "scripts" / "sources" / "ipa-vowel-chart.csv"
OBSTRUENTS = "pbtdkɡqʔfvszʃʒxχh"


def panphon_weights(by_file_label: bool = False) -> Tuple[float, ...]:
    """PanPhon's weights on the package's feature order: its 22 weights, and 0 for the features
    the package added.

    The file ``feature_weights.csv`` lists ``tense, long, velaric`` at its end. ``FeatureTable``
    reads the row without the names and gives the values to its own feature order, which ends
    ``velaric, tense, long``. A distance therefore weights ``velaric`` 0.25, ``tense`` 0.125 and
    ``long`` 0.25, and not the 0.25, 0.25 and 0.125 that the file's names say. The default is the
    weights that PanPhon applies; *by_file_label* gives the weights by the names in the file.
    """
    import panphon

    with open(Path(panphon.__file__).parent / "data" / "feature_weights.csv", newline="") as handle:
        names, values = list(csv.reader(handle))
    values = list(map(float, values))
    if not by_file_label:
        names = panphon.FeatureTable().names[: len(values)]
    unknown = set(names) - set(features.FEATURES)
    if unknown:
        raise ValueError(f"PanPhon weights for features the table lacks: {sorted(unknown)}")
    given = dict(zip(names, values))
    return tuple(given.get(f, 0.0) for f in features.FEATURES)


def flat_features():
    """A second copy of ``phonematcher.features`` in which no diacritic shifts a scale.

    A listed segment that is a listed base plus marks was built with each mark's shift applied.
    Here the same segments are rebuilt from their bases with the marks' content only, which is
    PanPhon's rule for a mark. ``reread`` with ``shifts=True`` rebuilds the table as it is, and
    ``test_bench_variants`` holds it to the package's table.
    """
    module = fresh_features()
    reread(module, shifts=False)
    return module


def fresh_features():
    spec = importlib.util.spec_from_file_location("phonematcher_flat_features", features.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reread(module, shifts: bool) -> int:
    """Rebuild the listed segments of *module* from their bases, shortest first, as the build
    script does. Returns how many segments changed."""
    if not shifts:
        for diacritic in module._DIACRITICS.values():
            diacritic.pop("shift", None)
    table = module.phone_features
    before = dict(table)
    for segment in sorted(before, key=len):
        for end in range(len(segment) - 1, 0, -1):
            base, marks = segment[:end], segment[end:]
            if base in table and all((m, "post") in module._DIACRITICS for m in marks):
                vector = table[base]
                try:
                    for mark in marks:
                        vector = module._apply_if(module._DIACRITICS[mark, "post"], vector, segment)
                except ValueError:
                    break
                table[segment] = vector
                break
    for cached in (module.vectorize_phones, module._signs, module.feature_distance):
        cached.cache_clear()
    return sum(table[s] != before[s] for s in before)


class Variant(PhoneMatcher):
    """phonematcher with other feature weights, other feature vectors or another indel cost."""

    def __init__(
        self, name: str, weights: Sequence[float] = features.WEIGHTS, indel: float = 1.0, vectorize=None, power: float = 1.0
    ):
        super().__init__()
        self.name = name
        self.weights = tuple(weights)
        self.indel = indel
        self.power = power
        if vectorize is not None:
            self._vectorize = vectorize
        self._substitution = self.substitution
        self._align_pairs = lambda a, b: edit_alignment(a, b, self.substitution, self.indel)

    def phone_distance(self, a: str, b: str) -> float:
        """The package's ``feature_distance`` on this variant's weights and vectors."""
        if a == b:
            return 0.0
        if a == " " or b == " ":
            return 1.0
        try:
            va, vb = self._vectorize(a), self._vectorize(b)
        except ValueError:
            return 1.0
        number = {True: 1, False: -1, None: 0}
        diff = sum(w * abs(number[x] - number[y]) / 2 for w, x, y in zip(self.weights, va, vb))
        return diff / sum(self.weights)

    def substitution(self, a: str, b: str) -> float:
        """The package's ``substitution_cost`` with this variant's phone distance."""
        if self._is_tone(a) or self._is_tone(b):
            cost = tone_distance(a, b) if self._is_tone(a) and self._is_tone(b) else 1.0
        else:
            cost = self.phone_distance(a, b)
        return cost ** self.power

    def _word_distance(self, a, b, normalized: bool) -> float:
        left = [p for s in a for p in self._parts(s)]
        right = [p for s in b for p in self._parts(s)]
        return per_length(edit_distance(left, right, self.substitution, self.indel), left, right, normalized)


def build_variant(name: str) -> Variant:
    if name in CANDIDATES:
        return build_candidate(name)
    p5 = name in P5_NAMES
    base = "pm-" + name.removeprefix("pm-p5-") if p5 else name
    if base not in NAMES:
        raise KeyError(f"unknown variant {name!r}; known: {', '.join(NAMES + P5_NAMES + CANDIDATES)}")
    costs = {"indel": 0.5, "power": 0.5} if p5 else {}
    if base == "pm-panphon22":
        return Variant(name, weights=panphon_weights(), **costs)
    if base == "pm-no-height":
        return Variant(name, weights=[0.0 if f in HEIGHT_STEPS else w for f, w in zip(features.FEATURES, features.WEIGHTS)], **costs)
    if base == "pm-flat-diacritics":
        return Variant(name, vectorize=flat_features().vectorize_phones, **costs)
    if base == "pm-uniform":
        return Variant(name, weights=[1.0] * features.NUM_FEATURES, **costs)
    return Variant(name, **{**costs, "indel": float(base.removeprefix("pm-indel-"))})


def c2_weights() -> List[float]:
    """Every feature 1, the six height steps 1/6 each, and front, back, round and lab 1/2 each."""
    return [1 / 6 if f in HEIGHT_STEPS else 0.5 if f in HALF_WEIGHT else 1.0 for f in features.FEATURES]


def chart_vowels() -> List[str]:
    with open(CHART, encoding="utf-8", newline="") as handle:
        return [row["symbol"] for row in csv.DictReader(handle)]


def k1(system: System) -> bool:
    """Constraint K1: every pair of chart vowels is nearer than any chart vowel and any obstruent."""
    vowels = chart_vowels()
    widest = max(system.segment_distance(a, b) for a, b in combinations(vowels, 2))
    return widest < min(system.segment_distance(v, o) for v in vowels for o in OBSTRUENTS)


def with_major_class(weight: float) -> List[float]:
    return [weight if f in MAJOR_CLASS else w for f, w in zip(features.FEATURES, c2_weights())]


def c3_weight() -> float:
    """The least weight for ``syl``, ``son`` and ``cons`` in C2 that passes K1, by bisection of
    [1, 10] to 0.01. The search keeps the upper end, which passes."""
    low, high = 1.0, 10.0
    while high - low > 0.01:
        mid = (low + high) / 2
        low, high = (low, mid) if k1(Variant("c3-search", weights=with_major_class(mid))) else (mid, high)
    return round(high, 2)


def build_candidate(name: str) -> Variant:
    if name == "pm-C1":
        return Variant(name, weights=[1.0] * features.NUM_FEATURES)
    if name == "pm-C2":
        return Variant(name, weights=c2_weights())
    if name == "pm-C3":
        return Variant(name, weights=with_major_class(c3_weight()))
    if name == "pm-P4":
        return Variant(name, indel=0.5)
    if name == "pm-P5":
        return Variant(name, indel=0.5, power=0.5)
    raise KeyError(f"unknown candidate {name!r}; known: {', '.join(CANDIDATES)}")


def phoible_segments(cache: Path) -> List[str]:
    """Every distinct ``Phoneme`` and every distinct item of ``Allophones`` in PHOIBLE 2.0."""
    from tasks.common import PHOIBLE_URL, fetch

    text = fetch(PHOIBLE_URL, Path(cache) / "C2" / "phoible.csv").read_text(encoding="utf-8")
    found = set()
    for row in csv.DictReader(io.StringIO(text)):
        found.add(row["Phoneme"])
        if row["Allophones"] not in ("", "NA"):
            found.update(row["Allophones"].split())
    return sorted(found)


def control(cache: Path, tolerance: float = 1e-9) -> dict:
    """``pm-panphon22`` against ``panphon-weighted`` on every PHOIBLE segment that both read.

    ``panphon-weighted`` sums the weighted value differences and does not halve them or divide by
    the weight total, so ``scale`` = 2 * sum of PanPhon's weights turns a ``pm-panphon22``
    distance into PanPhon's. A pair differs when the scaled distances disagree by more than
    *tolerance*. The table changes some of PanPhon's 22 values (``segments_with_vector_difference``),
    so a pair with such a segment can differ. The control proper is the pairs of two segments whose
    22 values equal PanPhon's: ``identical_vector_pairs_differing`` is the number of those that differ.
    """
    from systems import PanPhon

    ours, theirs = build_variant("pm-panphon22"), PanPhon(weighted=True)
    scale = 2 * sum(ours.weights)

    def whole(segment: str) -> bool:
        try:
            features.vectorize_phones(segment)
        except ValueError:
            return False
        return True

    all_segments = phoible_segments(cache)
    both = [s for s in all_segments if whole(s) and theirs.reads(s)]
    changed = vector_differences(both)
    pairs = differing = identical_pairs = identical_differing = 0
    for i, a in enumerate(both):
        for b in both[i + 1:]:
            pairs += 1
            differs = abs(ours.segment_distance(a, b) * scale - theirs.segment_distance(a, b)) > tolerance
            differing += differs
            if a not in changed and b not in changed:
                identical_pairs += 1
                identical_differing += differs
    return {
        "segments_in": len(all_segments),
        "read_by_pm_panphon22": sum(whole(s) for s in all_segments),
        "read_by_panphon_weighted": sum(theirs.reads(s) for s in all_segments),
        "segments_read_by_both": len(both),
        "pairs_compared": pairs,
        "pairs_differing": differing,
        "identical_vector_pairs": identical_pairs,
        "identical_vector_pairs_differing": identical_differing,
        "tolerance": tolerance,
        "scale": scale,
        "segments_with_vector_difference": len(changed),
        "vector_difference_causes": causes(changed),
        "vector_difference_features": feature_counts(changed),
        "segments_with_vector_difference_list": {s: changed[s] for s in sorted(changed)},
    }


def feature_counts(changed: Dict[str, List[str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for differ in changed.values():
        for name in differ:
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def causes(changed: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Split the changed segments by where the change starts: a bare letter whose own vector
    differs (the chart and Hayes values of ``overrides.json``), or a segment whose letters match
    PanPhon and whose marks or tie differ. The lists hold up to five examples."""
    import unicodedata

    letters = {"Ll", "Lu", "Lo"}
    out: Dict[str, List[str]] = {"letter": [], "marks_or_tie": []}
    counts = {"letter": 0, "marks_or_tie": 0}
    for s in changed:
        base = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) in letters)
        kind = "letter" if base in changed else "marks_or_tie"
        counts[kind] += 1
        if len(out[kind]) < 5:
            out[kind].append(s)
    return {"count_letter": counts["letter"], "count_marks_or_tie": counts["marks_or_tie"], **{f"examples_{k}": v for k, v in out.items()}}


def vector_differences(read_by_both: Sequence[str]) -> Dict[str, List[str]]:
    """For each segment whose 22 PanPhon features differ between the table and PanPhon, the
    names of the features that differ."""
    from panphon import FeatureTable

    table = FeatureTable()
    number = {True: 1, False: -1, None: 0}
    found: Dict[str, List[str]] = {}
    for s in read_by_both:
        theirs = dict(zip(table.names, table.fts(s).numeric()))
        mine = dict(zip(features.FEATURES, (number[v] for v in features.vectorize_phones(s))))
        differ = [n for n in table.names[:22] if mine[n] != theirs[n]]
        if differ:
            found[s] = differ
    return found


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["control"])
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "phonematcher-bench")
    args = parser.parse_args(argv)
    result = control(args.cache)
    print({k: v for k, v in result.items() if k != "segments_with_vector_difference_list"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
