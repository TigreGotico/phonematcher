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
    vowels: a diphthong is two segments, a vowel and a non-syllabic vowel, so ``a͡i`` gives ``a``
    and ``i̯``, as ``ai̯`` does. Spaces become a
    ``" "`` segment between words; stress, syllable and phrase-tone marks are dropped. A tone is
    read as tone letters after its syllable: a tone diacritic or a tone numeral is written as tone
    letters after the segment that carries it. A tone diacritic on a tone letter adds its
    levels to that tone. A tone diacritic before a tie bar's second symbol, or at the start of a
    word, belongs to the next base symbol. A tie bar with no symbol before it in its word stays on
    the next segment, as in ``͡ǃ``, so it never joins across a space and the segment does not read. Format characters (Unicode category Cf, such as U+200B and
    U+FEFF) are dropped.

    A tone then moves onto the segment that carries it: the last vowel or syllabic consonant before
    it in the same word that carries no tone yet. ``ma˥`` gives ``m``, ``a˥``, and ``tam˧˧`` gives
    ``t``, ``a˧˧``, ``m``. A tone with no such segment stays a segment of tone letters, as in ``˥˩``
    and ``ɡ˩a``. A length mark or a combining mark written after a tone belongs to the vowel right before
    the tone, so ``a˥ː`` gives ``aː˥`` and ``a˥̃`` gives ``ã˥``.
    """
    return [unicodedata.normalize("NFC", s) for s in _segments(unicodedata.normalize("NFD", ipa).translate(SPELLINGS))[0]]


def segment_spans(text: str) -> List[Tuple[int, int]]:
    """The ``(start, end)`` offsets in *text* of its segments, in order.

    ``[text[s:e] for s, e in segment_spans(text)]`` are the segments as written in *text*: no
    spelling is rewritten and nothing is normalized. A character that :func:`segments` drops, and
    a space between words, falls in a gap between two spans. A tone diacritic stays in the span of
    the letter it is written on, and segments that share a character share one span, so the
    :func:`segments` of each span, in turn, are those of *text* without its spaces. That last
    property fails only on malformed input with a tone mark or a tie bar on a prenasal mark.
    """
    spans: List[Tuple[int, int]] = []
    chars = _characters(text)
    for seg, at in zip(*_segments("".join(ch for ch, _ in chars))):
        if seg == " ":
            continue
        where = [chars[k][1] for k in at]
        start, end = min(where), max(where) + 1
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


def _segments(nfd: str) -> Tuple[List[str], List[List[int]]]:
    """The segments of the NFD string *nfd*, and the positions in *nfd* of the characters of each."""
    out: List[str] = []
    at: List[List[int]] = []
    pending, pending_at = "", []  # marks written before the base they belong to
    tone, tone_at = "", []  # a tone diacritic, written out after the segment that carries it
    carried, carried_at = "", []  # a tone diacritic that belongs to the next base symbol
    join_next = False
    tie_at = -1  # the tie bar that sets join_next
    offglide = -1  # the index in out of the offglide of a tied diphthong, which holds its ◌̯
    level_kind = None  # the notation of the tone letter last written: Chao, left-stem or numeral

    def release_pending() -> None:
        """A held mark with no following base belongs to the segment before it, if any."""
        nonlocal pending, pending_at
        if pending:
            if out and out[-1] != " ":
                out[-1] += pending
                at[-1] += pending_at
            else:
                out.append(pending)
                at.append(pending_at)
            pending, pending_at = "", []

    def release_tone() -> None:
        nonlocal tone, tone_at
        if tone:
            out.append(tone)
            at.append(tone_at)
            tone, tone_at = "", []

    for i, raw in enumerate(nfd):
        ch = NUMERALS.get(raw, raw)
        if ch in SUPRASEGMENTALS or unicodedata.category(ch) == "Cf":
            continue
        if ch in DIACRITIC_TONES:
            letters = DIACRITIC_TONES[ch]
            if not out or out[-1] == " ":
                carried += letters
                carried_at.append(i)
            elif is_tone(out[-1]) and not tone:
                out[-1] += letters
                at[-1].append(i)
            else:
                tone += letters
                tone_at += (min(at[-1]), i)  # the span of a tone mark holds the letter it is on
            level_kind = None
            continue
        if ch in LEVELS:
            # A tone run ends where its notation changes: ˨˩˦꜔꜒ is the tone 214, then the tone 35.
            kind = 0 if raw in LEVELS else 1 if "\ua712" <= raw <= "\ua716" else 2
            same_notation = level_kind in (None, kind)
            level_kind = kind
            if tone:
                tone += ch
                tone_at.append(i)
                continue
            release_pending()
            if out and is_tone(out[-1]) and same_notation:
                out[-1] += ch
                at[-1].append(i)
            else:
                release_tone()
                out.append(ch)
                at.append([i])
            continue
        level_kind = None
        attaches = unicodedata.combining(ch) or ch in POST_DIACRITICS
        if not attaches:
            release_tone()
        if ch.isspace():
            tone += carried
            tone_at += carried_at
            carried, carried_at = "", []
            release_tone()
            release_pending()
            if out and out[-1] != " ":
                out.append(" ")
                at.append([i])
            continue
        if ch in TIES and pending:  # a tie between two marks before a base, as in ᵑ͡ᵐk͡p
            pending += ch
            pending_at.append(i)
            continue
        if ch in TIES:
            join_next = bool(out) and out[-1] != " "
            if join_next:
                carried, tone = carried + tone, ""
                carried_at, tone_at = carried_at + tone_at, []
                out[-1] += ch
                at[-1].append(i)
                tie_at = i
            else:  # a tie bar with no segment before it stays with the next one, which then does not read
                pending += ch
                pending_at.append(i)
            continue
        if join_next and out[-1][-1] in TIES and is_vowel_phone(out[-1][:-1].replace(NON_SYLLABIC, "")) and is_vowel_phone(ch):
            out[-1] = out[-1][:-1]
            if NON_SYLLABIC in out[-1] and offglide != len(out) - 1:  # a rising diphthong with its glide marked: i̯͡a
                out.append(ch)
            else:  # the second vowel of a tied diphthong is its offglide
                out.append(ch + NON_SYLLABIC)
                offglide = len(out) - 1
            at.append([tie_at, i])  # the tie bar is in both spans, so the diphthong is one span
            join_next = False
            continue
        if ch == NON_SYLLABIC and out and offglide == len(out) - 1:
            at[-1].append(i)
            continue
        if ch in PRE_DIACRITICS and not join_next:
            base = next((seg for seg in reversed(out) if not _split_tone_marks(seg)[0]), " ")  # a tone letter does not end the vowel
            if base == " " or is_vowel_phone(base):
                pending += ch
                pending_at.append(i)
                continue
        if not pending and out and out[-1] != " " and (attaches or join_next):
            out[-1] += ch
            at[-1].append(i)
            if join_next:
                at[-1].append(tie_at)
        else:
            out.append(pending + ch)
            at.append(pending_at + [i])
            pending, pending_at = "", []
            tone, carried = tone + carried, ""
            tone_at, carried_at = tone_at + carried_at, []
        join_next = False
    release_pending()
    tone += carried
    tone_at += carried_at
    release_tone()
    if out and out[-1] == " ":
        out.pop()
        at.pop()
    return _carry_tones(out, at)


def carry_tones(segs: Sequence[str]) -> List[str]:
    """*segs* with each tone moved onto the segment that carries it, as :func:`segments` does: the
    last vowel or syllabic consonant before the tone in its word that has no tone yet. A tone with
    no such segment stays a segment of its own. For a tokenizer whose own segments hold tones apart:
    ``carry_tones(["m", "a", "˥"])`` gives ``["m", "a˥"]``."""
    return _carry_tones(list(segs), [[] for _ in segs])[0]


def _split_tone_marks(seg: str) -> Tuple[str, str]:
    """The tone letters of *seg* and the length or combining marks written after them, as ``("˥", "ː")``
    for ``˥ː``. A segment of tone letters alone gives ``(seg, "")``. Any other segment, and a tone
    followed by any other mark, gives ``("", "")``."""
    n = 0
    while n < len(seg) and seg[n] in LEVELS:
        n += 1
    marks = seg[n:]
    if n and all(ch in "ːˑ" or "\u0300" <= ch <= "\u036f" for ch in marks):
        return seg[:n], marks
    return "", ""


def _tone_carrier(out: List[str], marks: str) -> Optional[int]:
    """The index in *out* of the last vowel or syllabic consonant of the word that has no tone yet,
    if a tone followed by *marks* can move onto it. A coda between them stops *marks*, which cannot
    join the vowel's span."""
    for j in reversed(range(len(out))):
        if out[j] == " " or out[j][-1] in LEVELS:  # a word boundary, a tone or a toned segment
            return None
        if marks and j != len(out) - 1:
            return None
        if is_vowel_phone(out[j]):
            return j
    return None


