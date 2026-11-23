"""The ablation variants of ``benchmarks/variants.py``, on values worked out by hand.

The table's weights add up to 9.5: PanPhon's 22 features add up to 7.25, the four features
[front], [tap], [trill] and [atr] to 1.0 (0.25 each), the six height steps to 0.75 (0.125 each)
and the four secondary articulations to 0.5 (0.125 each).
"""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

import run  # noqa: E402
import systems  # noqa: E402
import variants  # noqa: E402
from phonematcher import align, edit_distance, features, feature_distance  # noqa: E402

BUILT = {name: variants.build_variant(name) for name in variants.NAMES}


def test_indel_half_prices_one_insertion_at_half():
    assert BUILT["pm-indel-0.5"].word_distance(["a"], []) == 0.5
    assert BUILT["pm-indel-0.5"].word_distance(["p", "a"], ["a"]) == 0.5
    # one deletion over the two segments of the longer word
    assert BUILT["pm-indel-0.5"].word_distance(["p", "a"], ["a"], normalized=True) == 0.25


def test_indel_one_and_a_half_prices_one_insertion_at_one_and_a_half():
    assert BUILT["pm-indel-1.5"].word_distance([], ["a"]) == 1.5
    assert BUILT["pm-indel-1.5"].word_distance(["p", "a"], ["a"]) == 1.5


def test_indel_variants_keep_the_package_substitution():
    # p and b differ in [voice] only: 0.125 of the 9.5 total, whatever the indel cost
    for name in ("pm-indel-0.5", "pm-indel-1.5"):
        assert BUILT[name].segment_distance("p", "b") == pytest.approx(0.125 / 9.5)
        assert BUILT[name].word_distance(["p"], ["b"]) == pytest.approx(0.125 / 9.5)


def test_a_substitution_dearer_than_two_gaps_becomes_two_gaps():
    # p and m differ in [son], [nas] and [voice]: (1 + 0.25 + 0.125) / 9.5 = 0.145. At indel 0.05
    # a deletion and an insertion cost 0.1, which is less.
    cheap = variants.Variant("cheap", indel=0.05)
    assert cheap.segment_distance("p", "m") == pytest.approx(1.375 / 9.5)
    assert cheap.word_distance(["p"], ["m"]) == pytest.approx(0.1)


def test_indel_variant_aligns_with_its_own_gap_cost():
    assert BUILT["pm-indel-0.5"].align(["p", "a"], ["a"]) == [("p", None), ("a", "a")]


def test_uniform_distance_is_the_share_of_features_that_differ():
    # p and b differ in 1 of 36 features; p and m in 3 ([son], [nas], [voice]).
    assert BUILT["pm-uniform"].segment_distance("p", "b") == pytest.approx(1 / 36)
    assert BUILT["pm-uniform"].segment_distance("p", "m") == pytest.approx(3 / 36)


def test_uniform_prices_a_zero_against_a_value_at_half():
    # p and t: [coronal] and [labial] flip, [distributed] goes from 0 to -: 1 + 1 + 0.5 of 36.
    assert BUILT["pm-uniform"].segment_distance("p", "t") == pytest.approx(2.5 / 36)


def test_panphon22_divides_by_panphons_weight_total():
    # PanPhon's weights add up to 7.25; p and b differ in [voice], weight 0.125.
    assert BUILT["pm-panphon22"].segment_distance("p", "b") == pytest.approx(0.125 / 7.25)
    assert BUILT["pm-panphon22"].segment_distance("p", "m") == pytest.approx(1.375 / 7.25)


def test_panphon22_ignores_the_features_panphon_lacks():
    # [tap] is one of the four features that PanPhon lacks, so its weight is 0 here and 0.25 in the
    # uniform variant's 1.
    assert features.FEATURES.index("tap") >= 22
    assert BUILT["pm-panphon22"].segment_distance("ɾ", "ɹ") != BUILT["pm-uniform"].segment_distance("ɾ", "ɹ")
    assert BUILT["pm-panphon22"].weights[features.FEATURES.index("tap")] == 0.0
    assert sum(BUILT["pm-panphon22"].weights) == 7.25


