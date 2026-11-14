# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- **Skills:** the project skills are in `.skills/`. To have Claude Code load them automatically, link them once from the repository root:

  ```bash
  mkdir -p .claude && ln -s ../.skills .claude/skills
  ```

  Use `unoq-board` for anything that runs on the board, `m3kang-copilot` for pipeline changes and experiments, `unoq-hardware-ui` for App Lab, the web page and the LED matrix, and `publish-project` for the deliverables.
- **You usually run on the laptop, not the board.** Commands that need the model servers (`predict.py`, `eval.py`, `build_index.py`, `explorer/server.py`) must run on the board over SSH. Say so explicitly instead of running them locally and reporting a connection error as a result.
- **Read before you act:** [docs/STATUS.md](docs/STATUS.md) for what exists, and [docs/TODO.md](docs/TODO.md) for what to do next.
- **When you finish a task:** update `docs/TODO.md`, `docs/STATUS.md`, and `docs/EXPERIMENTS.md` or `docs/DECISIONS.md` when relevant, in the same commit as the code.
