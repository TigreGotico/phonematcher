"""Distinctive features of IPA segments, and the weighted distance between two segments.

The table is PanPhon's (Mortensen et al. 2016, "PanPhon: A Resource for Mapping IPA Segments to
Articulatory Feature Vectors", COLING; MIT License), with the changes listed in
``data/overrides.json``, each of which names its source. ``scripts/build_features.py`` builds
``data/features.json`` from both.

A feature value is ``True`` (+), ``False`` (−) or ``None`` (0: the feature does not apply). The
four tone features at the end of every vector are numbers: ``tone_is`` is ``True`` on a segment with
a tone, and ``tone_start``, ``tone_mid`` and ``tone_end`` are its pitch at the start, middle and end
of the syllable, each Chao level 1 to 5 as (level − 3) / 2. A segment with no tone has ``None`` in
all four.
"""
import json
import re
import threading
import unicodedata
import warnings
from functools import lru_cache
from itertools import takewhile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from phonematcher.scales import shift
from phonematcher.tone import DIACRITIC_TONES, LEVELS, NUMERALS, _contour
from phonematcher.version import VERSION_MAJOR

_DATA = json.loads((Path(__file__).parent / "data" / "features.json").read_text(encoding="utf-8"))

#: The tone features, which end every vector.
TONE_FEATURES: Tuple[str, ...] = tuple(_DATA["tone"]["features"])
#: Feature names, in vector order.
FEATURES: Tuple[str, ...] = tuple(_DATA["features"]) + TONE_FEATURES
#: PanPhon's weight for each segment feature, then the weight of each tone feature.
WEIGHTS: Tuple[float, ...] = tuple(_DATA["weights"]) + tuple(_DATA["tone"]["weights"])
#: The divisor of a feature distance: the weight of the segment features. A tone adds to the
#: distance of two segments without changing the distance of two segments with no tone.
_TOTAL_WEIGHT = sum(_DATA["weights"])
NUM_FEATURES = len(FEATURES)
_INDEX = {name: i for i, name in enumerate(FEATURES)}
SOURCE: str = _DATA["source"]

Vector = Tuple[Union[None, bool, float], ...]

_VALUE = {"+": True, "-": False, "0": None}
_NUMBER = {True: 1, False: -1, None: 0}
_NO_TONE = (None,) * len(TONE_FEATURES)

#: Segment (NFD) -> feature vector.
phone_features: Dict[str, Vector] = {
    seg: tuple(_VALUE[c] for c in vec) + _NO_TONE for seg, vec in _DATA["phones"].items()
}

_DIACRITICS: Dict[Tuple[str, str], dict] = {
    (d["marker"], d["position"]): d for d in _DATA["diacritics"]
}
#: Diacritics written after their base.
POST_DIACRITICS = {marker for marker, position in _DIACRITICS if position == "post"}
#: Marks written before a stop: prenasalization takes PanPhon's rule for ◌ⁿ (the nasal's place
#: is the stop's), preaspiration its rule for ◌ʰ. Every superscript nasal letter is a
#: prenasalization mark.
PRE_DIACRITICS = {
    **{marker: (marker, "pre") for marker, position in _DIACRITICS if position == "pre"},
    **dict.fromkeys("ⁿᵐᵑᶬᶮᶯᶰ", ("ⁿ", "post")), "ʰ": ("ʰ", "post"),
}
#: The tie bars, above and below; the table writes the first.
TIES = ("͡", "͜")
#: Unicode categories of a base letter, as against a modifier letter or a combining mark.
_LETTER_CATEGORIES = {"Ll", "Lu", "Lo"}
#: Click letters, and the velar and uvular letters that write a click's accompaniment (voicing,
#: nasality) beside it. A click after any other letter with no tie bar is not read.
_CLICKS = set("ʘǀǃǂǁ‼ʞ")
_REAR_CLOSURES = set("kɡŋqɢɴ")
#: Small letters that write a click's velar or uvular closure.
_SMALL_REAR_CLOSURES = {"ᶢ": "ɡ", "ᵑ": "ŋ", "ᶰ": "ɴ"}
#: Glottal letters: a glottal beside another letter is two segments or glottal reinforcement, never
#: one tied segment, so the untied-letter rule does not tie them.
_GLOTTALS = set("ʔhɦ")
#: Implosive letters. With the ejective mark ʼ they write the glottalic consonants.
_IMPLOSIVES = set("ɓɗʄɠʛᶑ")
#: Non-IPA spellings (``data/spellings.json``) -> the IPA they read as.
SPELLINGS: Dict[int, str] = str.maketrans({
    row["spelling"]: row["reads_as"] for row in json.loads(
        (Path(__file__).parent / "data" / "spellings.json").read_text(encoding="utf-8"))
})
#: Letters whose glyph descends below the baseline. The mark ◌̍ (U+030D) on one of them is the
#: syllabic mark ◌̩ (U+0329) moved above the letter. The criterion is in ``docs/features.md``.
_DESCENDERS = "gjpqyŋȴȵȶɕɖɟɠɡɣɥɧɭɮɰɱɲɳɸɻɽʂʃʄʈʐʑʒʝʮβχ"
_ABOVE_DESCENDER = re.compile(f"(?:[{_DESCENDERS}]|c\u0327)[\u0300-\u036f]*")  # ç is c with a cedilla below

