"""``benchmarks/render.py``: the page is a function of the result files, and ``--check`` finds a page that is not.

The expected strings are built from the numbers in the result files, formatted as the page formats
them, not copied from the page.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parent.parent / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))

import render  # noqa: E402
import variants  # noqa: E402

SYSTEMS = ["phonematcher", *variants.CANDIDATES]


@pytest.fixture
def results(tmp_path):
    """A copy of the committed result files."""
    folder = tmp_path / "results"
    shutil.copytree(render.RESULTS, folder)
    return folder


def committed(name):
    return json.loads((render.RESULTS / name).read_text(encoding="utf8"))


def test_the_committed_page_is_a_fresh_render_of_the_committed_results():
    assert render.PAGE.read_text(encoding="utf8") == render.render(render.RESULTS)
    assert render.main(["--check"]) == 0


def test_each_committed_test_file_comes_from_the_registered_run():
    # The single run: commit f092f20 and the registered page, for the three tasks the page names.
    files = sorted(render.RESULTS.glob("*-test.json"))
    assert [f.name for f in files] == ["alignment-test.json", "cognates-test.json", "retrieval-test.json"]
    for path in files:
        payload = json.loads(path.read_text(encoding="utf8"))
        assert payload["split"] == "test"
        assert payload["commit"] == "f092f20c8bbe0aa49a6480946858c0354a2580a9"
        assert payload["prereg_sha256"] == "29927d4e0e8162276cf12c68450a3b28372dc039d3a24377bbf390a64bd2df7c"


def test_an_alignment_row_holds_the_numbers_of_its_file(results):
    row = committed("alignment-dev.json")["all"]["systems"]["phonematcher"]
    expected = f"| phonematcher | {row['n_scored']} of {row['n_in']} | {row['common_pas']:.4f} | {row['common_cs']:.4f} | {row['unread_at_zero_pas']:.4f} |"
    assert expected in render.render(results)


def test_a_cognate_row_holds_the_numbers_of_its_file(results):
    row = committed("cognates-dev.json")["systems"]["sca"]
    expected = (f"| sca | {row['unread_at_1']['average_precision']['mean']:.4f} | {row['unread_at_1']['bcubed_f']['mean']:.4f} | "
                f"{row['common']['average_precision']['mean']:.4f} | {row['common']['bcubed_f']['mean']:.4f} |")
    assert expected in render.render(results)


def test_a_retrieval_row_holds_the_recall_of_each_pair_and_their_mean(results):
    payload = committed("retrieval-dev.json")
    recalls = [pair["systems"]["levenshtein"]["all_items_unread_at_1"]["recall@1"] for pair in payload["pairs"].values()]
    cells = " | ".join(f"{r:.4f}" for r in recalls)
    assert f"| levenshtein | {cells} | {sum(recalls) / len(recalls):.4f} |" in render.render(results)


def test_a_changed_number_changes_the_page(results):
    path = results / "alignment-dev.json"
    payload = json.loads(path.read_text(encoding="utf8"))
    payload["all"]["systems"]["phonematcher"]["common_pas"] = 0.1234
    path.write_text(json.dumps(payload), encoding="utf8")
    assert "| 0.1234 |" in render.render(results)
    assert "| 0.1234 |" not in render.PAGE.read_text(encoding="utf8")


def test_check_fails_for_a_page_that_differs_and_for_a_missing_page(results, tmp_path, capsys):
    page = tmp_path / "page.md"
    args = ["--check", "--results", str(results), "--page", str(page)]
    assert render.main(args) == 1
    assert render.main(["--results", str(results), "--page", str(page)]) == 0
    assert render.main(args) == 0
    page.write_text(page.read_text(encoding="utf8").replace("0.", "1.", 1), encoding="utf8")
    assert render.main(args) == 1
    assert "differs from a fresh render" in capsys.readouterr().err


def test_check_fails_when_a_result_file_changes_after_the_page_was_written(results, tmp_path):
    page = tmp_path / "page.md"
    render.main(["--results", str(results), "--page", str(page)])
    path = results / "alignment-dev.json"
    payload = json.loads(path.read_text(encoding="utf8"))
    payload["all"]["systems"]["phonematcher"]["common_pas"] = 0.5
    path.write_text(json.dumps(payload), encoding="utf8")
    assert render.main(["--check", "--results", str(results), "--page", str(page)]) == 1


def interval(estimate):
    return {"estimate": estimate, "low": estimate - 0.01, "high": estimate + 0.01}


def paired(diff, low=None):
    return {"diff": diff, "low": diff - 0.01 if low is None else low, "high": diff + 0.01}


def candidates():
    return {n.removeprefix("pm-"): {"system": n, "k1": n != "pm-C1", **({"major_class_weight": 1.38} if n == "pm-C3" else {})} for n in variants.CANDIDATES}


def write_test_files(folder, c4_low):
    head = "a" * 40
    diffs = {n: paired(0.02, c4_low if n == "pm-P5" else -0.5) for n in variants.CANDIDATES}
    systems = {n: {"bcubed_f_at_training_threshold": {"bcubed_f": {"mean": 0.5 + i / 100}}} for i, n in enumerate(SYSTEMS)}
    intervals = {n: interval(0.6 + i / 100) for i, n in enumerate(SYSTEMS)}
    files = {
        "cognates": {"systems": systems},
        "alignment": {"n_items": 9, "all": {"n_common": 7, "systems": {
            n: {"n_scored": 8, "n_in": 9, "common_pas": 0.7, "common_cs": 0.8, "unread_at_zero_pas": 0.6} for n in SYSTEMS}}},
        "retrieval": {"pairs": {"en-US-UK": {"fuzzy_search": None, "systems": {
            n: {"queries_scored": 11, "all_items_unread_at_1": {"recall@1": 0.5, "recall@10": 0.9, "mrr": 0.6}} for n in SYSTEMS}}}},
    }
    for task, body in files.items():
        payload = {"task": task, "split": "test", "commit": head, "candidates": candidates(),
                   "intervals": intervals, "paired": {n: dict(d) for n, d in diffs.items()}, **body}
        (folder / f"{task}-test.json").write_text(json.dumps(payload), encoding="utf8")


def test_the_test_files_render_with_intervals_differences_and_the_decision(results):
    write_test_files(results, c4_low=0.01)
    page = render.render(results)
    assert "## Test split" in page and "Commit `aaaaaaaaaaaa`." in page
    assert "| pm-P5 | 0.6500 [0.6400, 0.6600] | +0.0200 [+0.0100, +0.0300] | 0.5500 |" in page
    assert "| C3 | pm-C3 | yes | syl, son and cons at 1.38 |" in page
    assert "| C1 | pm-C1 | no | - |" in page
    assert "C1: out by rule 1, K1 fails" in page
    assert "Weights and gap cost after the test: P5." in page


def test_the_decision_keeps_c0_when_no_candidate_beats_it(results):
    write_test_files(results, c4_low=-0.5)
    assert "Weights and gap cost after the test: C0." in render.render(results)


def test_the_decision_waits_for_all_three_test_files(results):
    write_test_files(results, c4_low=0.01)
    (results / "retrieval-test.json").unlink()
    page = render.render(results)
    assert "## Test split" in page and "### Decision" not in page


def test_the_speed_file_renders_its_medians_and_matrix_hash():
    payload = json.loads((render.RESULTS / "speed.json").read_text(encoding="utf8"))
    page = render.render(render.RESULTS)
    assert payload["matrix_sha256"] in page
    row = f"{payload['median']['segment_per_second']:.6g} |"
    assert f"| segment_per_second | {payload['before']['median']['segment_per_second']:.6g} | {row}" in page


def test_a_speed_file_without_before_renders_one_column():
    payload = {"machine": {"cpu": "c", "cores": 1, "python": "3"}, "head": "a" * 40, "pair_count": 4, "matrix_sha256": "h",
               "runs": [{"load_at_start": "0.50"}], "median": {"segment_per_second": 10.0}}
    lines = render.speed_section(payload)
    assert "| segment_per_second | 10 |" in lines
    assert "| Measure | Median |" in lines


README = render.README


def test_the_readme_table_holds_the_test_intervals_of_each_system_and_bolds_the_best():
    tests = {task: committed(f"{task}-test.json")["intervals"] for task in ("cognates", "alignment", "retrieval")}
    table = render.readme_table(render.RESULTS)

    def cell(task, system):
        row = tests[task][system]
        return f"{row['estimate']:.4f} [{row['low']:.4f}, {row['high']:.4f}]"

    for task, best in (("cognates", "sca"), ("alignment", "sca"), ("retrieval", "pm-P5")):
        assert f"**{cell(task, best)}**" in table
    assert f"| ALINE | {cell('cognates', 'aline')} | {cell('alignment', 'aline')} | {cell('retrieval', 'aline')} |" in table
    assert "| PanPhon, weighted | " + cell("cognates", "panphon-weighted") + " | — | " + cell("retrieval", "panphon-weighted") + " |" in table
    assert table.count("**") == 6
    assert "[docs/benchmarks.md](docs/benchmarks.md)" in table and "run once" in table and "did not change any word distance" in table


def test_the_readme_block_equals_the_rendered_table():
    block = render.readme_block(README.read_text(encoding="utf8"))
    assert block == render.readme_table(render.RESULTS)
    assert block == subprocess.run([sys.executable, str(BENCHMARKS / "render.py"), "--readme"], capture_output=True, text=True, check=True).stdout


def test_check_fails_when_one_number_of_the_readme_table_is_changed(tmp_path, capsys):
    text = README.read_text(encoding="utf8")
    changed = tmp_path / "README.md"
    changed.write_text(text.replace("0.8777 [0.8706", "0.8778 [0.8706", 1), encoding="utf8")
    assert changed.read_text(encoding="utf8") != text
    assert render.main(["--check", "--readme-file", str(README)]) == 0
    assert render.main(["--check", "--readme-file", str(changed)]) == 1
    assert "differs from a fresh render" in capsys.readouterr().err


def test_no_word_distance_moves_without_this_pin_and_the_readme_caption_changing():
    # The README caption says that the dev-only changes of the library did not change any word distance.
    # A change that moves one distance also changes this digest: update it together with the caption.
    import hashlib
    import random

    from phonematcher import ipa_distance
    from phonematcher.features import _DATA

    letters = sorted(_DATA["phones"])
    rng = random.Random(0)
    words = ["".join(rng.choice(letters) for _ in range(rng.randint(1, 8))) for _ in range(2000)]
    digest = hashlib.sha256("\n".join(f"{a} {b} {ipa_distance(a, b):.12f}" for a, b in zip(words[::2], words[1::2])).encode("utf8")).hexdigest()
    assert digest == "332c4f15a4fd50e616f8d4ae565b61b968859f6132c9016bb29fba6002d0058b"


def test_each_ablation_table_names_its_cost_rule():
    dev = render.ablations_section({"systems": ["phonematcher", "pm-p5-uniform"], "tasks": {}})
    old = render.ablations_section({"systems": ["phonematcher", "pm-uniform"], "tasks": {}})
    seen = render.ablations_section(committed("ablations-seen.json"))
    assert dev[0].startswith("Cost rule: the shipped P5 costs, gap 0.5") and "square root" in dev[0]
    assert old[0].startswith("Cost rule: the C0 costs, gap 1 and linear")
    assert seen[0].startswith("Cost rule: none matters here")
    committed_dev = committed("ablations-dev.json")
    assert all(name == "phonematcher" or name.startswith("pm-p5-") for name in committed_dev["systems"])
    assert render.ablations_section(committed_dev)[0] == render.P5_NOTE
