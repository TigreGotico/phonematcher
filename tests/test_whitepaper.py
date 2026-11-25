"""whitepaper.md: each table is a fresh render, and each number in the prose comes from a file.

The tables between ``<!-- whitepaper:<name>:start -->`` and ``<!-- whitepaper:<name>:end -->`` are
written by ``benchmarks/render.py --whitepaper``, and ``render.py --check`` compares them with a fresh
render. The prose is written by hand. This test computes each prose number from a result file or from
the library, asserts that the prose holds it, and binds each key number to the system and claim of
its sentence. It fails on any number in the prose that it did not compute or list below as an
identifier or as an audit-run number, which no file holds.
"""
import csv
import json
import math
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "benchmarks"))

import render  # noqa: E402

from phonematcher import PhoneticFuzzySearch  # noqa: E402
from phonematcher.distance import GAP_COST  # noqa: E402
from phonematcher.clustering import _letter_costs  # noqa: E402
from phonematcher.features import FEATURES, TONE_FEATURES, WEIGHTS  # noqa: E402

PAPER = render.WHITEPAPER.read_text(encoding="utf8")
RESULTS = render.RESULTS
ROMANCE = "Romance-110-43"

#: Numbers that name a thing rather than measure it: a version, a licence, a record, a confidence level.
IDENTIFIERS = {
    "0", "1",            # the ends of the distance scale, and seed 0
    "0.22.2",            # the PanPhon version, checked below against the installed package
    "2.0",               # PHOIBLE 2.0
    "4.0",               # CC BY 4.0
    "95",                # the 95% interval, and pull request 95
    "192607",            # the Zenodo record, checked below against the cognate test file
    "3.12",              # the Python version of the hash-seed note
    "7",                 # rule 7 of the pre-registration
    "21",                # the feature count the PanPhon paper states on p. 3475
}

#: Numbers from an audit run that no result file holds. The paper names the audit beside each.
AUDIT = {
    "875": "triangle check of the per-pair height form at ecde385: violations",
    "400,995": "triangle check of the per-pair height form at ecde385: unordered triples",
    "0.6394": "scripts/fit_weights.py at 3a134ef: Hillenbrand, fitted, leave one set out (seen)",
    "0.3395": "scripts/fit_weights.py at 3a134ef: Mandarin, fitted, leave one set out (seen)",
    "0.2981": "scripts/fit_weights.py at 3a134ef: Miller and Nicely, fitted, leave one set out (seen)",
    "0.1": "dev retrieval, share 0.08 against the absolute threshold of f092f20: that threshold",
    "0.0000": "dev retrieval, share 0.08 against the absolute threshold of f092f20: paired recall@1 difference and its interval",
    "23": "dev retrieval, share 0.08 against the absolute threshold of f092f20: most fewer candidates, in percent",
}


def results(name):
    return json.loads((RESULTS / name).read_text(encoding="utf8"))


def f4(value):
    return f"{value:.4f}"


def prose(text=PAPER):
    """The hand-written part of the paper: no rendered table, code, comment, heading number or reference."""
    text = re.sub(r"<!-- whitepaper:([\w-]+):start -->.*?<!-- whitepaper:\1:end -->", "", text, flags=re.S)
    text = text.split("## 10. References")[0]
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"(?m)^#+ [\d.]+ ", "", text)
    text = re.sub(r"(?m)^\d+\. ", "", text)
    text = re.sub(r"(?i)section \d+(\.\d+)?", "", text)
    return re.sub(r"\b(19|20)\d\d\b(, pp?\. [\d–]+)?", "", text)


def numbers(text):
    return re.findall(r"(?<![\w@.-])\d+(?:[.,]\d+)*", text)


def tone_scores():
    return results("tone-seen.json")["scored"]["main"]


def equal_cost():
    """The dev numbers of section 5.6 by system: AP on all and on common words, PAS on common pairs, mean recall@1."""
    tasks = results("equal-cost-dev.json")["tasks"]
    pairs = tasks["retrieval"]["pairs"].values()
    return {
        name: {
            "cog_all": tasks["cognates"]["systems"][name]["unread_at_1"]["average_precision"]["mean"],
            "cog_common": tasks["cognates"]["systems"][name]["common"]["average_precision"]["mean"],
            "pas": tasks["alignment"]["all"]["systems"][name]["common_pas"],
            "recall": math.fsum(p["systems"][name]["all_items_unread_at_1"]["recall@1"] for p in pairs) / len(pairs),
        }
        for name in tasks["cognates"]["systems"]
    }


