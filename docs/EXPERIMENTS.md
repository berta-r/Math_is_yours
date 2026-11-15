# Experiments

> A log of every evaluation worth keeping. `eval.py` writes `results/ablations.csv` on the board, but `results/` isn't committed, so **copy the row here**. Then the history lives in git and agents can read it.

## How to run an experiment

1. **Change one thing** (prompt, k, retrieval rule, model…) and commit it.
2. Contract check: `python3 predict.py --input data/sample_problems.jsonl --output results/check.csv`.
3. `python3 eval.py --limit 50 --name <short-label>`. Always use the same `--limit` and `--languages` to compare, because `eval.py` takes the same sample each time (seed 42).
4. Add a row below, with the **commit**, and a conclusion in one line.
5. For final numbers, use `--limit 0`.

The reference points are random guessing at 20%, always-D at about 25%, and the organizers' baseline at 22.5% (40 English problems).

## Results

| Date | Name | Commit | Input / langs / n | RAG k | Accuracy | Mean s | Worst s | Over 60 s | Change, and conclusion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | (organizers) baseline | template | 40 eng, text-only | 0 | 22.5% | 8.7 | 12.7 | 0 | Reference. Letter bias: D×21, A×14 |
| — | (organizers) value-not-letter | template | 40 eng | 0 | 17.5% | 9.3 | 13.5 | 0 | Worse |
| — | (organizers) one-line reasoning | template | 40 eng | 0 | 17.5% | 26.3 | 35.0 | 0 | Worse and 3× slower |
| 2026-11-14 | teaching-graph-v1 (fallback check only) | c081129 + uncommitted UI/teaching work | local val / eng / 8 | 0 | 25.0% (always D) | 2.0 | 2.0 | 0 | All 8 requests refused: no model service. Not a reasoning result. Contract check separately wrote 5 valid D letters with error status. Official solver unchanged. |
| 2026-11-14 | connected-graph-v2 (fallback check only) | c081129 + uncommitted teaching work | local val / eng / 30 | 0 | 43.3% (always D) | 2.0 | 2.1 | 0 | All 30 calls refused. Five sample contract rows remain valid D/error. No inference accuracy claim; solver unchanged. |
| 2026-11-14 | unoq-wifi-baseline | c081129 + uncommitted teaching deployment; solver unchanged | UNO Q val / eng / 30 | 0 | 36.7% (11/30) | 10.4 | 25.6 | 0 | All 30 status ok; trails always-D 43.3%. Deployment smoke baseline, not main-release confirmation. A/B/C/D/E predictions: 7/9/1/12/1. |

<!-- Add our rows below this line. Example:
| 2026-11-15 | baseline | abc1234 | val / all / 50 | 0 | 24.0% | 9.1 | 13.0 | 0 | Our board's baseline. Bias D×20 |
-->

| 2026-11-14 | usb-setup-v1 | c081129 + uncommitted setup work; solver unchanged | UNO Q val / eng / 30 (`--limit 50`, only 30 available) | 0 | 36.7% (11/30) | 8.3 | 12.3 | 0 | Five sample contract rows valid, all 30 validation statuses ok. Same aggregate answers as prior development baseline; always-D remains 43.3%. This checks deployment continuity, not a reasoning improvement or main-release result. |

## Error notes

Write qualitative findings from the explorer or from reading the per-problem CSVs here, such as "fails on problems that need the picture" or "Catalan is X points below English".

The Wi-Fi deployment baseline is a small, D-heavy English sample: true A/B/C/D/E
counts are 2/6/7/13/2. Accuracy is 7/17 with OCR text choices and 4/13 without
them; the text-only model server cannot inspect the original diagrams. This
does not establish that OCR or missing diagrams caused individual errors.
Accuracy by level: level 0 = 7/20; level 1 = 4/10. No solver changes or improvement
over the baseline are claimed. Teaching grading still uses the supplied labels.

## Teach-side metrics

Initial T-087 preparation: 39 application/graph tests and 11 deployment/launcher tests passed. Browser
checks at 1440x1100 and 390x844 exercise the connected map and reflection/review
gates. Only a 1,226-byte keyword relation export is loaded on the board runtime;
layout runs in the browser. Python/JavaScript syntax and archive checks pass.
No attached board or active model was available, and the user deferred hardware
testing. No board RAM, real USB/login behavior or live tutoring latency is claimed.
The T-047 simulation below predates the new path-first policy.

