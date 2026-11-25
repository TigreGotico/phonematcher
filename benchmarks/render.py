"""Render ``docs/benchmarks.md`` from the result files in ``benchmarks/results``.

    python benchmarks/render.py            # write docs/benchmarks.md
    python benchmarks/render.py --check    # exit 1 when docs/benchmarks.md, the README table, a whitepaper table or a design table differs from a fresh render
    python benchmarks/render.py --readme   # print the summary table of the README
    python benchmarks/render.py --whitepaper   # rewrite the marked tables of whitepaper.md
    python benchmarks/render.py --design   # rewrite the marked tables of docs/design.md

Every number in the page comes from a result file. The files of the ``seen`` and ``dev`` splits
are always rendered; the files of the ``test`` split are rendered when they exist.
"""
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import final  # noqa: E402
from tasks import ablations, allophones, confusions, coverage, tone  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "benchmarks" / "results"
PAGE = ROOT / "docs" / "benchmarks.md"
README = ROOT / "README.md"
WHITEPAPER = ROOT / "whitepaper.md"
DESIGN = ROOT / "docs" / "design.md"
README_START = "<!-- benchmark-table:start -->"
README_END = "<!-- benchmark-table:end -->"

SPLIT_TITLES = {
    "seen": "Seen data",
    "dev": "Development split",
    "test": "Test split",
}
SPLIT_TEXT = {
    "seen": "These data were inspected while the weights were fitted. The scores are descriptions, not tests.",
    "dev": "The development split holds the items that `benchmarks/split.py` assigns to dev. Weights, indel costs and sensitivities were chosen on it.",
    "test": "The test split ran once, from a clean tree, under the pre-registration in `benchmarks/prereg-2.md`. "
    "The rows `phonematcher` and `pm-` followed by a variant name (`pm-panphon22`, `pm-no-height`, `pm-flat-diacritics`, `pm-uniform`, `pm-indel-0.5`, `pm-indel-1.5`) use the C0 costs: gap 1 and linear substitutions. "
    "The candidate rows `pm-C1` to `pm-P5` carry their own costs, and `pm-P5` is the shipped library.",
}
C0_NOTE = ("Cost rule: the C0 costs, gap 1 and linear substitutions. The rows are compared with each other, not with the shipped library, "
           "which prices a word at the P5 costs.")
P5_NOTE = ("Cost rule: the shipped P5 costs, gap 0.5 and substitutions at the square root of the feature distance. "
           "`phonematcher` is the shipped library, and each `pm-p5-` row changes one thing in it. "
           "`pm-p5-indel-0.5` is the shipped costs again and serves as a control.")
SEEN_NOTE = ("Cost rule: none matters here. Each score ranks pairs of segments by their segment distance, and the square root keeps that order, "
             "so the C0 costs and the P5 costs give the same rows.")
TASK_ORDER = ["coverage", "allophones", "confusions", "tone", "cognates", "cognates-toneless", "alignment", "retrieval", "ablations"]


def num(value: Optional[float], digits: int = 4) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def span(row: dict) -> str:
    return f"{row['estimate']:.4f} [{row['low']:.4f}, {row['high']:.4f}]"


def difference(row: dict) -> str:
    return f"{row['diff']:+.4f} [{row['low']:+.4f}, {row['high']:+.4f}]"