def scale_mark_bound():
    """The least power of ten above every paired test difference of the variant with no scale marks."""
    diffs = [abs(results(f"{task}-test.json")["paired"]["pm-flat-diacritics"]["diff"]) for task in ("cognates", "alignment")]
    exponent = math.floor(math.log10(max(d for d in diffs if d))) + 1
    return f"{10.0 ** exponent:.{-exponent}f}"


#: Within one sentence: any text without a full stop, except the point of a decimal.
GAP = r"(?:[^.\n]|\.\d)*?"


def anchored(*parts):
    """A pattern for the parts in order, inside one sentence; a value is escaped, a word is literal."""
    return re.compile(GAP.join(re.escape(part) for part in parts))


def anchors():
    """Each key number with the system and claim it belongs to, in the order of its sentence."""
    cognates, retrieval = results("cognates-test.json"), results("retrieval-test.json")
    iv = {name: f4(row["estimate"]) for name, row in cognates["intervals"].items()}
    p5, sca = cognates["systems"]["pm-P5"], cognates["systems"]["sca"]
    seen = results("confusions-seen.json")["systems"]["phonematcher"]
    control = results("ablations-seen.json")["control"]
    letters = len(_letter_costs()[0])
    triples = math.comb(letters, 3)
    equal = equal_cost()
    return [
        anchored("It has the highest recall@1", f4(retrieval["intervals"]["phonematcher"]["estimate"])),
        anchored("precision is", iv["phonematcher"]),
        anchored("This is below SCA at", iv["sca"], "plain edit distance at", iv["levenshtein"], "CLTS sound vectors at", iv["soundvectors"]),
        anchored("the scores are", f4(retrieval["intervals"]["pm-P5"]["estimate"]), "for retrieval", iv["pm-P5"], "for cognates"),
        anchored("baseline has the higher point estimate", f4(tone_scores()["direction_baseline"]["score"]), "against", f4(tone_scores()["phonematcher"]["score"])),
        anchored("In", str(tone_scores()["direction_baseline"]["interval"]["undefined"]), "of the", str(cognates["resamples"]), "resamples"),
        anchored("On cognates, CLTS sound vectors score", f4(equal["soundvectors-p5"]["cog_all"]), "on all words and phonematcher", f4(equal["phonematcher"]["cog_all"])),
        anchored("On the common words, CLTS sound vectors score", f4(equal["soundvectors-p5"]["cog_common"]), "and phonematcher", f4(equal["phonematcher"]["cog_common"])),
        anchored("On alignment, PanPhon scores", f4(equal["panphon-weighted-p5"]["pas"]), "and phonematcher", f4(equal["phonematcher"]["pas"])),
        anchored("CLTS sound vectors score", f4(equal["soundvectors-p5"]["pas"])),
        anchored("On retrieval, phonematcher keeps the lead with", f4(equal["phonematcher"]["recall"]), "against", f4(equal["soundvectors-p5"]["recall"]),
                 "for CLTS sound vectors and", f4(equal["panphon-weighted-p5"]["recall"]), "for PanPhon"),
        anchored("Plain edit distance also has the higher point estimate", iv["levenshtein"], "against", iv["pm-P5"]),
        anchored("released library reached a B-cubed F", f4(p5["bcubed_f_at_training_threshold"]["bcubed_f"][ROMANCE]),
                 "against", f4(sca["bcubed_f_at_training_threshold"]["bcubed_f"][ROMANCE]), "for SCA"),
        anchored(str(p5["skipped"]["words"][ROMANCE]), "of the", str(cognates["words"][ROMANCE]), "Romance words",
                 str(p5["skipped"]["pairs"][ROMANCE]), "of its", str(p5["skipped"]["pairs_in"][ROMANCE]), "word pairs"),
        anchored(str(p5["common"]["words_out"][ROMANCE]), "Romance words", "released library scores", f4(p5["common"]["average_precision"][ROMANCE]),
                 "SCA", f4(sca["common"]["average_precision"][ROMANCE])),
        anchored("Hillenbrand correlation rose from", f4(seen["hillenbrand"]["unread_at_1"]["score"]), "to 0.6394",
                 "Mandarin one from", f4(seen["mandarin"]["unread_at_1"]["score"]), "to 0.3395",
                 "Miller and Nicely one fell from", f4(seen["miller_nicely"]["unread_at_1"]["score"]), "to 0.2981"),
        anchored(str(control["segments_with_vector_difference"]), "of the", str(control["segments_read_by_both"]), "segments"),
        anchored("total weight,", f"{sum(WEIGHTS[:-len(TONE_FEATURES)]):g}"),
        anchored("vector of", str(len(FEATURES)), "features"),
        anchored(str(letters), "base letters", f"{3 * triples:,}", "inequalities over", f"{triples:,}", "triples", "875 violated"),
        anchored("scale marks changes each paired test score by less than", scale_mark_bound()),
        anchored("deletion or an insertion costs", f"{GAP_COST:g}"),
        anchored("default share,", f"{PhoneticFuzzySearch().cluster_sensitivity:g}"),
    ]


