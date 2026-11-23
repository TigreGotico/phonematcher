"""The alignment task: parsing the gold files, the split, the scores and the run.

The fixture holds six pairs in ``full.psa`` and two in ``covington.psa``. The split keys are
``<file>:<index>``. ``is_test`` is ``int(sha1(key), 16) % 5 == 0``; sixteen is one more than a
multiple of five, so that remainder equals the sum of the sha1 hex digits modulo five. The sums
come from ``sha1sum`` and a shell loop, not from the code under test:

    full.psa:0 367 % 5 = 2 dev     full.psa:1 317 % 5 = 2 dev     full.psa:2 273 % 5 = 3 dev
    full.psa:3 265 % 5 = 0 test    full.psa:4 341 % 5 = 1 dev     full.psa:5 300 % 5 = 0 test
    covington.psa:0 292 % 5 = 2 dev     covington.psa:1 331 % 5 = 1 dev

So the dev split holds full 0, 1, 2, 4 and covington 0, 1 (six items); two items are left out.

Unit costs align by the rule "prefer a substitution, then a gap in the second word". Hand results:

* full 0: ``kat`` / ``kat`` aligns with no gap, as the gold does.
* full 1: ``pat`` / ``at``: the end ``t``/``t`` and ``a``/``a`` match, ``p`` is left against a gap. Gold equal.
* full 2: ``kat`` / ``kt``: ``t``/``t`` matches; ``a`` against ``k`` costs 1 + 1, a gap for ``a`` costs 1, so ``a`` is
  against a gap. Gold equal.
* full 4: ``ta`` / ``a``: the end ``a``/``a`` matches, so ``t`` is against a gap, columns (1,0) (2,1). The gold puts
  the gap last, columns (1,1) (2,0). No column is shared: perfect 0, column score 0.
* covington 0 and 1 equal the gold in the same way.

Column score of full 4 is 2 * 0 / (2 + 2) = 0, and for the others 1.
"""
import json
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import run  # noqa: E402
import systems  # noqa: E402
from tasks import alignment  # noqa: E402

FULL = """PairwiseGoldStandard
"one",(evobench_1/Andean)
Cuzco.	k	a	t
Sucre.	k	a	t
# 0.00

"two",(evobench_1/Andean)
Cuzco.	p	a	t
Sucre.	-	a	t
# 0.00

"three",(evobench_1/Andean)
Cuzco.	k	a	t
Sucre.	k	-	t
# 0.00

"four",(evobench_1/Andean)
Cuzco.	k	a	t
Sucre.	k	a	t
# 0.00

"five",(evobench_1/Andean)
Cuzco.	t	a
Sucre.	a	-
# 0.00

"six",(evobench_1/Andean)
Cuzco.	k	a	t
Sucre.	k	a	t
# 0.00
"""

COVINGTON = """Covington
yo/je
Spanish.	p	a	t
French..	-	a	t
# 4.0

x/y
Spanish.	☃	a
French..	-	a
# 4.0
"""


class Blind(systems.Levenshtein):
    """Unit costs, and a segment ``☃`` that it cannot read."""

    name = "blind"

    def reads(self, segment):
        return segment != "☃"


@pytest.fixture()
def cache(tmp_path):
    directory = tmp_path / "alignment" / f"SupplementaryMaterial-{alignment.SHA[:8]}" / "benchmark" / "psa"
    directory.mkdir(parents=True)
    (directory / "full.psa").write_text(FULL, encoding="utf8")
    (directory / "covington.psa").write_text(COVINGTON, encoding="utf8")
    return tmp_path


def test_parse_reads_two_rows_per_block_and_drops_the_header():
    pairs = alignment.parse(FULL)
    assert len(pairs) == 6
    assert pairs[1] == (["p", "a", "t"], ["-", "a", "t"])
    assert alignment.parse(COVINGTON)[1] == (["☃", "a"], ["-", "a"])


def test_the_dev_split_holds_the_keys_that_hash_to_dev(cache):
    items, left_out = alignment.load(cache / "alignment" / f"SupplementaryMaterial-{alignment.SHA[:8]}" / "benchmark" / "psa", "dev")
    assert [key for key, _, _ in items] == ["full.psa:0", "full.psa:1", "full.psa:2", "full.psa:4", "covington.psa:0", "covington.psa:1"]
    assert left_out == 2


def test_column_score_counts_shared_residue_pairs():
    # gold (1,1) (2,0) (3,2); test (1,1) (2,2) (3,0): one shared column of three each, 2 * 1 / 6
    gold = (["k", "a", "t"], ["k", "-", "t"])
    test = (["k", "a", "t"], ["k", "t", "-"])
    assert alignment.column_score(gold, test) == pytest.approx(1 / 3)
    assert alignment.column_score(gold, gold) == 1.0


