"""Distances between IPA strings, built on the segment distance in :mod:`phonematcher.features`."""
import math
import unicodedata
from functools import lru_cache
from typing import Callable, List, Optional, Sequence, Tuple

from phonematcher.features import POST_DIACRITICS, PRE_DIACRITICS, SPELLINGS, TIES, feature_distance, is_vowel_phone, phonetic_distance, vectorize_phones  # noqa: F401 (deprecated path)
from phonematcher.tone import DIACRITIC_TONES, LEVELS, NUMERALS, PHRASE_MARKS, is_tone, tone_distance

#: Stress, syllable and boundary marks: they carry no segment of their own.
SUPRASEGMENTALS = frozenset("ˈˌ.‿|‖") | PHRASE_MARKS

#: Cost of one deletion or insertion.
GAP_COST = 0.5

NON_SYLLABIC = "\u032f"


def segments(ipa: str) -> List[str]:
    """Split *ipa* into segments.

    A segment is a base symbol with the diacritics and modifier letters that follow it. A tie bar
    joins the symbols on both sides into one segment, so ``t͡ʃ`` is one affricate, unless both are
    vowels: a diphthong is two segments, so ``a͡i`` gives ``a`` and ``i``. Spaces become a
    ``" "`` segment between words; stress, syllable and phrase-tone marks are dropped. A tone is
    one segment of tone letters after its syllable: a tone diacritic or a tone numeral is written
    as tone letters after the segment that carries it. A tone diacritic on a tone letter adds its
    levels to that tone. A tone diacritic before a tie bar's second symbol, or at the start of a
    word, belongs to the next base symbol. A tie bar with no symbol before it in its word is dropped,
    so it never joins across a space. Format characters (Unicode category Cf, such as U+200B and
    U+FEFF) are dropped.
    """
    return [unicodedata.normalize("NFC", s) for s in _segments(unicodedata.normalize("NFD", ipa).translate(SPELLINGS))[0]]


def segment_spans(text: str) -> List[Tuple[int, int]]:
    """The ``(start, end)`` offsets in *text* of its segments, in order.

    ``[text[s:e] for s, e in segment_spans(text)]`` are the segments as written in *text*: no
    spelling is rewritten and nothing is normalized. A character that :func:`segments` drops, and
    a space between words, falls in a gap between two spans. A tone diacritic stays in the span of
    the letter it is written on, and segments that share a character share one span, so the
    :func:`segments` of each span, in turn, are those of *text* without its spaces.
    """
    spans: List[Tuple[int, int]] = []
    chars = _characters(text)
    for seg, at in zip(*_segments("".join(ch for ch, _ in chars), track=True)):
        if seg == " ":
            continue
        start, end = min(chars[k][1] for k in at), max(chars[k][1] for k in at) + 1
        while spans and start < spans[-1][1]:  # a segment written before one already emitted
            first, last = spans.pop()
            start, end = min(start, first), max(end, last)
        spans.append((start, end))
    return spans


def _characters(ipa: str) -> List[Tuple[str, int]]:
    """The characters of the NFD form of *ipa* with spellings read as IPA, each with the index in
    *ipa* of the character it comes from."""
    chars = [(d, i) for i, c in enumerate(ipa) for d in unicodedata.normalize("NFD", c)]
    i = 0
    while i < len(chars):  # the canonical order of combining marks, as NFD sorts them
        j = i
        while j < len(chars) and unicodedata.combining(chars[j][0]):
            j += 1
        if j - i > 1:
            chars[i:j] = sorted(chars[i:j], key=lambda pair: unicodedata.combining(pair[0]))
        i = max(j, i + 1)
    return [(t, i) for d, i in chars for t in d.translate(SPELLINGS)]


