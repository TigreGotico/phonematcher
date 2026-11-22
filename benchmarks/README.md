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
| `aline` | `nltk.metrics.aline` | it is a key of `feature_matrix` (ASCII `g`, no `ɡ`) |
| `soundvectors` | `soundvectors`, `pyclts` | `get_vec` returns |
| `sca` | `lingpy` (GPL-3.0, extra `bench-copyleft`) | `tokens2class` maps it to an SCA class |

Each system has `reads(segment)`, `segment_distance(a, b)` and `word_distance(a, b, normalized)`. A word is a list of segment strings. The method `word_distance` raises `UnreadSegment` for a word with an unread segment. `word_distance_or_one` returns 1.0 instead.

An edit distance is normalized by the length of the longer word. ALINE and SCA give a similarity score. Their distance is the mean self-similarity of the two words minus that score. The normalized form divides the distance by the mean.

## The splits

`split.is_test(key)` is true for one key in five, by the SHA-1 of the key. Each task names its key.

The `dev` and `seen` splits run freely. The `test` split runs only with `--final`, on a clean git tree. The result records the commit.

## Tests

`pytest --import-mode=importlib tests/test_bench_harness.py` covers every system except SCA.

The SCA tests import LingPy, so they are in `benchmarks/test_sca.py`. Run `pytest --import-mode=importlib benchmarks/test_sca.py`.
