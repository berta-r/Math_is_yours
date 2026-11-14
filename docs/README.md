# Project documentation

Our team's documentation for the Math on the Edge copilot. The organizers' setup guide is the root [README.md](../README.md). These files explain the project, track progress and record decisions, so that people and AI agents can pick up work without asking.

**Agents: start at [../AGENTS.md](../AGENTS.md).**

## Files

| File | Read it when | Changes |
| --- | --- | --- |
| [01-challenge.md](01-challenge.md) | You need the goal, the rules, the deliverables or the scoring | Rarely |
| [02-architecture.md](02-architecture.md) | You're about to change code, or need to know what calls what | When the architecture changes |
| [03-data.md](03-data.md) | You touch M3Kang, JSONL files, OCR, the index or the splits | When the data pipeline changes |
| [04-configuration.md](04-configuration.md) | You change a model, port, thread count, limit or seed | When `config.env` changes |
| [05-commands.md](05-commands.md) | You need to run, check or debug something | When a command changes |
| [06-git-workflow.md](06-git-workflow.md) | You create a branch, commit, merge or push | Rarely |
| [STATUS.md](STATUS.md) | You want to know what's done and working | **After every finished task** |
| [TODO.md](TODO.md) | You want to know what to do next | **After every finished or new task** |
| [EXPERIMENTS.md](EXPERIMENTS.md) | You ran `eval.py`, or want to compare approaches | **After every eval run worth keeping** |
| [DECISIONS.md](DECISIONS.md) | You want to know why something is the way it is | When the team decides something |

## Conventions

- **English, short sentences, exact paths and full commands.** Write for a reader with no context.
- **Link, don't copy.** If the root README explains a step, link to its heading (`../README.md#step-11-measure-the-baseline`) instead of repeating it.
- **Dates are absolute** (`2026-11-14`), never "yesterday" or "last week".
- **Numbers come with their conditions:** dataset, `--limit`, languages, commit. A number without conditions is useless.
- **Task IDs** (`T-012`) are stable. Don't renumber them. Reference them in commits: `T-012: add hint ladder rung 1`.
