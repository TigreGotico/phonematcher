"""C2: the allophone score on a tiny PHOIBLE file.

Inventory 1 (odd) holds p, b, t, k and lists b as an allophone of p. Distances from p: b 1, t 2,
k 1. The other phonemes are t and k. t is farther than b (counts 1), k ties (counts 1/2), so the
item scores (1 + 0.5) / 2 = 0.75. Inventory 2 (even) holds p, t, k and lists t as an allophone of p.
The other phoneme is k: d(p,t) 2, d(p,k) 1, so k is nearer, and the item scores 0.
The mean over both items is 0.375. The odd inventories alone score 0.75 and the even ones 0.
A third item in inventory 1 uses the unread allophone z: read-only skips it; at distance 1 it
is compared with t (2: farther, 1) and k (1: tie, 1/2) and b (1: tie, 1/2), so (1 + 0.5 + 0.5) / 3.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_fake import Fake

from tasks import allophones  # noqa: E402

PHOIBLE = (
    "InventoryID,Phoneme,Allophones\n"
    "1,p,b z\n1,b,NA\n1,t,\n1,k,NA\n"
    "2,p,t\n2,t,NA\n2,k,NA\n"
)
DISTANCES = {("p", "b"): 1, ("p", "t"): 2, ("p", "k"): 1, ("b", "t"): 1, ("b", "k"): 1, ("t", "k"): 1}


def test_items_lists_each_allophone_that_differs():
    found = allophones.items(PHOIBLE)
    assert [(i.inventory, i.phoneme, i.allophone) for i in found] == [(1, "p", "b"), (1, "p", "z"), (2, "p", "t")]
    assert found[0].phonemes == ("p", "b", "t", "k")


def test_share_farther_counts_ties_as_one_half():
    assert allophones.share_farther(1, [2, 1]) == 0.75
    assert allophones.share_farther(2, [1]) == 0


def test_scores_of_a_system():
    system = Fake("x", "pbtk", DISTANCES)
    row = allophones.variant([system], allophones.items(PHOIBLE), tie_retry=False)["x"]
    assert row["all"]["items_in"] == 3
    assert row["all"]["read_only"] == {"score": pytest.approx(0.375), "items_out": 2, "skipped": 1}
    assert row["odd"]["read_only"]["score"] == 0.75
    assert row["even"]["read_only"]["score"] == 0
    assert row["all"]["unread_at_1"]["items_out"] == 3
    assert row["all"]["unread_at_1"]["score"] == pytest.approx((0.75 + 0 + 2 / 3) / 3)


def test_common_subset_drops_what_another_system_cannot_read():
    full = Fake("x", "pbtk", DISTANCES)
    no_k = Fake("y", "pbt", DISTANCES)
    rows = allophones.variant([full, no_k], allophones.items(PHOIBLE), tie_retry=False)
    # Without k the first item has the other phoneme t only: b is nearer than t, so 1.
    # The even item has no other phoneme left and is skipped.
    assert rows["x"]["all"]["common_subset"] == {"score": 1.0, "items_out": 1, "skipped": 2}
    # y reads no k either, so its own read-only score also has the one item.
    assert rows["y"]["all"]["read_only"]["items_out"] == 1
