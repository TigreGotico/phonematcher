"""Copy result files of ``run.py`` from its output directory into ``benchmarks/results``.

    python benchmarks/copy_results.py                         # every file in ~/.cache/phonematcher-bench/results
    python benchmarks/copy_results.py --from DIR coverage-seen.json

A run writes outside the tree, so it records the commit it ran on with a clean tree. This step
puts the files where ``render.py`` and the tests read them.
"""
import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import DEFAULT_CACHE, RESULTS  # noqa: E402


def main(argv: Optional[List[str]] = None, results: Path = RESULTS) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--from", dest="source", type=Path, default=DEFAULT_CACHE / "results", help="the --out directory of run.py")
    parser.add_argument("names", nargs="*", help="file names to copy; default every .json file in --from")
    args = parser.parse_args(argv)

    paths = [args.source / name for name in args.names] or sorted(args.source.glob("*.json"))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing or not paths:
        raise SystemExit("no result file to copy: " + (", ".join(missing) or f"{args.source} holds no .json file"))
    results.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, results / path.name)
        print(f"copied {path.name}")
    print(f"{len(paths)} files in, {len(paths)} copied to {results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
