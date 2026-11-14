# Decisions

> Short records of why things are the way they are (a lightweight ADR). Add one whenever the team decides something that another person or agent might otherwise undo or question. Never delete an entry: if a decision changes, add a new one that says "Supersedes D-00X".

Template:

```
## D-00X · Title (YYYY-MM-DD)
**Status:** accepted | superseded by D-00Y
**Context:** what problem or question we had.
**Decision:** what we chose.
**Alternatives:** what we didn't choose, and why.
**Consequences:** what this implies for code, data or measurements.
```

---

## D-001 · Keep the organizers' pinned stack as our starting point (2026-11-14)
**Status:** accepted
**Context:** the template pins llama.cpp `2cbe0ec`, Qwen3.5 0.8B Q8_0 and bge-small-en-v1.5 Q8_0, all tested on the UNO Q 4 GB, so every team's results can be compared.
**Decision:** start from these exact versions. Any model change goes through an experiment and a new decision.
**Alternatives:** a bigger or different model from the start. Rejected because the RAM and the 60 s limit are unknown on our board until we measure.
**Consequences:** our baseline is comparable with the organizers' 22.5%.

## D-002 · Documentation in English, structured for AI agents (2026-11-14)
**Status:** accepted
**Context:** the README, code and skills are in English, and several AI agents will work on the repository.
**Decision:** `AGENTS.md` is the entry point, `CLAUDE.md` imports it, and `docs/` holds the challenge, architecture, data, configuration, commands, status, todo, experiments and decisions. The team talks in Catalan.
**Consequences:** every finished task updates TODO and STATUS in the same commit.

## D-003 · Idea to build (pending)
**Status:** pending, see TODO T-020
**Context / Decision:** to be filled in after the brainstorm: the idea, the metric we'll measure, and the first experiment.

## D-004 · Deliver both Teach and Reason (2026-11-14)
**Status:** accepted
**Context:** the task list treated Teach approaches as optional candidates alongside the official Reason score.
**Decision:** the team will deliver both Teach and Reason as required main workstreams, each with a P0 MVP and an owner. T-020 chooses the Teach approach and scopes the first Reason experiment; it does not choose between the two workstreams.
**Consequences:** evaluate Reason accuracy and latency, validate the selected Teach learning flow, and demonstrate both offline on the UNO Q. The specific approach in D-003 remains pending.

## D-005 · Reason strategies as composable pipeline steps, one branch (2026-11-14)
**Status:** accepted
**Context:** with less than a day left, we discussed several Reason ideas (calibrated logprobs, near-duplicate lookup, program of thought, a learned judge, NMF topics, fine-tuning, long reasoning). We need to compare them on the same validation sample without the overhead of one branch per idea.
**Decision:** `copilot/pipeline.py` runs a fixed-order list of steps selected with `--steps` (or `REASON_STEPS` in `config.env`): `dedup` → `letter`|`logprobs` → `pot`. A later step only replaces the answer when it finds a letter, so there is always an answer. `main` keeps `REASON_STEPS=letter` until a combination beats the baseline on the same sample. All strategies live on `exp/reason-strategies`; `eval.py --name` plus the `method`/`detail` columns tell which step answered each problem.
**Alternatives:** one branch per idea (more merges, harder to compare); long chain-of-thought (the organizers measured it: worse and 3× slower); fine-tuning (no workflow, no time); NMF/K-means topics (useful for Teach skill labels, not for picking a letter); a bigger GGUF model (kept as a later option, T-034).
**Consequences:** every step is measured on the computer with the model first (accuracy), then on the board (latency, `over 60 s` must be 0). Only the winning combination changes `REASON_STEPS` on `main`. The model-written expressions are evaluated through an AST whitelist (`copilot/safe_eval.py`), never with free `exec`.

## D-006 · Reason findings: the model is at chance; `predict.py` choice pending (2026-11-14)
**Status:** pending, see TODO T-039
**Context:** we measured the baseline and ten variants with the real model (Qwen3.5 0.8B Q8_0, pinned llama.cpp) on a laptop, on hundreds to thousands of problems instead of 40–100. Baseline: 20.1% ±0.7 on 3494 problems; always-D: 24.7%. No variant beats chance, including Qwen3.5 2B. Cause: under the one-letter grammar the model picks a position (rotating the options does not move its choice); it can write the value of a one-step sum (82%) but not solve multi-step problems within the token budget.
**Decision (so far):** none of the strategies is merged into `main` as the default. Sample sizes under a few hundred problems are not used to compare runs. Pruning or other home-made compression of a larger model is ruled out: zeroed weights give no size or speed gain in GGUF/llama.cpp, structured pruning needs retraining, and the binding limit is time, not RAM.
**Open:** what `predict.py` ships (model baseline at about 20%, or a no-model rule at about 25%); whether the organizers allow another model (the README lists it as an idea; a teammate reports it is not allowed); whether the hidden test provides the options as text.
**Consequences:** the Reason deliverable is the measured negative result plus a safe `predict.py`. The finding "ask for the value, not the letter" is usable in Teach to check one-step calculations.

