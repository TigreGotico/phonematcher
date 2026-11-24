# Use phonematcher with scikit-learn
<!-- agent-hint
covers: how to cluster segments and words with scikit-learn from phonematcher distances and feature rows
source: phonematcher/distance.py:pairwise_distances, phonematcher/features.py:PhoneFeatures
generated: no
verify: pytest --import-mode=importlib tests/test_docs.py -k scikit-learn.md
see: compare-sounds.md, compare-words.md, api.md
-->

This page turns phonematcher distances into a matrix for a scikit-learn clusterer, and turns segments into feature rows for a scikit-learn pipeline. phonematcher does not import scikit-learn. Install it yourself with `uv pip install scikit-learn`.

## 1. Cluster words by sound

`pairwise_distances` returns the matrix of `ipa_distance` between every two words, as a list of lists. Pass `metric="word"`. The clusterers of scikit-learn read it with `metric="precomputed"`.

```python
from sklearn.cluster import DBSCAN
from phonematcher import pairwise_distances

words = ["kasa", "kaza", "kaʒa", "mesa", "meza", "pɾato", "pɾatu", "bɔla", "bola"]
matrix = pairwise_distances(words, metric="word")
labels = DBSCAN(eps=0.6, min_samples=2, metric="precomputed").fit(matrix).labels_.tolist()
labels   # [0, 0, 0, 1, 1, 2, 2, 3, 3]
```

Each label is one group of words that sound alike. The label -1 marks a word with no neighbour. At `eps=1.0` the first two groups merge, because `kasa` and `mesa` are then close enough.

```python
DBSCAN(eps=1.0, min_samples=2, metric="precomputed").fit(matrix).labels_.tolist()   # [0, 0, 0, 0, 0, 1, 1, 2, 2]
```

With one argument the matrix is square, symmetric and zero on the diagonal, and each pair is computed once. With two arguments, the rows are the items of the first and the columns the items of the second, as for nearest-neighbour search:

```python
len(pairwise_distances(["kasa"], words, metric="word")[0])   # 9
```

## 2. Cluster segments by feature

With `metric="segment"`, which is the default, each item is one segment and each cell is `feature_distance`.

```python
segments = ["p", "b", "t", "d", "k", "ɡ", "a", "e", "i", "o", "u", "s", "z"]
distances = pairwise_distances(segments)
DBSCAN(eps=0.15, min_samples=2, metric="precomputed").fit(distances).labels_.tolist()   # [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0]
```

The consonants fall in one group and the vowels in another.

## 3. Put features in a pipeline

`PhoneFeatures` is a transformer. `transform` returns one row per segment, with one number for each name in `FEATURES`: + is 1.0, − is -1.0, 0 is 0.0, and a tone pitch is its number. The rows are lists, so numpy is not needed to call it.

```python
from phonematcher import FEATURES, PhoneFeatures

rows = PhoneFeatures().fit_transform(["p", "a˥"])
dict(zip(FEATURES, rows[1]))["tone_start"]   # 1.0
dict(zip(FEATURES, rows[0]))["tone_start"]   # 0.0
```

A segment that cannot be read raises `ValueError`. With `strict=False` it gives a row of NaN.

```python
PhoneFeatures(strict=False).transform(["?"])[0][0] != PhoneFeatures(strict=False).transform(["?"])[0][0]   # True
```

Because the class has `get_params` and `set_params`, it works in a `Pipeline` and with `clone`:

```python
from sklearn.cluster import KMeans
from sklearn.pipeline import make_pipeline

pipeline = make_pipeline(PhoneFeatures(), KMeans(2, n_init=10, random_state=0))
pipeline.fit_predict(segments).tolist()   # [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1]
```

[Index](index.md) · Previous: [Search by sound](search.md) · Next: [Add a segment](add-a-segment.md)
