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

<!-- Add our rows below this line. Example:
| 2026-11-15 | baseline | abc1234 | val / all / 50 | 0 | 24.0% | 9.1 | 13.0 | 0 | Our board's baseline. Bias D×20 |
-->

## Error notes

Write qualitative findings from the explorer or from reading the per-problem CSVs here, such as "fails on problems that need the picture" or "Catalan is X points below English".

(empty)

## Teach-side metrics

If we choose a Teach idea, its own metrics go here (hint leak rate, rung latency, simulated-student paths, rewrite pass rate…), with the same discipline: date, commit, conditions, number, conclusion.

(empty)
