"""Run one benchmark task on one system, or on all.

    python benchmarks/run.py --task selfcheck --system all
    python benchmarks/run.py --task <task> --system <name> --split dev --cache DIR

The test split runs only with ``--final`` on a clean git tree; the result then records the commit.
A run writes ``<task>-<split>.json`` into ``--out``, which defaults to ``<cache>/results``, so the
tree stays clean. ``benchmarks/copy_results.py`` copies the files into ``benchmarks/results``.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from systems import NAMES, System, build  # noqa: E402
from variants import NAMES as VARIANTS, P5_NAMES as P5_VARIANTS, TONE_NAMES  # noqa: E402
import final  # noqa: E402
from tasks import ablations, alignment, allophones, cognates, cognates_toneless, confusions, coverage, retrieval, tone, tone_weights  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = Path.home() / ".cache" / "phonematcher-bench"
SPLITS = ("dev", "seen", "test")


def commit_of_clean_tree(repo: Path) -> str:
    """The HEAD sha of *repo*. Raises ``SystemExit`` when the working tree has changes."""
    dirty = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout
    if dirty.strip():
        raise SystemExit("--final needs a clean git tree; commit or remove these changes:\n" + dirty)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def selfcheck(system: System) -> str:
    """One line: the system reads a letter, and gives distance 0 for a word against itself and a
    positive distance for ``pa`` against ``ba`` (``ta`` for SCA, which scores voicing as no change)."""
    other = "ta" if system.name == "sca" else "ba"
    same = system.word_distance(["p", "a"], ["p", "a"])
    different = system.word_distance(["p", "a"], [other[0], "a"])
    normalized = system.word_distance(["p", "a"], [other[0], "a"], normalized=True)
    reads, unread = system.reads("p"), system.reads("☃")
    if not reads or same != 0 or different <= 0:
        raise SystemExit(f"selfcheck failed for {system.name}: reads(p)={reads} same={same} different={different}")
    return (
        f"{system.name}: reads(p)={reads} reads(snowman)={unread} word(pa,pa)={same:g} "
        f"word(pa,{other})={different:.4f} normalized={normalized:.4f}"
    )


#: task name -> (function, the splits it has data for)
TASKS: Dict[str, tuple] = {"selfcheck": (selfcheck, ("dev",)), "alignment": (alignment.run, ("dev",))}

#: tasks that score all systems together and write ``results/<task>-<split>.json``; the value is the default systems
WHOLE_TASKS: Dict[str, tuple] = {"alignment": alignment.SYSTEMS}


#: task name -> module with ``SPLITS``, ``run(systems, split, cache)`` and ``lines(payload)``.
#: These tasks run every requested system together, because the common subset needs all of them.
SUITE_TASKS = {
    "coverage": coverage,
    "allophones": allophones,
    "confusions": confusions,
    "cognates": cognates,
    "cognates-toneless": cognates_toneless,
    "retrieval": retrieval,
    "tone": tone,
    "ablations": ablations,
    "tone-weights": tone_weights,
}
RESULTS = ROOT / "benchmarks" / "results"
#: ``--system`` values that stand for several systems
GROUPS = {"all": NAMES, "variants": ["phonematcher", *VARIANTS], "variants-p5": ["phonematcher", *P5_VARIANTS], "tone-weights": ["phonematcher", *TONE_NAMES]}


def write_result(path: Path, payload: dict, task: str, system: str, split: str, commit: Optional[str]) -> None:
    record = {"task": task, "system": system, "split": split, "commit": commit, **payload}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


def result_path(args: argparse.Namespace) -> Path:
    """The result file of a run: ``<task>-<split>.json`` in ``--out``, by default ``<cache>/results``."""
    return (args.out or args.cache / "results") / f"{args.task}-{args.split}.json"


def run_suite(module, args, names: List[str], commit: Optional[str], repo: Path) -> int:
    """Build every system, run the task once on all of them and write the result file."""
    if args.split not in module.SPLITS:
        raise SystemExit(f"task {args.task} has no {args.split} split")
    systems = []
    for name in names:
        try:
            systems.append(build(name, args.cache))
        except (ImportError, KeyError, subprocess.CalledProcessError) as error:
            print(f"error: system {name}: {error}", file=sys.stderr)
            return 1
    payload = module.run(systems, args.split, args.cache)
    print("\n".join(module.lines(payload)))
    git = ["git", "-C", str(repo)]
    sha = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run([*git, "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
    out = result_path(args)
    write_result(out, {"head": sha, "tree_dirty": dirty, **payload}, args.task, ",".join(names), args.split, commit)
    print(f"wrote {out}")
    return 0


def main(argv: Optional[List[str]] = None, repo: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--task", required=True, choices=sorted([*TASKS, *SUITE_TASKS]))
    parser.add_argument("--system", required=True, help=f"one of {', '.join([*NAMES, *VARIANTS])}, all, or variants (phonematcher and the ablation variants)")
    parser.add_argument("--split", default="dev", choices=SPLITS)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, help="directory for <task>-<split>.json; default <cache>/results")
    parser.add_argument("--final", action="store_true", help="allow the test split; needs a clean git tree")
    parser.add_argument("--dry-run", action="store_true", help="walk the --final path on the dev split, capped at --limit units, and write nothing")
    parser.add_argument("--limit", type=int, default=0, help="with --dry-run: units per data set, language pair or file")
    args = parser.parse_args(argv)

    if args.dry_run:
        if args.final or args.split != "dev" or args.task not in final.TASKS:
            raise SystemExit(f"--dry-run takes --split dev, no --final and one of {', '.join(final.TASKS)}")
        record = final.run_final(args.task, args.cache, args.split, args.limit)
        print("\n".join(final.report(args.task, args.split, record)))
        print("dry run: nothing written")
        return 0
    commit = None
    if args.split == "test" and not args.final:
        raise SystemExit("the test split runs only with --final")
    if args.final:
        if args.split != "test":
            raise SystemExit("--final applies to --split test only")
        commit = commit_of_clean_tree(repo)

    if args.final and args.task in final.TASKS:
        if args.system != "all":
            raise SystemExit("--final scores every system, the C10 variants and the candidates; pass --system all")
        record = final.run_final(args.task, args.cache, args.split)
        print("\n".join(final.report(args.task, args.split, record)))
        out = result_path(args)
        write_result(out, {"head": commit, "tree_dirty": False, **record}, args.task, ",".join(final.final_names()), args.split, commit)
        print(f"wrote {out}")
        return 0
    if args.task in SUITE_TASKS:
        names = GROUPS.get(args.system, [args.system])
        return run_suite(SUITE_TASKS[args.task], args, names, commit, repo)
    task, splits = TASKS[args.task]
    if args.split not in splits:
        raise SystemExit(f"task {args.task} has no {args.split} split")
    if args.task in WHOLE_TASKS:
        names = WHOLE_TASKS[args.task] if args.system == "all" else [args.system]
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        payload = task(names, args.cache, args.split)
        out = result_path(args)
        write_result(out, payload, args.task, ",".join(names), args.split, commit or head)
        print(f"wrote {out}")
        return 0
    names = GROUPS.get(args.system, [args.system])
    failed = 0
    for name in names:
        try:
            system = build(name, args.cache)
        except (ImportError, KeyError, subprocess.CalledProcessError) as error:
            print(f"error: system {name}: {error}", file=sys.stderr)
            failed += 1
            continue
        print(task(system))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
