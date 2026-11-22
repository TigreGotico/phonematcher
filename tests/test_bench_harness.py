"""The benchmark harness: the split, the systems and the guard on the test split.

Hand values:

``is_test`` is ``int(sha1(key), 16) % 5 == 0``. Sixteen is one more than a multiple of five, so
that remainder equals the sum of the key's sha1 hex digits modulo five. The digit sums below come
from ``sha1sum`` and a shell loop, not from the code under test.

    "x"       11f6ad8ec52a2984abaafd7c3b516503785c2072  digit sum 285  285 % 5 = 0  test
    "b"       e9d71f5ee7c92d6dc9e92ffdad17b8bd49418f98  digit sum 375  375 % 5 = 0  test
    "en:cat"  3c967e4015e1331b70cf2fa2ecde1068d43a347d  digit sum 282  282 % 5 = 2  dev
    "pt:gato" c2acd72829332e4e57234a2815427cdb82d94da2  digit sum 274  274 % 5 = 4  dev

``p`` and ``b`` differ in one feature, voicing, in PanPhon (+/- is two steps of one weight) and in
CLTS (one of 39 positions). ALINE gives voicing a salience of 5. The self-score of ``pa`` is
``35`` for ``p`` (C_sub 35, no vowel weight) plus ``25`` for ``a`` (35 - 5 - 5), 60; ``ba`` is 60
too; ``pa`` against ``ba`` scores ``30 + 25`` = 55, so the distance is 60 - 55 = 5.
"""
import subprocess
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import run  # noqa: E402
import split  # noqa: E402
import systems  # noqa: E402

from phonematcher import ipa_distance  # noqa: E402

CHECKED = [name for name in systems.NAMES if name != "sca"]
UNREAD = "☃"


@pytest.fixture(scope="module")
def built():
    return {name: systems.build(name, run.DEFAULT_CACHE) for name in CHECKED}


@pytest.mark.parametrize("key, expected", [("x", True), ("b", True), ("en:cat", False), ("pt:gato", False)])
def test_is_test_follows_the_hash_of_the_key(key, expected):
    assert split.is_test(key) is expected


@pytest.mark.parametrize("name", CHECKED)
def test_identical_words_are_at_distance_zero(built, name):
    assert built[name].word_distance(["p", "a"], ["p", "a"]) == 0
    assert built[name].word_distance(["p", "a"], ["p", "a"], normalized=True) == 0


@pytest.mark.parametrize("name", CHECKED)
def test_a_voicing_change_is_a_positive_distance(built, name):
    assert built[name].word_distance(["p", "a"], ["b", "a"]) > 0
    assert 0 < built[name].word_distance(["p", "a"], ["b", "a"], normalized=True) < 1


@pytest.mark.parametrize("name", CHECKED)
def test_segment_distance_is_zero_for_a_segment_against_itself(built, name):
    assert built[name].segment_distance("p", "p") == 0
    assert built[name].segment_distance("p", "b") > 0


def test_levenshtein_on_a_hand_case(built):
    # kitten -> sitting: k->s, e->i, insert g = 3 edits; the longer word has 7 segments.
    kitten, sitting = list("kitten"), list("sitting")
    assert built["levenshtein"].word_distance(kitten, sitting) == 3
    assert built["levenshtein"].word_distance(kitten, sitting, normalized=True) == 3 / 7


def test_phonematcher_system_uses_the_package_distance(built):
    assert built["phonematcher"].word_distance(["p", "a"], ["b", "a"]) == ipa_distance("pa", "ba")
    assert built["phonematcher"].word_distance(["p", "a"], ["b", "a"], True) == ipa_distance("pa", "ba", True)


def test_panphon_segment_distances_on_p_and_b(built):
    from panphon import FeatureTable

    table = FeatureTable()
    p, b = table.fts("p").numeric(), table.fts("b").numeric()
    differing = [name for name, x, y in zip(table.names, p, b) if x != y]
    assert differing == ["voi"]
    assert built["panphon-weighted"].segment_distance("p", "b") == 2 * table.weights[table.names.index("voi")]
    assert built["panphon-hamming"].segment_distance("p", "b") == 1 / len(table.names)


