"""The machinery of the single test run: pre-registration hash, candidates, bootstrap, decision rules
and the ``--final`` path. No test uses data of the test split; the ``--final`` path runs on tiny fixtures.

Hand values:

* C2 weights add up to 29: the 26 features that stay at 1, the six height steps at 1/6 (one in all)
  and front, back, round and lab at 1/2 (two in all).
* The table's weights add up to 9.5 and [voice] weighs 0.125, so p and b are 0.125 / 9.5 apart.
* Four units with scores 1, 1, 1, 0: a resample of four draws is the mean of k ones, k in 0..4.
  P(mean <= 0.25) = 0.25^4 + 4 * 0.75 * 0.25^3 = 0.0508 and P(mean = 0) = 0.0039, so the 2.5th
  percentile is 0.25. P(mean < 1) = 1 - 0.75^4 = 0.684, so the 97.5th percentile is 1.
* Average precision of the pooled pairs of two concepts: scores -0.1, -0.9 with labels T, F and
  scores -0.1, -0.2 with labels F, T. The two -0.1 tie: one threshold, 2 items, 1 hit, recall gain
  1/2, precision 1/2, giving 0.25. Then -0.2: 3 items, 2 hits, recall gain 1/2, precision 2/3,
  giving 0.3333. Total 0.5833.
"""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import final  # noqa: E402
import run  # noqa: E402
import variants  # noqa: E402
from systems import System  # noqa: E402
from tasks import cognates  # noqa: E402

REGISTERED = "29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c"


# ---- the pre-registration page


def test_the_committed_page_is_the_registered_one():
    assert hashlib.sha256((BENCHMARKS / "prereg-2.md").read_bytes()).hexdigest() == REGISTERED
    assert final.PREREG_SHA256 == REGISTERED


def test_the_run_reads_the_hash_from_the_page():
    assert final.prereg_sha256() == REGISTERED


def test_the_run_refuses_a_page_that_differs(tmp_path, monkeypatch):
    page = tmp_path / "prereg-2.md"
    page.write_bytes((BENCHMARKS / "prereg-2.md").read_bytes() + b" ")
    monkeypatch.setattr(final, "PREREG", page)
    with pytest.raises(SystemExit, match="not the registered"):
        final.prereg_sha256()


# ---- the candidates


def test_c1_weighs_every_feature_one():
    c1 = variants.build_variant("pm-C1")
    assert c1.segment_distance("p", "b") == pytest.approx(1 / 36)


def test_c2_gives_the_height_steps_a_sixth_and_the_pairs_a_half():
    weights = dict(zip(variants.features.FEATURES, variants.c2_weights()))
    assert [weights[f] for f in ("h1", "h6", "front", "back", "round", "lab", "voi", "syl")] == [1 / 6, 1 / 6, 0.5, 0.5, 0.5, 0.5, 1, 1]
    assert sum(weights.values()) == pytest.approx(29)
    assert variants.build_variant("pm-C2").segment_distance("p", "b") == pytest.approx(1 / 29)


def test_c3_is_c2_with_the_major_class_at_the_bisection_weight():
    c3 = variants.build_variant("pm-C3")
    weights = dict(zip(variants.features.FEATURES, c3.weights))
    assert [weights[f] for f in ("syl", "son", "cons")] == [variants.c3_weight()] * 3
    assert weights["voi"] == 1 and weights["h1"] == 1 / 6


def test_c3_weight_is_the_least_that_passes_k1_to_a_hundredth():
    weight = variants.c3_weight()
    assert weight == 1.38
    assert variants.k1(variants.Variant("at", weights=variants.with_major_class(weight)))
    assert not variants.k1(variants.Variant("below", weights=variants.with_major_class(weight - 0.01)))


