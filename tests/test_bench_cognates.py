"""Cognate detection benchmark: metrics, clustering and the guard on the test sets.

Hand values:

Average precision with tied scores. Scores 0.9, 0.8, 0.8, 0.1 with labels T, T, F, F: the first
score gives recall 1/2 at precision 1/1. The tie group of 0.8 holds one hit and one miss, so after
it hits are 2 and items are 3: recall gains 1/2 at precision 2/3. Total 1/2 + 1/3 = 5/6. Sorting
the tie as T before F would give 1.

Flat UPGMA on the matrix of the LingPy documentation (German 0, Swedish 1, Icelandic 2, English 3,
Dutch 4). German-Dutch at 0.2 merge first. Swedish-Icelandic at 0.4 merge second. English joins
German and Dutch at the mean of 0.8 and 0.3, which is 0.55. Every other mean is above 0.55.

B-cubed with the five words of Table 5 in List et al. (2017): gold 1, 2, 2, 3, 3 and test 1, 1, 1, 2, 2
give precision (1/3 + 2/3 + 2/3 + 2/2 + 2/2) / 5 = 0.7333, recall 1 and F 0.846153.

Fixture for ``evaluate``: one concept with A pa (cognate set 1), B pat (1), C ku (2), D xu (2).
Levenshtein over segments, normalized by the longer word: A-B 1/3, C-D 1/2, every other pair 1.
Pairs: A-B and C-D are cognate. Levenshtein ranks both first, so average precision is 1. The
second system cannot read ``x``, so D is unread. On all words its C-D distance is 1, which ties
with four non-cognate pairs: 1/2 + 1/2 * 2/6 = 2/3. On the common words A, B, C only A-B is
cognate and it ranks first: 1. Clusters, Levenshtein: A-B merge at 1/3, C-D at 1/2, the two pairs
at 1. At threshold 0.50 the clusters are the gold sets, F 1. Second system on all words: A-B at
1/3, then every distance is 1; at threshold 0.34 the clusters are {A,B}, {C}, {D}: precision 1,
recall (1 + 1 + 1/2 + 1/2) / 4 = 3/4, F 6/7.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import run  # noqa: E402
import systems  # noqa: E402
from tasks import cognates  # noqa: E402


class NoX(systems.Levenshtein):
    """Levenshtein that cannot read the segment ``x``."""

    name = "no-x"

    def reads(self, segment):
        return segment != "x"


def clusters(labels):
    return sorted(sorted(np.flatnonzero(labels == label).tolist()) for label in set(labels.tolist()))


def test_average_precision_takes_tied_scores_as_one_threshold():
    value = cognates.average_precision([0.9, 0.8, 0.8, 0.1], [True, True, False, False])
    assert value == pytest.approx(5 / 6)


def test_average_precision_without_positives_is_zero():
    assert cognates.average_precision([0.5, 0.4], [False, False]) == 0.0


MATRIX = np.array(
    [
        [0.0, 0.5, 0.67, 0.8, 0.2],
        [0.5, 0.0, 0.4, 0.7, 0.6],
        [0.67, 0.4, 0.0, 0.8, 0.8],
        [0.8, 0.7, 0.8, 0.0, 0.3],
        [0.2, 0.6, 0.8, 0.3, 0.0],
    ]
)


@pytest.mark.parametrize(
    "threshold, expected",
    [
        (0.19, [[0], [1], [2], [3], [4]]),
        (0.2, [[0, 4], [1], [2], [3]]),
        (0.45, [[0, 4], [1, 2], [3]]),
        (0.54, [[0, 4], [1, 2], [3]]),
        (0.56, [[0, 3, 4], [1, 2]]),
    ],
)
def test_flat_upgma_merges_while_the_mean_is_at_most_the_threshold(threshold, expected):
    assert clusters(cognates.flat_upgma(MATRIX, [threshold])[0]) == expected


def test_flat_upgma_joins_the_second_cluster_to_the_first_among_equal_distances():
    # A-B and B-C are both 0.5; the pair that comes first in cluster order merges: A and B.
    matrix = np.array([[0, 0.5, 0.9], [0.5, 0, 0.5], [0.9, 0.5, 0]])
    assert clusters(cognates.flat_upgma(matrix, [0.5])[0]) == [[0, 1], [2]]


def test_flat_upgma_of_one_word_is_one_cluster():
    assert cognates.flat_upgma(np.zeros((1, 1)), [0.5])[0].tolist() == [0]


def test_lingpy_order_lists_each_language_once_per_round_in_alphabetical_order():
    w = [cognates.Word("c", lang, (lang + str(i),), "1") for i, lang in enumerate(["b", "b", "a"])]
    assert [x.tokens[0] for x in cognates.lingpy_order(w)] == ["a2", "b0", "b1"]


def test_concepts_follow_the_lingpy_word_order():
    words = [cognates.Word("c", "b", ("m",), "1"), cognates.Word("c", "a", ("n",), "2"), cognates.Word("c", "b", ("m", "n"), "1")]
    [concept] = cognates.concepts_of(systems.Levenshtein(), words)
    assert concept.language.tolist() == [0, 1, 1]
    assert concept.distances[1, 2] == 0.5  # words m and m n, one insertion over the longer length 2


def test_bcubed_of_the_published_example():
    gold, test = np.array([1, 2, 2, 3, 3]), np.array([1, 1, 1, 2, 2])
    precision, recall = (x / 5 for x in cognates.bcubed(gold, test))
    assert precision == pytest.approx(0.7333, abs=1e-4)
    assert recall == pytest.approx(1.0)
    assert cognates.f_score(precision, recall) == pytest.approx(0.846153, abs=1e-6)


def test_bcubed_in_lingpy_counting_drops_a_second_word_of_one_language():
    # Gold set 0 holds words 0, 1 and 2; words 0 and 1 are one language. LingPy keeps words 0
    # and 2 of that set and, for the test sets, words 0 and 2 of set 0 and word 1 of set 1.
    gold, test, language = np.array([0, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1])
    p, r, pn, rn = cognates.bcubed_first_words(gold, test, language)
    assert (p / pn, r / rn) == (1.0, 1.0)
    per_word_recall = cognates.bcubed(gold, test)[1] / 3
    assert per_word_recall == pytest.approx(5 / 9)


WORDS = [
    cognates.Word("c", "A", ("p", "a"), "1"),
    cognates.Word("c", "B", ("p", "a", "t"), "1"),
    cognates.Word("c", "C", ("k", "u"), "2"),
    cognates.Word("c", "D", ("x", "u"), "2"),
]


@pytest.fixture(scope="module")
def report():
    built = {"levenshtein": systems.Levenshtein(), "no-x": NoX()}
    sets = {name: {"t": cognates.concepts_of(system, WORDS)} for name, system in built.items()}
    return cognates.evaluate(sets, ["t"])


def test_evaluate_average_precision(report):
    assert report["levenshtein"]["unread_at_1"]["average_precision"]["t"] == pytest.approx(1.0)
    assert report["no-x"]["unread_at_1"]["average_precision"]["t"] == pytest.approx(2 / 3)
    assert report["no-x"]["common"]["average_precision"]["t"] == pytest.approx(1.0)
    assert report["levenshtein"]["common"]["average_precision"]["t"] == pytest.approx(1.0)


def test_evaluate_bcubed(report):
    assert report["levenshtein"]["unread_at_1"]["threshold"] == pytest.approx(0.5)
    assert report["levenshtein"]["unread_at_1"]["bcubed_f"]["t"] == pytest.approx(1.0)
    assert report["no-x"]["unread_at_1"]["threshold"] == pytest.approx(0.34)
    assert report["no-x"]["unread_at_1"]["bcubed_f"]["t"] == pytest.approx(6 / 7)
    assert report["no-x"]["common"]["bcubed_f"]["t"] == pytest.approx(1.0)


def test_evaluate_gives_the_main_and_the_per_word_score(report):
    one = report["levenshtein"]["unread_at_1"]
    assert one["bcubed_f"]["t"] == pytest.approx(1.0)
    assert one["per_word"]["bcubed_f"]["t"] == pytest.approx(1.0)
    assert one["per_word"]["threshold"] == pytest.approx(0.5)


def test_evaluate_counts_words_and_pairs_in_and_out(report):
    assert report["no-x"]["skipped"] == {"words": {"t": 1}, "pairs": {"t": 3}, "pairs_in": {"t": 6}}
    assert report["levenshtein"]["skipped"]["words"] == {"t": 0}
    assert report["no-x"]["common"]["words_in"] == {"t": 4}
    assert report["no-x"]["common"]["words_out"] == {"t": 3}
    assert report["no-x"]["unread_at_1"]["words_out"] == {"t": 4}


def test_cluster_scores_count_by_lingpy_or_by_word():
    # Words a (language 1), z (language 1) and a (language 2) are one cognate set. At threshold 0.5 the
    # two a words merge and z stays alone: precision is 1 in both countings. Recall: LingPy keeps the
    # first word of each language, so words 0 and 2 only and recall is 1. Per word it is
    # (2/3 + 1/3 + 2/3) / 3 = 5/9, as in the test of ``bcubed_first_words``.
    words = [cognates.Word("c", "L1", ("a",), "1"), cognates.Word("c", "L1", ("z",), "1"), cognates.Word("c", "L2", ("a",), "1")]
    concepts = cognates.concepts_of(systems.Levenshtein(), words)
    assert cognates.cluster_scores(concepts, [0.5], "lingpy")[0].tolist() == [1.0, 1.0]
    assert cognates.cluster_scores(concepts, [0.5], "per_word")[0] == pytest.approx([1.0, 5 / 9])


def test_load_skips_comment_and_blank_lines(tmp_path):
    table = tmp_path / "D.tsv"
    table.write_text(
        "# Wordlist\n\n# DATA\nID\tDOCULECT\tCONCEPT\tIPA\tTOKENS\tCOGID\n#\n1\tAa\tI\tma\tm a\t7\n2\tBb\tI\tmi\tm i\t-8\n",
        encoding="utf8",
    )
    assert cognates.load(table) == [
        cognates.Word("I", "Aa", ("m", "a"), "7"),
        cognates.Word("I", "Bb", ("m", "i"), "-8"),
    ]


def test_load_can_drop_tone_tokens(tmp_path):
    table = tmp_path / "D.tsv"
    table.write_text("ID\tDOCULECT\tCONCEPT\tIPA\tTOKENS\tCOGID\n1\tAa\tI\tma\tm a ⁵⁵ ˥˩ ʰ\t7\n", encoding="utf8")
    assert cognates.load(table)[0].tokens == ("m", "a", "⁵⁵", "˥˩", "ʰ")
    assert cognates.load(table, drop_tones=True)[0].tokens == ("m", "a", "ʰ")


def test_a_data_set_with_no_common_word_is_left_out_of_the_common_scores():
    class OnlyP(systems.Levenshtein):
        name = "only-p"

        def reads(self, segment):
            return segment == "p"

    built = {"levenshtein": systems.Levenshtein(), "only-p": OnlyP()}
    sets = {name: {"t": cognates.concepts_of(system, WORDS), "u": cognates.concepts_of(system, WORDS[:2])} for name, system in built.items()}
    sets["only-p"]["t"] = cognates.concepts_of(built["only-p"], WORDS)
    result = cognates.evaluate(sets, ["t", "u"])
    assert result["only-p"]["common"] is None
    assert result["levenshtein"]["common"] is None
    assert result["levenshtein"]["unread_at_1"]["data_sets_scored"] == ["t", "u"]


@pytest.mark.parametrize("task", ["cognates", "cognates-toneless"])
def test_the_test_sets_do_not_run_without_final(tmp_path, task):
    with pytest.raises(SystemExit, match="--final"):
        run.main(["--task", task, "--system", "levenshtein", "--split", "test", "--cache", str(tmp_path)])
    assert not (tmp_path / "cognates").exists()


def test_the_training_and_test_sets_are_the_papers():
    assert [n.split("-")[0] for n in cognates.TRAINING] == ["Austronesian", "Bai", "Chinese", "IndoEuropean", "Japanese", "ObUgrian"]
    assert [n.split("-")[0] for n in cognates.TEST] == ["Bahnaric", "Chinese", "Huon", "Romance", "Tujia", "Uralic"]