def table(head: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    return ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|", *("| " + " | ".join(r) + " |" for r in rows), ""]


def text_block(lines: Sequence[str]) -> List[str]:
    return ["```text", *lines, "```", ""]


def candidate_rows(payload: dict) -> List[str]:
    rows = []
    for name, row in payload["candidates"].items():
        weight = f", syl, son and cons at {row['major_class_weight']}" if "major_class_weight" in row else ""
        rows.append([name, row["system"], "yes" if row["k1"] else "no", weight.lstrip(", ") or "-"])
    return ["Candidates and rule 1 (constraint K1):", "", *table(["Id", "System", "K1 holds", "Weight found"], rows)]


def cognates_table(payload: dict) -> List[str]:
    if "intervals" in payload:
        rows = []
        for name, entry in payload["systems"].items():
            rows.append([
                name, span(payload["intervals"][name]),
                difference(payload["paired"][name]) if name in payload["paired"] else "-",
                num(entry["bcubed_f_at_training_threshold"]["bcubed_f"]["mean"]),
            ])
        return [*table(["System", "Mean AP [95% interval]", "AP minus phonematcher", "Mean B-cubed F at the training threshold"], rows),
                *candidate_rows(payload)]
    rows = []
    for name, entry in payload["systems"].items():
        row = [name]
        for label in ("unread_at_1", "common"):
            part = entry[label]
            row += [num(part and part["average_precision"]["mean"]), num(part and part["bcubed_f"]["mean"])]
        row.append(str(sum(entry["skipped"]["words"].values())))
        rows.append(row)
    return table(["System", "AP, unread at 1", "F, unread at 1", "AP, common words", "F, common words", "Words skipped"], rows)


def alignment_table(payload: dict) -> List[str]:
    rows = []
    for name, entry in payload["all"]["systems"].items():
        row = [name, f"{entry['n_scored']} of {entry['n_in']}", num(entry["common_pas"]), num(entry["common_cs"]), num(entry["unread_at_zero_pas"])]
        if "intervals" in payload:
            row[2:3] = [span(payload["intervals"][name]), difference(payload["paired"][name]) if name in payload["paired"] else "-"]
        rows.append(row)
    head = ["System", "Pairs read", "PAS, common pairs", "CS, common pairs", "PAS, unread at 0"]
    if "intervals" in payload:
        head[2:3] = ["PAS, common pairs [95% interval]", "PAS minus phonematcher"]
    return [f"Common pairs: {payload['all']['n_common']} of {payload['n_items']}.", "",
            *table(head, rows)]


def retrieval_table(payload: dict) -> List[str]:
    pairs = list(payload["pairs"])
    systems = list(next(iter(payload["pairs"].values()))["systems"])

    def mean(system: str, key: str) -> float:
        return math.fsum(payload["pairs"][p]["systems"][system]["all_items_unread_at_1"][key] for p in pairs) / len(pairs)

    rows = []
    for name in systems:
        row = [name, *(num(payload["pairs"][p]["systems"][name]["all_items_unread_at_1"]["recall@1"]) for p in pairs),
               num(mean(name, "recall@1")), num(mean(name, "recall@10")), num(mean(name, "mrr")),
               "/".join(str(payload["pairs"][p]["systems"][name]["queries_scored"]) for p in pairs)]
        if "intervals" in payload:
            row[len(pairs) + 1] = span(payload["intervals"][name])
            row.insert(len(pairs) + 2, difference(payload["paired"][name]) if name in payload["paired"] else "-")
        rows.append(row)
    head = ["System", *pairs, "Mean recall@1", "Mean recall@10", "Mean MRR", "Queries per pair"]
    if "intervals" in payload:
        head[len(pairs) + 1:len(pairs) + 2] = ["Mean recall@1 [95% interval]", "Minus phonematcher"]
    out = table(head, rows)
    fuzzy = [[p, str(r["sensitivity"]), num(r["candidate_recall"]), f"{r['mean_candidates']:.1f}", num(r["recall@1"])]
             for p in pairs for r in payload["pairs"][p]["fuzzy_search"] or []]
    if fuzzy:
        out += ["Fuzzy search of phonematcher:", "", *table(["Pair", "Sensitivity", "Candidate recall", "Mean candidates", "Recall@1"], fuzzy)]
    return out


def ablations_section(payload: dict) -> List[str]:
    if "control" in payload:
        out = [SEEN_NOTE, ""]
    else:
        out = [P5_NOTE if any(name.startswith("pm-p5-") for name in payload["systems"]) else C0_NOTE, ""]
    for task in TASK_ORDER:
        if task in payload["tasks"] and task != "ablations":
            out += [f"#### {task}", "", *TASKS[task](payload["tasks"][task])]
    controls = [line for line in ablations.lines(payload) if line.startswith("[control]")]
    return out + (["#### control", "", *text_block(controls)] if controls else [])


def lines_block(module) -> Callable[[dict], List[str]]:
    return lambda payload: text_block(module.lines(payload))


TASKS: Dict[str, Callable[[dict], List[str]]] = {
    "coverage": lines_block(coverage),
    "allophones": lines_block(allophones),
    "confusions": lines_block(confusions),
    "tone": lines_block(tone),
    "cognates": cognates_table,
    "cognates-toneless": cognates_table,
    "alignment": alignment_table,
    "retrieval": retrieval_table,
    "ablations": ablations_section,
}


def load_results(directory: Path) -> Dict[str, Dict[str, dict]]:
    """``split -> task -> payload`` for every ``<task>-<split>.json`` in *directory*."""
    found: Dict[str, Dict[str, dict]] = {}
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf8"))
        found.setdefault(payload.get("split", ""), {})[payload["task"]] = payload
    return found


def provenance(payload: dict) -> str:
    head = payload.get("commit") or payload.get("head")
    return f"Commit `{head[:12]}`." if head else ""


def decision_section(tests: Dict[str, dict]) -> List[str]:
    if not all(task in tests for task in final.TASKS):
        return []
    outcome = final.decide({
        name: {"k1": row["k1"], **{task: tests[task]["paired"][row["system"]] for task in final.TASKS}}
        for name, row in tests["cognates"]["candidates"].items()
    })
    return ["### Decision", "", *[f"- {reason}" for reason in outcome["reasons"]], "", f"Weights and gap cost after the test: {outcome['winner']}.", ""]


def load_list(block: dict) -> str:
    return ", ".join(run["load_at_start"] for run in block["runs"])


def speed_section(payload: dict) -> List[str]:
    machine = payload["machine"]
    after = flatten(payload["median"])
    before = flatten(payload["before"]["median"]) if "before" in payload else {}
    intro = f"Median of {len(payload['runs'])} runs on {machine['cpu']}, {machine['cores']} cores, Python {machine['python']}. "
    if before:
        intro += (f"Both columns start from commit `{payload['before']['head'][:12]}`. The After column adds the change under test. "
                  f"Load average at the start of each run: {load_list(payload['before'])} before; {load_list(payload)} after.")
        header = ["| Measure | Before | After |", "|---|---|---|"]
        rows = [f"| {name} | {before[name]:.6g} | {value:.6g} |" for name, value in sorted(after.items())]
    else:
        intro += f"{provenance(payload)} Load average at the start of each run: {load_list(payload)}."
        header = ["| Measure | Median |", "|---|---|"]
        rows = [f"| {name} | {value:.6g} |" for name, value in sorted(after.items())]
    same = before and payload["before"]["matrix_sha256"] == payload["matrix_sha256"]
    return ["## Speed", "", intro, "",
            f"The distance matrix of {payload['pair_count']} ordered letter pairs has sha256 `{payload['matrix_sha256']}`"
            + (", before and after." if same else "."), "",
            "A cold figure is the first pass over its input from empty caches. A warm figure is a second pass over the same input.", "",
            *header, *rows, ""]


def flatten(tree: dict, prefix: str = "") -> Dict[str, float]:
    """``a.b -> value`` for every number in a nested dict."""
    flat: Dict[str, float] = {}
    for key, value in tree.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, name + "."))
        elif isinstance(value, (int, float)):
            flat[name] = value
    return flat


