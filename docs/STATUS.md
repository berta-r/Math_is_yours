# Status

> What's done and working **right now**. Update it whenever a task in [TODO.md](TODO.md) is finished. Keep it short: facts, numbers with their conditions, and dates.

**Last updated:** 2026-11-14

## Summary

The [demo-first AI proposal guide](AI-PROPOSAL-GUIDE.md) has been recovered from `docs/demo-first-proposals` and is linked from AGENTS.md.

AGENTS.md now requires direct, critical, evidence-based answers limited to the user's question; the proposal guide's full format applies only when requested.

**Reason (14 November, branch `exp/reason-strategies`, unmerged; all numbers from a laptop with the board's GGUF and the pinned llama.cpp, CPU only):** the one-letter baseline is at chance, 20.1% ±0.7 on 3494 problems, below always-D (24.7%). Ten variants were measured and none beats chance: calibrated logprobs, 4 fixed examples, option rotation with voting, 80 tokens of reasoning, program of thought, value instead of letter, a learned judge, and Qwen3.5 2B. The model chooses a position, not a value: on trivial additions it picks the right letter 19% of the time but writes the right number 82%. Full table and notes in [EXPERIMENTS.md](EXPERIMENTS.md). Pending: what `predict.py` ships (TODO T-039), board latency, and the hidden-test format. `main` is unchanged (`REASON_STEPS=letter`).

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
| Train / val sizes | 2932 / 562 (eng+cat, shard 0); text-only 1376 / 246 |

## Key numbers

| Metric | Value | Conditions |
| --- | --- | --- |
| Baseline accuracy | 20.1% ±0.7 | laptop, same GGUF, train+val eng+cat, n=3494. Text-only: 20.6% ±1.0 (n=1622) |
| Baseline latency (mean / worst) | — | |
| RAG k=1 accuracy | — | |
| Best accuracy so far | 24.7% (always D, no model) | n=3494. No model-based variant beats chance |

## Main workstreams

Both **Teach and Reason are required main deliverables** (TODO T-023 and T-024). Teach is delegated to a teammate; its specific learning flow and the first Reason improvement still need to be scoped in T-020. Neither MVP is marked complete. See [DECISIONS.md](DECISIONS.md).

## Known issues

None yet.
