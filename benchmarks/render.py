"""Render ``docs/benchmarks.md`` from the result files in ``benchmarks/results``.

    python benchmarks/render.py            # write docs/benchmarks.md
    python benchmarks/render.py --check    # exit 1 when docs/benchmarks.md or the README table differs from a fresh render
    python benchmarks/render.py --readme   # print the summary table of the README

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
    "test": "The test split ran once, from a clean tree, under the pre-registration in `benchmarks/prereg-2.md`.",
}
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
    out = []
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


def speed_section(payload: dict) -> List[str]:
    machine = payload["machine"]
    loads = ", ".join(run["load_at_start"] for run in payload["runs"])
    rows = [f"| {name} | {value:.6g} |" for name, value in sorted(flatten(payload["median"]).items())]
    return ["## Speed", "", f"Median of {len(payload['runs'])} runs on {machine['cpu']}, {machine['cores']} cores, "
            f"Python {machine['python']}; load average at the start of each run: {loads}. {provenance(payload)}", "",
            f"The distance matrix of {payload['pair_count']} ordered letter pairs has sha256 `{payload['matrix_sha256']}`.", "",
            "| Measure | Median |", "|---|---|", *rows, ""]


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
    caption = ("Test split, run once under `benchmarks/prereg-2.md`. Each cell is the estimate with its 95% interval. "
               "The best value in each column is in bold. A dash means that the system does not run the task. "
               f"SCA ran retrieval on a sample of {sca_sample} queries per pair and ALINE on the first {aline_sample} of those, "
               "so these two retrieval cells are not on the same queries as the other rows. "
               "The shipped library is the P5 candidate, with its test numbers. "
               "The later changes of the library (one segment cost, a relative sensitivity and strict input) were made on dev only "
               "and did not change any word distance. "
               "[docs/benchmarks.md](docs/benchmarks.md) holds every result.")
    return "\n".join([caption, "", *table(["System", *(title for _, title in README_COLUMNS)], rows)]).rstrip("\n") + "\n"


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
    args = parser.parse_args(argv)
    if args.readme:
        print(readme_table(args.results), end="")
        return 0
    fresh = render(args.results)
    if args.check:
        if not args.page.exists() or args.page.read_text(encoding="utf8") != fresh:
            print(f"{args.page} differs from a fresh render; run benchmarks/render.py", file=sys.stderr)
            return 1
        if readme_block(args.readme_file.read_text(encoding="utf8")) != readme_table(args.results):
            print(f"the table in {args.readme_file} differs from a fresh render; run benchmarks/render.py --readme", file=sys.stderr)
            return 1
        print(f"{args.page} and the table in {args.readme_file} match a fresh render")
        return 0
    args.page.write_text(fresh, encoding="utf8")
    print(f"wrote {args.page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
