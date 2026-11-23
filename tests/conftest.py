"""Helpers and fixtures that several test modules share."""
import json
import subprocess
from pathlib import Path

import pytest

from phonematcher.features import FEATURES, vectorize_phones

RESULTS = Path(__file__).resolve().parent.parent / "benchmarks" / "results"


def feature(segment, name):
    return vectorize_phones(segment)[FEATURES.index(name)]


def differs(a, b):
    """The features whose values differ between segments *a* and *b*."""
    return {f for f in FEATURES if feature(a, f) is not feature(b, f)}


def results(name):
    """A committed benchmark result file, parsed."""
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """A git repository with one committed file, ``f.txt``, in a directory of its own."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    (root / "f.txt").write_text("one\n")
    git(root, "add", "f.txt")
    git(root, "commit", "-q", "-m", "first")
    return root