T-088 physical-board follow-up: all 51 application/deployment checks pass with
`python3 -S`, including the added real-systemd parser regression. The deployed
runtime's 260 files match the local source byte-for-byte after correcting the
installer's `WorkingDirectory` quoting. Both model hashes and the llama.cpp
checkout match `config.env`. No teammate repository or model service was changed.
The owner installed the system boot service via App Lab. Automatic process
recovery retained synthetic notebook evidence; an actual board reboot and USB
opening remain untested. The service's measured memory peak before recovery was
19,005,440 bytes (18.1 MiB, systemd accounting).

The official-entry-point contract/eval/repeat sequence collected 206 memory samples
at two-second intervals: minimum MemAvailable 2697 MiB, maximum used swap 0,
peak sampled RSS 31.1 MiB for the temporary tutor, 1058.7 MiB for the LLM and
76.4 MiB for embeddings. The tutor was restarted/installed during this sequence;
its sampled RSS refers to the initial test process, not a continuous service peak.
No competing model-inference test ran during evaluation. Five sample answers
repeated exactly; this is a sample determinism check, not a universal proof.

Reports, per-problem CSVs and the runtime hash manifest are in ignored
`results/unoq-wifi/`; browser screenshots are `results/board-browser-*.png`.
These numbers describe the uncommitted development deployment, not an official
main-branch result. The fresh 30-row validation file was copied separately for QA
and is not part of the student runtime bundle or its catalog.

Final bundle check restored 118 missing training images from local cached Parquet:
170/170 originals present, zero required diagrams missing. Existing images and
training JSONL were unchanged byte-for-byte; restored labels matched the source.
Training-only packaging excludes validation records/images and all student DBs.

If we choose a Teach idea, its own metrics go here (hint leak rate, rung latency, simulated-student paths, rewrite pass rate…), with the same discipline: date, commit, conditions, number, conclusion.

| Date | Change | Conditions | Result | Limitation |
| --- | --- | --- | --- | --- |
| 2026-11-14 | T-090 standalone Windows setup | PyInstaller 6.22.0; Python/Tk and ADB bundled; Windows x64 per-user install; UNO Q setup QA | 26,771,591-byte installer verifies all 993 payload files, including when run from MATHTUTOR (D:). Both frozen GUIs open. Registered login command opens the tutor with only System32 on PATH and invalid external Python paths. 21 PC checks pass with two platform skips; all nine new setup checks pass on the board, including USB rollback. FAT16 passes `fsck.fat -n`; setup-drive service active/enabled. Windows selected inbox storage/WinUSB/serial drivers. Full safe shutdown/replug passed: boot ID changed, four services active, read-only volume returned, installed watcher opened the tutor at 22:12:15 Europe/Madrid and model ready by 22:12:21; three synthetic attempts retained, SQLite check ok. User confirmed drive/browser. | Fresh-PC behavior and actual Windows login remain unverified. Restricted PATH testing does not establish a pristine machine. Disconnect-to-opening time includes the user's physical unplug/replug interval, not just boot. Earlier application/USB checks remain separate. Artifacts: `results/windows-setup-latest.json`, `results/setup-login-command-check.json`, `results/setup-gui-check.json`, `results/setup-drive-windows.json`, `results/setup-drive-board.json`, `results/setup-replug-check.json`. |
| 2026-11-14 | T-089 USB boot and automatic reopening | Actual UNO Q USB serial 2727288917; existing PC Python/ADB; temporary watcher on 7013; safe shutdown and physical unplug/replug | Board boot ID changed; all three services active; watcher logged disconnect at 20:32:37 Europe/Madrid and automatic opening at 20:33:06; model ready by 20:33:12. Three synthetic notebook attempts survived, SQLite check ok. Browser USB tests passed with no JS errors or external requests; user confirmed opening. | No new installation or Windows startup changes. Requires the temporary watcher running on this already prepared PC. Windows login startup and a PC without tools were not tested; Wi-Fi was not disabled. No solver changes or repeat accuracy evaluation. Evidence: `results/usb-demo-check.json`, `results/usb-browser-check.json`. |
| 2026-11-14 | T-088 live tutor on UNO Q | Wi-Fi SSH tunnel, 170 training items + 30 original diagnostics, existing Qwen and bge services; synthetic notebooks | All 170 original images served; 51 automated tests; desktop/mobile-width browser flow; persistent BKT/path updates; real hint selection succeeds for all 4 requests in 10.1–23.0 s, immediate stored guidance 16–21 ms | Four hint samples do not establish a latency distribution or teaching quality. No real learning outcomes, USB, Windows startup or full-board reboot test. |
| 2026-11-14 | T-088 skill embedding graph | Authored descriptions, existing bge-small model through SSH, cosine threshold 0.65, 2 neighbors per skill | 12 related edges in a 2214-byte artifact; runtime loads edges without embedding calls | Descriptions, threshold and relations have not been educator validated; similarity never creates prerequisites or learner evidence. |
| 2026-11-14 | T-085 option display enrichment | Laptop OCR on 52 train + 8 validation starter rows; local images | Train: 34 text sets + 10 picture-preview sets; validation: 5 text sets + 1 picture-preview set. All 60 official labels preserved. Live UI grading accepted all 52 supplied training labels. | Measures choice-display coverage and key-based grading, not SLM accuracy. OCR/crops are not fully reviewed. `eval.py` and board contract checks not run: board model services are unavailable. |
| 2026-11-14 | T-086 graph/student model | Uncommitted `ui/student-practice`; original fixtures and temporary databases | 28 tests pass: BKT, first-answer/assistance/translation rules, concurrency, migration, multi-skill diagnosis, review/transfer, scoped reports, bounded hint validation, clustering/export and media | Parameters and initial annotations are provisional. Live SLM and board measurements unavailable. |
| 2026-11-14 | T-086 browser flow | Installed Chrome; 1360x1000 and 390x844; temporary profile DB | Graph/evidence, recommendations, hints, report, image Close/Escape/backdrop, reveal and display modes pass; no JS errors, external requests or page-wide horizontal overflow | Headless desktop browser at mobile width, not a physical touch device or board test. |
| 2026-11-14 | T-047 selector simulation | Seed 42; 30 synthetic learners, 20 recommendations each; same seeded diagnostic failure; original fixtures; static response probabilities | Weak/supporting-skill targeting: adaptive 36.8%, random 22.0%, correct-harder 23.5%; all 600 recommendations per policy fresh. Mean skills practised: 6.33 / 9.47 / 9.50. Adaptive Python selection mean 0.310 ms, worst 1.772 ms on laptop | Targeting is a declared tag proxy, not learning improvement. Most diagnostics share grade level 0, limiting the harder/easier comparator. No learned student parameters, delayed assessment or board latency. |
| 2026-11-14 | T-086 clustering preparation | 52 unique English training IDs; deterministic k=8, seed 42; explicit TF-IDF fallback | Review CSV and vectors/centroids/assignments/representatives exported to ignored `data/clustering-teaching-v1/`; no labels inferred automatically | Keyword clustering exercised locally; semantic embedding quality and educator label review pending. |
| 2026-11-14 | Preserve option display after dataset regeneration | Input files were expanded during T-086 to 170 train / 30 validation rows. Re-enriched remaining incomplete choices and checked IDs/labels before and after. | Train: 101 text + 10 picture sets; validation: 17 text + 1 picture set. All 200 supplied labels unchanged. Added a source-change check so OCR cannot overwrite a concurrently regenerated JSONL file. | 59 train / 12 validation items still require original images. New questions remain unclassified without reviewed tags. This is display preparation, not solver evaluation. |

