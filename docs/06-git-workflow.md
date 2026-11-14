# 06 · Git workflow

> Read this before you create a branch, commit, merge or push. It's how our team of 4 works during the 24-hour datathon. Agents must follow it too.

## The model

`main` is the version that **always works on the board**. All work happens on short-lived branches that are merged back into `main` within a few hours, not at the end.

```
main     ──●──────●──────────●────   ← always works on the board
            \    /            \
feature/x    ●──●              ●──●  ← one task, merged in a few hours
```

## Branches by role

One branch per person and task (a task is a TODO item). Roles come from TODO T-021. Each role touches different files, which keeps conflicts rare.

| Role | Prefix | Example | Main files |
| --- | --- | --- | --- |
| Board / infra | `infra/` | `infra/services` | `board/`, `config.env` |
| Copilot / experiments | `exp/` | `exp/debias-logprobs` | `copilot/`, `docs/EXPERIMENTS.md` |
| UI (App Lab + LED) | `ui/` | `ui/web-led` | App Lab app (`python/`, `sketch/`, `assets/`) |
| Docs / pitch | `docs/` | `docs/readme-final` | `README.md`, `docs/` |
| Quick bug fix | `fix/` | `fix/timeout-margin` | any file |

Name branches `<prefix>/<what>`, in lowercase with hyphens.

## The cycle for every task

```bash
git checkout main && git pull                  # start from the latest main
git checkout -b exp/debias-logprobs            # one branch per task
# … work, with small commits that reference the task:
git commit -m "T-030: request logprobs from llama-server"
git push -u origin exp/debias-logprobs         # back it up and share it

# On the board: check the contract, then measure (see 05-commands.md)
python3 predict.py --input data/sample_problems.jsonl --output results/check.csv
python3 eval.py --limit 50 --name debias-v1

# Merge
git checkout main && git pull
git merge exp/debias-logprobs && git push
git branch -d exp/debias-logprobs && git push origin --delete exp/debias-logprobs
```

## Rules

1. **`main` must always work.** Before you merge, `predict.py` must give one letter for each of the 5 sample problems.
2. **Never work directly on `main`.** The only exception is small updates to `docs/STATUS.md` and `docs/TODO.md`.
3. **Pull often**, and always before you start a new task.
4. **One experiment, one branch.** If it doesn't improve the numbers, don't merge it, but still log it in [EXPERIMENTS.md](EXPERIMENTS.md) (on `main`). What didn't work is part of the deliverable.
5. **Pull requests are optional.** Merging directly is faster. Open a PR (and ask a teammate to look) only for changes to `copilot/pipeline.py` or `copilot/llm.py`, because they change the official score.
6. **Delete merged branches**, both locally and on GitHub.
7. **Never commit M3Kang data** (`data/*.jsonl` except the sample, `data/images/`, `*.db`) or models (`*.gguf`). Run `git status` before every commit.

## The board is shared

There's one board, with its own clone at `~/datathon-UPC-maths-qualcomm-arduino-unoq`.

- Its default state is `main`: `git checkout main && git pull`.
- To test a branch: `git fetch && git checkout <branch>`. **Tell the team first**, because the services, the RAM and the CPU are shared, and two `eval.py` runs at once slow both down and make their latencies meaningless.
- Put it back on `main` when you're done.
- Official numbers (for STATUS, the final evaluation and the pitch) always come from `main`.
- `results/` isn't committed. Copy the important rows of `results/ablations.csv` into `docs/EXPERIMENTS.md`.

## Conflicts

- Whoever merges resolves the conflict.
- Hot spots: `docs/TODO.md`, `docs/STATUS.md` and `copilot/pipeline.py`. If two people need `pipeline.py`, agree first, or put new logic in a new module (`copilot/hints.py`…) and add only one call to `pipeline.py`.
- For conflicts in TODO or STATUS, keep both sides' updates.

## For AI agents

- Before you change code, check the branch with `git branch --show-current`. If it's `main`, create a branch following the table above.
- Don't push or merge unless the person you're working with asks you to.
- Reference the task ID in commit messages (`T-030: …`).