def test_p4_halves_the_gap_cost_and_keeps_the_table():
    p4 = variants.build_variant("pm-P4")
    assert p4.word_distance(["p", "a"], ["a"]) == 0.5
    assert p4.word_distance(["p", "a"], ["a"], normalized=True) == 0.25
    assert p4.segment_distance("p", "b") == pytest.approx(0.125 / 9.5)


def test_p5_takes_the_square_root_of_every_substitution_and_halves_the_gap():
    p5 = variants.build_variant("pm-P5")
    assert p5.segment_distance("p", "b") == pytest.approx(math.sqrt(0.125 / 9.5))
    assert p5.word_distance(["p"], ["b"]) == pytest.approx(math.sqrt(0.125 / 9.5))
    assert p5.word_distance(["p", "a"], ["a"]) == 0.5


def test_the_library_is_the_winning_candidate():
    from phonematcher import ipa_distance, segments

    p5 = variants.build_variant("pm-P5")
    # p and b differ by 0.125 of the 9.5 weights, so the substitution costs sqrt(0.125 / 9.5);
    # the missing "a" costs 0.5 over a longer word of 2 segments.
    assert ipa_distance("pa", "ba") == pytest.approx(math.sqrt(0.125 / 9.5))
    assert ipa_distance("pa", "a") == 0.5
    assert ipa_distance("pa", "a", normalized=True) == 0.25
    for a, b in [("pa", "ba"), ("pa", "a"), ("pat", "bata"), ("ma˥", "ma˦")]:
        words = [list(segments(x)) for x in (a, b)]
        assert ipa_distance(a, b) == pytest.approx(p5.word_distance(*words), abs=1e-12)
        assert ipa_distance(a, b, normalized=True) == pytest.approx(p5.word_distance(*words, normalized=True), abs=1e-12)


def test_p5_takes_the_square_root_of_a_tone_substitution_too():
    from phonematcher.tone import tone_distance

    p5, c0 = variants.build_variant("pm-P5"), variants.Variant("c0")
    assert tone_distance("˥", "˩") > 0
    assert p5.segment_distance("˥", "˩") == pytest.approx(math.sqrt(tone_distance("˥", "˩")))
    assert p5.segment_distance("˥", "p") == 1.0
    assert c0.segment_distance("˥", "˩") == pytest.approx(tone_distance("˥", "˩"))


def test_the_candidates_are_the_five_of_the_page_and_each_builds():
    assert variants.CANDIDATES == ["pm-C1", "pm-C2", "pm-C3", "pm-P4", "pm-P5"]
    assert [variants.build_variant(n).name for n in variants.CANDIDATES] == variants.CANDIDATES


def test_k1_follows_weight_fit_for_each_candidate():
    # weight-fit.md: the table's weights pass K1; C1 and C2 fail; C3 passes by construction.
    assert variants.k1(variants.Variant("c0"))
    assert [variants.k1(variants.build_variant(n)) for n in variants.CANDIDATES] == [False, False, True, True, True]


class Chart(System):
    """Every vowel pair 0.3 apart and every vowel-obstruent pair 0.5 apart, except one pair given by hand."""

    name = "chart"

    def __init__(self, special=None, value=0.0):
        self.special, self.value = special, value

    def segment_distance(self, a, b):
        if {a, b} == self.special:
            return self.value
        return 0.3 if a in variants.chart_vowels() and b in variants.chart_vowels() else 0.5


def test_k1_holds_when_every_vowel_pair_is_nearer_than_every_vowel_obstruent_pair():
    assert variants.k1(Chart())


def test_k1_fails_when_one_vowel_and_one_obstruent_are_as_near_as_two_vowels():
    assert not variants.k1(Chart({"i", "ʔ"}, 0.3))
    assert variants.k1(Chart({"i", "ʔ"}, 0.31))


def test_the_chart_holds_28_vowels():
    assert len(variants.chart_vowels()) == 28


# ---- the bootstrap


def mean_of(values):
    values = np.asarray(values, dtype=float)
    return lambda picks: float(values[picks].mean())