#: Letters that Unicode does not decompose into a base and its mark: the rhotic vowels, and [ɫ],
#: the IPA chart's example of ◌̴ (velarized or pharyngealized). Spellings read as their IPA.
_COMPOSED_LETTERS = {**SPELLINGS, **str.maketrans({"ɚ": "ə˞", "ɝ": "ɜ˞", "ɫ": "l\u0334"})}


def _is_diphthong(seg: str) -> bool:
    plain = seg.replace(TIES[0], "").replace(TIES[1], "").replace("\u032f", "")
    return any(_is_listed_vowel(plain[:i]) and _is_listed_vowel(plain[i:]) for i in range(1, len(plain)))


def _is_listed_vowel(seg: str) -> bool:
    return seg in phone_features and phone_features[seg][0] is True


def _unrecognized(segment: str, note: str = "") -> ValueError:
    """The error for a segment with no vector. It lists the code points, so a combining mark that
    prints as nothing is visible."""
    points = " ".join(f"U+{ord(c):04X}" for c in segment)
    return ValueError(f"Unrecognized phone {segment!r} ({points}){note}. A word distance or a search"
                      " takes strict=True to raise on such a segment instead of costing it 1")


_TONE_MARKS = {**DIACRITIC_TONES, **NUMERALS, **{letter: letter for letter in LEVELS}}


def phone_and_tone(segment: str) -> Tuple[str, str]:
    """The phone of *segment* and its tone as tone letters: ``a˥˩`` and ``â`` both give ``a`` and
    ``˥˩``. A segment with no tone gives an empty tone. The phone is in NFD."""
    seg = unicodedata.normalize("NFD", segment)
    tone = "".join(_TONE_MARKS.get(ch, "") for ch in seg)
    return ("".join(ch for ch in seg if ch not in _TONE_MARKS), tone) if tone else (seg, "")