FOOTER = "[Index](index.md) · Previous: [API reference](api.md)"


def test_figure(tests: Dict[str, dict]) -> List[str]:
    """The figure of the test split, with alt text read from the same result files."""
    parts = []
    for task, title in README_COLUMNS:
        cells = tests[task]["intervals"]
        best = max(cells, key=lambda s: cells[s]["estimate"])
        lead = "the best" if best == "pm-P5" else f"best {best} {cells[best]['estimate']:.2f}"
        parts.append(f"{title}: P5 {cells['pm-P5']['estimate']:.2f}, {lead}")
    return [
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset="img/test-split-dark.svg">',
        f'  <img alt="Test split by task. {". ".join(parts)}." src="img/test-split.svg">',
        "</picture>",
        "",
        "`img/plot_test_split.py` makes this figure from `benchmarks/results/*-test.json`.",
        "",
    ]


def render(directory: Path = RESULTS) -> str:
    results = load_results(directory)
    out = [
        "# Benchmarks",
        "<!-- agent-hint",
        "covers: every benchmark result of phonematcher and of the systems it is compared with",
        "source: benchmarks/results/*.json, benchmarks/render.py",
        "generated: yes, by benchmarks/render.py; edit the generator, not the page",
        "verify: python benchmarks/render.py --check",
        "see: search.md, compare-words.md, ../benchmarks/README.md",
        "-->",
        "",
        "This page is generated by `benchmarks/render.py` from `benchmarks/results/*.json`. Each number comes from a result file.",
        "",
    ]
    for split, title in SPLIT_TITLES.items():
        if split not in results:
            continue
        out += [f"## {title}", "", SPLIT_TEXT[split], ""]
        if split == "test":
            out += test_figure(results[split])
        for task in TASK_ORDER:
            if task in results[split]:
                payload = results[split][task]
                out += [f"### {task}", "", provenance(payload), "", *TASKS[task](payload)]
        if split == "test":
            out += decision_section(results[split])
    if "speed" in results.get("", {}):
        out += speed_section(results[""]["speed"])
    out += ["", FOOTER]
    return "\n".join(line for i, line in enumerate(out) if line or i == 0 or out[i - 1]).rstrip("\n") + "\n"