def test_the_interval_of_three_ones_and_a_zero():
    out = final.paired_bootstrap({"x": mean_of([1, 1, 1, 0])}, [4])
    assert out["systems"]["x"] == pytest.approx({"estimate": 0.75, "low": 0.25, "high": 1.0})


def test_the_paired_difference_uses_the_same_draws_for_both_systems():
    # x is a with 0.1 added on every unit: the difference is 0.1 in every resample, however a varies.
    a = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    out = final.paired_bootstrap({"a": mean_of(a), "x": mean_of([v + 0.1 for v in a])}, [6], baseline="a")
    assert out["paired"]["x"] == pytest.approx({"diff": 0.1, "low": 0.1, "high": 0.1})
    assert out["systems"]["a"]["high"] - out["systems"]["a"]["low"] > 0.3


def test_a_system_equal_to_the_baseline_differs_by_exactly_zero():
    out = final.paired_bootstrap({"a": mean_of([1, 0, 1]), "b": mean_of([1, 0, 1])}, [3], baseline="a")
    assert out["paired"]["b"] == {"diff": 0.0, "low": 0.0, "high": 0.0}


def test_a_baseline_is_not_paired_with_itself():
    out = final.paired_bootstrap({"a": mean_of([1, 0]), "b": mean_of([0, 1])}, [2], baseline="a")
    assert list(out["paired"]) == ["b"]


def test_there_are_one_thousand_resamples_with_seed_zero():
    drawn = []
    final.paired_bootstrap({"x": lambda picks: drawn.append(picks) or 0.0}, [5])
    assert final.RESAMPLES == 1000 and final.SEED == 0
    assert len(drawn) == 1 + 1000
    expected = np.random.default_rng(0).integers(0, 5, 5)
    assert drawn[1].tolist() == expected.tolist()


def test_the_seed_decides_the_draws():
    def first_draw(seed):
        drawn = []
        final.paired_bootstrap({"x": lambda picks: drawn.append(picks) or 0.0}, [50], resamples=1, seed=seed)
        return drawn[1].tolist()

    assert first_draw(0) == first_draw(0)
    assert first_draw(0) != first_draw(1)


def test_each_stratum_is_resampled_inside_itself():
    drawn = []
    final.paired_bootstrap({"x": lambda picks: drawn.append(picks) or 0.0}, [2, 3], resamples=50)
    assert all((d[:2] < 2).all() and (d[2:] >= 2).all() and len(d) == 5 for d in drawn[1:])


def test_stratified_mean_is_the_mean_of_the_stratum_means():
    metric = final.stratified_mean([np.array([1.0, 0.0]), np.array([0.5])])
    assert metric(np.arange(3)) == 0.5
    assert metric(np.array([0, 0, 2])) == 0.75


def test_cognate_metric_is_the_mean_over_data_sets_of_the_pooled_average_precision():
    first = (np.array([-0.1, -0.9]), np.array([True, False]))
    second = (np.array([-0.1, -0.2]), np.array([False, True]))
    third = (np.array([-0.1, -0.2]), np.array([True, False]))
    metric = final.cognate_metric([[first, second], [third]])
    assert metric(np.arange(3)) == pytest.approx((0.25 + 1 / 3 + 1.0) / 2)
    # concept 0 twice: both -0.1 scores are cognate and tie, so the first set scores 1
    assert metric(np.array([0, 0, 2])) == 1.0