def test_levenshtein_aligns_with_a_gap_where_the_hand_trace_puts_it():
    lev = systems.Levenshtein()
    assert lev.align(["p", "a", "t"], ["a", "t"]) == [("p", None), ("a", "a"), ("t", "t")]
    assert lev.align(["t", "a"], ["a"]) == [("t", None), ("a", "a")]


def test_an_unread_segment_stops_align():
    with pytest.raises(systems.UnreadSegment):
        Blind().align(["☃"], ["a"])


def test_phonematcher_align_returns_tone_numerals_as_given():
    pm = systems.build("phonematcher", Path("/nonexistent"))
    assert pm.align(["p", "a", "³³"], ["p", "a", "⁵⁵"]) == [("p", "p"), ("a", "a"), ("³³", "⁵⁵")]
    assert pm.align(["p", "a", "³³"], ["a", "³³"]) == [("p", None), ("a", "a"), ("³³", "³³")]
    with pytest.raises(systems.UnreadSegment):
        pm.align(["☃"], ["a"])


def test_phonematcher_reads_tones_as_the_library_reads_them():
    from phonematcher import ipa_distance

    pm = systems.build("phonematcher", Path("/nonexistent"))
    assert pm.reads("³³") and pm.reads("˧˧") and not pm.reads("⁰")
    # the library's own word path: a numeral and its tone letters are one tone, and ³³ and ⁵⁵ are not
    assert ipa_distance("a³³", "a˧˧") == 0
    assert pm.word_distance(["a", "³³"], ["a", "˧˧"]) == 0
    assert ipa_distance("a³³", "a⁵⁵") > 0
    assert pm.word_distance(["a", "³³"], ["a", "⁵⁵"]) == pytest.approx(ipa_distance("a³³", "a⁵⁵"))


def test_aline_alignment_is_global_with_the_ends_paired_off():
    aline = systems.build("aline", Path("/nonexistent"))
    assert aline.align(["p", "a"], ["p", "a"]) == [("p", "p"), ("a", "a")]
    # The local region is i p a. The s of one word and the t of the other lie outside it.
    assert aline.align(["s", "i", "p", "a"], ["i", "p", "a", "t"]) == [("s", None), ("i", "i"), ("p", "p"), ("a", "a"), (None, "t")]


def test_evaluate_and_summarize_on_the_dev_items(cache):
    items, _ = alignment.load(alignment.fetch(cache), "dev")
    lev, blind = systems.Levenshtein(), Blind()
    scores = {"levenshtein": alignment.evaluate(lev, items), "blind": alignment.evaluate(blind, items)}
    assert scores["levenshtein"]["full.psa:4"] == (0.0, 0.0)
    assert scores["blind"]["covington.psa:1"] is None
    keys = [key for key, _, _ in items]
    summary = alignment.summarize(scores, keys)
    assert summary["n_common"] == 5
    lev_row, blind_row = summary["systems"]["levenshtein"], summary["systems"]["blind"]
    assert (lev_row["n_in"], lev_row["n_scored"], lev_row["n_skipped"]) == (6, 6, 0)
    assert (blind_row["n_in"], blind_row["n_scored"], blind_row["n_skipped"]) == (6, 5, 1)
    assert lev_row["unread_at_zero_pas"] == pytest.approx(5 / 6)
    assert lev_row["common_pas"] == pytest.approx(4 / 5)
    assert blind_row["common_cs"] == pytest.approx(4 / 5)
    assert blind_row["unread_at_zero_pas"] == pytest.approx(4 / 6)


def test_run_writes_the_result_with_n_in_and_n_out(cache, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    status = run.main(["--task", "alignment", "--system", "levenshtein", "--cache", str(cache)], repo=repo)
    assert status == 0
    record = json.loads((cache / "results" / "alignment-dev.json").read_text(encoding="utf8"))
    assert not (repo / "benchmarks").exists()
    assert (record["n_in"], record["n_items"], record["n_left_out"]) == (8, 6, 2)
    assert record["data"]["sha"] == alignment.SHA
    row = record["all"]["systems"]["levenshtein"]
    assert (row["n_scored"], row["n_skipped"]) == (6, 0)
    assert row["common_pas"] == pytest.approx(5 / 6)
    assert record["by_file"]["full.psa"]["systems"]["levenshtein"]["common_pas"] == pytest.approx(3 / 4)
    assert record["by_file"]["covington.psa"]["systems"]["levenshtein"]["common_pas"] == 1.0


def test_the_test_split_is_refused_without_final(cache):
    with pytest.raises(SystemExit, match="only with --final"):
        run.main(["--task", "alignment", "--system", "levenshtein", "--split", "test", "--cache", str(cache)])