@lru_cache(maxsize=4096)
def vectorize_phones(segment: str) -> Vector:
    """The feature vector of one IPA *segment*.

    A vowel or a syllabic consonant may carry a tone, in tone letters, tone numerals or tone
    diacritics: ``a˥˩`` and ``â`` have the vector of ``a`` with the four tone features set. A tone
    on any other segment, or a tone with no segment, raises ``ValueError``.

    A segment in the table is read as listed. Otherwise the longest listed base in it takes the
    diacritics around it, each by PanPhon's rule for that diacritic, as long as the rule's
    conditions hold. Marks before the segment apply to a tied segment as to a listed one. Base
    letters with no tie bar read as the segment with a tie bar between each two of them, as the IPA
    chart allows two symbols for an affricate, with the tie bar added only if necessary. A letter
    that repeats the one before it (a geminate) and a click get no tie bar.
    Raises ``ValueError`` for a segment it cannot read.
    """
    phone, tone = phone_and_tone(segment)
    if tone:
        vec = vectorize_phones(phone) if phone else None
        if vec is None or vec[0] is not True:
            raise _unrecognized(segment, ": a tone is carried by a vowel or a syllabic consonant")
        levels = [LEVELS[letter] for letter in tone]
        return vec[:-len(TONE_FEATURES)] + (True,) + tuple((p - 3) / 2 for p in _contour(levels))
    seg = unicodedata.normalize("NFD", segment).translate(_COMPOSED_LETTERS)
    # the vertical line above a descender is the syllabic mark; NFD again puts the marks in order
    seg = unicodedata.normalize("NFD", _ABOVE_DESCENDER.sub(lambda m: m.group().replace("\u030d", "\u0329"), seg))
    if seg[:1] in _SMALL_REAR_CLOSURES and seg[1:2] in _CLICKS:
        seg = _SMALL_REAR_CLOSURES[seg[0]] + TIES[0] + seg[1:]
    if seg in phone_features:
        return phone_features[seg]
    untied = seg.replace(TIES[1], TIES[0])
    if untied in phone_features:
        return phone_features[untied]

    start = 0
    while start < len(seg) and (seg[start] in PRE_DIACRITICS or (
            seg[start] in TIES and start and seg[start + 1:start + 2] in PRE_DIACRITICS)):
        start += 1
    pre_marks = [c for c in seg[:start] if c not in TIES]  # ᵑ͡ᵐ marks a labial-velar as ᵑᵐ does
    for end in range(len(seg), start, -1):
        base = seg[start:end]
        if base in phone_features and all(m in POST_DIACRITICS for m in seg[end:]):
            vec = phone_features[base]
            for marker in pre_marks:
                vec = _apply_pre(marker, vec, segment)
            for marker in seg[end:]:
                vec = _apply_if(_DIACRITICS[marker, "post"], vec, segment)
            return vec
    if TIES[0] in untied:
        parts = untied.split(TIES[0])
        if any(c in _CLICKS for part in parts for c in part):
            # A click tie is one velar or uvular letter, then the click (IPA Handbook, 2.5). The
            # click takes only voi and nas from that letter, so it may carry combining marks only.
            if len(parts) == 2 and parts[0][:1] in _CLICKS and parts[1][:1] in _REAR_CLOSURES:
                # The letter after the click reads as the letter before it: its combining marks
                # stay with it, a modifier letter after it goes with the click.
                letter = parts[1][:1] + "".join(takewhile(unicodedata.combining, parts[1][1:]))
                return vectorize_phones(letter + TIES[0] + parts[0] + parts[1][len(letter):])
            rear_letter = parts[0][0] in _REAR_CLOSURES and all(map(unicodedata.combining, parts[0][1:]))
            if len(parts) != 2 or not rear_letter or parts[1][0] not in _CLICKS:
                raise _unrecognized(segment)
            rear, click = (vectorize_phones(part) for part in parts)
            out = list(click)
            out[_VOI], out[_NAS] = rear[_VOI], rear[_NAS]
            return tuple(out)
        try:
            return compose_tie([vectorize_phones(part) for part in parts])
        except ValueError:
            pass
    if start:
        try:
            vec = vectorize_phones(seg[start:])
        except ValueError:
            raise _unrecognized(segment) from None
        for marker in pre_marks:
            vec = _apply_pre(marker, vec, segment)
        return vec
    if seg and TIES[0] not in untied:
        clusters: List[str] = []  # a character and the combining marks after it
        for c in seg:
            if clusters and unicodedata.combining(c):
                clusters[-1] += c
            else:
                clusters.append(c)
        tied = clusters[0]
        for before, cluster in zip(clusters, clusters[1:]):
            joins = (unicodedata.category(cluster[0]) in _LETTER_CATEGORIES and cluster != before
                     and not _GLOTTALS & {cluster[0], before[0]}
                     and not (cluster[0] in _REAR_CLOSURES and _CLICKS.intersection(tied))
                     and (cluster[0] not in _CLICKS or before[0] in _REAR_CLOSURES))
            tied += (TIES[0] if joins else "") + cluster
        if tied != seg:
            return vectorize_phones(tied)
    raise _unrecognized(segment, ": a diphthong is two segments, a vowel and a non-syllabic vowel" if _is_diphthong(seg) else "")


_NAS, _SON, _CONT, _DELREL, _SG, _CG, _VOI = (
    _INDEX[f] for f in ("nas", "son", "cont", "delrel", "sg", "cg", "voi"))
#: Articulators: in a double articulation each one the parts use is used.
_ARTICULATORS = {_INDEX[f] for f in ("lab", "cor", "hi", "back")}


def _tie(first: Vector, second: Vector) -> Vector:
    def stop(v: Vector) -> bool:
        return v[_SON] is False and v[_CONT] is False

    def nasal(v: Vector) -> bool:
        return v[_NAS] is True and v[_CONT] is False

    out = list(second)
    if nasal(first) and second[_SON] is False:
        out[_NAS] = True  # prenasalized, as ᵐb
    elif stop(first) and second[_SON] is False and second[_CONT] is True:
        out[_CONT], out[_DELREL] = False, True  # affricate: the fricative with a stop onset
        for i in (_SG, _CG):
            out[i] = True if True in (first[i], second[i]) else second[i]
    elif (stop(first) and stop(second)) or (nasal(first) and nasal(second)):
        out = [x if x == y else y if x is None else x if y is None  # double, as k͡p
               else True if i in _ARTICULATORS else None
               for i, (x, y) in enumerate(zip(first, second))]
    else:
        raise ValueError("a tie of these parts has no reading")
    return tuple(out)


def compose_tie(parts: List[Vector]) -> Vector:
    """The vector of tied segments, from the vectors of the parts, right to left: a nasal before
    an obstruent prenasalizes it, a stop before a fricative makes an affricate with the glottal
    features of both, and two stops or two nasals make a double articulation: a feature one part
    leaves at 0 takes the other's value, an articulator either part uses is +, and other features
    the parts set apart are 0. Other ties, such as two vowels, raise ``ValueError``."""
    vec = parts[-1]
    for part in reversed(parts[:-1]):
        vec = _tie(part, vec)
    return vec