def test_panphon22_weights_are_the_ones_panphon_applies():
    # feature_weights.csv names tense 0.25, long 0.125, velaric 0.25 but FeatureTable gives its
    # values in the order of its own names, which end velaric, tense, long.
    from panphon import FeatureTable

    table = FeatureTable()
    applied = dict(zip(table.names, table.weights))
    weights = dict(zip(features.FEATURES, variants.panphon_weights()))
    assert applied["velaric"] == 0.25 and applied["tense"] == 0.125 and applied["long"] == 0.25
    assert {n: weights[n] for n in applied} == applied
    by_label = dict(zip(features.FEATURES, variants.panphon_weights(by_file_label=True)))
    assert (by_label["tense"], by_label["long"], by_label["velaric"]) == (0.25, 0.125, 0.25)


def test_no_height_drops_the_steps_and_their_weight():
    # 9.5 less six steps of 0.125 is 8.75
    assert BUILT["pm-no-height"].segment_distance("p", "b") == pytest.approx(0.125 / 8.75)


def test_no_height_gives_two_vowels_that_differ_only_in_height_steps_distance_zero():
    # ɘ and ə differ in the step [h3] only; ɛ and e in [h3] and [h4] (the IPA chart's close-mid
    # and open-mid rows), with [high] and [low] the same.
    assert BUILT["pm-no-height"].segment_distance("ɘ", "ə") == 0.0
    assert BUILT["pm-no-height"].segment_distance("ɛ", "e") == 0.0
    assert feature_distance("ɘ", "ə") == pytest.approx(0.125 / 9.5)
    assert feature_distance("ɛ", "e") == pytest.approx(0.25 / 9.5)


def test_flat_diacritics_leave_a_lowered_vowel_as_its_base():
    # The package reads e̞ one row lower (a flip of [h4]); PanPhon's rule for the mark has no content.
    assert feature_distance("e", "e̞") == pytest.approx(0.125 / 9.5)
    assert BUILT["pm-flat-diacritics"].segment_distance("e", "e̞") == 0.0


def test_flat_diacritics_read_what_the_package_reads():
    flat = BUILT["pm-flat-diacritics"]
    for segment in ("e̞", "t̪", "k͡p", "ɡ", "☃", "ei", "²²"):
        assert flat.reads(segment) == systems.PhoneMatcher().reads(segment), segment


def test_flat_diacritics_change_only_segments_built_with_a_shift():
    flat = variants.flat_features()
    changed = {s for s in features.phone_features if flat.phone_features[s] != features.phone_features[s]}
    assert "e̞" in changed and "k̟" not in changed and "p" not in changed
    assert all(any(mark in s for mark in "̟̠̝̞̹̜̣̭̽˔˕˖˗") for s in changed)


def test_rebuilding_the_table_from_its_bases_reproduces_it():
    # With the shifts kept, the rebuild must give back every listed vector, so a difference in the
    # flat table comes from the shifts and from nothing else.
    module = variants.fresh_features()
    assert variants.reread(module, shifts=True) == 0
    assert module.phone_features == features.phone_features


def test_the_package_table_is_untouched_by_building_the_flat_variant():
    before = dict(features.phone_features)
    variants.build_variant("pm-flat-diacritics")
    assert features.phone_features == before
    assert feature_distance("e", "e̞") > 0


def test_every_variant_is_a_system_with_its_own_name():
    assert [v.name for v in BUILT.values()] == variants.NAMES
    for name, variant in BUILT.items():
        assert isinstance(variant, systems.System) and variant.name == name


P5_BUILT = {name: variants.build_variant(name) for name in variants.P5_NAMES}


def test_every_p5_variant_is_named_for_a_c0_variant():
    assert variants.P5_NAMES == [name.replace("pm-", "pm-p5-", 1) for name in variants.NAMES]
    assert [v.name for v in P5_BUILT.values()] == variants.P5_NAMES


def test_p5_variants_take_the_square_root_of_the_feature_distance():
    # p and b differ in [voice] only. Without the six steps (0.75) the weights total 8.75, so the
    # linear distance is 0.125 / 8.75 and the shipped rule is its square root.
    assert P5_BUILT["pm-p5-no-height"].segment_distance("p", "b") == pytest.approx((0.125 / 8.75) ** 0.5)
    assert BUILT["pm-no-height"].segment_distance("p", "b") == pytest.approx(0.125 / 8.75)
    # uniform weights: 1 of 36 features
    assert P5_BUILT["pm-p5-uniform"].segment_distance("p", "b") == pytest.approx((1 / 36) ** 0.5)


