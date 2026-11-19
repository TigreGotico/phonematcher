"""Distinctive features of IPA segments, and the weighted distance between two segments.

The table is PanPhon's (Mortensen et al. 2016, "PanPhon: A Resource for Mapping IPA Segments to
Articulatory Feature Vectors", COLING; MIT License), with the changes listed in
``data/overrides.json``, each of which names its source. ``scripts/build_features.py`` builds
``data/features.json`` from both.

A feature value is ``True`` (+), ``False`` (−) or ``None`` (0: the feature does not apply).
"""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

_DATA = json.loads((Path(__file__).parent / "data" / "features.json").read_text(encoding="utf-8"))

#: Feature names, in vector order.
FEATURES: Tuple[str, ...] = tuple(_DATA["features"])
#: PanPhon's weight for each feature.
WEIGHTS: Tuple[float, ...] = tuple(_DATA["weights"])
NUM_FEATURES = len(FEATURES)
SOURCE: str = _DATA["source"]

Vector = Tuple[Optional[bool], ...]

_VALUE = {"+": True, "-": False, "0": None}

#: Segment (NFD) -> feature vector.
phone_features: Dict[str, Vector] = {
    seg: tuple(_VALUE[c] for c in vec) for seg, vec in _DATA["phones"].items()
}

_DIACRITICS: Dict[Tuple[str, str], dict] = {
    (d["marker"], d["position"]): d for d in _DATA["diacritics"]
}
#: Diacritics written after their base.
POST_DIACRITICS = {marker for marker, position in _DIACRITICS if position == "post"}
#: Marks written before a stop: prenasalization takes PanPhon's rule for ◌ⁿ (the nasal's place
#: is the stop's), preaspiration its rule for ◌ʰ.
PRE_DIACRITICS = {
    **{marker: (marker, "pre") for marker, position in _DIACRITICS if position == "pre"},
    "ⁿ": ("ⁿ", "post"), "ᵐ": ("ⁿ", "post"), "ᵑ": ("ⁿ", "post"), "ʰ": ("ʰ", "post"),
}
_TIES = ("͡", "͜")


def _applies(diacritic: dict, vec: Vector) -> bool:
    conditions = diacritic["conditions"]
    return not conditions or any(
        all(vec[FEATURES.index(f)] is _VALUE[v] for f, v in cond.items()) for cond in conditions
    )


def _apply(diacritic: dict, vec: Vector) -> Vector:
    out = list(vec)
    for f, v in diacritic["content"].items():
        out[FEATURES.index(f)] = _VALUE[v]
    return tuple(out)


@lru_cache(maxsize=4096)
def vectorize_phones(segment: str) -> Vector:
    """The feature vector of one IPA *segment*.

    A segment in the table is read as listed. Otherwise the longest listed base in it takes the
    diacritics around it, each by PanPhon's rule for that diacritic, as long as the rule's
    conditions hold. Raises ``ValueError`` for a segment it cannot read.
    """
    seg = unicodedata.normalize("NFD", segment)
    if seg in phone_features:
        return phone_features[seg]
    untied = seg.replace(_TIES[1], _TIES[0])
    if untied in phone_features:
        return phone_features[untied]

    start = 0
    while start < len(seg) and seg[start] in PRE_DIACRITICS:
        start += 1
    for end in range(len(seg), start, -1):
        base = seg[start:end]
        if base in phone_features and all(m in POST_DIACRITICS for m in seg[end:]):
            vec = phone_features[base]
            for marker in seg[:start]:
                vec = _apply_if(_DIACRITICS[PRE_DIACRITICS[marker]], vec, segment)
            for marker in seg[end:]:
                vec = _apply_if(_DIACRITICS[marker, "post"], vec, segment)
            return vec
    raise ValueError(f"Unrecognized phone {segment!r}")


def _apply_if(diacritic: dict, vec: Vector, segment: str) -> Vector:
    if not _applies(diacritic, vec):
        raise ValueError(f"{diacritic['marker']!r} does not apply to the base of {segment!r}")
    return _apply(diacritic, vec)


def is_vowel_phone(segment: str) -> bool:
    """True for a syllabic segment."""
    try:
        return vectorize_phones(segment)[0] is True
    except ValueError:
        return False


def _number(value: Optional[bool]) -> int:
    return 1 if value is True else -1 if value is False else 0


def phonetic_distance(a: str, b: str) -> float:
    """Weighted feature distance between two segments, from 0 (same features) to 1.

    Each feature contributes its PanPhon weight times half the difference of its values, with
    + = 1, 0 = 0 and − = −1, so a +/− mismatch costs the full weight and a 0 against + or − costs
    half. The sum is divided by the total weight. A segment that cannot be read is at distance 1
    from every other segment. A space matches only a space.
    """
    if a == b:
        return 0.0
    if a == " " or b == " ":
        return 1.0
    try:
        va, vb = vectorize_phones(a), vectorize_phones(b)
    except ValueError:
        return 1.0
    diff = sum(w * abs(_number(x) - _number(y)) / 2 for w, x, y in zip(WEIGHTS, va, vb))
    return diff / sum(WEIGHTS)
