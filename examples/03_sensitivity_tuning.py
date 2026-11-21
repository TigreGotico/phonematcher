"""What cluster_sensitivity controls: which sounds share a search cluster.

A higher value puts more sounds in one cluster, so a search finds more candidates. Ranking by
edit distance then orders them.

Run::

    python examples/03_sensitivity_tuning.py
"""
from phonematcher.clustering import phone_clusters

PAIRS = [("p", "b"), ("ʁ", "χ"), ("s", "ʃ"), ("e", "ɛ"), ("a", "ɐ"), ("p", "t"), ("ʁ", "k"), ("e", "o")]

for sensitivity in (0.02, 0.1, 0.2):
    clusters = phone_clusters(sensitivity)
    shared = [f"{a}{b}" for a, b in PAIRS if clusters[a] == clusters[b]]
    print(f"{sensitivity}: {len(set(clusters.values()))} clusters; together: {' '.join(shared)}")