README_SYSTEMS = [
    ("levenshtein", "plain edit distance"),
    ("panphon-weighted", "PanPhon, weighted"),
    ("panphon-hamming", "PanPhon, Hamming"),
    ("aline", "ALINE"),
    ("soundvectors", "CLTS sound vectors"),
    ("sca", "SCA"),
    ("phonematcher", "phonematcher, starting weights (C0)"),
    ("pm-P5", "phonematcher, shipped library (P5)"),
]
README_COLUMNS = [
    ("cognates", "Cognates, mean AP"),
    ("alignment", "Alignment, PAS on common pairs"),
    ("retrieval", "Retrieval, mean recall@1"),
]


def readme_table(directory: Path = RESULTS) -> str:
    """The summary table of the README: the test-split interval of each system on each task."""
    tests = load_results(directory).get("test", {})
    missing = [task for task, _ in README_COLUMNS if task not in tests]
    if missing:
        raise SystemExit(f"no test result file for {', '.join(missing)}")
    cells: Dict[str, Dict[str, Optional[dict]]] = {
        system: {task: tests[task]["intervals"].get(system) for task, _ in README_COLUMNS} for system, _ in README_SYSTEMS
    }
    best = {task: max(c[task]["estimate"] for c in cells.values() if c[task]) for task, _ in README_COLUMNS}
    rows = []
    for system, label in README_SYSTEMS:
        row = [label]
        for task, _ in README_COLUMNS:
            cell = cells[system][task]
            text = "—" if cell is None else span(cell)
            row.append(f"**{text}**" if cell and cell["estimate"] == best[task] else text)
        rows.append(row)
    sizes = {system: {pair["systems"][system]["sample"] for pair in tests["retrieval"]["pairs"].values()} for system in ("sca", "aline")}
    if any(len(size) != 1 for size in sizes.values()):
        raise SystemExit(f"retrieval sample sizes differ between pairs: {sizes}")
    (sca_sample,), (aline_sample,) = sizes["sca"], sizes["aline"]
    caption = ("Test split, run once under [`benchmarks/prereg-2.md`](https://github.com/TigreGotico/phonematcher/blob/dev/benchmarks/prereg-2.md). Each cell is the estimate with its 95% interval. "
               "The best value in each column is in bold. A dash means that the system does not run the task. "
               f"SCA ran retrieval on a sample of {sca_sample} queries per pair and ALINE on the first {aline_sample} of those, "
               "so these two retrieval cells are not on the same queries as the other rows. "
               "The shipped library is the P5 candidate, with its test numbers. "
               "[docs/benchmarks.md](docs/benchmarks.md) holds every result.")
    return "\n".join([caption, "", *table(["System", *(title for _, title in README_COLUMNS)], rows)]).rstrip("\n") + "\n"