#: The names the paper gives the systems whose order it states.
PAPER_NAMES = {"pm-P5": "phonematcher", "phonematcher": "It", "sca": "SCA", "levenshtein": "plain edit distance", "aline": "ALINE"}


def retrieval_leader(systems=None):
    """The paper's name for the system with the highest mean recall@1 over the test pairs, on all queries."""
    pairs = results("retrieval-test.json")["pairs"].values()
    systems = systems or [name for name, _ in render.README_SYSTEMS]
    mean = {s: math.fsum(p["systems"][s]["all_items_unread_at_1"]["recall@1"] for p in pairs) for s in systems}
    best = max(mean, key=mean.get)
    return PAPER_NAMES.get(best, best)


def comparison(low_side, high_side, words):
    """``words[0]`` when the first interval lies wholly below the second, ``words[1]`` when wholly above, else ``words[2]``."""
    if low_side["high"] < high_side["low"]:
        return words[0]
    if low_side["low"] > high_side["high"]:
        return words[1]
    return words[2]


def order_sentences():
    """Each sentence of the paper that states an order between systems, with its order words taken from the files."""
    cognates, alignment = results("cognates-test.json"), results("alignment-test.json")
    iv, av = cognates["intervals"], alignment["intervals"]
    p5, sca = iv["pm-P5"], iv["sca"]
    common = {s: cognates["systems"][s]["common"]["average_precision"]["mean"] for s, _ in render.README_SYSTEMS}
    others = [s for s in common if s not in ("pm-P5", "sca")]
    panphon = cognates["paired"]["pm-panphon22"]
    tone = tone_scores()
    c0 = {"retrieval": results("retrieval-test.json")["intervals"], "alignment": av}
    first = [s for s, _ in render.README_SYSTEMS if s != "pm-P5"]
    skipped = {s: cognates["systems"][s]["skipped"]["words"][ROMANCE] for s in ("pm-P5", "panphon-weighted", "panphon-hamming", "aline")}
    overlap = "do not overlap" if p5["high"] < sca["low"] or p5["low"] > sca["high"] else "overlap"
    higher = lambda a, b: "higher" if a > b else "lower"  # noqa: E731
    clts = c0["retrieval"]["soundvectors"]
    c0_retrieval = c0["retrieval"]["phonematcher"]
    below = lambda other: "below" if iv["phonematcher"]["estimate"] < iv[other]["estimate"] else "not below"  # noqa: E731
    return [
        f"{retrieval_leader(first)} has the highest recall@1 on word retrieval across dialects",
        "its interval " + ("overlaps" if c0_retrieval["low"] <= clts["high"] and clts["low"] <= c0_retrieval["high"] else "does not overlap") + " that of CLTS sound vectors",
        f"This is {below('sca')} SCA at",
        f"On alignment, it is {'below' if all(av['phonematcher']['estimate'] < av[s]['estimate'] for s in ('sca', 'aline')) else 'not below'} SCA and ALINE, "
        f"and its interval lies {'below' if av['phonematcher']['high'] < av['sca']['low'] else 'not below'} that of SCA",
        f"PanPhon's own features scored {higher(panphon['diff'], 0)} than our full table on test cognates",
        "PanPhon's 22 features alone are " + comparison({"low": 0, "high": 0}, panphon, ("better", "worse", "not different from"))
        + " than our table on test cognates, and the interval is " + ("above" if panphon["low"] > 0 else "not above") + " zero",
        "The data does not show that our tone distance is " + ("better" if tone["phonematcher"]["score"] < tone["direction_baseline"]["score"] else "worse")
        + " than a baseline",
        "The data does not show that the tone distance is " + ("better" if tone["phonematcher"]["score"] < tone["direction_baseline"]["score"] else "worse")
        + " than a baseline",
        f"On the common words, phonematcher has a {higher(common['pm-P5'], common['sca'])} average precision than SCA. "
        f"It has a {higher(common['pm-P5'], max(common[s] for s in others))} average precision than all other systems.",
        f"On all words, phonematcher is {'worse' if p5['estimate'] < sca['estimate'] else 'better'} than SCA, and the intervals {overlap}.",
        f"On alignment, phonematcher is {'below' if all(av['pm-P5']['estimate'] < av[s]['estimate'] for s in ('sca', 'aline')) else 'not below'} "
        "SCA and ALINE on the point estimate.",
        "phonematcher is " + comparison(av["levenshtein"], av["pm-P5"], ("clearly better", "clearly worse", "not clearly different"))
        + " than plain edit distance.",
        "PanPhon and ALINE lose " + ("more" if min(skipped[s] for s in skipped if s != "pm-P5") > skipped["pm-P5"] else "not more")
        + " Romance words than phonematcher.",
        f"On cognate detection, SCA scores {higher(sca['estimate'], p5['estimate'])} than phonematcher on all words, "
        f"and the intervals {overlap}. On the common words, SCA scores {higher(common['sca'], common['pm-P5'])} only on the point estimate.",
    ]


