"""The systems that the benchmark tasks compare.

Every system answers the same three questions about segments, given as strings:
``reads(segment)``, ``segment_distance(a, b)`` and ``word_distance(a, b, normalized)``, where a
word is a list of segments. ``word_distance`` raises ``UnreadSegment`` when a segment of either
word is outside the system's symbol set, so a task decides whether to skip the item or to score
it at distance 1. ``word_distance_or_one`` is the second choice.

Third-party packages are imported when a system is built, so a missing package is an
``ImportError`` at that point and never a silent skip.
"""
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

CLTS_URL = "https://github.com/cldf-clts/clts"
CLTS_TAG = "v2.3.1"

Word = Sequence[str]


class UnreadSegment(ValueError):
    """A word holds a segment that the system cannot read."""


def edit_distance(a: Word, b: Word, substitution: Callable[[str, str], float]) -> float:
    """Edit distance with the given substitution cost and unit deletion and insertion."""
    row = [float(j) for j in range(len(b) + 1)]
    for i, x in enumerate(a, start=1):
        prev, row[0] = row[0], float(i)
        for j, y in enumerate(b, start=1):
            prev, row[j] = row[j], min(row[j] + 1.0, row[j - 1] + 1.0, prev + substitution(x, y))
    return row[-1]


class System:
    """Base class: subclasses give ``reads``, ``segment_distance`` and ``_word_distance``."""

    name: str

    def reads(self, segment: str) -> bool:
        raise NotImplementedError

    def segment_distance(self, a: str, b: str) -> float:
        raise NotImplementedError

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        raise NotImplementedError

    def word_distance(self, a: List[str], b: List[str], normalized: bool = False) -> float:
        """Distance between two words. Raises ``UnreadSegment`` for a segment the system cannot read."""
        for segment in (*a, *b):
            if not self.reads(segment):
                raise UnreadSegment(f"{self.name} cannot read {segment!r}")
        return self._word_distance(a, b, normalized)

    def word_distance_or_one(self, a: List[str], b: List[str], normalized: bool = False) -> float:
        """The word distance, or 1.0 when either word holds an unread segment."""
        try:
            return self.word_distance(a, b, normalized)
        except UnreadSegment:
            return 1.0


def per_length(raw: float, a: Word, b: Word, normalized: bool) -> float:
    """Divide by the length of the longer word, as the normalized distance of every edit system."""
    if not normalized:
        return raw
    longest = max(len(a), len(b))
    return raw / longest if longest else 0.0


class PhoneMatcher(System):
    """This package: feature-weighted substitutions, unit deletion and insertion."""

    name = "phonematcher"

    def __init__(self):
        from phonematcher import edit_distance, phonetic_distance, vectorize_phones

        self._edit, self._distance, self._vectorize = edit_distance, phonetic_distance, vectorize_phones

    def reads(self, segment: str) -> bool:
        try:
            self._vectorize(segment)
        except ValueError:
            return False
        return True

    def segment_distance(self, a: str, b: str) -> float:
        return self._distance(a, b)

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        return per_length(self._edit(a, b), a, b, normalized)


class Levenshtein(System):
    """Unit costs over the same segments: a substitution of two different segments costs 1."""

    name = "levenshtein"

    def reads(self, segment: str) -> bool:
        return bool(segment)

    def segment_distance(self, a: str, b: str) -> float:
        return 0.0 if a == b else 1.0

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        return per_length(edit_distance(a, b, self.segment_distance), a, b, normalized)


class PanPhon(System):
    """PanPhon 0.22.2 edit distances, run on one feature vector per given segment.

    ``Distance.weighted_feature_edit_distance`` and ``hamming_feature_edit_distance`` segment a
    string themselves. Here each segment is looked up with ``FeatureTable.fts`` and the same
    ``Distance.min_edit_distance`` call runs on the vectors, so every system sees the same
    segments. The normalized distance divides by the longer word, as PanPhon's ``_div_maxlen``
    methods do.
    """

    def __init__(self, weighted: bool):
        from panphon.distance import Distance
        from panphon.segment import Segment

        self.name = "panphon-weighted" if weighted else "panphon-hamming"
        self._segment_type = Segment
        self._distance = Distance()
        self._weighted = weighted
        self._vectors: Dict[str, Optional[List[int]]] = {}

    def _vector(self, segment: str) -> Optional[List[int]]:
        if segment not in self._vectors:
            found = self._distance.fm.fts(segment)
            self._vectors[segment] = found.numeric() if isinstance(found, self._segment_type) else None
        return self._vectors[segment]

    def reads(self, segment: str) -> bool:
        return self._vector(segment) is not None

    def segment_distance(self, a: str, b: str) -> float:
        d = self._distance
        cost = d.weighted_substitution_cost if self._weighted else d.hamming_substitution_cost
        return cost(self._vector(a), self._vector(b))

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        d = self._distance
        if self._weighted:
            indel, sub = d.weighted_deletion_cost, d.weighted_substitution_cost
        else:
            indel, sub = (lambda v: 1), d.hamming_substitution_cost
        raw = d.min_edit_distance(
            indel, indel, sub, [[]], [self._vector(s) for s in a], [self._vector(s) for s in b]
        )
        return per_length(raw, a, b, normalized)


