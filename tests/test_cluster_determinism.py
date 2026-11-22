"""The phone clusters do not depend on the hash seed of the process that builds them."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARES = (0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.5, 1.0)
PROGRAM = (
    "import json; from phonematcher.clustering import phone_clusters; "
    "print(json.dumps({str(t): phone_clusters(t) for t in " + repr(SHARES) + "}, sort_keys=True))"
)
# On Python before 3.12, seeds 0 and 1 order the sets of the average-linkage sums differently.
SEEDS = ("0", "1")


def clusters_under(seed):
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
    done = subprocess.run([sys.executable, "-c", PROGRAM], env=env, cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def test_the_clusters_are_the_same_under_two_hash_seeds():
    first, second = (clusters_under(seed) for seed in SEEDS)
    assert first == second
    assert len(set(first["0.08"].values())) == 25
