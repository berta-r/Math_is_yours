# AGENTS.md

Entry point for any AI agent (Claude Code, Codex, Cursor, Copilot…) working in this repository. Read this file first, then open only the `docs/` file your task needs.

## What this project is

Our team's entry to the **Datathon FME 2026, Qualcomm challenge: "Math on the Edge"**. We must build a **math copilot that runs entirely offline on an Arduino UNO Q (4 GB)** and uses the **M3Kang** dataset (multilingual Kangaroo competition problems) to help students learn to reason mathematically.

Our team will deliver both **Teach** (hints, adaptive practice, error analysis, physical interaction) and **Reason** (pick the right letter A–E on a hidden test set). `predict.py` is scored on the hidden test set whatever else we build.

This repository started from the organizers' template. The template's step-by-step guide is [docs/DATATHON-GUIDE.md](docs/DATATHON-GUIDE.md) (steps 0–15; it was the root README until publication). The root [README.md](README.md) is our public project README. Our own documentation lives in [docs/](docs/).

## Current state (update this line when it changes)

**T-129 offline coach integration (2026-11-15):** `exp/slm-learning-coach` merges main through `0b42034` and adds Python-verified arithmetic, bounded local SLM dialogue, durable conversations/drafts and safe shutdown to main's UI. Read [docs/SLM-COACH.md](docs/SLM-COACH.md) for implementation/deployment and [docs/COACH-DESIGN.md](docs/COACH-DESIGN.md) before changing the interface. Existing BKT/Elo, thinking gates and map loaders are preserved. Local tests/browser checks pass; new hardware inference/deployment is pending because no board is visible over USB. This PC has 170 training rows with images but lacks newer ML/generated artifacts; activation refuses to drop installed data silently. See STATUS and accepted experimental D-018. The earlier deployed dialogue remains preserved at `694d2b6`.

**Teach and Reason are both required main workstreams** (D-003). **Tutor deployed and tested on the UNO Q over Wi-Fi and USB.** The [student app](student_app/README.md) has a connected semantic graph, progressive paths, reflection before answers, provisional BKT and live local hint selection. Its boot service is enabled; 51 application/deployment checks and nine new setup checks pass on the board. Prepared data: 170 train / 30 validation. The standalone Windows launcher is installed on this PC with a login entry and bundled Python/ADB. The board presents a verified read-only MATHTUTOR setup drive using Windows inbox USB drivers. Full shutdown/replug testing passed: the drive returned, the installed watcher opened the tutor, the model became ready and progress survived. A fresh PC and actual Windows login remain to be verified. Large-model teaching content (steps, hints, solutions, explanations, tags) is generated and verified for the whole prepared set but not yet deployed to the board. Educator review and reasoning improvements remain pending. Reason: `predict.py` now uses the compute-first solver (SOLVER=compute, third service `math-compute` on 8084, 15/30 on the practice set on the board); see docs/COMPUTE_SOLVER.md. See [docs/STATUS.md](docs/STATUS.md) and [deployment instructions](board/STUDENT_DEPLOYMENT.md).

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
README.md                 ← our public project README (what it does, architecture, replication, results)
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
  compute.py              ←   compute-first solver (SOLVER=compute): code model → one expression
  safe_eval.py            ←   whitelist evaluator for that expression
  values.py               ←   option values ("12 cm", "1,5") and matching to A–E
explorer/                 ← browser app on the board to inspect problems
laptop/prepare_m3kang.py  ← laptop: download M3Kang, OCR the options, split train/val
board/00–05_*.sh          ← board setup scripts; board/systemd/ service templates
board/06_compute_server.sh ← math-compute (:8084) + math-compute-warm, for SOLVER=compute
data/                     ← sample_problems.jsonl (committed), generated data (ignored)
results/                  ← eval outputs + ablations.csv (ignored by git)
.skills/                  ← Claude skills: unoq-board, m3kang-copilot, unoq-hardware-ui, publish-project
docs/                     ← OUR documentation (see below)
docs/DATATHON-GUIDE.md    ← organizers' guide, steps 0–15 (source of truth for setup)
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
| Explain the selection system (difficulty, Elo, 70% rule, map, paths) | [docs/ML.md](docs/ML.md) |
| Choose an ML improvement for the tutor | [docs/ML-OPTIONS.md](docs/ML-OPTIONS.md) |
| Change the look of the student app | [docs/DESIGN.md](docs/DESIGN.md) |
| Board-specific operations | [.skills/unoq-board/SKILL.md](.skills/unoq-board/SKILL.md) |
| Change or measure the copilot | [.skills/m3kang-copilot/SKILL.md](.skills/m3kang-copilot/SKILL.md) |
| Change or measure the Reason solver | [docs/COMPUTE_SOLVER.md](docs/COMPUTE_SOLVER.md) |
| Web page or LED matrix (App Lab) | [.skills/unoq-hardware-ui/SKILL.md](.skills/unoq-hardware-ui/SKILL.md) |
| Final README or Project Hub write-up | [.skills/publish-project/SKILL.md](.skills/publish-project/SKILL.md) |

## How to work here

- **Where code runs:** the model servers and `predict.py`/`eval.py` run **on the board** (`ssh arduino@<board-ip>`, repo at `~/datathon-UPC-maths-qualcomm-arduino-unoq`). Data prep (`laptop/`) runs **on the laptop**. You can't run an evaluation on the laptop unless llama-server is running there too.
- **Before you change code,** read `copilot/pipeline.py`. `predict.py` and `eval.py` both call `solve()`, so a change there changes the official result.
- **After a change:** run `python3 predict.py --input data/sample_problems.jsonl --output results/check.csv` (contract check), then `python3 eval.py --limit 50 --name <label>`.
- **Keep the docs current.** When you finish a task, tick it in [docs/TODO.md](docs/TODO.md), update [docs/STATUS.md](docs/STATUS.md), and log any experiment or decision. Don't duplicate the README: link to it.
- **Language:** code, docs and commit messages are in English. The team talks in Catalan.