def test_the_training_threshold_decides_not_the_scored_sets():
    # A: one concept, words 0 and 1 cognate at distance 0.2, word 2 apart at 0.8: F is 1 from 0.2 up.
    # B: the same cognates at distance 0.5. At 0.2 no word of B merges: every test cluster is one word,
    # so precision is 1. In LingPy counting the cognate set of two words scores 1 of 2 entries for each
    # word and the single-word set scores 1: recall (1 + 1) / 3 = 2/3 and F = 2 * 1 * (2/3) / (1 + 2/3) = 0.8.
    # At B's own best threshold, 0.5, F would be 1.
    def concept(d01):
        distances = np.array([[0, d01, 0.8], [d01, 0, 0.8], [0.8, 0.8, 0]])
        return cognates.Concept(np.array([0, 0, 1]), np.array([0, 1, 2]), distances, np.zeros(3, dtype=bool))

    out = cognates.at_training_threshold({"A": [concept(0.2)]}, {"B": [concept(0.5)]})
    assert out["threshold"] == 0.2
    assert out["bcubed_f"]["B"] == pytest.approx(0.8)
    assert out["bcubed_f"]["mean"] == pytest.approx(0.8)


# ---- the decision rules


def result(k1=True, c4=(0.02, 0.01, 0.03), c5=(0.0, -0.01, 0.01), c6=(0.02, 0.01, 0.03)):
    named = lambda t: {"diff": t[0], "low": t[1], "high": t[2]}  # noqa: E731
    return {"k1": k1, "cognates": named(c4), "alignment": named(c5), "retrieval": named(c6)}


def test_no_candidate_beats_c0_and_the_weights_stay():
    out = final.decide({"C1": result(c4=(0.02, -0.01, 0.05)), "P4": result(c6=(0.0, -0.02, 0.02))})
    assert out["winner"] == "C0" and out["beating"] == []
    assert out["reasons"][-1].startswith("no candidate beats C0 (rule 5)")
    assert "C4 lower bound -0.0100 is not above 0" in out["reasons"][0]
    assert "C6 lower bound -0.0200 is not above 0" in out["reasons"][1]


def test_one_winner():
    out = final.decide({"C2": result(c4=(0.02, -0.01, 0.05)), "P5": result()})
    assert out["winner"] == "P5" and out["beating"] == ["P5"]
    assert "P5 is the only candidate that beats C0" in out["reasons"][-1]


def test_two_winners_go_to_the_larger_c4_difference():
    out = final.decide({"P4": result(c4=(0.0200, 0.01, 0.03), c6=(0.09, 0.05, 0.1)), "P5": result(c4=(0.0300, 0.01, 0.05))})
    assert out["winner"] == "P5" and out["beating"] == ["P4", "P5"]
    assert out["reasons"][-1] == "P5 has the largest C4 difference of 2 candidates that beat C0 (rule 4)"


def test_a_tie_on_c4_at_four_decimals_goes_to_the_larger_c6_difference():
    out = final.decide({"P4": result(c4=(0.02001, 0.01, 0.03), c6=(0.02, 0.01, 0.03)), "P5": result(c4=(0.02004, 0.01, 0.03), c6=(0.03, 0.01, 0.05))})
    assert out["winner"] == "P5"
    assert "tie on C4 at four decimals" in out["reasons"][-1]
    # the same tie with the c6 differences swapped goes the other way
    swapped = final.decide({"P4": result(c4=(0.02001, 0.01, 0.03), c6=(0.03, 0.01, 0.05)), "P5": result(c4=(0.02004, 0.01, 0.03))})
    assert swapped["winner"] == "P4"


def test_a_difference_of_one_in_the_fourth_decimal_is_not_a_tie():
    out = final.decide({"P4": result(c4=(0.0200, 0.01, 0.03), c6=(0.09, 0.05, 0.1)), "P5": result(c4=(0.0201, 0.01, 0.03))})
    assert out["winner"] == "P5"


def test_a_candidate_that_fails_k1_is_out_whatever_it_scores():
    out = final.decide({"C1": result(k1=False, c4=(0.5, 0.4, 0.6)), "P4": result()})
    assert out["winner"] == "P4"
    assert out["reasons"][0] == "C1: out by rule 1, K1 fails"
    assert final.decide({"C1": result(k1=False)})["winner"] == "C0"


