"""Distances between IPA strings, built on the segment distance in :mod:`phonematcher.features`."""
import unicodedata
from typing import List, Sequence

from phonematcher.features import POST_DIACRITICS, PRE_DIACRITICS, is_vowel_phone, phonetic_distance
from phonematcher.tone import DIACRITIC_TONES, LEVELS, NUMERALS, PHRASE_MARKS, is_tone, tone_distance

#: Stress, syllable and boundary marks: they carry no segment of their own.
SUPRASEGMENTALS = frozenset("ˈˌ.‿|‖") | PHRASE_MARKS

_TIES = ("͡", "͜")


def segments(ipa: str) -> List[str]:
    """Split *ipa* into segments.

    A segment is a base symbol with the diacritics and modifier letters that follow it. A tie bar
    joins the symbols on both sides into one segment, so ``t͡ʃ`` is one affricate. Spaces become a
    ``" "`` segment between words; stress, syllable and phrase-tone marks are dropped. A tone is
    one segment of tone letters after its syllable: a tone diacritic or a Chao numeral is written
    as tone letters after the segment that carries it.
    """
    out: List[str] = []
    join_next = False
    pending = ""  # marks written before the base they belong to

    def release_pending() -> None:
        """A held mark with no following base belongs to the segment before it, if any."""
        nonlocal pending
        if pending:
            if out and out[-1] != " ":
                out[-1] += pending
            else:
                out.append(pending)
            pending = ""

    tone = ""  # a tone diacritic, written out after the segment that carries it

    def release_tone() -> None:
        nonlocal tone
        if tone:
            out.append(tone)
            tone = ""

    for ch in unicodedata.normalize("NFD", ipa):
        ch = NUMERALS.get(ch, ch)
        if ch in SUPRASEGMENTALS:
            continue
        if ch in DIACRITIC_TONES and out and out[-1] != " ":
            tone += DIACRITIC_TONES[ch]
            continue
        if ch in LEVELS:
            release_pending()
            if out and is_tone(out[-1]) and not tone:
                out[-1] += ch
            else:
                release_tone()
                out.append(ch)
            continue
        if not (unicodedata.combining(ch) or ch in POST_DIACRITICS):
            release_tone()
        if ch.isspace():
            release_tone()
            release_pending()
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
    release_pending()
    release_tone()
    if out and out[-1] == " ":
        out.pop()
    return [unicodedata.normalize("NFC", s) for s in out]


def substitution_cost(a: str, b: str) -> float:
    """Cost of replacing segment *a* by *b*, from 0 to 1, so a substitution never costs more than a
    deletion plus an insertion: the tone distance of two tones, 1 for a tone and a phone, and the
    feature distance of two phones."""
    if is_tone(a) or is_tone(b):
        return tone_distance(a, b) if is_tone(a) and is_tone(b) else 1.0
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