def _carry_tones(segs: List[str], at: List[List[int]]) -> Tuple[List[str], List[List[int]]]:
    """Move each tone of *segs* onto the segment that carries it, or leave it a segment of its own.
    A tone written right after its segment joins that segment's positions; a tone written after a
    coda is left out of them, so each segment keeps a span of its own. A length or combining mark
    written after the tone goes onto the vowel right before the tone; after a coda, the tone and
    its mark stay one segment."""
    out: List[str] = []
    out_at: List[List[int]] = []
    for seg, seg_at in zip(segs, at):
        tone, marks = _split_tone_marks(seg)
        j = _tone_carrier(out, marks) if tone else None
        if j is None:
            out.append(seg)
            out_at.append(seg_at)
            continue
        out[j] += marks + tone
        if j == len(out) - 1:
            out_at[j] = out_at[j] + seg_at
    return out, out_at


@lru_cache(maxsize=65536)
def substitution_cost(a: str, b: str) -> float:
    """Cost of replacing segment *a* by *b*, from 0 to 1, so a substitution never costs more than a
    deletion plus an insertion: the square root of the tone distance of two tone segments, 1 for a
    tone segment and a phone, and the square root of the feature distance of two phones, which
    holds the tone a phone carries. The square root keeps the
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


def _check_sequences(function: str, a: Sequence[str], b: Sequence[str], strict: bool) -> None:
    for name, value in (("a", a), ("b", b)):
        if not isinstance(value, (str, list, tuple)):
            raise TypeError(f"{function}() argument {name} must be a list of segments, not {type(value).__name__}")
    if strict:
        check_readable(a, " ".join(a))
        check_readable(b, " ".join(b))


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
    _check_sequences("edit_distance", a, b, strict)
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
    _check_sequences("align", a, b, strict)
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


def pairwise_distances(
    a: Sequence[str], b: Optional[Sequence[str]] = None, metric: str = "segment", *, strict: bool = False
) -> List[List[float]]:
    """The matrix of distances between the items of *a* and the items of *b*, for scikit-learn's
    ``metric="precomputed"``.

    With *metric* ``"segment"``, each item is one segment and each cell is
    :func:`~phonematcher.features.feature_distance`. With ``"word"``, each item is an IPA string and
    each cell is :func:`ipa_distance`. *a* and *b* are lists of items: a bare string raises
    ``TypeError``. With no *b*, the matrix is square and symmetric, with a zero diagonal, and each
    pair is computed once.

    With *strict*, an item that phonematcher cannot read raises ``ValueError`` that names it, as in
    :func:`ipa_distance`. Without it, such an item is at distance 1 from every other item.
    """
    for name, value in (("a", a), ("b", b)):
        if isinstance(value, str):
            raise TypeError(f"pairwise_distances() argument {name} must be a list of items, not str")
    distance = {"segment": feature_distance, "word": ipa_distance}.get(metric)
    if distance is None:
        raise ValueError(f"metric must be 'segment' or 'word', not {metric!r}")
    if strict:
        for item in (*a, *(b or ())):
            check_readable(segments(item) if metric == "word" else [item], item)
    if b is None:
        matrix = [[0.0] * len(a) for _ in a]
        for i, x in enumerate(a):
            for j in range(i + 1, len(a)):
                matrix[i][j] = matrix[j][i] = distance(x, a[j])
        return matrix
    return [[distance(x, y) for y in b] for x in a]