def test_a_candidate_worse_on_c5_does_not_win_but_one_not_worse_does():
    worse = result(c5=(-0.05, -0.08, -0.01))
    out = final.decide({"C3": worse})
    assert out["winner"] == "C0" and "C5 upper bound -0.0100 is below 0" in out["reasons"][0]
    # an interval that reaches 0 is not worse than the interval
    assert final.decide({"C3": result(c5=(-0.05, -0.08, 0.0))})["winner"] == "C3"


def test_the_c4_and_c6_bounds_must_be_strictly_above_zero():
    assert final.decide({"P4": result(c4=(0.02, 0.0, 0.03))})["winner"] == "C0"
    assert final.decide({"P4": result(c6=(0.02, 0.0, 0.03))})["winner"] == "C0"


def test_the_decision_reads_the_three_test_files(tmp_path):
    for task in final.TASKS:
        paired = {name: {"diff": 0.0, "low": -0.1, "high": 0.1} for name in variants.CANDIDATES}
        paired["pm-P5"] = {"diff": 0.03, "low": 0.01, "high": 0.05}
        candidates = {n.removeprefix("pm-"): {"system": n, "k1": True} for n in variants.CANDIDATES}
        (tmp_path / f"{task}-test.json").write_text(json.dumps({"paired": paired, "candidates": candidates}))
    assert final.decide(final.decision_input(tmp_path))["winner"] == "P5"


# ---- the --final path, on fixtures


@pytest.fixture
def fixture_run(monkeypatch):
    """``run_final`` with two systems and an adapter whose per-unit scores are fixed by hand."""
    calls = []

    def adapter(systems, split, cache, limit):
        calls.append((split, limit))
        a, b = [1.0, 0.0, 1.0, 0.0], [1.0, 1.0, 1.0, 0.0]
        metrics = {"phonematcher": mean_of(a), "pm-C1": mean_of(b)}
        return {"payload_key": 1}, {"all": (list(metrics), metrics, [4])}, {"phonematcher": 0.5, "pm-C1": 0.75}

    monkeypatch.setattr(final, "final_names", lambda: ["phonematcher", "pm-C1"])
    monkeypatch.setattr(final, "build", lambda name, cache: SimpleNamespace(name=name))
    monkeypatch.setitem(final.ADAPTERS, "alignment", adapter)
    return calls


def head_of(repo):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def test_final_writes_the_test_file_with_commit_prereg_hash_systems_and_differences(repo, tmp_path, fixture_run, capsys):
    assert run.main(["--task", "alignment", "--system", "all", "--split", "test", "--final", "--out", str(tmp_path)], repo=repo) == 0
    record = json.loads((tmp_path / "alignment-test.json").read_text(encoding="utf8"))
    assert record["split"] == "test" and record["commit"] == head_of(repo)
    assert record["prereg_sha256"] == REGISTERED
    assert record["task"] == "alignment" and record["system"] == "phonematcher,pm-C1"
    assert record["paired"]["pm-C1"]["diff"] == pytest.approx(0.25)
    assert record["intervals"]["phonematcher"]["estimate"] == 0.5
    assert record["candidates"]["C3"]["major_class_weight"] == 1.38
    assert {n: c["k1"] for n, c in record["candidates"].items()} == {"C1": False, "C2": False, "C3": True, "P4": True, "P5": True}
    assert fixture_run == [("test", 0)]
    assert "2 systems in, 2 scored" in capsys.readouterr().out


def test_final_refuses_a_page_that_differs_before_it_scores(repo, tmp_path, fixture_run, monkeypatch):
    page = tmp_path / "prereg-2.md"
    page.write_bytes(b"changed")
    monkeypatch.setattr(final, "PREREG", page)
    with pytest.raises(SystemExit, match="not the registered"):
        run.main(["--task", "alignment", "--system", "all", "--split", "test", "--final", "--out", str(tmp_path)], repo=repo)
    assert fixture_run == [] and not (tmp_path / "alignment-test.json").exists()


