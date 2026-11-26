"""Ordered scales of the IPA vowel chart, on which some diacritics move a vowel one step.

A vector here is a mapping from feature name to "+", "-" or "0". Heights run from close (row 0)
to open (row 6) through the step features h1 ... h6; columns run front, central, back through
[front] and [back]; rounding runs -, 0, + through [round] and [labial].
"""
from typing import Dict, MutableMapping

STEPS = tuple(f"h{k}" for k in range(1, 7))
COLUMNS = (("+", "-"), ("-", "-"), ("-", "+"))  # (front, back): front, central, back
ROUNDING = ("-", "0", "+")
MID = 3


def _clamp(value: int, top: int) -> int:
    return max(0, min(top, value))


def set_height(vec: MutableMapping[str, str], row: int) -> None:
    row = _clamp(row, len(STEPS))
    vec.update({s: "+" if row >= k else "-" for k, s in enumerate(STEPS, 1)})
    vec["hi"] = "+" if row <= 1 else "-"
    vec["lo"] = "+" if row >= 5 else "-"


def shift(vec: MutableMapping[str, str], moves: Dict[str, int]) -> None:
    """Move a chart vowel along the scales in *moves*; any other segment is left as it is.

    ``height`` moves the row (+1 is one row more open), ``toward_mid`` moves the row one step
    toward mid, ``column`` moves the column (+1 is one column further back), ``central`` sets the
    central column, and ``round`` moves the rounding (+1 is more rounded).
    """
    if vec.get("syl") != "+" or vec.get(STEPS[0], "0") == "0":
        return
    row = sum(vec[s] == "+" for s in STEPS)
    if "height" in moves:
        set_height(vec, row + moves["height"])
    if moves.get("toward_mid"):
        set_height(vec, row + (row < MID) - (row > MID))
    column = COLUMNS.index((vec["front"], vec["back"])) if (vec["front"], vec["back"]) in COLUMNS else 1
    if "column" in moves:
        vec["front"], vec["back"] = COLUMNS[_clamp(column + moves["column"], 2)]
    if moves.get("central"):
        vec["front"], vec["back"] = COLUMNS[1]
    if "round" in moves:
        step = ROUNDING[_clamp(ROUNDING.index(vec["round"]) + moves["round"], 2)]
        vec["round"] = vec["lab"] = step
