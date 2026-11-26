"""Task C6, variant retrieval, on a tiny fixture.

Split keys are ``<language>:<word>``. ``sha1sum`` and a shell loop give ``int(hash, 16) % 5``:

    "en:cat"  2  dev
    "en:sun"  1  dev
    "en:dog"  0  test
    "en:fish" 0  test

Hand values for the ranks. Distances to four terms are 0.1, 0.3, 0.3 and 0.5 and the gold term is
the second: one term is closer (s=1) and two are tied (t=2). The gold term takes place 2 or 3 with
equal chance. Recall@1 is 0, recall@2 is 1/2, recall@10 is 1, and the mean reciprocal rank is
(1/2 + 1/3) / 2 = 5/12.

Levenshtein distances over segments, divided by the longer word: ``b a`` against ``p a`` is 1/2,
and ``b a`` against ``b a t`` is 1/3.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
sys.path.insert(0, str(BENCHMARKS / "tasks"))

import retrieval  # noqa: E402
import systems  # noqa: E402

A = {
    "cat": [("k", "a", "t")],
    "dog": [("d", "o", "g")],
    "fish": [("f", "i", "s")],
    "sun": [("s", "a", "n"), ("s", "u", "n")],
    "tree": [("t", "r", "i")],
}
B = {
    "cat": [("k", "a", "t")],
    "dog": [("d", "o", "k")],
    "fish": [("f", "i", "s")],
    "sun": [("s", "a", "n")],
    "tree": [("t", "r", "i", "i")],
    "moon": [("m", "u", "n")],
}


def test_load_tsv_keeps_pronunciations_in_file_order_without_repeats(tmp_path):
    path = tmp_path / "x.tsv"
    path.write_text("sun\ts a n\nsun\ts u n\nsun\ts a n\ncat\tk a t\nbad line\n", encoding="utf8")
    assert retrieval.load_tsv(path) == {"sun": [("s", "a", "n"), ("s", "u", "n")], "cat": [("k", "a", "t")]}


def test_items_are_shared_words_whose_dialect_b_reading_is_new():
    pair = retrieval.build_pair("en-US-UK", A, B, split="dev")
    # shared words: cat dog fish sun tree. cat and fish are equal; sun's B reading is among A's.
    # dog (d o k) and tree (t r i i) differ. dog is "en:dog" = test, tree is "en:tree" = 3 = dev.
    assert pair.counts["shared_words"] == 5
    assert pair.counts["same_pronunciations"] == 2
    assert pair.counts["b_within_a"] == 1
    assert pair.counts["item_words"] == 2
    assert pair.counts["items_in_other_split"] == 1
    assert pair.queries == [("tree", ("t", "r", "i", "i"))]
    test_pair = retrieval.build_pair("en-US-UK", A, B, split="test")
    assert test_pair.queries == [("dog", ("d", "o", "k"))]


def test_index_holds_every_reading_of_the_first_words_in_sorted_order():
    pair = retrieval.build_pair("en-US-UK", A, B, split="dev", cap=3)
    assert pair.words == ["cat", "dog", "fish"]
    assert pair.prons == [("k", "a", "t"), ("d", "o", "g"), ("f", "i", "s")]
    assert pair.owner == [0, 1, 2]
    assert pair.counts["items_outside_index_cap"] == 1  # tree is the fifth word
    assert pair.queries == []


def test_tie_rank_counts_closer_and_tied_terms():
    assert retrieval.tie_rank(np.array([0.1, 0.3, 0.3, 0.5]), 1) == (1, 2)


def test_recall_and_reciprocal_rank_share_the_ties():
    assert retrieval.recall_at(1, 1, 2) == 0
    assert retrieval.recall_at(2, 1, 2) == 0.5
    assert retrieval.recall_at(10, 1, 2) == 1
    assert retrieval.reciprocal_rank(1, 2) == pytest.approx(5 / 12)
    scores = retrieval.retrieval_scores([(1, 2), (0, 1)])
    assert scores["recall@1"] == 0.5
    assert scores["mrr"] == pytest.approx((5 / 12 + 1) / 2)


@pytest.fixture(scope="module")
def levenshtein():
    return systems.build("levenshtein", Path("unused"))


def pair_of(index, queries):
    """A pair whose index is *index* (word to readings, in sorted order) and whose queries are given."""
    words = sorted(index)
    return retrieval.Pair(
        "xx-A-B", words,
        [p for w in words for p in index[w]],
        [i for i, w in enumerate(words) for _ in index[w]],
        queries,
    )


def test_batched_distances_equal_the_hand_values(levenshtein):
    pair = pair_of({"pa": [("p", "a")], "bat": [("b", "a", "t")]}, [("pa", ("b", "a"))])
    engine = retrieval.Batched(levenshtein, pair)
    # index order: bat (b a t), pa (p a). Query b a: 1/3 to bat, 1/2 to pa.
    assert engine.prons_distance(("b", "a")) == pytest.approx([1 / 3, 1 / 2])
    assert engine.word_distances(("b", "a")) == pytest.approx([1 / 3, 1 / 2])


def test_a_word_with_two_readings_is_at_its_nearest_reading(levenshtein):
    a = {"sun": [("s", "a", "n"), ("s", "u", "n")], "tin": [("t", "i", "n")]}
    pair = pair_of(a, [("sun", ("s", "u", "m"))])
    engine = retrieval.Batched(levenshtein, pair)
    # sun: min(2/3 against s a n, 1/3 against s u n) = 1/3; tin: three substitutions, 3/3
    assert engine.word_distances(("s", "u", "m")) == pytest.approx([1 / 3, 1.0])


def test_an_unread_segment_is_at_distance_one():
    phonematcher = systems.build("phonematcher", Path("unused"))
    pair = pair_of({"pa": [("p", "a")], "bat": [("b", "a", "t")]}, [("pa", ("☃", "a"))])
    engine = retrieval.Batched(phonematcher, pair)
    assert engine.prons_distance(("☃", "a")).tolist() == [1.0, 1.0]
    assert engine.query_unread(("☃", "a"))


def test_brute_force_ranks_the_gold_word(levenshtein):
    a = {"bat": [("b", "a", "t")], "pa": [("p", "a")], "ta": [("t", "a")]}
    pair = pair_of(a, [("pa", ("b", "a"))])
    record = retrieval.brute_force(levenshtein, pair, [0])
    # query b a: bat 1/3, pa 1/2, ta 1/2. Gold pa is tied with ta: s=1, t=2.
    assert (record["s"], record["t"], record["unread"]) == ([1], [2], [False])
    assert record["pairs_checked"] > 0


def test_brute_force_flags_an_item_with_an_unread_query():
    phonematcher = systems.build("phonematcher", Path("unused"))
    a = {"pa": [("p", "a")], "ta": [("t", "a")]}
    pair = pair_of(a, [("pa", ("☃", "a"))])
    record = retrieval.brute_force(phonematcher, pair, [0])
    assert (record["s"], record["t"], record["unread"]) == ([0], [2], [True])


def test_sample_is_fixed_sorted_and_whole_when_small():
    queries = list(range(2000))
    first = retrieval.sample_queries(queries, 500)
    assert first == retrieval.sample_queries(queries, 500)
    assert len(first) == 500 and first == sorted(first) and len(set(first)) == 500
    assert retrieval.sample_queries(queries[:30], 500) == list(range(30))


def test_fuzzy_search_never_recalls_more_than_it_finds():
    a = {"bat": [("b", "a", "t")], "pa": [("p", "a")], "ta": [("t", "a")]}
    pair = pair_of(a, [("pa", ("b", "a")), ("bat", ("b", "a"))])
    for sensitivity in retrieval.SENSITIVITIES:
        row = retrieval.fuzzy_search(pair, range(len(pair.queries)), sensitivity)
        assert row["n"] == len(pair.queries) == 2
        assert row["top1"] <= row["candidate_hits"] <= row["n"]
        assert row["candidates"] >= row["candidate_hits"]


def test_fuzzy_search_finds_an_exact_reading():
    a = {"ma": [("m", "a")], "ta": [("t", "a")]}
    pair = pair_of(a, [("ma", ("m", "a"))])
    row = retrieval.fuzzy_search(pair, [0], 0.0)
    assert (row["candidate_hits"], row["top1"]) == (1, 1.0)


def test_aggregate_scores_common_subset_without_unread_items(tmp_path):
    folder = tmp_path / "C6"
    folder.mkdir()
    counts = {"queries": 3}

    def write(system, s, t, unread, sample=None):
        record = {"pair": "en-US-UK", "system": system, "counts": counts, "sample": sample, "queries_in": 3,
                  "brute": {"index": [0, 1, 2], "s": s, "t": t, "unread": unread, "pairs_checked": 1},
                  "brute_seconds": 1.0}
        (folder / f"ranks-dev-{system}-en-US-UK.json").write_text(json.dumps(record))

    write("phonematcher", [0, 0, 5], [1, 1, 1], [False, False, False])
    write("levenshtein", [0, 1, 0], [1, 1, 1], [False, False, True])
    result = retrieval.aggregate(tmp_path, "dev", names=["phonematcher", "levenshtein"])
    pair = result["pairs"]["en-US-UK"]
    assert pair["common_queries"] == 2  # query 2 is unread for levenshtein
    assert pair["systems"]["phonematcher"]["common_subset"]["recall@1"] == 1.0
    assert pair["systems"]["levenshtein"]["common_subset"]["recall@1"] == 0.5
    assert pair["systems"]["levenshtein"]["skipped_unread"] == 1
    assert pair["systems"]["phonematcher"]["all_items_unread_at_1"]["recall@1"] == pytest.approx(2 / 3)
    assert result["source"]["sha"] == retrieval.WIKIPRON_SHA


def test_a_diphthong_given_as_one_segment_is_two_segments_for_phonematcher():
    phonematcher = systems.build("phonematcher", Path("unused"))
    pair = pair_of({"tai": [("t", "aɪ")], "ta": [("t", "a")]}, [("tai", ("t", "a", "ɪ"))])
    engine = retrieval.Batched(phonematcher, pair)
    # index order: ta, tai. t a ɪ against t a ɪ (from t aɪ) is 0; against t a it is one insertion, 0.5 over 3.
    assert engine.word_distances(("t", "a", "ɪ")) == pytest.approx([1 / 6, 0.0])
    assert engine.check(pair) > 0


def test_a_sample_above_the_cap_raises_instead_of_shrinking():
    queries = list(range(5000))
    with pytest.raises(ValueError, match="at most 500"):
        retrieval.sample_queries(queries, 1000)
    assert len(retrieval.sample_queries(queries, 500)) == 500


def test_a_smaller_sample_is_inside_the_larger_one():
    queries = list(range(700))
    assert set(retrieval.sample_queries(queries, 100)) <= set(retrieval.sample_queries(queries, 500))
    assert len(retrieval.sample_queries(queries, 100)) == 100


def test_aggregate_scores_the_subset_that_the_full_run_systems_read(tmp_path):
    folder = tmp_path / "C6"
    folder.mkdir()

    def write(system, indices, s, unread, sample):
        record = {"pair": "en-US-UK", "system": system, "counts": {}, "sample": sample, "queries_in": 3,
                  "brute": {"index": indices, "s": s, "t": [1] * len(s), "unread": unread, "pairs_checked": 1},
                  "brute_seconds": 1.0}
        (folder / f"ranks-dev-{system}-en-US-UK.json").write_text(json.dumps(record))

    write("phonematcher", [0, 1, 2], [0, 1, 0], [False, False, False], None)
    write("levenshtein", [0, 1, 2], [0, 0, 0], [False, False, False], None)
    write("aline", [1], [0], [True], 1)  # ALINE scored query 1 only
    pair = retrieval.aggregate(tmp_path, "dev", names=["phonematcher", "levenshtein", "aline"])["pairs"]["en-US-UK"]
    assert pair["common_queries"] == 0
    assert pair["common_full_run_queries"] == 3
    assert pair["systems"]["phonematcher"]["common_full_run_subset"]["recall@1"] == pytest.approx(2 / 3)
    assert pair["systems"]["aline"]["common_full_run_subset"]["n"] == 1  # only query 1 was scored for ALINE