WHITEPAPER_SYSTEMS = [*README_SYSTEMS[:-2], ("phonematcher", "phonematcher, original costs"), ("pm-P5", "phonematcher, released costs")]
CANDIDATE_NAMES = {"C1": "equal weights", "C2": "one unit per dimension", "C3": "heavier major classes",
                   "P4": "half gap", "P5": "released costs"}


def bare(row: dict) -> str:
    return f"{row['diff']:+.4f} [{row['low']:+.4f}, {row['high']:+.4f}]"


def wp_coverage(results: dict) -> str:
    census = results["seen"]["coverage"]
    rows = []
    for label, key in (("PHOIBLE 2.0", "phoible"), ("WikiPron", "wikipron"), ("orthography2ipa", "orthography2ipa")):
        row = census["systems"]["phonematcher"][key]["direct"]
        rows.append([label, str(row["types"]), str(row["types_read"]), num(row["type_share"]), num(row["token_share"])])
    return "\n".join(table(["Corpus", "Segment types", "Types read", "Share of types", "Share of tokens"], rows))


def wp_readings(results: dict) -> str:
    census = results["seen"]["coverage"]
    phoible = census["phonematcher_readings"]["segments_only"]["phoible"]
    full = census["systems"]["phonematcher"]["phoible"]["direct"]
    rows = [[label, f"{row['types_read']} of {row['types']}", num(row["type_share"])] for label, row in (
        ("the segment as written", phoible["direct"]),
        ("as written, or with a tie bar between its pieces", phoible["tie_retry"]),
        ("as the library reads a word: whole, split into segments, tones included", full),
    )]
    return "\n".join(table(["Reading of a PHOIBLE segment", "Types read", "Share of types"], rows))


def wp_cognates(results: dict) -> str:
    test = results["test"]["cognates"]
    romance = "Romance-110-43"
    first = test["systems"]["pm-P5"]["common"]
    words = sum(first["words_out"].values())
    sets = ", ".join(name.split("-")[0] for name in first["data_sets_scored"])
    empty = " and ".join(name.split("-")[0] for name, n in first["words_out"].items() if n == 0)
    rows = []
    for system, label in WHITEPAPER_SYSTEMS:
        entry = test["systems"][system]
        common, every = entry["common"], entry["unread_at_1"]
        rows.append([label, num(common["average_precision"]["mean"]), num(common["bcubed_f"]["mean"]),
                     num(common["average_precision"][romance]), span(test["intervals"][system]),
                     num(every["average_precision"][romance])])
    head = ["System", "AP, common words", "B-cubed F, common words", "Romance AP, common words",
            "AP, all words [95% interval]", "Romance AP, all words"]
    caption = (f"Test split. The common words are the {words} words that every system reads, in {sets}; "
               f"{empty} have no word that every system reads. The common columns have no interval. "
               "The all-words column is the pre-registered main metric, with unread pairs at distance 1.")
    return "\n".join([caption, "", *table(head, rows)])


def wp_romance(results: dict) -> str:
    test = results["test"]["cognates"]
    rows = []
    for name, total in test["words"].items():
        systems = ("pm-P5", "panphon-weighted", "aline", "soundvectors", "levenshtein", "sca")
        rows.append([name.split("-")[0], str(total), *(str(test["systems"][system]["skipped"]["words"][name]) for system in systems)])
    head = ["Test set", "Words", "phonematcher", "PanPhon", "ALINE", "CLTS sound vectors", "plain edit distance", "SCA"]
    return "\n".join(["Test split. Words that each system cannot read; both PanPhon systems read the same words.", "", *table(head, rows)])