def order_failures(text):
    return [sentence for sentence in order_sentences() if sentence not in text]


def anchor_failures(text):
    return [pattern.pattern for pattern in anchors() if not pattern.search(text)]


def prose_values():
    """Each prose number, computed from a result file or the library, with what it is."""
    cognates, alignment, retrieval = (results(f"{task}-test.json") for task in ("cognates", "alignment", "retrieval"))
    values = {
        f4(retrieval["intervals"]["phonematcher"]["estimate"]): "retrieval, original costs, test",
        f4(cognates["intervals"]["phonematcher"]["estimate"]): "cognates, original costs, test",
        f4(cognates["intervals"]["soundvectors"]["estimate"]): "cognates, CLTS sound vectors, test",
        f"{retrieval['index_cap']:,}": "words in the retrieval index",
        f4(tone_scores()["direction_baseline"]["score"]): "tone, direction baseline, seen",
        f4(tone_scores()["phonematcher"]["score"]): "tone, tone distance, seen",
        str(tone_scores()["direction_baseline"]["interval"]["undefined"]): "resamples with an undefined baseline correlation",
        f4(retrieval["intervals"]["pm-P5"]["estimate"]): "retrieval, P5, test",
        f4(cognates["intervals"]["pm-P5"]["estimate"]): "cognates, P5, test",
        f4(cognates["intervals"]["sca"]["estimate"]): "cognates, SCA, test",
        str(len(FEATURES)): "features in the table",
        str(len(FEATURES) - len(TONE_FEATURES)): "segment features in the table",
        str(FEATURES.index("velaric") + 1): "PanPhon columns of the table",
        f"{sum(WEIGHTS[:-len(TONE_FEATURES)]):g}": "total weight of the segment features",
        f"{GAP_COST:g}": "gap cost",
        f"{PhoneticFuzzySearch().cluster_sensitivity:g}": "default sensitivity",
        str(cognates["resamples"]): "bootstrap resamples",
    }
    with open(ROOT / "scripts" / "sources" / "ipa-vowel-chart.csv", encoding="utf8") as handle:
        values[str(len(list(csv.DictReader(handle))))] = "vowel letters of the chart"

    dev = results("retrieval-dev.json")["pairs"]
    by_share = {}
    for pair in dev.values():
        for row in pair["fuzzy_search"]:
            by_share.setdefault(row["sensitivity"], []).append(row["recall@1"])
    means = {share: math.fsum(r) / len(r) for share, r in by_share.items()}
    best = max(round(m, 4) for m in means.values())
    tied = sorted(share for share, m in means.items() if round(m, 4) == best)
    assert tied == [PhoneticFuzzySearch().cluster_sensitivity]
    values.update({f"{share:g}": "sensitivity with the best dev recall@1" for share in tied})
    values[f4(best)] = "best mean dev recall@1 of the fuzzy search"
    values["0.08"] = "sensitivity that rule 7 did not pick"
    values[f4(means[0.08])] = "mean dev recall@1 of the fuzzy search at share 0.08"

    samples = {system: {p["systems"][system]["sample"] for p in retrieval["pairs"].values()} for system in ("sca", "aline")}
    values.update({str(n): f"{system} retrieval sample" for system, (n,) in samples.items()})

    p5 = cognates["systems"]["pm-P5"]
    values[f4(p5["bcubed_f_at_training_threshold"]["bcubed_f"][ROMANCE])] = "Romance B-cubed F of P5"
    values[f4(cognates["systems"]["sca"]["bcubed_f_at_training_threshold"]["bcubed_f"][ROMANCE])] = "Romance B-cubed F of SCA"
    values[str(p5["skipped"]["words"][ROMANCE])] = "Romance words unread"
    values[str(cognates["words"][ROMANCE])] = "Romance words"
    values[str(p5["skipped"]["pairs"][ROMANCE])] = "Romance pairs at distance 1"
    values[str(p5["skipped"]["pairs_in"][ROMANCE])] = "Romance pairs"
    values[str(p5["common"]["words_out"][ROMANCE])] = "Romance words every system reads"
    values[f4(p5["common"]["average_precision"][ROMANCE])] = "Romance common AP of P5"
    values[f4(cognates["systems"]["sca"]["common"]["average_precision"][ROMANCE])] = "Romance common AP of SCA"

    values[str(results("tone-seen.json")["pairs"])] = "tone pairs"
    equal = equal_cost()
    for system, keys in (("phonematcher", ("cog_all", "cog_common", "pas", "recall")), ("soundvectors-p5", ("cog_all", "cog_common", "pas", "recall")),
                         ("panphon-weighted-p5", ("pas", "recall"))):
        for key in keys:
            values[f4(equal[system][key])] = f"{system}, {key}, equal costs, dev"
    values[scale_mark_bound()] = "bound on the paired test differences of the scale-mark variant"
    confusions = results("confusions-seen.json")["systems"]["phonematcher"]
    for name in ("hillenbrand", "mandarin", "miller_nicely"):
        values[f4(confusions[name]["unread_at_1"]["score"])] = f"{name} correlation of the library (seen)"
    control = results("ablations-seen.json")["control"]
    values[str(control["segments_with_vector_difference"])] = "segments with a changed PanPhon value"
    values[str(control["segments_read_by_both"])] = "segments both read"
    parts = {"CSV features": ("front", "tap", "trill"), "height steps": tuple(f"h{i}" for i in range(1, 7)),
             "tongue root": ("atr",), "secondary features": ("palatalized", "labialized", "velarized", "pharyngealized"),
             "tone features": TONE_FEATURES}
    assert all(name in FEATURES for names in parts.values() for name in names)
    assert FEATURES.index("velaric") + 1 + sum(len(names) for names in parts.values()) == len(FEATURES)
    values.update({str(len(names)): what for what, names in parts.items()})
    letters = len(_letter_costs()[0])
    triples = math.comb(letters, 3)
    values[str(letters)] = "base letters of the table"
    values[f"{triples:,}"] = "unordered triples of the base letters"
    values[f"{3 * triples:,}"] = "triangle inequalities of those triples"
    values[f"{cognates['intervals']['levenshtein']['estimate']:.4f}"] = "cognates, plain edit distance, test"
    weights = dict(zip(FEATURES, WEIGHTS))
    values.update({f"{weights['tense']:g}": "weight of tense", f"{weights['long']:g}": "weight of long"})
    return values