def test_p5_variants_keep_the_shipped_gap_unless_the_variant_sets_it():
    for name, variant in P5_BUILT.items():
        assert variant.indel == {"pm-p5-indel-0.5": 0.5, "pm-p5-indel-1.5": 1.5}.get(name, 0.5)
    assert P5_BUILT["pm-p5-uniform"].word_distance(["a"], []) == 0.5
    assert P5_BUILT["pm-p5-indel-1.5"].word_distance(["a"], []) == 1.5


def test_the_p5_indel_half_variant_is_the_shipped_library():
    words = [(["p", "a", "t"], ["b", "a"]), (["k", "i", "t", "a"], ["k", "e", "t"]), ([], ["a"])]
    shipped, control = systems.build("phonematcher", Path(".")), P5_BUILT["pm-p5-indel-0.5"]
    for left, right in words:
        assert control.word_distance(left, right) == pytest.approx(shipped.word_distance(left, right))
        assert control.word_distance(left, right, normalized=True) == pytest.approx(shipped.word_distance(left, right, normalized=True))


def test_an_unknown_variant_is_an_error():
    with pytest.raises(KeyError):
        variants.build_variant("pm-nothing")
    with pytest.raises(KeyError):
        systems.build("pm-indel-2", Path("."))


def test_all_leaves_the_variants_out_and_variants_adds_them(capsys):
    assert not [n for n in systems.NAMES if n.startswith("pm-")]
    assert run.main(["--task", "selfcheck", "--system", "variants"]) == 0
    printed = [line.split(":")[0] for line in capsys.readouterr().out.splitlines()]
    assert printed == ["phonematcher", *variants.NAMES]
    assert run.main(["--task", "selfcheck", "--system", "variants-p5"]) == 0
    printed = [line.split(":")[0] for line in capsys.readouterr().out.splitlines()]
    assert printed == ["phonematcher", *variants.P5_NAMES]


def test_the_package_edit_distance_takes_the_substitution_and_gap_costs():
    sub = lambda a, b: 0.0 if a == b else 1.0  # noqa: E731
    assert edit_distance(["a", "b"], [], substitution=sub, gap=1.0) == 2.0
    assert edit_distance(["a", "b"], [], substitution=sub, gap=0.5) == 1.0
    assert edit_distance(["a"], ["b"], substitution=sub, gap=0.5) == 1.0
    assert align(["a", "b"], ["b"], substitution=sub, gap=0.5) == [("a", None), ("b", "b")]
    assert align(["a", "b"], ["c"], substitution=sub, gap=1.0) == [("a", None), ("b", "c")]
    # unit costs: levenshtein prices a substitution of two different segments at 1, a gap at 1
    assert systems.Levenshtein().word_distance(["k", "a", "t"], ["k", "o"]) == 2.0


def test_control_on_a_tiny_inventory(tmp_path):
    # p, b and m keep PanPhon's 22 values, so their 3 pairs must agree with panphon-weighted after
    # the scale of 2 * 7.25. The table gives a the IPA chart's [back] and [tense], so its 3 pairs differ.
    folder = tmp_path / "C2"
    folder.mkdir()
    with open(folder / "phoible.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Phoneme", "Allophones"])
        for segment in ("p", "b", "m", "a"):
            writer.writerow([segment, "NA"])
    result = variants.control(tmp_path)
    assert result["segments_read_by_both"] == 4
    assert result["pairs_compared"] == 6
    assert result["scale"] == 14.5
    assert result["identical_vector_pairs"] == 3
    assert result["identical_vector_pairs_differing"] == 0
    assert result["segments_with_vector_difference_list"] == {"a": ["back", "tense"]}
    assert result["pairs_differing"] == 3


def test_reread_leaves_no_stale_distance_in_the_module_caches():
    module = variants.fresh_features()
    assert "pʰ" in module.phone_features
    module.phone_features["pʰ"] = module.phone_features["k"]
    stale = module.feature_distance("pʰ", "p")
    assert stale != feature_distance("pʰ", "p")
    variants.reread(module, shifts=True)
    assert module.feature_distance("pʰ", "p") == feature_distance("pʰ", "p")
