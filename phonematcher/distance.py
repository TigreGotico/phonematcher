"""Distances between IPA strings, built on the segment distance in :mod:`phonematcher.features`."""
import unicodedata
from typing import List, Sequence

from phonematcher.features import POST_DIACRITICS, PRE_DIACRITICS, is_vowel_phone, phonetic_distance

#: Stress, syllable and boundary marks: they carry no segment of their own.
SUPRASEGMENTALS = frozenset("ˈˌ.‿|‖")

_TIES = ("͡", "͜")


def segments(ipa: str) -> List[str]:
    """Split *ipa* into segments.

    A segment is a base symbol with the diacritics and modifier letters that follow it. A tie bar
    joins the symbols on both sides into one segment, so ``t͡ʃ`` is one affricate. Spaces become a
    ``" "`` segment between words; stress and syllable marks are dropped.
    """
    out: List[str] = []
    join_next = False
    pending = ""  # marks written before the base they belong to
    for ch in unicodedata.normalize("NFD", ipa):
        if ch in SUPRASEGMENTALS:
            continue
        if ch.isspace():
            if out and out[-1] != " ":
                out.append(" ")
            continue
        if ch in _TIES:
            join_next = bool(out)
            if join_next:
                out[-1] += ch
            continue
        starts_word = not out or out[-1] == " "
        if ch in PRE_DIACRITICS and (starts_word or is_vowel_phone(out[-1])) and not join_next:
            pending += ch
            continue
        attaches = unicodedata.combining(ch) or ch in POST_DIACRITICS
        if not pending and out and out[-1] != " " and (attaches or join_next):
            out[-1] += ch
        else:
            out.append(pending + ch)
            pending = ""
        join_next = False
    if pending:
        out.append(pending)
    if out and out[-1] == " ":
        out.pop()
    return [unicodedata.normalize("NFC", s) for s in out]


def substitution_cost(a: str, b: str) -> float:
    """Cost of replacing segment *a* by *b*: their feature distance, from 0 to 1, so a
    substitution never costs more than a deletion plus an insertion."""
    return phonetic_distance(a, b)


def edit_distance(a: Sequence[str], b: Sequence[str]) -> float:
    """Levenshtein distance between two segment sequences, with feature-weighted substitutions.

    Deletion and insertion cost 1. Pass the output of :func:`segments`, or call
    :func:`ipa_distance` on strings.
    """
    row = [float(j) for j in range(len(b) + 1)]
    for i, seg in enumerate(a, start=1):
        prev, row[0] = row[0], float(i)
        for j in range(1, len(b) + 1):
            cur = min(row[j] + 1.0, row[j - 1] + 1.0, prev + substitution_cost(seg, b[j - 1]))
            prev, row[j] = row[j], cur
    return row[-1]


def ipa_distance(a: str, b: str) -> float:
    """:func:`edit_distance` between two IPA strings."""
    return edit_distance(segments(a), segments(b))