def test_the_tables_equal_a_fresh_render():
    assert render.fill_whitepaper(PAPER, render.whitepaper_blocks()) == PAPER
    assert render.main(["--check"]) == 0


def test_every_table_has_its_markers_and_holds_its_numbers():
    blocks = render.whitepaper_blocks()
    for name, block in blocks.items():
        assert f"<!-- whitepaper:{name}:start -->\n{block}<!-- whitepaper:{name}:end -->" in PAPER
    cognates = results("cognates-test.json")
    row = cognates["intervals"]["pm-P5"]
    assert f"{row['estimate']:.4f} [{row['low']:.4f}, {row['high']:.4f}]" in blocks["cognates"]
    assert f4(cognates["systems"]["pm-P5"]["common"]["average_precision"]["mean"]) in blocks["cognates"]


def test_check_fails_when_one_rendered_number_is_changed(tmp_path, capsys):
    cell = "| phonematcher, released costs | 0.9179 |"
    assert PAPER.count(cell) == 1
    changed = tmp_path / "whitepaper.md"
    changed.write_text(PAPER.replace(cell, cell.replace("0.9179", "0.9180")), encoding="utf8")
    assert render.main(["--check", "--whitepaper-file", str(render.WHITEPAPER)]) == 0
    assert render.main(["--check", "--whitepaper-file", str(changed)]) == 1
    assert "differs from a fresh render" in capsys.readouterr().err
    assert render.main(["--whitepaper", "--whitepaper-file", str(changed)]) == 0
    assert changed.read_text(encoding="utf8") == PAPER