## Process metrics (planned, not yet measured)

Defined by T-091, to be measured with real students in T-093. All come from
`thinking_events` (first choice per step) and `learning_events` joined to
`sessions` by session ID; `/api/profile` returns them as `process_summary` and the
notebook prints them. They are descriptive indicators: steps never change BKT.

| Metric | Definition | Conditions |
| --- | --- | --- |
| `steps_first_try_rate` | Steps answered right on the first choice / steps attempted | First choice per step and session only; retries excluded |
| `problems_with_all_steps_right` | Problem sessions with all three steps done and no wrong choice | Sessions with thinking steps only |
| `first_attempt_accuracy_when_steps_right` | Share of correct answers among eligible first attempts in sessions where every step was right first time | Eligible = unaided first exposure, as in BKT; null without data |
| `first_attempt_accuracy_when_step_missed` | Same, in sessions where at least one step was missed first time | Same conditions; the gap between the two is the "does process predict outcome" signal, not a causal effect |

Also planned for T-093: hints requested per problem before and after steps were
introduced, on comparable problems. Nothing has been measured yet.


## Error signatures (T-108)

`laptop/ml/signatures.py` on 2026-11-15 (laptop, standard library, 0.2 s). Input:
`data/train.jsonl` + `data/val.jsonl` (1747 canonical problems, English row used,
Catalan row checked for the same numeral multiset). Coincidence limit 0.6; costs and
order as in [laptop/ml/README.md](../laptop/ml/README.md). Report:
`results/signatures-report.json`.

| Measure | Value |
| --- | --- |
| Problems considered | 1747 |
| Problems with all five options numeric | 805 |
| Distractors (4 per numeric problem) | 3220 |
| Distractors explained | 981 (30.5%) |
| … excluding copied number and off-by-one-from-answer | 402 (12.5%) |
| Matches dropped as coincidental | 407 |
| Problems with ≥ 1 explained distractor | 518 |
| Problems with an unambiguous `answer_op` | 125 |
| English/Catalan pairs whose numerals differ | 40 (OCR/translation, e.g. `lvl-0_2015_4`); English row used |

