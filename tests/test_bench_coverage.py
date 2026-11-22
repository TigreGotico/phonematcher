"""C1: counting what a system reads.

Hand values. Counts a=3, b=1, c=2 give 3 types and 6 tokens. A system that reads a and b reads
2 of 3 types and 4 of 6 tokens. A second system that reads b and c shares only b with it: 1 type, 1 token.
``segments("ts")`` is ["t", "s"], so the tied retry reads "t͡s". ``segments("↓")`` is empty.
"""
import sys
from pathlib import Path
import types


sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_fake import Fake

from tasks import coverage  # noqa: E402

COUNTS = {"a": 3, "b": 1, "c": 2}


def test_census_counts_types_and_tokens():
    result = coverage.census(Fake("x", "ab"), COUNTS)
    assert (result["types"], result["types_read"], result["types_unread"]) == (3, 2, 1)
    assert (result["tokens"], result["tokens_read"]) == (6, 4)
    assert result["type_share"] == 2 / 3 and result["token_share"] == 4 / 6


def test_common_subset_is_what_every_system_reads():
    shared = coverage.common([Fake("x", "ab"), Fake("y", "bc")], COUNTS)
    assert shared == {"types_read_by_all": 1, "tokens_read_by_all": 1}


def test_tie_retry_reads_the_tied_form_only_when_asked():
    system = Fake("x", ["t͡s"])
    assert not coverage.reads(system, "ts")
    assert coverage.reads(system, "ts", tie_retry=True)


def test_an_empty_join_is_not_a_segment():
    system = Fake("x", [""])
    assert not coverage.reads(system, "↓", tie_retry=True)
    assert not coverage.reads(system, "")


def test_orthography2ipa_drops_the_stress_marks_and_keeps_bare_length_and_palatal(monkeypatch):
    registry = types.SimpleNamespace(available_codes=lambda: ["aa", "bb"], get=lambda code: code)
    inventories = {"aa": ["p", "ˈ", "ˌ", "ː"], "bb": ["p", "ˈ", "ʲ", "ˈa"]}
    package = types.ModuleType("orthography2ipa")
    package.registry = registry
    inventory = types.ModuleType("orthography2ipa.inventory")
    inventory.phoneme_inventory = lambda code: inventories[code]
    monkeypatch.setitem(sys.modules, "orthography2ipa", package)
    monkeypatch.setitem(sys.modules, "orthography2ipa.inventory", inventory)
    counts, specs = coverage.orthography2ipa_inventories()
    assert specs == 2
    assert counts == {"p": 2, "ː": 1, "ʲ": 1, "ˈa": 1}


def test_the_segments_only_rule_leaves_tones_to_the_system():
    # U+02E5 is the extra-high tone letter, ³³ is two superscript digits. p is a plain consonant.
    segments_only = coverage.SegmentsOnly()
    assert [segments_only.reads(x) for x in ("p", "˥", "˥˩", "³³", "☃")] == [True, False, False, False, False]
