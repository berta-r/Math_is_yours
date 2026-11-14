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
