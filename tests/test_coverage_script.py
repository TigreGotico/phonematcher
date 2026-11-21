"""The coverage census counts what ``vectorize_phones`` reads.

The fixture is hand-counted: ``p``, ``aː``, ``ɡ`` and ``t͡ʃ`` are on the IPA chart (a consonant, a
long vowel, the voiced velar plosive and the voiceless postalveolar affricate), so they read. ``H``
is a capital Latin letter and ``#`` is a punctuation mark: neither is an IPA segment, so neither
reads. ``tʃ`` is two letters with no tie bar: it fails as written and reads only when a tie bar is
put between its two parts.
"""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "coverage.py"
_spec = importlib.util.spec_from_file_location("coverage_script", SCRIPT)
coverage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coverage)

#: segment -> tokens
FIXTURE = {"p": 10, "aː": 5, "ɡ": 3, "t͡ʃ": 2, "H": 4, "#": 1}


def test_census_counts_read_and_unread_segments():
    result = coverage.census(FIXTURE)
    # Read: p, aː, ɡ, t͡ʃ = 4 types and 10 + 5 + 3 + 2 = 20 tokens.
    # Unread: H (4 tokens) and # (1 token) = 2 types and 5 tokens. Total 6 types, 25 tokens.
    assert (result.distinct, result.read, result.read_by_tie) == (6, 4, 0)
    assert result.unread == {"H": 4, "#": 1}
    assert (result.tokens, result.tokens_read) == (25, 20)


def test_a_tie_bar_between_the_parts_reads_a_segment_that_fails_as_written():
    counts = {**FIXTURE, "tʃ": 7}
    plain = coverage.census(counts)
    assert plain.unread == {"H": 4, "#": 1, "tʃ": 7}
    retried = coverage.census(counts, tie_retry=True)
    # tʃ becomes t͡ʃ and reads: 4 read as written, 1 read after the tie bar, 2 unread.
    assert (retried.distinct, retried.read, retried.read_by_tie) == (7, 4, 1)
    assert retried.unread == {"H": 4, "#": 1}
    assert (retried.tokens, retried.tokens_read) == (32, 27)


def test_an_unread_segment_that_splits_into_readable_pieces_is_counted_apart():
    # ma˥ is the segment m, the segment a and the tone letter ˥: all read or are tones.
    result = coverage.census({"p": 1, "ma˥": 6, "H": 2})
    assert result.unread == {"ma˥": 6, "H": 2}
    assert (result.split_readable, result.tokens_split_readable) == (1, 6)
