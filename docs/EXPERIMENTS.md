# Experiments

> A log of every evaluation worth keeping. `eval.py` writes `results/ablations.csv` on the board, but `results/` isn't committed, so **copy the row here**. Then the history lives in git and agents can read it.

## How to run an experiment

1. **Change one thing** (prompt, k, retrieval rule, model…) and commit it.
2. Contract check: `python3 predict.py --input data/sample_problems.jsonl --output results/check.csv`.
3. `python3 eval.py --limit 50 --name <short-label>`. Always use the same `--limit` and `--languages` to compare, because `eval.py` takes the same sample each time (seed 42).
4. Add a row below, with the **commit**, and a conclusion in one line.
5. For final numbers, use `--limit 0`.

The reference points are random guessing at 20%, always-D at about 25%, and the organizers' baseline at 22.5% (40 English problems).

**Reason strategies** (branch `exp/reason-strategies`): compare on the same sample, in this order.

```bash
python3 analyze_data.py data                                        # data facts: numeric options, duplicates, label bias
python3 eval.py --limit 100 --steps letter   --name baseline
python3 eval.py --limit 100 --steps logprobs --name logprobs       # calibrated letter probabilities
CALIBRATION=none python3 eval.py --limit 100 --steps logprobs --name logprobs-raw
python3 build_index.py                                             # once, for dedup
python3 eval.py --limit 100 --steps dedup,logprobs --name dedup
python3 eval.py --limit 100 --steps logprobs,pot --name pot        # program of thought
python3 eval.py --limit 100 --steps dedup,logprobs,pot --name all
```

Write down the machine (board or which computer) with each row: accuracy transfers between machines with the same GGUF, latency does not. On a computer, read the **Board estimate** line instead of Latency: it converts the tokens each problem read and wrote into board seconds (`BOARD_PREFILL_TPS`, `BOARD_GEN_TPS` in `config.env`). The per-problem CSV has `method` (which step answered) and `detail` (scores, neighbour, expression): read it before deciding.

## Results

| Date | Name | Commit | Input / langs / n | RAG k | Accuracy | Mean s | Worst s | Over 60 s | Change, and conclusion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | (organizers) baseline | template | 40 eng, text-only | 0 | 22.5% | 8.7 | 12.7 | 0 | Reference. Letter bias: D×21, A×14 |
| — | (organizers) value-not-letter | template | 40 eng | 0 | 17.5% | 9.3 | 13.5 | 0 | Worse |
| — | (organizers) one-line reasoning | template | 40 eng | 0 | 17.5% | 26.3 | 35.0 | 0 | Worse and 3× slower |

| 2026-11-14 | baseline-all (laptop) | 6dcbc88 | train+val, eng+cat, n=3494 | 0 | 20.1% ±0.7 | — | ~10 est. | 0 | One letter under the grammar is chance. Always-D on the same set: 24.7%. Text-only (n=1622): 20.6% ±1.0 |
| 2026-11-14 | logprobs calibrated (laptop) | 6dcbc88 | val text-only, n=246 | 0 | 19.9% ±2.5 | — | ~10 est. | 0 | Content-free and train-marginal calibration: no gain over raw (23.6% ±2.7) |
| 2026-11-14 | fewshot-4 fixed (laptop) | 6dcbc88 | text-only with options, n=400 | 0 | 23.5% ±2.1 | — | ~10 est. | 0 | Same sample baseline 21.5% ±2.1: within noise |
| 2026-11-14 | perm3 vote (laptop) | 6dcbc88 | same 400 | 0 | 17.8% ±1.9 | — | ~30 est. | 0 | Rotating the options: the model keeps choosing the same position, not the same value |
| 2026-11-14 | cot80 (laptop) | 6dcbc88 | same 400 | 0 | 18.0% ±1.9 | — | ~37 est. | 0 | 80 tokens of reasoning, then the letter: chance, 3.5× slower |
| 2026-11-14 | logprobs+pot (laptop) | 891d44d | val text-only, n=100 | 0 | 28% ±4.5 | — | ~32 est. | 2 est. | Program of thought: matched an option in 11 problems, 3 right. Same sample baseline 29% |
| 2026-11-14 | value-not-letter (laptop) | 6dcbc88 | text-only numeric options, n=300 | 0 | 18.7% ±2.2 | — | ~8 est. | 0 | Model writes the value, Python matches it. Matches 17%, right 6% of those |
| 2026-11-14 | Qwen3.5 2B Q4_K_M letter (laptop) | 6dcbc88 | same 400 as fewshot | 0 | 17.2% ±1.9 | — | ~25 est. | 0 | Bigger model, same format: chance, bias to A (251/400) |
| 2026-11-14 | judge: priors + model (laptop) | 6dcbc88 | fit on train, val text-only n=246 | 0 | 20.7% ±2.6 | — | 0 extra | 0 | Logistic regression on letter, value rank and model log-probs. Model weight ≈ 0. Priors alone: train 31%, val 22% (overfits) |
<!-- Add our rows below this line. Example:
| 2026-11-15 | baseline | abc1234 | val / all / 50 | 0 | 24.0% | 9.1 | 13.0 | 0 | Our board's baseline. Bias D×20 |
-->

## Error notes

Write qualitative findings from the explorer or from reading the per-problem CSVs here, such as "fails on problems that need the picture" or "Catalan is X points below English".

- **The one-letter format measures position bias, not maths (14 Nov, laptop, pinned llama.cpp, same GGUF).** On 100 trivial additions ("What is 34 + 52?" with five options) the 0.8B picks the right letter 19% of the time (always A), but writes the right number 82% of the time (2B: 19% vs 100%). On two-step word problems the written value drops to 28% (0.8B) and 13% (2B), and on Kangaroo problems to chance.
- **Sample size:** with n=40–100 the margin is ±5–7 points. Our first 100-problem baseline read 29%; on all 3494 problems it is 20.1% ±0.7. Do not compare runs under a few hundred problems.
- **llama-server returns `top_logprobs` before the grammar is applied:** the letters are often not in the top 10 tokens (first choices are "The", "To", "2"…). `copilot/logprobs.py` asks for 200.
- Laptop numbers are accuracy only; "est." times are tokens converted with 11 tok/s read and 5.5 tok/s write. Nothing here was run on the board.

## Teach-side metrics

If we choose a Teach idea, its own metrics go here (hint leak rate, rung latency, simulated-student paths, rewrite pass rate…), with the same discipline: date, commit, conditions, number, conclusion.

(empty)
