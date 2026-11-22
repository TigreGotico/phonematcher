"""The cognate task with tone tokens removed from every word, for every system."""
from pathlib import Path
from typing import List

from systems import System
from tasks import cognates

SPLITS = cognates.SPLITS


def run(systems: List[System], split: str, cache: Path) -> dict:
    return cognates.run(systems, split, cache, drop_tones=True)


lines = cognates.lines
