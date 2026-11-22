"""A system with a fixed symbol set and fixed segment distances, for the task tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

from systems import System  # noqa: E402


class Fake(System):
    def __init__(self, name, read, distances=None):
        self.name = name
        self._read = set(read)
        self._distances = {}
        for (a, b), d in (distances or {}).items():
            self._distances[a, b] = self._distances[b, a] = d

    def reads(self, segment):
        return segment in self._read

    def segment_distance(self, a, b):
        return self._distances[a, b]
