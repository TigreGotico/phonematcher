"""Every number on docs/design.md equals the value in a benchmark result file or a hand value.

The page is written by hand. This test reads the result files and checks that the page holds
the same numbers, so a rerun of the benchmarks that moves a number fails here until the page
follows. Hand values: the weights of the table sum to 9.5, so one step feature (weight 0.125)
is 0.125 / 9.5 of the distance; a deletion and an insertion cost 0.5 each.
"""
import json
from itertools import combinations
from pathlib import Path

import pytest

from phonematcher import ipa_distance, segments, vectorize_phones
from phonematcher.distance import GAP_COST, substitution_cost
from phonematcher.features import FEATURES, feature_distance

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "docs" / "design.md").read_text(encoding="utf-8")
RESULTS = ROOT / "benchmarks" / "results"


def results(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def signed(value):
    return f"{value:+.4f}"


def test_the_coverage_table_equals_the_census_file():
    census = results("coverage-seen.json")
    assert census["tree_dirty"] is True and "uncommitted changes" in PAGE and "`4a31c7f`" in PAGE
    rows = []
    for label, key in (("PHOIBLE 2.0", "phoible"), ("WikiPron", "wikipron"), ("orthography2ipa", "orthography2ipa")):
        row = census["systems"]["phonematcher"][key]["direct"]
        assert row["types_read"] + row["types_unread"] == row["types"]
        rows.append(f"| {label} | {row['types']} | {row['types_read']} | {row['types_unread']} | {row['token_share']:.4f} |")
    for row in rows:
        assert row in PAGE


def test_the_word_cost_table_equals_the_paired_differences_of_the_test_run():
    test = {task: results(f"{task}-test.json") for task in ("cognates", "alignment", "retrieval")}
    candidates = test["cognates"]["candidates"]
    for name in ("C1", "C2", "C3", "P4", "P5"):
        cells = [signed(test[task]["paired"][f"pm-{name}"]["diff"]) for task in ("cognates", "alignment", "retrieval")]
        k1 = "yes" if candidates[name]["k1"] else "no"
        assert f"| {name} | {k1} | " + " | ".join(cells) + " |" in PAGE


def test_the_shipped_costs_are_the_winner_and_sit_below_edit_distance_and_sca():
    cognates = results("cognates-test.json")
    assert GAP_COST == 0.5
    intervals = cognates["intervals"]
    assert f"{intervals['pm-P5']['estimate']:.4f}" in PAGE
    assert f"{intervals['levenshtein']['estimate']:.4f}" in PAGE
    assert f"{intervals['sca']['estimate']:.4f}" in PAGE
    assert intervals["pm-P5"]["estimate"] < intervals["levenshtein"]["estimate"] < intervals["sca"]["estimate"]


def test_the_height_numbers_equal_the_ablation_files():
    confusions = results("ablations-seen.json")["tasks"]["confusions"]["systems"]
    scores = {name: confusions[name]["hillenbrand"]["unread_at_1"] for name in ("phonematcher", "pm-p5-no-height", "pm-p5-panphon22")}
    for score in scores.values():
        assert f"{score['score']:.4f}" in PAGE
    spans = [(s["interval"]["low"], s["interval"]["high"]) for s in scores.values()]
    assert all(max(a[0], b[0]) < min(a[1], b[1]) for a, b in combinations(spans, 2))
    paired = results("cognates-test.json")["paired"]["pm-no-height"]
    assert f"by {signed(paired['diff'])}" in PAGE
    assert f"{paired['low']:.4f}" in PAGE and signed(paired["high"]) in PAGE


def test_the_scale_marks_move_the_paired_cognate_score_by_less_than_one_ten_thousandth():
    paired = results("cognates-test.json")["paired"]["pm-flat-diacritics"]
    assert abs(paired["diff"]) < 1e-4
    assert "less than 0.0001" in PAGE


def test_the_dev_ablations_of_the_shipped_costs_equal_the_ablation_file():
    # The test-set numbers of this page use the C0 costs; the development numbers use the shipped
    # costs, so the file's rows are the pm-p5- ones, and its control row repeats the shipped library.
    cognates = results("ablations-dev.json")["tasks"]["cognates"]["systems"]
    scores = {name: cognates[name]["unread_at_1"]["average_precision"]["mean"] for name in ("phonematcher", "pm-p5-no-height", "pm-p5-flat-diacritics", "pm-p5-indel-0.5")}
    assert scores["pm-p5-indel-0.5"] == scores["phonematcher"]
    assert f"{scores['pm-p5-no-height']:.4f}" in PAGE and f"{scores['phonematcher']:.4f}" in PAGE
    assert f"{scores['pm-p5-flat-diacritics']:.4f}" == f"{scores['pm-p5-no-height']:.4f}"


def test_the_tone_numbers_equal_the_tone_file():
    tone = results("tone-seen.json")
    main, alternative = tone["scored"]["main"], tone["scored"]["alternative"]
    assert tone["pairs"] == 15 and "15 tone pairs" in PAGE
    for system in ("phonematcher", "direction_baseline"):
        row = main[system]
        assert (row["pairs_in"], row["pairs_out"]) == (15, 15)
        assert f"{row['score']:.4f}" in PAGE
        assert f"{row['interval']['low']:.4f}" in PAGE and f"{row['interval']['high']:.4f}" in PAGE
    assert f"{alternative['phonematcher']['score']:.4f}" in PAGE
    assert main["phonematcher"]["score"] < main["direction_baseline"]["score"]
    assert main["phonematcher"]["interval"]["high"] > main["direction_baseline"]["interval"]["low"]
    rates = tone["pair_rates"]
    assert sorted(rates, key=rates.get)[-2:] == ["T1-T3", "T3-T6"]


def test_the_allophone_views_equal_the_allophone_file():
    row = results("allophones-seen.json")["systems"]["phonematcher"]["direct"]["all"]
    assert row["unread_at_1"]["items_out"] == row["items_in"] == 12716
    assert (row["read_only"]["items_out"], row["read_only"]["skipped"]) == (12492, 224)
    assert f"{row['unread_at_1']['score']:.4f}" in PAGE and f"{row['read_only']['score']:.4f}" in PAGE
    assert "12716" in PAGE and "224" in PAGE and "12492" in PAGE


def test_the_panphon_control_numbers_equal_the_ablation_file():
    control = results("ablations-seen.json")["control"]
    assert control["identical_vector_pairs_differing"] == 0
    for key in ("identical_vector_pairs", "pairs_compared", "pairs_differing"):
        assert str(control[key]) in PAGE


def test_every_example_of_an_unread_kind_raises_value_error():
    kinds = ["ai", "ˁ", "ʳ", "ᵊ", "eˣ", "k̃", "m̃", "aʰ", "ʉʰ", "↓", "ʅ"]
    for example in kinds:
        assert f"`{example}`" in PAGE
        with pytest.raises(ValueError):
            vectorize_phones(example)
        assert feature_distance(example, "a") == 1.0


def test_pharyngealized_and_retracted_tongue_root_differ_in_one_feature():
    a, b = vectorize_phones("iˤ"), vectorize_phones("i̙")
    assert [name for name, x, y in zip(FEATURES, a, b) if x != y] == ["pharyngealized"]
    assert dict(zip(FEATURES, a))["atr"] == dict(zip(FEATURES, b))["atr"] == False  # noqa: E712


def test_a_tone_against_a_phone_costs_a_deletion_plus_an_insertion():
    assert substitution_cost("˥", "a") == substitution_cost("a", "˥") == 1.0 == 2 * GAP_COST


def test_a_diphthong_is_two_segments_and_costs_one_deletion_against_its_nucleus():
    assert segments("a͡i") == ["a", "i"]
    assert ipa_distance("a͡i", "a") == GAP_COST


def test_the_closest_two_letters_differ_by_one_step_feature_of_weight_one_eighth():
    import importlib.util
    spec = importlib.util.spec_from_file_location("same_vector_page", ROOT / "scripts" / "same_vector.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    letters = script.base_letters()
    assert len(letters) == 135 and "135 letters" in PAGE
    smallest = min(feature_distance(a, b) for a, b in combinations(letters, 2))
    assert smallest == pytest.approx(0.125 / 9.5) and f"{smallest:.4f}" in PAGE
    assert feature_distance("a", "æ") == pytest.approx(0.125 / 9.5)
    assert [n for n, x, y in zip(FEATURES, vectorize_phones("a"), vectorize_phones("æ")) if x != y] == ["h6"]


def test_the_vowel_height_decision_equals_the_ablation_files():
    ablations = RESULTS / "ablations"
    dev = json.loads((ablations / "vowel-height-dev.json").read_text(encoding="utf-8"))
    seen = json.loads((ablations / "vowel-height-seen.json").read_text(encoding="utf-8"))
    cognates = dev["cognates"]["paired"]["pm-F1-segment"]
    alignment = dev["alignment"]["paired"]["pm-F1-segment"]
    assert cognates["high"] < 0 < alignment["low"]
    for value in (cognates["diff"], cognates["low"], alignment["diff"], alignment["low"], alignment["high"]):
        assert signed(value) in PAGE
    assert f"{cognates['high']:.4f}" in PAGE
    systems = seen["tasks.confusions"]["systems"]
    shipped = results("confusions-seen.json")["systems"]["phonematcher"]["hillenbrand"]["unread_at_1"]["score"]
    assert systems["phonematcher"]["hillenbrand"]["unread_at_1"]["score"] == shipped
    one_encoding = systems["pm-F1-segment"]["hillenbrand"]["unread_at_1"]["score"]
    assert f"from {shipped:.4f} to {one_encoding:.4f}" in PAGE


def test_the_one_encoding_form_of_vowel_height_is_not_the_table():
    # In the one-encoding form a vowel's hi and lo are 0, so the steps carry height. The table keeps
    # hi and lo on a vowel: i and e differ on hi and on two steps h1 and h2.
    names = list(FEATURES)
    i, e = vectorize_phones("i"), vectorize_phones("e")
    differing = [n for n, x, y in zip(names, i, e) if x != y]
    assert differing == ["hi", "h1", "h2"]