def test_final_keeps_its_clean_tree_check_for_the_three_tasks(repo, fixture_run):
    (repo / "f.txt").write_text("two\n")
    for task in final.TASKS:
        with pytest.raises(SystemExit, match="clean git tree"):
            run.main(["--task", task, "--system", "all", "--split", "test", "--final"], repo=repo)
    assert fixture_run == []


def test_final_scores_every_system_and_nothing_less(repo, tmp_path, fixture_run):
    with pytest.raises(SystemExit, match="pass --system all"):
        run.main(["--task", "alignment", "--system", "phonematcher", "--split", "test", "--final", "--out", str(tmp_path)], repo=repo)


def test_two_final_runs_in_a_row_from_a_clean_tree_both_start_and_record_head(repo, tmp_path, fixture_run, monkeypatch):
    # The committed results directory sits inside the tree; a run must not write there.
    monkeypatch.setattr(run, "RESULTS", repo / "benchmarks" / "results")
    cache = tmp_path / "cache"
    for _ in range(2):
        assert run.main(["--task", "alignment", "--system", "all", "--split", "test", "--final", "--cache", str(cache)], repo=repo) == 0
    assert fixture_run == [("test", 0), ("test", 0)]
    record = json.loads((cache / "results" / "alignment-test.json").read_text(encoding="utf8"))
    assert record["commit"] == record["head"] == head_of(repo) and record["tree_dirty"] is False


def test_the_final_systems_are_the_seven_the_variants_and_the_candidates():
    assert final.final_names() == [*run.NAMES, *variants.NAMES, *variants.CANDIDATES]
    assert len(final.final_names()) == 18


def test_the_test_split_still_needs_final_for_the_three_tasks(repo):
    for task in final.TASKS:
        with pytest.raises(SystemExit, match="only with --final"):
            run.main(["--task", task, "--system", "all", "--split", "test"], repo=repo)


def test_a_dry_run_walks_the_path_on_dev_and_writes_nothing(tmp_path, fixture_run, monkeypatch, capsys):
    results = tmp_path / "results"
    monkeypatch.setattr(run, "RESULTS", results)
    before = sorted(p.name for p in tmp_path.iterdir())
    assert run.main(["--task", "alignment", "--system", "all", "--split", "dev", "--dry-run", "--limit", "7"]) == 0
    assert fixture_run == [("dev", 7)]
    assert sorted(p.name for p in tmp_path.iterdir()) == before and not results.exists()
    text = capsys.readouterr().out
    assert "pm-C1 - phonematcher: +0.2500" in text and "dry run: nothing written" in text and REGISTERED in text


@pytest.mark.parametrize("args", [["--split", "test"], ["--split", "dev", "--final"]])
def test_a_dry_run_is_for_dev_only(args, fixture_run):
    with pytest.raises(SystemExit, match="--dry-run takes --split dev"):
        run.main(["--task", "alignment", "--system", "all", "--dry-run", *args])
    assert fixture_run == []


def test_a_dry_run_is_for_the_three_final_tasks():
    with pytest.raises(SystemExit, match="--dry-run takes"):
        run.main(["--task", "tone", "--system", "all", "--dry-run"])


# ---- the cognate score of a final run, on a fixture


class Words(System):
    """Reads p, a and k; distance 0 between equal words, 0.2 for words that differ in the first
    segment of p and k pairs only when marked, else 0.8."""

    name = "words"

    def reads(self, segment):
        return segment in "pak"

    def _word_distance(self, a, b, normalized):
        return 0.0 if a == b else 0.2 if {a[0], b[0]} == {"p", "k"} else 0.8


def write_sets(root, prefix, names):
    code = root / "cognates" / "x" / "pkg" / "code"
    code.mkdir(parents=True, exist_ok=True)
    for name in names:
        rows = ["ID\tCONCEPT\tDOCULECT\tTOKENS\tCOGID", "1\tc\tL1\tp a\t1", "2\tc\tL2\tk a\t1", "3\tc\tL3\ta a\t2"]
        (code / f"{prefix}{name}.tsv").write_text("\n".join(rows) + "\n", encoding="utf8")


