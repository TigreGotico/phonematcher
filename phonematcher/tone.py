"""Tone as a sequence of pitch levels, read from the IPA chart's tone letters and tone diacritics.

A tone is its own segment, written in tone letters after the syllable it belongs to: ``má`` and
``ma˦`` are both ``m``, ``a``, ``˦``. Levels run from 1 (extra low, ``˩``) to 5 (extra high, ``˥``).
"""
from typing import Optional, Tuple

#: Tone letters and their levels.
LEVELS = {"˩": 1, "˨": 2, "˧": 3, "˦": 4, "˥": 5}

#: Tone diacritics and the tone letters the IPA chart prints beside them.
DIACRITIC_TONES = {
    "\u030b": "˥", "\u0301": "˦", "\u0304": "˧", "\u0300": "˨", "\u030f": "˩",
    "\u030c": "˩˥", "\u0302": "˥˩", "\u1dc4": "˧˥", "\u1dc5": "˩˧", "\u1dc8": "˧˦˨",
}

#: Tone numerals, written as superscript digits: the digit is the level. The left-stem tone
#: letters U+A712 to U+A716 have the same levels as the tone letters.
NUMERALS = {"¹": "˩", "²": "˨", "³": "˧", "⁴": "˦", "⁵": "˥",
            "\ua712": "˥", "\ua713": "˦", "\ua714": "˧", "\ua715": "˨", "\ua716": "˩"}

#: Marks this module does not read: downstep and upstep, global rise and global fall, and the
#: neutral-tone numeral ⁰, which has no level.
PHRASE_MARKS = frozenset("ꜜꜛ↗↘↓↑⁰")

_POINTS = 3


def is_tone(segment: str) -> bool:
    """True for a segment made only of tone letters."""
    return bool(segment) and all(ch in LEVELS for ch in segment)


def tone_levels(segment: str) -> Optional[Tuple[int, ...]]:
    """The levels of a tone segment, or None for a segment that is not a tone."""
    return tuple(LEVELS[ch] for ch in segment) if is_tone(segment) else None


def _contour(levels: Tuple[int, ...]) -> Tuple[float, ...]:
    """The pitch at the start, middle and end of the syllable, by linear interpolation."""
    if len(levels) == 1:
        return (float(levels[0]),) * _POINTS
    out = []
    for k in range(_POINTS):
        x = k * (len(levels) - 1) / (_POINTS - 1)
        i = min(int(x), len(levels) - 2)
        out.append(levels[i] + (levels[i + 1] - levels[i]) * (x - i))
    return tuple(out)


def tone_distance(a: str, b: str) -> float:
    """The mean pitch difference of two tones at the start, middle and end of the syllable,
    divided by the range of four steps, so the result is from 0 to 1.

    Experimental. On 15 Cantonese tone pairs it correlates with listener confusion at Spearman
    0.2475, against 0.7817 for a baseline that compares only the direction of the contour (issue
    #68, https://github.com/TigreGotico/phonematcher/issues/68).
    """
    for name, value in (("a", a), ("b", b)):
        if not isinstance(value, str):
            raise TypeError(f"tone_distance() argument {name} must be str, not {type(value).__name__}")
        if not is_tone(value):
            raise ValueError(f"tone_distance() argument {name} is not a tone: {value!r}")
    pa, pb = _contour(tone_levels(a)), _contour(tone_levels(b))
    return sum(abs(x - y) for x, y in zip(pa, pb)) / (4 * _POINTS)
