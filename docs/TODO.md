# TODO

> The task list for people and agents. Each task has a stable ID, where it runs, what "done" means and the files it touches. Pick the first unblocked task with the highest priority. When you finish one, tick it, add the date, and update [STATUS.md](STATUS.md).
>
> **We will deliver both Teach and Reason as main workstreams.** Reason covers the official `predict.py` score; Teach covers the student learning experience. The Teach approach is still to be chosen (T-020): keep both workstreams and prune only the unused Teach candidates in phase D.

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
- [ ] **T-011** [P0] [board] **Measure our baseline on the board.** Laptop measurement done 2026-11-14 with the same GGUF and pinned llama.cpp: 20.1% ±0.7 on all 3494 problems, 20.6% ±1.0 on text-only. Still needed on the board: latency, and `--limit 0` once. Use a few hundred problems or more; 50 gives ±6 points.
- [ ] **T-012** [P0] [board] **Build the RAG index and measure k=1 and k=2.** `build_index.py --only-with-options`, then `eval.py --rag 1 --name rag1` and `--rag 2 --name rag2`. Done when both rows are in EXPERIMENTS, with their latency.
- [ ] **T-013** [P1] [board] **Run the explorer** and look at 10 wrong baseline answers. Write down the patterns in EXPERIMENTS (error notes).
- [ ] **T-014** [P1] [board] **Measure baseline accuracy by language** (`--languages cat` vs `--languages eng` on the same sample).

## Phase C · Define the Teach and Reason scope (README step 13)

- [ ] **T-020** [P0] [team] **Define the minimum deliverable for both Teach and Reason** (1 h). Choose one Teach approach using the [step 13.4](../README.md#134-choose-one) questions, and define the Reason improvement to measure first. Record both scopes, success metrics and first experiments in DECISIONS. Prune only unused Teach candidates in phase D; both workstreams remain P0.
- [ ] **T-021** [P0] [team] **Assign owners for both main workstreams:** Teach (learning experience + UI) and Reason (copilot + experiments), with board/infra and docs/pitch support. Done when each workstream has an owner and a first deliverable.
- [ ] **T-022** [P1] [laptop] **Link the skills** for Claude Code: `mkdir -p .claude && ln -s ../.skills .claude/skills`.

## Phase D · Implement both Teach and Reason (README step 14)

- [ ] **T-023** [P0] [board] **Deliver the Reason MVP.** Run `predict.py` offline with one A–E answer per problem, deterministic settings and the 60 s limit. Record baseline and selected improvements in EXPERIMENTS, including accuracy and latency.
- [ ] **T-024** [P0] [board] **Deliver the Teach MVP.** Implement the learning flow selected in T-020 and demonstrate it offline on the UNO Q. Define and record its teaching-quality checks and latency; complete the selected Teach tasks below.

D0 is the Reason workstream. D1–D5 are candidate approaches within the required Teach workstream; select and detail the chosen tasks in T-020.

### D0 · Reason: official score (required main workstream)

- [x] **T-030** [P0] [laptop] **Fix the letter bias.** Done 2026-11-14 on `exp/reason-strategies` (`copilot/logprobs.py`). **Result: no gain.** Raw 23.6% ±2.7, content-free and train-marginal calibration 19–20% (val text-only, n=246). The letter carries no signal to calibrate. See EXPERIMENTS.
- [ ] **T-036** [P2] [board] **Near-duplicate answers.** Code done (`copilot/dedup.py`), **not measured with the real model**. Data check: 28/281 English val problems have a near-identical train text but only 4 share the correct value (Kangaroo reuses texts with other numbers), so the ceiling is about 1%. Low priority.
- [x] **T-037** [P0] [laptop] **Program of thought.** Done 2026-11-14 (`copilot/pot.py`, `copilot/safe_eval.py`). **Result: no gain**, 28% vs 29% on the same 100, about 32 s on the board (estimate). The 0.8B rarely writes a valid, correct expression: 11 matches, 3 right.
- [x] **T-038** [P1] [laptop] **Judge / fusion.** Done 2026-11-14 (offline, not in the repo). **Result: no gain.** Logistic regression on letter, value rank and model log-probs: val text-only 20.7% ±2.6; the model weight is about 0. Priors alone overfit (train 31%, val 22%).
- [ ] **T-039** [P0] [team] **Decide what `predict.py` ships.** Every model-based variant is at chance (17–23%); always-D is 24.7% on 3494 problems. Options: keep the model baseline, or a no-model rule. Ask the organizers whether the hidden test gives the options as text. Log it in DECISIONS.
- [ ] **T-031** [P1] [board] **Retrieval tuning:** a similarity threshold, same-level examples, hybrid keyword + embedding search. Keep it under 60 s.
- [ ] **T-032** [P1] [board] **Problem decomposition:** classify the type, then compute arithmetic and counting in Python, and ask the model only for what it's good at.
- [ ] **T-033** [P2] [laptop] **Better OCR** (crop the options area), then re-run T-009 and compare accuracy with and without options.
- [x] **T-034** [P2] [laptop] **Try another GGUF model.** Done 2026-11-14: Qwen3.5 2B Q4_K_M (1.4 GB, Apache 2.0), laptop only. **Result: no gain**, 17.2% ±1.9 with one letter, 22.3% ±2.4 writing the value (n=300–400). Board time and RAM not measured. Not adopted.
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
- [ ] **T-072** [P0] [team] **Demo both Teach and Reason:** Wi-Fi off, services started at boot, problems chosen in advance, a backup video recorded. Done when the Teach learning flow and the Reason A–E prediction both run on the board.
- [ ] **T-073** [P0] [team] **3-minute pitch covering both Teach and Reason**, including the learning experience and measured Reason results, rehearsed twice with a timer.
- [ ] **T-074** [P0] [laptop] **Rewrite the root README** for our project: what it does, architecture, replication, results, error analysis, what didn't work, team, license. Use the `publish-project` skill.
- [ ] **T-075** [P0] [laptop] **Arduino Project Hub write-up.**
- [ ] **T-076** [P0] [laptop] **Pre-publish check:** no M3Kang data, an MIT LICENSE, a clean clone that follows our README. Make the repo public and send both links.

---

## Done

- [x] **T-084** [P1] [laptop] **Set direct and critical AI communication rules.** Updated AGENTS.md and aligned the proposal guide: answer only the question, challenge unsupported assumptions, keep recommendations realistic and distinguish implementation from measured results. (2026-11-14)

- [x] **T-081** [P0] [laptop] **Restore demo-first AI proposal guidelines.** Recovered AI-PROPOSAL-GUIDE.md from docs/demo-first-proposals and linked it from AGENTS.md without replacing current Reason documentation. (2026-11-14)

- [x] **T-083** [P0] [team] **Establish Teach and Reason as required main workstreams.** Added separate P0 MVPs, ownership and acceptance criteria, and updated scope selection and the demo to cover both. (2026-11-14)


- [x] **T-080** [P1] [laptop] **Create the Tukey side-project workspace.** Added the brief, judging criteria, proposed decision views, data sources, and next steps in [side-project/README.md](../side-project/README.md). Dashboard implementation is pending. (2026-11-14)
