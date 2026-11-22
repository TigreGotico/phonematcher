# phonematcher benchmarks

<!-- agent-hint
covers: how to run the benchmark harness and what each system's three methods mean
source: benchmarks/systems.py, benchmarks/run.py, benchmarks/split.py
generated: no
verify: python benchmarks/run.py --task selfcheck --system all 2>/dev/null | diff - <(awk '/^```text/{f=1;next}/^```/{f=0}f' benchmarks/README.md)
see: ../docs/features.md, ../AGENTS.md
-->

This directory compares phonematcher with other phonetic distance tools on one set of tasks. It is not part of the wheel.

## Run the self-check

The self-check builds each system and prints one line for it. Install the extras first.

```bash
uv venv
uv pip install --prerelease=allow -e '.[test,build,bench,bench-copyleft]'
python benchmarks/run.py --task selfcheck --system all
```

```text
phonematcher: reads(p)=True reads(snowman)=False word(pa,pa)=0 word(pa,ba)=0.0132 normalized=0.0066
levenshtein: reads(p)=True reads(snowman)=True word(pa,pa)=0 word(pa,ba)=1.0000 normalized=0.5000
panphon-weighted: reads(p)=True reads(snowman)=False word(pa,pa)=0 word(pa,ba)=0.2500 normalized=0.1250
panphon-hamming: reads(p)=True reads(snowman)=False word(pa,pa)=0 word(pa,ba)=0.0417 normalized=0.0208
aline: reads(p)=True reads(snowman)=False word(pa,pa)=0 word(pa,ba)=5.0000 normalized=0.0833
soundvectors: reads(p)=True reads(snowman)=False word(pa,pa)=0 word(pa,ba)=0.0256 normalized=0.0128
sca: reads(p)=True reads(snowman)=False word(pa,pa)=0 word(pa,ta)=13.0000 normalized=0.6667
```

A missing package is an error, and the run exits with status 1. `--system` also takes one name from the list.

SCA scores `p` and `b` in one sound class, so its line uses `pa` against `ta`.

The `soundvectors` system clones the CLTS data (tag v2.3.1) into `~/.cache/phonematcher-bench` on first use.

Pass `--cache DIR` to put it elsewhere. Data never goes into the repository.

## The systems

| Name | Package | Reads a segment when |
|---|---|---|
| `phonematcher` | this repository | `vectorize_phones` returns |
| `levenshtein` | none | the segment is not empty |
| `panphon-weighted`, `panphon-hamming` | `panphon` 0.22.2 | `FeatureTable.fts` finds it |
| `aline` | `nltk.metrics.aline` | it is a key of `feature_matrix` (ASCII `g`; the input mapping `ɡ` to `g` is the only one) |
| `soundvectors` | `soundvectors`, `pyclts` | `get_vec` returns |
| `sca` | `lingpy` (GPL-3.0, extra `bench-copyleft`) | `tokens2class` maps it to an SCA class |

Each system has `reads(segment)`, `segment_distance(a, b)` and `word_distance(a, b, normalized)`. A word is a list of segment strings. The method `word_distance` raises `UnreadSegment` for a word with an unread segment. `word_distance_or_one` returns 1.0 instead.

An edit distance is normalized by the length of the longer word. ALINE and SCA give a similarity score. Their distance is the mean self-similarity of the two words minus that score. The normalized form divides the distance by the mean.

## Tasks

### alignment

```bash
python benchmarks/run.py --task alignment --system all --split dev
```

The task aligns the word pairs of the Benchmark Database of Phonetic Alignments (List and Prokić 2014) and compares each alignment with the gold alignment. It uses `full.psa` and `covington.psa` of `github.com/SequenceComparison/SupplementaryMaterial`, at a pinned commit, fetched into the cache on first use. The repository states no licence, so the data stays in the cache.

The split key is the file name and the pair index, such as `full.psa:17`. `--system all` runs `phonematcher`, `levenshtein`, `aline` and `sca`. The run writes `benchmarks/results/alignment-dev.json`.

Two scores, as List (2014) defines them. The perfect alignments score is the share of pairs whose alignment equals the gold alignment. The column score is `2 * |Ct & Cr| / (|Cr| + |Ct|)` for the columns of one alignment, averaged over the pairs. A system that cannot read a segment skips the item. The all-items score gives a skipped item 0 for both scores.

ALINE aligns locally. Its output is made global: the segments outside the aligned region are paired off from the region outward, and the extra ones go against gaps. `phonematcher` reads a tone as the library reads it in a word, so `³³` and `˧˧` are the same tone.

### The seen-data tasks

Three tasks score every system on data that the weight fitting already used. Their results are labelled `seen`.

```bash
python benchmarks/run.py --task coverage --system all --split seen
python benchmarks/run.py --task allophones --system all --split seen
python benchmarks/run.py --task confusions --system all --split seen
python benchmarks/run.py --task tone --system phonematcher --split seen
```

`coverage` counts the segments of PHOIBLE, WikiPron and the orthography2ipa inventories that each system reads. `allophones` asks whether an allophone lies nearer to its phoneme than the other phonemes of the inventory do. `confusions` correlates the segment distance with four sets of listener confusions.

Each run downloads its data into `~/.cache/phonematcher-bench/C1`, `C2` or `C3` and writes `benchmarks/results/<task>-seen.json`. The scripts print one line per system. Pass `--out FILE` to write the result elsewhere. A task scores all its systems in one run, because the common subset needs every system.

`tone` correlates the tone distance with the confusions of the six Cantonese tones (15 pairs, Wong, Cheng and Chen 2018) and scores a contour-direction baseline beside it. It needs no download. The other systems have no tone model, so only phonematcher and the baseline are scored.

## Cognate detection

The `cognates` task uses the word lists of List, Greenhill and Gray (2017), Zenodo record 192607 (CC BY 4.0). It downloads the archive to `CACHE/cognates` and checks its md5. The six training sets are the `dev` split. The six test sets are the `test` split.

```bash
python benchmarks/run.py --task cognates --system all --split dev
```

The run scores all systems together and writes `benchmarks/results/cognates-dev.json`. Each system gets two scores per data set, once on the words that every system reads and once on all words with unread pairs at distance 1. The first score is the average precision of the negative normalized distance for "same cognate set", over all word pairs of one concept. The second is the B-cubed F-score of a flat UPGMA cut at the threshold that is best on average over the six training sets. The B-cubed score uses LingPy's counting, as the paper's figures do, and the `per_word` entry holds the score with every word counted. A `control` entry holds the levenshtein system under LingPy's B-cubed counting next to the paper's Table 6. The task `cognates-toneless` runs the same with tone tokens removed from every word.

## The splits

`split.is_test(key)` is true for one key in five, by the SHA-1 of the key. Each task names its key.

The `dev` and `seen` splits run freely. The `test` split runs only with `--final`, on a clean git tree. The result records the commit.

## Tests

`pytest --import-mode=importlib tests/test_bench_harness.py` covers every system except SCA.

The SCA tests import LingPy, so they are in `benchmarks/test_sca.py`. Run `pytest --import-mode=importlib benchmarks/test_sca.py`.