def _segments(nfd: str, track: bool = False) -> Tuple[List[str], List[List[int]]]:
    """The segments of the NFD string *nfd*. With *track*, also the positions in *nfd* of the
    characters of each segment; without it, the second list is empty."""
    out: List[str] = []
    at: List[List[int]] = []  # with track: the positions of each segment, and of the held marks below
    pending_at, tone_at, carried_at = [], [], []
    join_next = False
    pending = ""  # marks written before the base they belong to

    def release_pending() -> None:
        """A held mark with no following base belongs to the segment before it, if any."""
        nonlocal pending, pending_at
        if pending:
            if out and out[-1] != " ":
                out[-1] += pending
                if track:
                    at[-1] += pending_at
            else:
                out.append(pending)
                if track:
                    at.append(pending_at)
            pending, pending_at = "", []

    tone = ""  # a tone diacritic, written out after the segment that carries it
    carried = ""  # a tone diacritic that belongs to the next base symbol

    def release_tone() -> None:
        nonlocal tone, tone_at
        if tone:
            out.append(tone)
            if track:
                at.append(tone_at)
            tone, tone_at = "", []

    for i, ch in enumerate(nfd):
        ch = NUMERALS.get(ch, ch)
        if ch in SUPRASEGMENTALS or unicodedata.category(ch) == "Cf":
            continue
        if ch in DIACRITIC_TONES and (not out or out[-1] == " "):
            carried += DIACRITIC_TONES[ch]
            if track:
                carried_at.append(i)
            continue
        if ch in DIACRITIC_TONES and is_tone(out[-1]) and not tone:
            out[-1] += DIACRITIC_TONES[ch]
            if track:
                at[-1].append(i)
            continue
        if ch in DIACRITIC_TONES:
            tone += DIACRITIC_TONES[ch]
            if track:
                tone_at += (min(at[-1]), i)  # the span of a tone mark holds the letter it is on
            continue
        if ch in LEVELS and tone:
            tone += ch
            if track:
                tone_at.append(i)
            continue
        if ch in LEVELS:
            release_pending()
            if out and is_tone(out[-1]):
                out[-1] += ch
                if track:
                    at[-1].append(i)
            else:
                release_tone()
                out.append(ch)
                if track:
                    at.append([i])
            continue
        attaches = unicodedata.combining(ch) or ch in POST_DIACRITICS
        if not attaches:
            release_tone()
        if ch.isspace():
            tone += carried
            carried = ""
            if track:
                tone_at += carried_at
                carried_at = []
            release_tone()
            release_pending()
            if out and out[-1] != " ":
                out.append(" ")
                if track:
                    at.append([i])
            continue
        if ch in TIES:
            join_next = bool(out) and out[-1] != " "
            if join_next:
                carried, tone = carried + tone, ""
                out[-1] += ch
                if track:
                    carried_at, tone_at = carried_at + tone_at, []
                    at[-1].append(i)
                    tie_at = i  # the tie bar that sets join_next
            continue
        if join_next and out[-1][-1] in TIES and is_vowel_phone(out[-1][:-1].replace(NON_SYLLABIC, "")) and is_vowel_phone(ch):
            out[-1] = out[-1][:-1]
            if track:
                at[-1].pop()
            join_next = False
        starts_word = not out or out[-1] == " "
        if ch in PRE_DIACRITICS and (starts_word or is_vowel_phone(out[-1])) and not join_next:
            pending += ch
            if track:
                pending_at.append(i)
            continue
        if not pending and out and out[-1] != " " and (attaches or join_next):
            out[-1] += ch
            if track:
                at[-1].append(i)
                if join_next:
                    at[-1].append(tie_at)
        else:
            out.append(pending + ch)
            pending = ""
            tone, carried = tone + carried, ""
            if track:
                at.append(pending_at + [i])
                pending_at = []
                tone_at, carried_at = tone_at + carried_at, []
        join_next = False
    release_pending()
    tone += carried
    if track:
        tone_at += carried_at
    release_tone()
    if out and out[-1] == " ":
        out.pop()
        if track:
            at.pop()
    return out, at


@lru_cache(maxsize=65536)
def substitution_cost(a: str, b: str) -> float:
    """Cost of replacing segment *a* by *b*, from 0 to 1, so a substitution never costs more than a
    deletion plus an insertion: the square root of the tone distance of two tones, 1 for a tone and
    a phone, and the square root of the feature distance of two phones. The square root keeps the
    cost a metric.
    """
    a_tone, b_tone = is_tone(a), is_tone(b)
    if a_tone and b_tone:
        return math.sqrt(tone_distance(a, b))
    if a_tone or b_tone:
        return 1.0
    return math.sqrt(feature_distance(a, b))


def check_readable(segs: Sequence[str], source: str) -> None:
    """Raise ``ValueError`` naming the first segment of *segs* that phonematcher cannot read.
    A space and a tone are always readable. *source* is the input the segments came from."""
    for seg in segs:
        if seg != " " and not is_tone(seg):
            try:
                vectorize_phones(seg)
            except ValueError:
                raise ValueError(f"cannot read the segment {seg!r} in {source!r}") from None