def wp_alignment(results: dict) -> str:
    test = results["test"]["alignment"]
    rows = []
    for system, label in WHITEPAPER_SYSTEMS:
        entry = test["all"]["systems"].get(system)
        if entry is None:
            continue
        rows.append([label, f"{entry['n_scored']} of {entry['n_in']}", span(test["intervals"][system]), num(entry["common_cs"])])
    caption = f"Test split. Every system is scored on the {test['all']['n_common']} pairs that all four aligning systems read."
    return "\n".join([caption, "", *table(["System", "Pairs read", "PAS, common pairs [95% interval]", "Column score, common pairs"], rows)])


def wp_retrieval(results: dict) -> str:
    test = results["test"]["retrieval"]
    pairs = list(test["pairs"].values())

    def mean(system: str, view: str) -> str:
        return num(math.fsum(p["systems"][system][view]["recall@1"] for p in pairs) / len(pairs))

    common = sum(p["common_queries"] for p in pairs)
    shared = sum(p["shared_sampled_queries"] for p in pairs)
    rows = [[label, mean(system, "common_subset"), mean(system, "on_shared_queries"), span(test["intervals"][system]),
             "/".join(str(p["systems"][system]["queries_scored"]) for p in pairs)] for system, label in WHITEPAPER_SYSTEMS]
    caption = (f"Test split, mean recall@1 over the four dialect pairs ({', '.join(test['pairs'])}). "
               f"The common queries are the {common} queries that every system reads and scores. "
               f"The shared queries are the {shared} queries of the ALINE sample, which every system scores. "
               "These two columns have no interval.")
    head = ["System", f"Common queries ({common})", f"Shared queries ({shared})", "All queries [95% interval]", "Queries per pair"]
    return "\n".join([caption, "", *table(head, rows)])


def wp_candidates(results: dict) -> str:
    tests = results["test"]
    rows = []
    for name, row in tests["cognates"]["candidates"].items():
        rows.append([CANDIDATE_NAMES[name], "yes" if row["k1"] else "no", *(bare(tests[task]["paired"][row["system"]]) for task in final.TASKS)])
    head = ["Candidate", "Passes the vowel rule", "Cognates, AP minus original", "Alignment, PAS minus original", "Retrieval, recall@1 minus original"]
    return "\n".join(table(head, rows))


def wp_ablations(results: dict) -> str:
    tests, dev = results["test"], results["dev"]["ablations"]["tasks"]["cognates"]["systems"]
    rows = []
    for name, label in (("panphon22", "PanPhon's 22 features"), ("no-height", "no height steps"),
                        ("flat-diacritics", "no scale marks"), ("uniform", "every weight 1")):
        rows.append([label, bare(tests["cognates"]["paired"][f"pm-{name}"]), bare(tests["alignment"]["paired"][f"pm-{name}"]),
                     num(dev[f"pm-p5-{name}"]["unread_at_1"]["average_precision"]["mean"])])
    rows.append(["the table (control)", "-", "-", num(dev["phonematcher"]["unread_at_1"]["average_precision"]["mean"])])
    head = ["Variant", "Test cognates, AP minus table (original costs)", "Test alignment, PAS minus table (original costs)", "Dev cognates, AP (released costs)"]
    return "\n".join(table(head, rows))


def wp_confusions(results: dict) -> str:
    systems = results["seen"]["ablations"]["tasks"]["confusions"]["systems"]
    rows = []
    for name, label in (("phonematcher", "the table"), ("pm-p5-no-height", "no height steps"), ("pm-p5-panphon22", "PanPhon's 22 features")):
        row = systems[name]["hillenbrand"]["unread_at_1"]
        interval = row.get("interval")
        rows.append([label, f"{row['score']:.4f} [{interval['low']:.4f}, {interval['high']:.4f}]" if interval else num(row["score"])])
    pairs = systems["phonematcher"]["hillenbrand"]["pairs_in"]
    return "\n".join([f"Seen data, {pairs} vowel pairs. Spearman correlation of the negative segment distance with confusion.", "",
                      *table(["Feature set", "Hillenbrand vowels [95% interval]"], rows)])