_HI, _LO = _INDEX["hi"], _INDEX["lo"]
_SIGN = {True: "+", False: "-", None: "0"}


def _apply_if(diacritic: dict, vec: Vector, segment: str) -> Vector:
    """Apply one diacritic. A mark with a consonant reading sets its features on a base that
    matches the reading's class. [+high, +low] is impossible, so a mark that adds one keeps the
    other as the base has it."""
    conditions = diacritic["conditions"]
    if conditions and not any(
        all(vec[_INDEX[f]] is _VALUE[v] for f, v in cond.items()) for cond in conditions
    ):
        raise ValueError(f"{diacritic['marker']!r} does not apply to the base of {segment!r}")
    out = list(vec)
    for f, v in diacritic["content"].items():
        out[_INDEX[f]] = _VALUE[v]
    for reading in diacritic.get("consonant", ()):
        if all(out[_INDEX[f]] is _VALUE[v] for f, v in reading["when"].items()):
            for f, v in reading["set"].items():
                out[_INDEX[f]] = _VALUE[v]
            break
    if "shift" in diacritic:
        signs = {f: _SIGN[v] for f, v in zip(FEATURES, out)}
        shift(signs, diacritic["shift"])
        out = [_VALUE[signs[f]] for f in FEATURES]
    if out[_HI] is True and out[_LO] is True:
        out[_LO if vec[_HI] is True else _HI] = False
    return tuple(out)


def _apply_pre(marker: str, vec: Vector, segment: str) -> Vector:
    """Apply a mark written before its base. A nasal mark on an obstruent adds [+nasal] to it, as
    a nasal tied before the obstruent does: prenasalized stops, affricates and fricatives. The
    glottal continuants h and ɦ are approximants, which are never prenasalized. Nor is a glottalic
    consonant (an ejective, an implosive or ʔ, all [+cg])."""
    base = segment.lstrip("".join(PRE_DIACRITICS))[:1]
    nasal = PRE_DIACRITICS[marker][0] == "ⁿ"
    if nasal and (base in _IMPLOSIVES or "ʼ" in segment):
        raise _unrecognized(segment)
    if nasal and vec[_SON] is False and base not in _GLOTTALS:
        return tuple(True if i == _NAS else x for i, x in enumerate(vec))
    return _apply_if(_DIACRITICS[PRE_DIACRITICS[marker]], vec, segment)


def is_vowel_phone(segment: str) -> bool:
    """True for a syllabic segment."""
    try:
        return vectorize_phones(segment)[0] is True
    except ValueError:
        return False


@lru_cache(maxsize=4096)
def _signs(segment: str) -> Tuple[float, ...]:
    """The vector of *segment* with + = 1, 0 = 0 and − = −1. A tone pitch stays a number."""
    return tuple(value if type(value) is float else _NUMBER[value] for value in vectorize_phones(segment))


#: Unread segments that have already raised their warning in this process.
_WARNED: set = set()
_WARNED_LOCK = threading.Lock()


@lru_cache(maxsize=65536)
def feature_distance(a: str, b: str) -> float:
    """Weighted feature distance between two segments, from 0 (same features) to 1.

    Each feature contributes its weight times half the difference of its values, with
    + = 1, 0 = 0 and − = −1, so a +/− mismatch costs the full weight and a 0 against + or − costs
    half. A tone pitch is its number, from −1 to 1. The sum is divided by the total weight of the
    segment features, so a tone adds to the distance, and the result is capped at 1. A segment
    that cannot be read is at distance 1 from every other segment, and the first time it is
    priced in the process it issues a ``UserWarning`` that names it. A space matches only a space.
    """
    if a == b:
        return 0.0
    if a == " " or b == " ":
        return 1.0
    try:
        va, vb = _signs(a), _signs(b)
    except ValueError:
        for seg in (a, b):
            if seg in _WARNED:
                continue
            try:
                _signs(seg)
            except ValueError:
                with _WARNED_LOCK:
                    if seg in _WARNED:
                        continue
                    _WARNED.add(seg)
                points = " ".join(f"U+{ord(c):04X}" for c in seg)
                warnings.warn(f"Unrecognized phone {seg!r} ({points}) costs 1 against every other"
                              " segment; pass strict=True to raise instead", UserWarning, stacklevel=2)
        return 1.0
    diff = sum(w * abs(x - y) / 2 for w, x, y in zip(WEIGHTS, va, vb))
    return min(diff / _TOTAL_WEIGHT, 1.0)


def phonetic_distance(a: str, b: str) -> float:
    """Deprecated alias of :func:`feature_distance`."""
    warnings.warn(
        f"phonetic_distance is deprecated and will be removed in {VERSION_MAJOR + 1}.0.0; "
        "use feature_distance",
        DeprecationWarning,
        stacklevel=2,
    )
    return feature_distance(a, b)