def test_a_final_cognate_score_adds_the_training_threshold_f_and_the_concepts(tmp_path):
    write_sets(tmp_path, "D_training_", cognates.TRAINING)
    payload, sets = cognates.score([Words()], "dev", tmp_path, final=True)
    row = payload["systems"]["words"]["bcubed_f_at_training_threshold"]
    # p a and k a are cognate at 0.2, a a is apart at 0.8: the best training threshold is the first, 0.2
    assert row["threshold"] == 0.2
    assert row["bcubed_f"]["mean"] == pytest.approx(1.0)
    assert set(sets["words"]) == set(cognates.TRAINING)
    assert "bcubed_f_at_training_threshold" not in cognates.score([Words()], "dev", tmp_path)[0]["systems"]["words"]


def test_a_cognate_score_on_a_fixture_test_split_takes_the_threshold_from_the_training_files(tmp_path):
    write_sets(tmp_path, "D_training_", cognates.TRAINING)
    write_sets(tmp_path, "D_test_", cognates.TEST)
    payload, _ = cognates.score([Words()], "test", tmp_path, final=True)
    assert payload["systems"]["words"]["bcubed_f_at_training_threshold"]["threshold"] == 0.2
    assert payload["datasets"] == cognates.TEST


def test_a_limit_keeps_the_first_concepts_of_each_set(tmp_path):
    words = [cognates.Word(c, "L", ("a",), "1") for c in ("x", "y", "x", "z")]
    assert [w.concept for w in cognates.first_concepts(words, 2)] == ["x", "y", "x"]


# ---- the retrieval adapter, on four tiny dialect pairs


def write_pairs(cache):
    """Per language pair, three dev words listed in both dialects; each B pronunciation differs from A's."""
    from split import is_test
    from tasks import retrieval

    folder = cache / "C6"
    folder.mkdir(parents=True)
    for name, (a_file, b_file) in retrieval.PAIRS.items():
        language = name.split("-")[0]
        words = [w for w in (f"w{k}" for k in range(40)) if not is_test(f"{language}:{w}")][:3]
        rows_a = [(w, p) for w, p in zip(words, ("a b", "x y", "y x"))]
        rows_b = [(w, p) for w, p in zip(words, ("a c", "x c", "y c"))]
        (folder / f"{a_file}.tsv").write_text("".join(f"{w}\t{p}\n" for w, p in rows_a), encoding="utf8")
        (folder / f"{b_file}.tsv").write_text("".join(f"{w}\t{p}\n" for w, p in rows_b), encoding="utf8")


def test_the_retrieval_adapter_pairs_systems_on_the_same_queries_of_each_pair(tmp_path):
    from systems import Levenshtein

    write_pairs(tmp_path)
    built = [variants.Variant("phonematcher"), variants.build_variant("pm-C1"), Levenshtein()]
    payload, groups, expected = final.retrieval_final(built, "dev", tmp_path, limit=2)
    assert list(groups) and len(groups) == 1
    (names, metrics, strata), = groups.values()
    assert names == ["phonematcher", "pm-C1", "levenshtein"] and strata == [2, 2, 2, 2]
    intervals, paired = final._bootstrap_groups(groups)
    # every query has its gold word strictly nearest under unit costs: recall@1 is 1 on both queries of each pair
    assert intervals["levenshtein"] == {"estimate": 1.0, "low": 1.0, "high": 1.0}
    assert expected["levenshtein"] == 1.0
    assert set(paired) == {"pm-C1", "levenshtein"}
    assert paired["levenshtein"] == {"diff": 0.0, "low": 0.0, "high": 0.0}
    assert payload["split"] == "dev" and sorted(payload["pairs"]) == sorted(run.retrieval.PAIRS)