def test_check_fails_when_a_marker_is_missing(tmp_path):
    changed = tmp_path / "whitepaper.md"
    changed.write_text(PAPER.replace("<!-- whitepaper:tone:end -->", ""), encoding="utf8")
    try:
        render.main(["--check", "--whitepaper-file", str(changed)])
    except SystemExit as stop:
        assert "whitepaper:tone:end" in str(stop)
    else:
        raise AssertionError("a missing marker passed the check")


def test_each_prose_number_is_computed_from_a_file_and_is_in_the_prose():
    text = prose()
    found = set(numbers(text))
    values = prose_values()
    for value, what in values.items():
        assert value in found, f"{what}: {value} is not in the prose"
    stray = found - set(values) - IDENTIFIERS - set(AUDIT)
    assert not stray, f"numbers in the prose with no file behind them: {sorted(stray)}"


def test_each_key_number_sits_beside_its_system_and_claim():
    assert anchor_failures(PAPER) == []


def test_a_swapped_system_or_value_fails_the_anchors():
    swaps = [
        ("precision is 0.7326. This is below SCA at 0.8835, plain edit distance at 0.8234", "precision is 0.8835. This is below SCA at 0.7326, plain edit distance at 0.8234"),
        ("On cognates, CLTS sound vectors score 0.7776 on all words and phonematcher 0.7876", "On cognates, CLTS sound vectors score 0.7876 on all words and phonematcher 0.7776"),
        ("On retrieval, phonematcher keeps the lead with 0.8736, against 0.8585", "On retrieval, phonematcher keeps the lead with 0.8585, against 0.8736"),
        ("library scores an average precision of 0.9812 and SCA 0.9877", "library scores an average precision of 0.9877 and SCA 0.9812"),
        ("0.8234 against 0.8035", "0.8035 against 0.8234"),
        ("0.3631 at its training threshold, against 0.8660 for SCA", "0.8660 at its training threshold, against 0.3631 for SCA"),
    ]
    for old, new in swaps:
        assert PAPER.count(old) == 1, old
        assert anchor_failures(PAPER.replace(old, new)), f"the swap {new!r} passed"


def test_each_order_sentence_states_the_order_of_the_files():
    assert order_failures(PAPER) == []


def test_a_reversed_order_sentence_fails():
    reversals = [
        ("It has the highest recall@1 on word retrieval across dialects", "SCA has the highest recall@1 on word retrieval across dialects"),
        ("PanPhon's own features scored higher than our full table", "PanPhon's own features scored lower than our full table"),
        ("PanPhon's 22 features alone are better than our table", "PanPhon's 22 features alone are worse than our table"),
        ("This is below SCA at", "This is above SCA at"),
        ("its interval overlaps that of CLTS sound vectors", "its interval does not overlap that of CLTS sound vectors"),
        ("On alignment, it is below SCA and ALINE", "On alignment, it is above SCA and ALINE"),
        ("The data does not show that our tone distance is better", "The data does not show that our tone distance is worse"),
        ("The data does not show that the tone distance is better", "The data does not show that the tone distance is worse"),
        ("phonematcher has a lower average precision than SCA", "phonematcher has a higher average precision than SCA"),
        ("It has a higher average precision than all other systems", "It has a lower average precision than all other systems"),
        ("On all words, phonematcher is worse than SCA", "On all words, phonematcher is better than SCA"),
        ("On alignment, phonematcher is below SCA and ALINE on the point estimate", "On alignment, phonematcher is above SCA and ALINE on the point estimate"),
        ("phonematcher is clearly better than plain edit distance", "phonematcher is clearly worse than plain edit distance"),
        ("PanPhon and ALINE lose more Romance words", "PanPhon and ALINE lose fewer Romance words"),
        ("SCA scores higher than phonematcher on all words", "SCA scores lower than phonematcher on all words"),
        ("On the common words, SCA scores higher only", "On the common words, SCA scores lower only"),
    ]
    for old, new in reversals:
        assert PAPER.count(old) == 1, old
        changed = PAPER.replace(old, new)
        assert order_failures(changed) or anchor_failures(changed), f"the reversal {new!r} passed"