def wp_tone(results: dict) -> str:
    tone = results["seen"]["tone"]
    rows = []
    for values, label in (("main", "main Chao values"), ("alternative", "alternative Chao values")):
        for system, name in (("phonematcher", "tone distance"), ("direction_baseline", "direction baseline")):
            row = tone["scored"][values][system]
            rows.append([name, label, f"{row['score']:.4f} [{row['interval']['low']:.4f}, {row['interval']['high']:.4f}]"])
    return "\n".join([f"Seen data, {tone['pairs']} Cantonese tone pairs.", "", *table(["System", "Tone values", "Spearman [95% interval]"], rows)])


def wp_vowel_height(directory: Path) -> str:
    dev = json.loads((directory / "ablations" / "vowel-height-dev.json").read_text(encoding="utf8"))
    rows = [[label, bare(dev[task]["paired"]["pm-F1-segment"])] for task, label in (
        ("cognates", "Cognates, AP"), ("alignment", "Alignment, PAS"), ("retrieval", "Retrieval, recall@1"))]
    return "\n".join(["Dev split, released costs. One height encoding minus the table.", "", *table(["Task", "Paired difference [95% interval]"], rows)])


def wp_control(results: dict) -> str:
    control = results["seen"]["ablations"]["control"]
    rows = [["segment pairs that both read", str(control["pairs_compared"]), str(control["pairs_differing"])],
            ["pairs whose 22 values equal PanPhon's", str(control["identical_vector_pairs"]), str(control["identical_vector_pairs_differing"])]]
    return "\n".join(table(["Pairs", "Count", "Distance differs"], rows))


def whitepaper_blocks(directory: Path = RESULTS) -> Dict[str, str]:
    """The text of each marked table of whitepaper.md, by name."""
    results = load_results(directory)
    blocks = {name: build(results) for name, build in (
        ("coverage", wp_coverage), ("readings", wp_readings), ("cognates", wp_cognates), ("romance", wp_romance),
        ("alignment", wp_alignment), ("retrieval", wp_retrieval), ("candidates", wp_candidates),
        ("ablations", wp_ablations), ("confusions", wp_confusions), ("tone", wp_tone), ("control", wp_control))}
    blocks["vowel-height"] = wp_vowel_height(directory)
    return {name: text.rstrip("\n") + "\n" for name, text in blocks.items()}


TONE_LABELS = {
    "pm-p5-tone-standalone": "tone as a segment of its own",
    "pm-p5-tone-0-0": "0 and 0: the tone is read and not priced",
    "pm-p5-tone-0.25-0.125": "0.25 and 0.125, chosen",
}


def design_tone_weights(results: dict) -> str:
    rows = []
    for name, row in results["dev"]["tone-weights"]["systems"].items():
        if name == "phonematcher":
            continue
        label = TONE_LABELS.get(name) or " and ".join(name.removeprefix("pm-p5-tone-").split("-"))
        rows.append([label, num(row["average_precision"]), num(row["bcubed_f"]), num(row["chinese_average_precision"])])
    return "\n".join(table(["Tone weights", "Average precision", "B-cubed F", "Chinese average precision"], rows))


def design_corrections(directory: Path) -> str:
    data = json.loads((directory / "ablations" / "corrections-dev.json").read_text(encoding="utf8"))
    rows = []
    for task, label in (("cognates", "Cognates, AP"), ("alignment", "Alignment, PAS"), ("retrieval", "Retrieval, recall@1")):
        key = {"cognates": "cognates_ap", "alignment": "alignment_pas", "retrieval": "retrieval_recall@1"}[task]
        rows.append([label, num(data["before"][key]), num(data["after"][key]), difference(data["paired"][task]["paired"]["after"])])
    return "\n".join(table(["Task", "Without", "With", "Paired difference [95% interval]"], rows))


