# Status

> What's done and working **right now**. Update it whenever a task in [TODO.md](TODO.md) is finished. Keep it short: facts, numbers with their conditions, and dates.

**Last updated:** 2026-11-14

## Summary

**Reason strategies (14 November, branch `exp/reason-strategies`, unmerged):** `copilot/pipeline.py` now runs a list of steps chosen with `--steps` / `REASON_STEPS` (`dedup`, `letter`, `logprobs`, `pot`; see [02-architecture.md](02-architecture.md)). `main` behaviour is unchanged (`REASON_STEPS=letter`). Verified end-to-end against a mock llama-server on the laptop (contract, timeouts, value matching); **not yet measured with the real model**: a teammate runs `eval.py` on the computer with the model and on the board. Data: the full `train.jsonl`/`val.jsonl` (eng+cat, shard 0) are being prepared by a teammate; a laptop run of `prepare_m3kang.py` takes about an hour (OCR).

Conversation update (14 November): the user reports that the board model is installed and answering questions; this has not been independently verified here. Teach is delegated to a teammate and Reason improvements remain unmeasured. The setup checklist below has not yet been reconciled with the board.

The main challenge code is still based on the organizers' template. Prepared data availability, setup completion and baseline measurements remain unverified; the specific Teach approach and Reason improvement are pending. The [Tukey side project](../side-project/README.md) has a workspace and dashboard brief; implementation and measurements are pending.

## Setup progress (README steps)

| Step | What | State | Date | Notes |
| --- | --- | --- | --- | --- |
| 0 | Connect to the board (App Lab update, IP, SSH) | ⬜ pending | | |
| 1 | Check the board (RAM, disk, clock, internet) | ⬜ pending | | |
| 2 | Install the build tools | ⬜ pending | | |
| 3 | Build llama.cpp at the pinned commit | ⬜ pending | | |
| 4 | Download and verify the models | ⬜ pending | | |
| 5 | Hello world: language model | ⬜ pending | | |
| 6 | Hello world: embeddings | ⬜ pending | | |
| 7 | Run both models as services | ⬜ pending | | |
| 8 | Clone the repo on the board and run the sample problems | ⬜ pending | | **Minimum required for every team** |
| 9 | Prepare M3Kang on the laptop | ⬜ pending | | |
| 10 | Copy the data to the board | ⬜ pending | | |
| 11 | Measure our baseline | ⬜ pending | | |
| 12 | Build the RAG index and try it | ⬜ pending | | |
| — | Explorer (optional) | ⬜ pending | | |
| 13 | Choose the idea | ⬜ pending | | |
| 14 | Implement, measure, analyse errors, UI, pitch | ⬜ pending | | |
| 15 | Publish (GitHub + Project Hub) | ⬜ pending | | |

States: ⬜ pending · 🟨 in progress · ✅ done · ❌ blocked (say why).

## Environment facts

| What | Value |
| --- | --- |
| Board IP | unknown |
| Board free RAM with both services running | not measured |
| llama.cpp commit built | not built |
| Languages in our dataset | not decided |
| Train / val sizes | — |

## Key numbers

| Metric | Value | Conditions |
| --- | --- | --- |
| Baseline accuracy | — | |
| Baseline latency (mean / worst) | — | |
| RAG k=1 accuracy | — | |
| Best accuracy so far | — | |

## Main workstreams

Both **Teach and Reason are required main deliverables** (TODO T-023 and T-024). Teach is delegated to a teammate; its specific learning flow and the first Reason improvement still need to be scoped in T-020. Neither MVP is marked complete. See [DECISIONS.md](DECISIONS.md).

## Known issues

None yet.
