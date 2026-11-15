# Compute-first solver for `predict.py`

`predict.py` no longer asks the language model for a letter. A small code model writes one
Python expression for the problem, Python computes the value, and the value is matched to the
options. Set `SOLVER=letter` in `config.env` to get the organisers' baseline back.

## How it works

1. **Blind try.** The model sees only the statement and writes one expression. The answer is
   accepted only if the computed value equals one of the options.
2. **Informed try.** The model sees the statement and the options and replies with an
   expression or with one of the option values.
3. **Guess.** Problems that need their figure, problems without options and problems that run
   out of time get a letter without calling the model: the letter given least often so far.

The expression is evaluated by `copilot/safe_eval.py` (one expression, whitelisted syntax, no
imports, time limit) and matched with `copilot/values.py`. Both files come from the branch
`exp/reason-strategies`.

A planner keeps every problem under the 60 s limit. It uses the board's measured speeds
(`COMPUTE_READ_TPS`, `COMPUTE_GEN_TPS`) and the request timeout as the hard stop.

## Model and service

- Model: Qwen2.5-Coder 1.5B Instruct, Q8_0, 1.9 GB, Apache 2.0.
- Service: `math-compute`, a third `llama-server` on `127.0.0.1:8084` with two slots, one per
  prompt, so the examples are read once and stay cached.
- Install on a board: `bash board/06_compute_server.sh` (downloads and checks the model,
  installs the service, starts it at boot). `math-llm` and `math-embed` are not changed.
- If the service is not running, `predict.py` falls back to the letter call by itself.

The first `predict.py` after a restart reads the examples once. On our board that took 379 s.
With the examples already cached it takes about one minute. Run
`python3 predict.py --input data/sample_problems.jsonl --output results/check.csv` once before
a timed run.

## Results

Measured on the organisers' practice set (50 problems, English and Catalan, 100 rows).

| Where | Rows | Correct | Latency |
|---|---|---|---|
| Laptop, same model file | 100 | 49 (49.0%) | not comparable |
| Board, first planner | 30 | 14 (46.7%) | mean 28.3 s, worst 56.1 s, none over 60 s |
| Board, final planner | 30 | 15 (50.0%) | mean 26.2 s, worst 56.0 s, none over 60 s |

In the last board run, 9 of the 30 rows were guessed (6 need their figure) and 3 of those
guesses were right, where 1.8 is expected by chance. On the 21 rows the model answered, 12
were right. By language: English 9/15, Catalan 6/15.

## Limits

- The examples in the prompt were written after looking at the practice set, so the practice
  numbers are optimistic. Expect less on new problems.
- 30 rows is a small sample: two or three answers either way is noise.
- Figure problems are not solved, only guessed.
- The solver was not measured with other programs using the board. A shared board is slower
  and more problems run out of time.