def design_blocks(directory: Path = RESULTS) -> Dict[str, str]:
    """The text of each marked table of docs/design.md, by name."""
    blocks = {"tone-weights": design_tone_weights(load_results(directory)), "corrections": design_corrections(directory)}
    return {name: text.rstrip("\n") + "\n" for name, text in blocks.items()}


def fill_marked(text: str, blocks: Dict[str, str], page: str) -> str:
    """*text* with the content between each pair of markers replaced by its block; a missing marker raises."""
    for name, block in blocks.items():
        start, end = f"<!-- {page}:{name}:start -->", f"<!-- {page}:{name}:end -->"
        if text.count(start) != 1 or text.count(end) != 1:
            raise SystemExit(f"{page}.md needs one {start} and one {end}")
        head, rest = text.split(start, 1)
        tail = rest.split(end, 1)[1]
        text = f"{head}{start}\n{block}{end}{tail}"
    return text


def fill_whitepaper(text: str, blocks: Dict[str, str]) -> str:
    return fill_marked(text, blocks, "whitepaper")


def readme_block(text: str) -> Optional[str]:
    """The text between the two marker comments of the README, or None when a marker is missing."""
    if README_START not in text or README_END not in text:
        return None
    return text.split(README_START, 1)[1].split(README_END, 1)[0].strip("\n") + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="fail when the page differs from a fresh render")
    parser.add_argument("--readme", action="store_true", help="print the summary table of the README")
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--page", type=Path, default=PAGE)
    parser.add_argument("--readme-file", type=Path, default=README)
    parser.add_argument("--whitepaper", action="store_true", help="rewrite the marked tables of whitepaper.md")
    parser.add_argument("--whitepaper-file", type=Path, default=WHITEPAPER)
    parser.add_argument("--design", action="store_true", help="rewrite the marked tables of docs/design.md")
    parser.add_argument("--design-file", type=Path, default=DESIGN)
    args = parser.parse_args(argv)
    if args.readme:
        print(readme_table(args.results), end="")
        return 0
    if args.whitepaper:
        paper = args.whitepaper_file.read_text(encoding="utf8")
        args.whitepaper_file.write_text(fill_whitepaper(paper, whitepaper_blocks(args.results)), encoding="utf8")
        print(f"wrote the tables of {args.whitepaper_file}")
        return 0
    if args.design:
        page = args.design_file.read_text(encoding="utf8")
        args.design_file.write_text(fill_marked(page, design_blocks(args.results), "design"), encoding="utf8")
        print(f"wrote the tables of {args.design_file}")
        return 0
    fresh = render(args.results)
    if args.check:
        if not args.page.exists() or args.page.read_text(encoding="utf8") != fresh:
            print(f"{args.page} differs from a fresh render; run benchmarks/render.py", file=sys.stderr)
            return 1
        if readme_block(args.readme_file.read_text(encoding="utf8")) != readme_table(args.results):
            print(f"the table in {args.readme_file} differs from a fresh render; run benchmarks/render.py --readme", file=sys.stderr)
            return 1
        paper = args.whitepaper_file.read_text(encoding="utf8")
        if fill_whitepaper(paper, whitepaper_blocks(args.results)) != paper:
            print(f"a table in {args.whitepaper_file} differs from a fresh render; run benchmarks/render.py --whitepaper", file=sys.stderr)
            return 1
        design = args.design_file.read_text(encoding="utf8")
        if fill_marked(design, design_blocks(args.results), "design") != design:
            print(f"a table in {args.design_file} differs from a fresh render; run benchmarks/render.py --design", file=sys.stderr)
            return 1
        print(f"{args.page}, the table in {args.readme_file} and the tables in {args.whitepaper_file} and {args.design_file} match a fresh render")
        return 0
    args.page.write_text(fresh, encoding="utf8")
    print(f"wrote {args.page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
