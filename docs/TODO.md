# TODO

> The task list for people and agents. Each task has a stable ID, where it runs, what "done" means and the files it touches. Pick the first unblocked task with the highest priority. When you finish one, tick it, add the date, and update [STATUS.md](STATUS.md).
>
> **We haven't chosen our idea yet**, so phases A–C are concrete, and phase D lists candidate tasks for each idea. Once the idea is chosen (T-020), delete the candidates we won't do and split the chosen ones into smaller tasks.

Format: `- [ ] **T-XXX** [priority] [where] Title`. Priority: **P0** = must have, **P1** = should have, **P2** = nice to have. Where: board, laptop or team.

---

## Phase A · Board setup (README steps 0–8). Minimum required.

- [ ] **T-001** [P0] [laptop] **Update the board and connect over SSH.** Follow [README step 0](../README.md#step-0-connect-to-the-board). Done when `ssh arduino@<ip>` works and the IP is written in STATUS.
- [ ] **T-002** [P0] [board] **Check the board.** Run `bash board/00_check_board.sh`. Done when it reports no problems: enough RAM and disk, the right clock, internet.
- [ ] **T-003** [P0] [board] **Install the build tools and build llama.cpp.** README steps 2–3, or scripts `01` and `02`. Done when `~/llama.cpp/build/bin/llama-server --version` shows the pinned commit.
- [ ] **T-004** [P0] [board] **Download and verify the models.** README step 4, or `03_download_models.sh`. Done when the SHA256 of both GGUF files matches.
- [ ] **T-005** [P0] [board] **Hello world with both models.** README steps 5–6. Done when we know the tokens/s on our own board (write it in STATUS).
- [ ] **T-006** [P0] [board] **Run the models as services.** README step 7, or `04_install_services.sh`. Done when both are `active` after a reboot and `/health` answers on 8081 and 8082.
- [ ] **T-007** [P0] [board] **First test.** Clone the repo on the board, then run `predict.py` on `data/sample_problems.jsonl`, or `05_smoke_test.sh`. Done when there are 5 rows with one letter each and status `ok`.

## Phase B · Data and baseline (README steps 9–12)

- [ ] **T-008** [P0] [team] **Decide the languages and the split.** Default `eng,cat`, 15% of IDs held out. Do we add `esp`? Hold out years? Log it in DECISIONS.
- [ ] **T-009** [P0] [laptop] **Prepare M3Kang.** `pip install -r laptop/requirements.txt`, then `python3 laptop/prepare_m3kang.py --languages <…> --save-images`. Done when `train.jsonl` and `val.jsonl` exist, and the counts and the share of problems with options are in [03-data.md](03-data.md).
- [ ] **T-010** [P0] [laptop] **Copy the data to the board** (JSONL, plus images if we want the explorer). Check `git status` shows no data files.
- [ ] **T-011** [P0] [board] **Measure our baseline.** `python3 eval.py --limit 50 --name baseline`, then `--limit 0 --name baseline-full` when there's time. Done when the numbers are in EXPERIMENTS and STATUS, with the letter bias noted.
- [ ] **T-012** [P0] [board] **Build the RAG index and measure k=1 and k=2.** `build_index.py --only-with-options`, then `eval.py --rag 1 --name rag1` and `--rag 2 --name rag2`. Done when both rows are in EXPERIMENTS, with their latency.
- [ ] **T-013** [P1] [board] **Run the explorer** and look at 10 wrong baseline answers. Write down the patterns in EXPERIMENTS (error notes).
- [ ] **T-014** [P1] [board] **Measure baseline accuracy by language** (`--languages cat` vs `--languages eng` on the same sample).

## Phase C · Choose the idea (README step 13)

- [ ] **T-020** [P0] [team] **Brainstorm and choose ONE idea** (1 h). Score each candidate against the [step 13.4](../README.md#134-choose-one) questions. Write down in DECISIONS: the idea, the metric we'll measure, and the first experiment. Then prune phase D.
- [ ] **T-021** [P0] [team] **Split roles:** board/infra, copilot/experiments, UI (App Lab + LED), docs/pitch.
- [ ] **T-022** [P1] [laptop] **Link the skills** for Claude Code: `mkdir -p .claude && ln -s ../.skills .claude/skills`.

## Phase D · Implementation (README step 14). Candidates, prune after T-020.

### D0 · Always: the Reason score (predict.py runs on the hidden test set for every team)

- [ ] **T-030** [P0] [board] **Fix the letter bias.** Request `logprobs` (`top_logprobs: 5`) and calibrate against the letter prior from the train set. Measure it with `eval.py --name debias-v1`.
- [ ] **T-031** [P1] [board] **Retrieval tuning:** a similarity threshold, same-level examples, hybrid keyword + embedding search. Keep it under 60 s.
- [ ] **T-032** [P1] [board] **Problem decomposition:** classify the type, then compute arithmetic and counting in Python, and ask the model only for what it's good at.
- [ ] **T-033** [P2] [laptop] **Better OCR** (crop the options area), then re-run T-009 and compare accuracy with and without options.
- [ ] **T-034** [P2] [board] **Try another GGUF model** that fits the RAM and time limits. Update all four `LLM_*` keys, check the license, and log it in DECISIONS.
- [ ] **T-035** [P2] [board] **Vision experiment** for problems without options (mmproj, :8083). Measure RAM and time.

### D1 · Teach: hint ladder

- [ ] **T-040** Rung 1: the nearest neighbour at a lower level (embeddings + `level`).
- [ ] **T-041** Rung 2: topic or method from the neighbours (needs topics, see T-060).
- [ ] **T-042** Rung 3: a one-sentence model hint, plus a Python leak check (reject a hint that contains the correct option's value).
- [ ] **T-043** Measure: leak rate over the whole validation set, latency per rung, a manual check of 20 problems.

### D2 · Teach: adaptive trainer

- [ ] **T-045** A problem map: embedding + level + topic, in SQLite.
- [ ] **T-046** A policy: right → a neighbour one level up; wrong → same topic, one level down. Student profile in SQLite.
- [ ] **T-047** Simulated students to measure whether the path stays on topic and settles at the right level.

### D3 · Teach: classroom debate box

- [ ] **T-050** A voting web page + vote counts on the LED matrix.
- [ ] **T-051** A two-sentence devil's-advocate argument. Prefetch the problem into the prompt cache. Measure `prompt_n` and the latency after the vote.

### D4 · Teach: multilingual bridge

- [ ] **T-055** Search with the English text of the same `id`, and show results in the student's language. Measure retrieval and accuracy for `cat` against `eng`.

### D5 · Teach: dyslexia / dyscalculia adaptations

- [ ] **T-057** Rewrite the problems offline, ahead of time, store them in SQLite, and check in code that numbers, options and answer are unchanged.
- [ ] **T-058** Readability metrics, plus model accuracy on rewritten vs original problems. LED dots or bars for quantities.

### Shared (needed by most ideas)

- [ ] **T-060** [P1] **Topic labels:** cluster the embeddings plus keywords, and hand-label 50 problems to check. Required for the error analysis by topic.
- [ ] **T-061** [P1] **App Lab app skeleton:** `python/main.py` with `web_ui` + `sketch/sketch.ino` LED matrix + Bridge. Check that `127.0.0.1:8081/health` works from the app, and watch `free -m`.

## Phase E · Analysis, demo and publication (README steps 14.3–15)

- [ ] **T-070** [P0] [board] **Final evaluation** with `--limit 0` on the chosen configuration. Put it in EXPERIMENTS and STATUS.
- [ ] **T-071** [P0] [laptop] **Error analysis by topic, language and level**: join `results/eval-*.csv` with `val.jsonl`, plus 10 wrong answers by hand.
- [ ] **T-072** [P0] [team] **Demo:** Wi-Fi off, services started at boot, problems chosen in advance, a backup video recorded.
- [ ] **T-073** [P0] [team] **3-minute pitch**, rehearsed twice with a timer.
- [ ] **T-074** [P0] [laptop] **Rewrite the root README** for our project: what it does, architecture, replication, results, error analysis, what didn't work, team, license. Use the `publish-project` skill.
- [ ] **T-075** [P0] [laptop] **Arduino Project Hub write-up.**
- [ ] **T-076** [P0] [laptop] **Pre-publish check:** no M3Kang data, an MIT LICENSE, a clean clone that follows our README. Make the repo public and send both links.

---

## Done

- [x] **T-080** [P1] [laptop] **Create the Tukey side-project workspace.** Added the brief, judging criteria, proposed decision views, data sources, and next steps in [side-project/README.md](../side-project/README.md). Dashboard implementation is pending. (2026-11-14)