def _check_sequences(function: str, a: Sequence[str], b: Sequence[str]) -> None:
    for name, value in (("a", a), ("b", b)):
        if not isinstance(value, (str, list, tuple)):
            raise TypeError(f"{function}() argument {name} must be a list of segments, not {type(value).__name__}")


def edit_distance(
    a: Sequence[str],
    b: Sequence[str],
    *,
    strict: bool = False,
    substitution: Callable[[str, str], float] = substitution_cost,
    gap: float = GAP_COST,
) -> float:
    """Levenshtein distance between two segment sequences, with feature-weighted substitutions.

    Deletion and insertion cost ``GAP_COST``, 0.5. Pass the output of :func:`segments`, or call
    :func:`ipa_distance` on strings. A string is read as one segment per character, so it is not
    split into the segments of :func:`segments`.

    A segment that phonematcher cannot read is at distance 1 from every other segment. With *strict*, an unread segment raises ``ValueError`` instead. *substitution* and *gap*
    replace the cost of a substitution and of one deletion or insertion.
    """
    _check_sequences("edit_distance", a, b)
    if strict:
        check_readable(a, " ".join(a))
        check_readable(b, " ".join(b))
    row = [j * gap for j in range(len(b) + 1)]
    for i, seg in enumerate(a, start=1):
        prev, row[0] = row[0], i * gap
        for j in range(1, len(b) + 1):
            cur = min(row[j] + gap, row[j - 1] + gap, prev + substitution(seg, b[j - 1]))
            prev, row[j] = row[j], cur
    return row[-1]


def align(
    a: Sequence[str],
    b: Sequence[str],
    *,
    strict: bool = False,
    substitution: Callable[[str, str], float] = substitution_cost,
    gap: float = GAP_COST,
) -> List[Tuple[Optional[str], Optional[str]]]:
    """One least-cost alignment of two segment sequences, as pairs ``(left, right)``.

    ``None`` marks a gap. The costs, with *substitution* and *gap*, are those of
    :func:`edit_distance`. The traceback starts at the end and prefers a substitution, then a
    deletion (a gap in *b*), then an insertion, so the result is deterministic. Two costs are
    equal in the traceback when they differ by less than 1e-9 (``math.isclose`` with
    ``rel_tol=0`` and ``abs_tol=1e-9``). With *strict*, an unread segment raises ``ValueError``, as
    in :func:`edit_distance`.
    """
    _check_sequences("align", a, b)
    if strict:
        check_readable(a, " ".join(a))
        check_readable(b, " ".join(b))
    n, m = len(a), len(b)
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i * gap
    for j in range(1, m + 1):
        cost[0][j] = j * gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i][j] = min(
                cost[i - 1][j] + gap,
                cost[i][j - 1] + gap,
                cost[i - 1][j - 1] + substitution(a[i - 1], b[j - 1]),
            )
    pairs: List[Tuple[Optional[str], Optional[str]]] = []
    i, j = n, m
    while i or j:
        if i and j and math.isclose(
            cost[i][j], cost[i - 1][j - 1] + substitution(a[i - 1], b[j - 1]), rel_tol=0, abs_tol=1e-9
        ):
            pairs.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i and math.isclose(cost[i][j], cost[i - 1][j] + gap, rel_tol=0, abs_tol=1e-9):
            pairs.append((a[i - 1], None))
            i -= 1
        else:
            pairs.append((None, b[j - 1]))
            j -= 1
    pairs.reverse()
    return pairs


def ipa_distance(a: str, b: str, normalized: bool = False, *, strict: bool = False) -> float:
    """:func:`edit_distance` between two IPA strings.

    With *normalized*, the distance is divided by the segment count of the longer string, so it
    falls between 0 and 1. Two empty strings are at distance 0.

    A segment that phonematcher cannot read is at distance 1 from every other segment. With
    *strict*, it raises ``ValueError`` that names the segment and the string.
    """
    for name, value in (("a", a), ("b", b)):
        if not isinstance(value, str):
            raise TypeError(f"ipa_distance() argument {name} must be str, not {type(value).__name__}")
    sa, sb = segments(a), segments(b)
    if strict:
        check_readable(sa, a)
        check_readable(sb, b)
    dist = edit_distance(sa, sb)
    if not normalized:
        return dist
    longest = max(len(sa), len(sb))
    return dist / longest if longest else 0.0