def test_each_audit_number_is_marked_and_its_run_is_named():
    paragraphs = prose().split("\n\n")
    for value, source in AUDIT.items():
        paragraph = next(p for p in paragraphs if value in numbers(p))
        assert "audit run" in paragraph, f"{value} ({source}) is stated without saying it is an audit run"
    reproducibility = PAPER.split("## 9. Reproducibility")[1].split("## 10.")[0]
    assert "`ecde385`" in reproducibility and "`3a134ef`" in reproducibility and "scripts/fit_weights.py" in reproducibility


def test_the_identifiers_match_their_sources():
    assert metadata.version("panphon") == "0.22.2" and "PanPhon 0.22.2" in PAPER
    assert "192607" in results("cognates-test.json")["source"]
    assert "Zenodo record 192607" in PAPER


def test_panphon_applies_its_weights_in_its_own_order():
    import panphon

    data = Path(panphon.__file__).parent / "data" / "feature_weights.csv"
    names, weights = data.read_text(encoding="utf8").split()
    by_name = dict(zip(names.split(","), map(float, weights.split(","))))
    applied = dict(zip(panphon.FeatureTable().names, panphon.FeatureTable().weights))
    assert (by_name["tense"], by_name["long"], by_name["velaric"]) == (0.25, 0.125, 0.25)
    assert (applied["velaric"], applied["tense"], applied["long"]) == (0.25, 0.125, 0.25)
    assert "`tense` 0.25, `long` 0.125 and `velaric` 0.25" in PAPER
    assert "0.25 to `velaric`, 0.125 to `tense` and 0.25 to `long`" in PAPER
    assert dict(zip(FEATURES, WEIGHTS))["tense"] == by_name["tense"]


def test_the_stated_orders_hold_in_the_test_files():
    cognates, alignment, retrieval = (results(f"{task}-test.json") for task in ("cognates", "alignment", "retrieval"))
    systems = [name for name, _ in render.README_SYSTEMS]
    # Cognates: P5 trails SCA with no overlap; it overlaps plain edit distance; on the common words only SCA is above it.
    iv = cognates["intervals"]
    assert iv["pm-P5"]["high"] < iv["sca"]["low"]
    assert iv["pm-P5"]["high"] > iv["levenshtein"]["low"]
    common = {s: cognates["systems"][s]["common"]["average_precision"]["mean"] for s in systems}
    assert sorted(common, key=common.get)[-2:] == ["pm-P5", "sca"]
    # Alignment: P5 below SCA and ALINE with overlap; above plain edit distance with no overlap.
    av = alignment["intervals"]
    for other in ("sca", "aline"):
        assert av["pm-P5"]["estimate"] < av[other]["estimate"] and av["pm-P5"]["high"] > av[other]["low"]
    assert av["pm-P5"]["low"] > av["levenshtein"]["high"]
    # Retrieval: P5 highest on all, common and shared queries.
    pairs = retrieval["pairs"].values()
    for view in ("all_items_unread_at_1", "common_subset", "on_shared_queries"):
        mean = {s: math.fsum(p["systems"][s][view]["recall@1"] for p in pairs) for s in systems}
        assert max(mean, key=mean.get) == "pm-P5", view
    assert "pm-P5" in retrieval["paired"] and "sca" not in retrieval["paired"] and "aline" not in retrieval["paired"]
    # P5 gained more than P4 on each task, and C3 lost on each.
    for payload in (cognates, alignment, retrieval):
        assert payload["paired"]["pm-P5"]["diff"] > payload["paired"]["pm-P4"]["diff"] > 0
        assert payload["paired"]["pm-C3"]["high"] < 0
    # Seven systems ran beside the variants and candidates.
    assert len([s for s in systems if s != "pm-P5"]) == 7 and "Seven systems ran" in PAPER


def test_the_null_and_negative_results_hold():
    cognates, alignment = results("cognates-test.json"), results("alignment-test.json")
    flat = [cognates["paired"]["pm-flat-diacritics"], alignment["paired"]["pm-flat-diacritics"]]
    assert all(abs(row["diff"]) < 1e-4 for row in flat)
    assert cognates["paired"]["pm-panphon22"]["low"] > 0
    tone = results("tone-seen.json")["scored"]["main"]
    assert tone["phonematcher"]["score"] < tone["direction_baseline"]["score"]
    assert tone["phonematcher"]["interval"]["high"] > tone["direction_baseline"]["interval"]["low"]
    height = json.loads((RESULTS / "ablations" / "vowel-height-dev.json").read_text(encoding="utf8"))
    assert height["cognates"]["paired"]["pm-F1-segment"]["high"] < 0
    seen = results("ablations-seen.json")["tasks"]["confusions"]["systems"]
    spans = [seen[s]["hillenbrand"]["unread_at_1"]["interval"] for s in ("phonematcher", "pm-p5-panphon22")]
    assert spans[0]["low"] < spans[1]["high"]


