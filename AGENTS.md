# AGENTS.md

Entry point for any AI agent (Claude Code, Codex, Cursor, Copilot…) working in this repository. Read this file first, then open only the `docs/` file your task needs.

## What this project is

Our team's entry to the **Datathon FME 2026, Qualcomm challenge: "Math on the Edge"**. We must build a **math copilot that runs entirely offline on an Arduino UNO Q (4 GB)** and uses the **M3Kang** dataset (multilingual Kangaroo competition problems) to help students learn to reason mathematically.

The copilot must either **Teach** (hints, adaptive practice, error analysis, physical interaction) or **Reason** (pick the right letter A–E on a hidden test set). `predict.py` is scored on the hidden test set whatever else we build.

This repository started from the organizers' template. The template's step-by-step guide is [README.md](README.md) (steps 0–15). Our own documentation lives in [docs/](docs/).

## Current state (update this line when it changes)

**Main challenge setup pending.** The board isn't set up, there's no baseline and no idea chosen. The [Tukey side-project workspace](side-project/README.md) and dashboard brief are created; implementation is pending. See [docs/STATUS.md](docs/STATUS.md).

## Hard rules: never break these

1. **`predict.py` contract:** for every input problem, write exactly one letter `A`–`E`. Output CSV columns: `id,language,answer,seconds,status`.
2. **≤ 60 seconds per problem** (`TIME_LIMIT_SECONDS`). On a timeout or error, answer `FALLBACK_ANSWER` (`D`). `copilot/pipeline.py` keeps a 3 s margin.
3. **Offline:** no network calls at runtime except `127.0.0.1` (the model servers). No cloud APIs.
4. **Deterministic:** `temperature 0`, `seed 42`. The same input must give the same answers.
5. **Board budget:** 4 GB RAM in total, about 3.6 GB usable. Prefill is about 11 tok/s and generation about 5–6 tok/s. Every prompt token costs time.
6. **Board code is standard library only.** No `pip` on the board. `laptop/requirements.txt` is for the laptop only.
7. **Never commit M3Kang data:** no `data/train.jsonl`, `data/val.jsonl`, `data/images/` or `*.db`. The license is research only. `.gitignore` already excludes them. Check `git status` before every commit.
8. **One change at a time, measured.** Every experiment goes through `eval.py --name <label>` and gets a row in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).
9. **Never work directly on `main`:** use a short branch per task (`exp/`, `ui/`, `infra/`, `docs/`, `fix/`), see [docs/06-git-workflow.md](docs/06-git-workflow.md). `main` must always work on the board.
10. If you change `config.env` (model, ports, threads), re-run `board/04_install_services.sh` on the board so the systemd services match.

## Repository map

```
AGENTS.md / CLAUDE.md     ← agent entry points (this file)
README.md                 ← organizers' guide, steps 0–15 (source of truth for setup)
config.env                ← all shared settings (Bash + Python read it)
predict.py                ← OFFICIAL entry point (jury runs it)
eval.py                   ← measure accuracy/latency → results/
build_index.py            ← embed train set into data/index.db (RAG)
copilot/                  ← the copilot library (stdlib only)
  config.py               ←   parses config.env, env vars override
  client.py               ←   tiny JSON HTTP client
  llm.py                  ←   prompt + call to llama-server, grammar [A-E]
  embed.py                ←   call to the embedding server, normalised vectors
  rag.py                  ←   SQLite vector index + brute-force cosine search
  pipeline.py             ←   solve(problem) → letter; THE FILE TO CHANGE FIRST
explorer/                 ← browser app on the board to inspect problems
laptop/prepare_m3kang.py  ← laptop: download M3Kang, OCR the options, split train/val
board/00–05_*.sh          ← board setup scripts; board/systemd/ service templates
data/                     ← sample_problems.jsonl (committed), generated data (ignored)
results/                  ← eval outputs + ablations.csv (ignored by git)
.skills/                  ← Claude skills: unoq-board, m3kang-copilot, unoq-hardware-ui, publish-project
docs/                     ← OUR documentation (see below)
```

## Where to look

| Task | Read |
| --- | --- |
| Understand the challenge, deliverables and scoring | [docs/01-challenge.md](docs/01-challenge.md) |
| Understand how the code fits together | [docs/02-architecture.md](docs/02-architecture.md) |
| Work with problems, JSONL or OCR | [docs/03-data.md](docs/03-data.md) |
| Change a setting, model or port | [docs/04-configuration.md](docs/04-configuration.md) |
| Run something (setup, eval, explorer, debugging) | [docs/05-commands.md](docs/05-commands.md) |
| Create a branch, commit, merge or push | [docs/06-git-workflow.md](docs/06-git-workflow.md) |
| Know what's done | [docs/STATUS.md](docs/STATUS.md) |
| Pick the next task | [docs/TODO.md](docs/TODO.md) |
| Record or compare an experiment | [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) |
| Know why something was decided | [docs/DECISIONS.md](docs/DECISIONS.md) |
| Board-specific operations | [.skills/unoq-board/SKILL.md](.skills/unoq-board/SKILL.md) |
| Change or measure the copilot | [.skills/m3kang-copilot/SKILL.md](.skills/m3kang-copilot/SKILL.md) |
| Web page or LED matrix (App Lab) | [.skills/unoq-hardware-ui/SKILL.md](.skills/unoq-hardware-ui/SKILL.md) |
| Final README or Project Hub write-up | [.skills/publish-project/SKILL.md](.skills/publish-project/SKILL.md) |

## How to work here

- **Where code runs:** the model servers and `predict.py`/`eval.py` run **on the board** (`ssh arduino@<board-ip>`, repo at `~/datathon-UPC-maths-qualcomm-arduino-unoq`). Data prep (`laptop/`) runs **on the laptop**. You can't run an evaluation on the laptop unless llama-server is running there too.
- **Before you change code,** read `copilot/pipeline.py`. `predict.py` and `eval.py` both call `solve()`, so a change there changes the official result.
- **After a change:** run `python3 predict.py --input data/sample_problems.jsonl --output results/check.csv` (contract check), then `python3 eval.py --limit 50 --name <label>`.
- **Keep the docs current.** When you finish a task, tick it in [docs/TODO.md](docs/TODO.md), update [docs/STATUS.md](docs/STATUS.md), and log any experiment or decision. Don't duplicate the README: link to it.
- **Language:** code, docs and commit messages are in English. The team talks in Catalan.
