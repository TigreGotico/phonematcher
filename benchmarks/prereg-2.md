# phonematcher: pre-registration of the single test run

This page fixes the systems, the tasks, the metrics, the candidates and the decision rules before any test-split number exists. The test run happens once, after this page is committed to the wiki. Its sha256 is recorded in every test result file. A rule on this page does not change after the run starts.

No agent has scored a test item of the cognate, alignment or retrieval data with phonematcher or a candidate. One exception is known: during C5, SCA alone was run over all 7,126 `full.psa` alignment pairs, test side included, to match its published settings (C5.md). SCA is an untuned baseline, so this does not touch a phonematcher decision. It is reported in the paper.

## Tasks and test data

| Task | Test data | Unit for the bootstrap |
|---|---|---|
| C4 cognates | the six `D_test_*` files of List, Greenhill and Gray 2017 (Bahnaric, Chinese, Huon, Romance, Tujia, Uralic) | concept |
| C5 alignment | the `full.psa` and `covington.psa` pairs for which `benchmarks.split.is_test` is true | pair |
| C6 retrieval | the queries of the four WikiPron dialect pairs for which `is_test("<lang>:<word>")` is true | query |

C1, C2, C3 and C7 have no test split. Their data was seen during weight fitting or during C7, and the paper labels them "seen".

## Systems

All seven systems run on the test data: phonematcher, levenshtein, panphon-weighted, panphon-hamming, aline, soundvectors and sca, as `benchmarks/systems.py` defines them at the commit of the run. aline and sca keep the C6 samples: a fixed random sample of 500 test queries per dialect pair for sca and the first 100 of those for aline, with seed 0. The C10 variants run on the test data too, as ablations, with no decision attached.

## Metrics

| Task | Main metric | Second metric |
|---|---|---|
| C4 | mean average precision over the six test sets, tones kept, unread pairs at distance 1 | mean B-cubed F, LingPy counting, at the threshold that is best on the six training sets for that system |
| C5 | perfect-alignment score (PAS) on the pairs every aligning system reads | mean column score on the same pairs |
| C6 | recall@1 of brute-force search, mean over the four dialect pairs, unread at distance 1 | recall@10 and MRR |

Each metric gets a 95% bootstrap interval with 1,000 resamples of the task's unit and seed 0.

## Weight candidates

The candidates are the four of weight-fit.md plus two that the dev data suggested. The last two were chosen after reading dev results, in C4-loss.md and C10.md. That is why they must win on test data that no one has scored.

| Id | Definition |
|---|---|
| C0 | the table's weights, gap cost 1 (the library on dev) |
| C1 | every feature weight 1, gap cost 1 |
| C2 | every feature 1; h1 to h6 1/6 each; front and back 1/2 each; round and lab 1/2 each; gap cost 1 |
| C3 | C2 with syl, son and cons at the least weight that passes K1 (bisection to 0.01), gap cost 1 |
| P4 | C0 weights, gap cost 0.5 |
| P5 | C0 weights, gap cost 0.5, and each substitution cost raised to the power 0.5 |

Each candidate is built as a `System` in `benchmarks/variants.py` without a change to the package. P5 keeps the distance a metric: the square root of a metric is a metric.

## Decision rules

1. Constraint K1 from weight-fit.md holds for a candidate, or the candidate is out: every pair of chart vowels is nearer than any chart vowel and any of `p b t d k ɡ q ʔ f v s z ʃ ʒ x χ h`. K2 is dropped, because weight-fit.md shows that its "i not with u" half was wrong to require.
2. For each candidate X and each task, compute the paired difference X − C0 on the same units, with its 95% bootstrap interval (1,000 resamples, seed 0).
3. X beats C0 only if the lower bound of the C4 difference is above 0, the lower bound of the C6 difference is above 0, and the upper bound of the C5 difference is not below 0. That is, X must be better on C4 and on C6, and not worse on C5.
4. If more than one candidate beats C0, the one with the largest C4 difference wins. A tie on C4 at four decimals goes to the larger C6 difference.
5. If no candidate beats C0, the weights and the gap cost stay as they are.
6. The winner's default search sensitivity is chosen afterwards on dev data only, by rule 7. The test data is not used for it.
7. Default sensitivity rule: of the values 0.0, 0.05, 0.1, 0.15 and 0.2, take the one with the highest mean `PhoneticFuzzySearch` recall@1 over the four C6 dev pairs, among the values whose mean candidate count is at most 5% of the index pronunciations in every pair.

## Default sensitivity for C0, fixed now

Rule 7 on `benchmarks/results/retrieval-dev.json`, dev commit 5ea9a38:

| Sensitivity | Mean recall@1 | Largest candidate count against 5% of the index | Allowed |
|---|---|---|---|
| 0.0 | 0.6905 | 48.0 of 904 (hy) | yes |
| 0.05 | 0.8085 | 135.1 of 1,333 (en) | yes |
| 0.1 | 0.8165 | 388.8 of 1,333 (en) | yes |
| 0.15 | 0.8073 | 1,081.4 against 1,047 (es) | no |
| 0.2 | 0.8028 | 3,926.6 against 1,047 (es) | no |

The index holds 26,653 (en), 28,806 (pt), 20,944 (es) and 18,090 (hy) pronunciations. The rule gives 0.1, which is the library's default (`clustering.py`, `cluster_sensitivity: float = 0.1`). The default stays at 0.1 unless a candidate wins.

## Running the test

- One `run.py ... --split test --final` call per task, from a clean tree at one commit, for all systems, the C10 variants and the candidates. The commit sha and this page's sha256 are written into each result file.
- A crash is logged with its traceback in `knowledge/wiki/audits/phonematcher/C9-run.md`, fixed in a PR that changes no metric or rule, and the crashed task runs again. No task runs again for any other reason.
- `docs/benchmarks.md` is generated from the result files by `benchmarks/render.py`, with no number typed by hand.

## What the paper reports either way

Every row of every system and candidate, passing or not, with its interval. A candidate that loses is reported as a loss. A task where phonematcher is behind another system is reported as it is, with the dev loss audits (C4-loss.md, C5-loss.md) as the explanation.