def test_soundvectors_differs_in_one_of_39_positions(built):
    assert built["soundvectors"].segment_distance("p", "b") == 1 / 39


def test_aline_distance_follows_the_hand_scores(built):
    assert built["aline"].similarity(["p", "a"], ["p", "a"]) == 60
    assert built["aline"].word_distance(["p", "a"], ["b", "a"]) == 5
    assert built["aline"].word_distance(["p", "a"], ["b", "a"], normalized=True) == pytest.approx(5 / 60)


@pytest.mark.parametrize("name", [n for n in CHECKED if n != "levenshtein"])
def test_a_word_with_an_unread_segment_raises_and_scores_one_when_asked(built, name):
    system = built[name]
    assert not system.reads(UNREAD)
    with pytest.raises(systems.UnreadSegment):
        system.word_distance(["p", UNREAD], ["p", "a"])
    assert system.word_distance_or_one(["p", UNREAD], ["p", "a"]) == 1.0


def test_aline_reads_the_ipa_g_as_the_ascii_g(built):
    aline = built["aline"]
    assert aline.reads("ɡ") and aline.reads("g")
    assert aline.word_distance(["ɡ", "a"], ["g", "a"]) == 0
    assert aline.word_distance(["ɡ", "a"], ["k", "a"]) == aline.word_distance(["g", "a"], ["k", "a"])


def test_aline_maps_the_ipa_g_and_nothing_else(built):
    # ALINE's symbol set has ASCII "g" only. These letters are also outside it and stay unread.
    assert systems.Aline.INPUT == {"ɡ": "g"}
    for letter in ("ʤ", "ʧ", "t͡ʃ", "ǥ"):
        assert not built["aline"].reads(letter)


@pytest.mark.parametrize("name", CHECKED)
def test_selfcheck_prints_one_line_for_the_system(name, capsys):
    assert run.main(["--task", "selfcheck", "--system", name, "--cache", str(run.DEFAULT_CACHE)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1 and lines[0].startswith(f"{name}: ")


def test_a_system_whose_package_is_missing_is_an_error(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "lingpy", None)
    assert run.main(["--task", "selfcheck", "--system", "sca"]) == 1
    assert "error: system sca" in capsys.readouterr().err


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org", *args],
        check=True, capture_output=True,
    )


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "f.txt").write_text("one\n")
    git(tmp_path, "add", "f.txt")
    git(tmp_path, "commit", "-q", "-m", "first")
    return tmp_path


def test_the_test_split_needs_final(repo):
    with pytest.raises(SystemExit, match="only with --final"):
        run.main(["--task", "selfcheck", "--system", "levenshtein", "--split", "test"], repo=repo)


def test_final_refuses_a_dirty_tree(repo):
    (repo / "f.txt").write_text("two\n")
    with pytest.raises(SystemExit, match="clean git tree"):
        run.main(["--task", "selfcheck", "--system", "levenshtein", "--split", "test", "--final"], repo=repo)


def test_final_refuses_an_untracked_file(repo):
    (repo / "new.txt").write_text("x\n")
    with pytest.raises(SystemExit, match="clean git tree"):
        run.commit_of_clean_tree(repo)


def test_a_clean_tree_gives_the_head_sha(repo):
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert run.commit_of_clean_tree(repo) == head


def test_final_on_a_clean_tree_still_runs_no_task_without_a_test_split(repo, capsys):
    with pytest.raises(SystemExit, match="has no test split"):
        run.main(["--task", "selfcheck", "--system", "levenshtein", "--split", "test", "--final"], repo=repo)
    assert capsys.readouterr().out == ""


def test_final_applies_to_the_test_split_only(repo):
    with pytest.raises(SystemExit, match="--split test only"):
        run.main(["--task", "selfcheck", "--system", "levenshtein", "--final"], repo=repo)


def test_a_result_file_records_split_and_commit(tmp_path):
    import json

    path = tmp_path / "out" / "t.json"
    run.write_result(path, {"score": 0.5}, "t", "levenshtein", "dev", None)
    assert json.loads(path.read_text(encoding="utf8")) == {
        "task": "t", "system": "levenshtein", "split": "dev", "commit": None, "score": 0.5,
    }