def downey(similarity: float, self_a: float, self_b: float, normalized: bool) -> float:
    """Turn an alignment similarity into a distance: the mean self-similarity minus the score,
    and for the normalized form that difference over the mean (Downey et al. 2008, as LingPy's
    ``distance=True``)."""
    mean = (self_a + self_b) / 2
    if not normalized:
        return mean - similarity
    return 1 - similarity / mean if mean else 0.0


class Aline(System):
    """ALINE as ported in ``nltk.metrics.aline``.

    ``aline.align`` returns only the best local alignments, with no score. The score of the first
    one is summed from the module's own ``sigma_skip``, ``sigma_sub`` and ``sigma_exp``. A segment
    is read when it is a key of ``aline.feature_matrix``, which holds ASCII ``g`` and no ``ɡ``.
    Words go in as lists, so an expansion pair has a list as one member and a segment never does.
    """

    name = "aline"

    def __init__(self):
        from nltk.metrics import aline

        self._aline = aline

    def reads(self, segment: str) -> bool:
        return segment in self._aline.feature_matrix

    def similarity(self, a: Word, b: Word) -> float:
        a, b = list(a), list(b)
        found = self._aline.align(a, b)
        if not found:
            return 0.0
        aline = self._aline
        total = 0.0
        for p, q in found[0]:
            if p == "-":
                total += aline.sigma_skip(q)
            elif q == "-":
                total += aline.sigma_skip(p)
            elif isinstance(q, list):
                total += aline.sigma_exp(p, q)
            elif isinstance(p, list):
                total += aline.sigma_exp(q, p)
            else:
                total += aline.sigma_sub(p, q)
        return float(total)

    def segment_distance(self, a: str, b: str) -> float:
        return self._word_distance([a], [b], True)

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        return downey(self.similarity(a, b), self.similarity(a, a), self.similarity(b, b), normalized)


class SoundVectors(System):
    """CLTS sound vectors (soundvectors 1.0 with pyclts and the BIPA transcription system).

    The CLTS data is cloned at a fixed tag into ``cache/clts-<tag>`` when it is missing. A segment
    is read when ``SoundVectors.get_vec`` returns without ``ValueError``. The segment distance is
    the share of the 39 vector positions that differ; deletion and insertion cost 1.
    """

    name = "soundvectors"

    def __init__(self, cache: Path):
        from pyclts import CLTS
        from soundvectors import SoundVectors as Vectors

        clone = Path(cache) / f"clts-{CLTS_TAG}"
        if not clone.exists():
            clone.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--depth", "1", "--branch", CLTS_TAG, CLTS_URL, str(clone)],
                check=True,
            )
        self._vectors = Vectors(ts=CLTS(str(clone)).bipa)
        self._seen: Dict[str, Optional[Tuple[int, ...]]] = {}

    def _vector(self, segment: str) -> Optional[Tuple[int, ...]]:
        if segment not in self._seen:
            try:
                self._seen[segment] = self._vectors.get_vec(segment)
            except ValueError:
                self._seen[segment] = None
        return self._seen[segment]

    def reads(self, segment: str) -> bool:
        return self._vector(segment) is not None

    def segment_distance(self, a: str, b: str) -> float:
        va, vb = self._vector(a), self._vector(b)
        return sum(x != y for x, y in zip(va, vb)) / len(va)

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        return per_length(edit_distance(a, b, self.segment_distance), a, b, normalized)


class Sca(System):
    """LingPy's SCA pairwise alignment (``lingpy.align.pairwise.Pairwise``, global mode).

    The score is the SCA similarity; the distance is derived as for ALINE. A segment is read when
    ``tokens2class`` maps it to an SCA class. SCA gives voiced and voiceless stops of one place
    one class, so ``p`` and ``b`` are at distance 0.
    """

    name = "sca"

    def __init__(self):
        import logging

        from lingpy.align.pairwise import Pairwise
        from lingpy.sequence.sound_classes import tokens2class

        logging.getLogger("lingpy").setLevel(logging.WARNING)
        self._pairwise, self._classes = Pairwise, tokens2class

    def reads(self, segment: str) -> bool:
        try:
            self._classes([segment], "sca")
        except ValueError:
            return False
        return True

    def similarity(self, a: Word, b: Word) -> float:
        if not a or not b:
            return 0.0
        pair = self._pairwise(list(a), list(b))
        pair.align(mode="global", distance=False)
        return float(pair.alignments[0][2])

    def segment_distance(self, a: str, b: str) -> float:
        return self._word_distance([a], [b], True)

    def _word_distance(self, a: Word, b: Word, normalized: bool) -> float:
        return downey(self.similarity(a, b), self.similarity(a, a), self.similarity(b, b), normalized)


def build(name: str, cache: Path) -> System:
    """Build one system by name. Raises ``ImportError`` when its package is missing."""
    factories: Dict[str, Callable[[], System]] = {
        "phonematcher": PhoneMatcher,
        "levenshtein": Levenshtein,
        "panphon-weighted": lambda: PanPhon(weighted=True),
        "panphon-hamming": lambda: PanPhon(weighted=False),
        "aline": Aline,
        "soundvectors": lambda: SoundVectors(cache),
        "sca": Sca,
    }
    if name not in factories:
        raise KeyError(f"unknown system {name!r}; known: {', '.join(NAMES)}")
    return factories[name]()


NAMES = ["phonematcher", "levenshtein", "panphon-weighted", "panphon-hamming", "aline", "soundvectors", "sca"]