def test_only_the_test_files_carry_a_clean_commit():
    for path in sorted(RESULTS.glob("*-*.json")):
        payload = json.loads(path.read_text(encoding="utf8"))
        if payload.get("split") == "test":
            assert payload["commit"] == "f092f20c8bbe0aa49a6480946858c0354a2580a9"
            assert payload["prereg_sha256"] == "29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c"
        else:
            assert "prereg_sha256" not in payload, path.name
    development = [json.loads(p.read_text(encoding="utf8")) for p in sorted(RESULTS.glob("*-*.json"))]
    development = [p for p in development if p.get("split") in ("seen", "dev") and p["task"] != "equal-cost"]
    older = {"retrieval-dev.json": "4f254da108460c3a56c25c482751aa0cae11fe1c"}  # ALINE and SCA take many hours; section 8 says so
    heads = {p.get("head") or p.get("commit") for p in development if p["task"] + "-" + p["split"] + ".json" not in older}
    assert len(heads) == 1 and all(p.get("tree_dirty") is not True for p in development)
    for name, head in older.items():
        assert json.loads((RESULTS / name).read_text(encoding="utf8"))["head"] == head
        assert f"`{head[:7]}`" in PAPER
    assert f"`{heads.pop()[:7]}`" in PAPER
    equal = json.loads((RESULTS / "equal-cost-dev.json").read_text(encoding="utf8"))
    assert equal["head"] == "22f3615241dfb85b5404e5df041af520128ec352" and equal["tree_dirty"] is True  # section 8 says so
    assert f"`{equal['head'][:7]}`" in PAPER
    assert "`f092f20c8bbe0aa49a6480946858c0354a2580a9`" in PAPER
    assert "`29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c`" in PAPER


def test_each_reference_is_cited_and_each_citation_has_a_reference():
    body, references = PAPER.split("## 10. References")
    entries = re.findall(r"^- (.+)$", references, flags=re.M)
    assert entries == sorted(entries)
    listed = set()
    for entry in entries:
        surname, year = re.match(r"[\w-]+", entry).group(), re.search(r"\b((?:19|20)\d\d)\.", entry).group(1)
        listed.add((surname, year))
        assert re.search(re.escape(surname) + r"[^()\d]{0,40}?\(?" + year, body), f"{surname} {year} is not cited"
        assert re.search(r"<https?://[^>]+>$", entry), f"{surname} {year} has no link"
    cited = set(re.findall(r"([A-Z][\w-]+)(?: et al\.)?[^()\d.]{0,40}?\(?((?:19|20)\d\d)\b", body))
    assert len(cited) == len(listed)
    assert cited <= listed, f"cited with no reference: {sorted(cited - listed)}"


def test_the_readme_and_the_index_link_the_paper():
    assert "(whitepaper.md)" in (ROOT / "README.md").read_text(encoding="utf8")
    assert "(../whitepaper.md)" in (ROOT / "docs" / "index.md").read_text(encoding="utf8")


def test_equal_costs_give_every_feature_system_a_gain_and_the_table_no_clear_lead():
    equal = equal_cost()
    for released, plain in (("phonematcher", "pm-C0"), ("panphon-weighted-p5", "panphon-weighted"), ("soundvectors-p5", "soundvectors")):
        for key in ("cog_all", "pas", "recall"):
            assert equal[released][key] > equal[plain][key], (released, key)
    gain = {s: {k: equal[s][k] - equal[p][k] for k in ("cog_all", "recall")}
            for s, p in (("phonematcher", "pm-C0"), ("soundvectors-p5", "soundvectors"))}
    for key in ("cog_all", "recall"):
        assert abs(gain["phonematcher"][key] - gain["soundvectors-p5"][key]) < 0.005, key
    assert equal["soundvectors-p5"]["cog_common"] > equal["phonematcher"]["cog_common"]
    assert equal["phonematcher"]["recall"] == max(row["recall"] for row in equal.values())
    assert abs(equal["panphon-weighted-p5"]["pas"] - equal["phonematcher"]["pas"]) < 0.001
    assert equal["soundvectors-p5"]["pas"] < equal["phonematcher"]["pas"]
    assert "Every feature system gains from the released costs on all three tasks" in PAPER
    assert "nearly the same amount" in PAPER