Operations: answer −1 246, answer +1 215, copied number 118, difference 55, sum 52,
double 49, half 49, product 30, ×10 24, quotient 20, count of numbers 19, −1 17,
÷10 16, +1 16, (a+b)×c 14, add all 11, a×b−c 9, square 7, (a−b)×c 6, a×b+c 5,
multiply all 3. Samples: 15/20 distractors explained.

Ablation of the coincidence limit (same input): no limit 1388 explained (43.1%);
0.67 → 1075; **0.6 → 981 (chosen)**; 0.5 → 962 but drops the textbook (2+3)×4 slip in
sample-2; 0.34 → 834. Two rule changes after a first spot check: the copied-number
match is tried first (a "10" in the text was explained as "11 − 1"), and sums or
differences with 0 and products or quotients with 1 are not generated.

**Spot check (agent, not yet a human review):** 30 random explained distractors
(seed 2026, off-by-one excluded) were judged against the problem text: 11/30 are a
plausible slip (8 of them copied numbers, e.g. "48 children" answering "how many
families"), 19/30 are coincidences, mostly small values or numbers like years.
Conclusion: real Kangaroo problems rarely fail by one naive operation, so arithmetic
signatures are worded as "could come from" and kept to one sentence; the copied
number and the method-rung hint are the reliable parts. A teammate should repeat the
30-item check before the pitch quotes a precision figure (T-112).

## Difficulty model (T-102, laptop, 2026-11-15)

Target: points (3/4/5) derived from the problem's position within its level-year
paper (thirds). Features: PCA(32) of the English bge-small embedding (laptop fp32
vectors, see the note below) plus level, text length, words, numerals, image,
option count, numeric options and option spread. Hold-out: years 2023–2024
(215 rows); CV: 5-fold grouped by year. Majority class is 5 points.

| Model | Hold-out accuracy | Majority | MAE (expected points) | Spearman vs position (pooled / within paper) | CV accuracy |
| --- | --- | --- | --- | --- | --- |
| Decision tree, depth 6 | 0.465 | 0.395 | 0.708 | 0.322 / 0.343 | 0.403 ± 0.036 |
| Gradient boosting, 150×depth 3 | **0.516** | 0.395 | **0.644** | **0.435 / 0.475** | 0.474 ± 0.015 |

The exported models are refitted on all 1747 labelled rows. `b = (level + (points − 3)/2) / 8`
uses observed points for every current row; the model only fills in problems
without a paper position. Pure-Python evaluation matches scikit-learn within 5e-7.
Artifacts: `data/ml/difficulty_model.json` (372 KiB), `data/ml/difficulty.json`,
`results/difficulty-metrics.json`.

## Cross-lingual alignment (T-104, laptop, 2026-11-15)

Orthogonal Procrustes on 1398 training (eng, cat) pairs, 349 held out (seed 42),
retrieval against all 1747 English vectors.

| Metric (held-out, cat → eng) | Before | After |
| --- | --- | --- |
| recall@1 | 0.501 | **0.725** |
| recall@5 | 0.696 | **0.894** |
| Mean cosine of true pairs | 0.723 | 0.831 |

Training-split recall@1 reaches 0.97, so the 384×384 fit overfits; quote the
held-out numbers. Matrix: `data/ml/procrustes.json`, 1.18 MB.

## Problem map (T-106, laptop, 2026-11-15)

1747 nodes (English vectors), kNN k=5 cosine, 6971 undirected edges, Louvain
(seed 42) → 15 clusters, modularity 0.699; UMAP layout (seed 42). File 286 KB.
Cross-lingual check on the 349 held-out ids: the Catalan vector's nearest English
neighbour lies in the English twin's cluster 0.722 (unaligned) → 0.888 (aligned);
an English vector's nearest English neighbour does so 0.907 of the time.
Stepping-stone paths use cost 10·Δb² + 0.1 per edge; from the five easiest problems
to the hardest the path climbs 0.375 → 0.5 → 0.625 → 0.69 → 0.75 → 0.875 → 1.0.
Artifacts: `data/ml/problem_map.json`, `results/map-metrics.json`.

**Embedding note:** all three artifacts use laptop fp32 `BAAI/bge-small-en-v1.5`
vectors (`laptop/ml/embed_problems.py --local`) because the board was unreachable
overnight. Regenerate with `--port 8082` (board GGUF Q8) before quoting numbers in
the final README; differences are expected to be small.
