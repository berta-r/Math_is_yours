# TODO

> The task list for people and agents. Each task has a stable ID, where it runs, what "done" means and the files it touches. Pick the first unblocked task with the highest priority. When you finish one, tick it, add the date, and update [STATUS.md](STATUS.md).
>
> **We haven't chosen our idea yet**, so phases A–C are concrete, and phase D lists candidate tasks for each idea. Once the idea is chosen (T-020), delete the candidates we won't do and split the chosen ones into smaller tasks.

Format: `- [ ] **T-XXX** [priority] [where] Title`. Priority: **P0** = must have, **P1** = should have, **P2** = nice to have. Where: board, laptop or team.

---

## Phase A · Board setup (README steps 0–8). Minimum required.

- [x] **T-001** [P0] [laptop] **Update the board and connect over SSH.** Follow [README step 0](../README.md#step-0-connect-to-the-board). Done when `ssh arduino@<ip>` works and the IP is written in STATUS. SSH verified at `10.198.34.77`; App Lab session supplied by the owner. (2026-11-14)
- [ ] **T-002** [P0] [board] **Check the board.** Run `bash board/00_check_board.sh`. Done when it reports no problems: enough RAM and disk, the right clock, internet.
- [ ] **T-003** [P0] [board] **Install the build tools and build llama.cpp.** README steps 2–3, or scripts `01` and `02`. Done when `~/llama.cpp/build/bin/llama-server --version` shows the pinned commit.
- [x] **T-004** [P0] [board] **Download and verify the models.** README step 4, or `03_download_models.sh`. Done when the SHA256 of both GGUF files matches. Existing board models verified against both pinned SHA-256 values. (2026-11-14)
- [ ] **T-005** [P0] [board] **Hello world with both models.** README steps 5–6. Done when we know the tokens/s on our own board (write it in STATUS).
- [x] **T-006** [P0] [board] **Run the models as services.** README step 7, or `04_install_services.sh`. Done when both are `active` after a reboot and `/health` answers on 8081 and 8082. Both model services and math-student are active after the subsequent board boot; loopback health is ready. (2026-11-14)
- [x] **T-007** [P0] [board] **First test.** Clone the repo on the board, then run `predict.py` on `data/sample_problems.jsonl`, or `05_smoke_test.sh`. Done when there are 5 rows with one letter each and status `ok`. Five valid letters/status ok on the UNO Q; repeated answer sequence identical. Run from isolated development release. (2026-11-14)

## Phase B · Data and baseline (README steps 9–12)

- [ ] **T-008** [P0] [team] **Decide the languages and the split.** Default `eng,cat`, 15% of IDs held out. Do we add `esp`? Hold out years? Log it in DECISIONS.
- [ ] **T-009** [P0] [laptop] **Prepare M3Kang.** `pip install -r laptop/requirements.txt`, then `python3 laptop/prepare_m3kang.py --languages <…> --save-images`. Done when `train.jsonl` and `val.jsonl` exist, and the counts and the share of problems with options are in [03-data.md](03-data.md).
- [x] **T-010** [P0] [laptop] **Copy the data to the board** (JSONL, plus images if we want the explorer). Check `git status` shows no data files. 170 train originals and JSONL deployed; 30 validation records copied separately for QA. No data tracked by Git. (2026-11-14)
- [ ] **T-011** [P0] [board] **Measure our baseline.** `python3 eval.py --limit 50 --name baseline`, then `--limit 0 --name baseline-full` when there's time. Done when the numbers are in EXPERIMENTS and STATUS, with the letter bias noted. Development-release check measured 11/30, 10.4 s mean, 25.6 s worst; main-branch confirmation remains pending. (2026-11-14)
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
- [x] **T-047** Synthetic selector comparison implemented in `laptop/eval_teaching.py`: adaptive, random and correct-harder policies, fixed response probabilities, targeting/coverage/freshness metrics. Calibrated difficulty, real student learning and board latency remain unmeasured. (2026-11-14)

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

- [x] **T-090** [P1] [board/laptop] **Ship one-time Windows setup from the Arduino.** Standalone x64 installer, bundled Python/Tk/ADB, per-user login watcher, Start-menu control and read-only FAT16 delivery image built. Installed and checked on this PC without external Python on PATH; nine setup/rollback checks pass on the board. Setup-drive service active/enabled, Windows volume and installer verified, inbox drivers loaded. Full shutdown/replug passed: all services resumed, drive returned, installed watcher opened the tutor, model became ready and test progress survived. User confirmed both drive and browser. A fresh Windows PC and actual Windows reboot/login remain separate validation. (2026-11-14)

- [x] **T-087** [P1] **Prepare the connected learning map and plug-in deployment.** Browser force graph with related/prerequisite/path links, compact offline graph export, evidence-based paths, server-enforced reflection and delayed answer review, reasoning snapshots, board systemd installer, versioned deployment bundle and per-user Windows USB launcher. Wi-Fi deployment is now verified in T-088; USB testing remains in T-089. See [deployment guide](../board/STUDENT_DEPLOYMENT.md). (2026-11-14)

- [x] **T-086** [P1] [laptop] **Build the knowledge graph and separate student model.** Ten Markdown skills, thirty original diagnostics, conservative BKT, persistent rich events, prerequisite/transfer/review recommendations, Markdown reports, reviewed-label export and optional bounded local SLM hint selection. 51 local M3Kang topic mappings need educator validation. 28 automated tests and desktop/mobile-width browser checks pass. Live SLM, board deployment and physical controls remain pending. (2026-11-14)

- [x] **T-085** [P1] [laptop] **Extract answer choices and reveal official answers.** Added laptop-only OCR enrichment and choice-image previews, plus a session-aware answer-reveal endpoint/control. Revealed answers count as assisted practice. Grading uses the official label, independent of OCR. Ten HTTP integration tests pass. (2026-11-14)

- [x] **T-084** [P1] [laptop] **Make enlarged images dismissible.** Replaced raw-image navigation with an accessible native dialog, Close button, Escape and backdrop dismissal, scroll lock and focus restoration. Practice state is preserved. (2026-11-14)

- [x] **T-083** [P1] [laptop] **Load M3Kang in the student app with multimodal display.** Added JSONL catalog, composite ID/language identity, local image serving, combined/text/image modes, language filter, missing-image warnings and view-only handling for absent answer keys. Prepared 60 real English rows with images (52 train / 8 validation) without OCR. Eight integration tests and a real-data HTTP check pass; board and visual browser QA remain pending. (2026-11-14)

- [x] **T-082** [P1] [laptop] **Polish the student web-app design.** Compact notebook header, clearer practice hierarchy, answer badges, symbol-labelled graph states, pointer press feedback and responsive layouts. Backend checks pass; visual browser and device QA remain pending. (2026-11-14)

- [x] **T-081** [P1] [laptop] **Create the offline student web-app prototype.** Added standard-library server, sample practice, reviewed hints, persistent local profiles and an illustrative skill graph in `student_app/`. Board deployment, model integration and learned clusters remain pending. (2026-11-14)

- [x] **T-080** [P1] [laptop] **Create the Tukey side-project workspace.** Added the brief, judging criteria, proposed decision views, data sources, and next steps in [side-project/README.md](../side-project/README.md). Dashboard implementation is pending. (2026-11-14)

- [x] **T-088** [P1] [board/laptop] **Deploy and test the tutor over Wi-Fi.** Verified UNO Q identity, pinned models, 51 tests, all training images, real SLM hints, semantic skill relations, desktop/mobile-width browser flow, persistent evidence and automatic service recovery. Owner installed the enabled boot service; official-entry-point development benchmark recorded. Fixed and tested systemd path parsing. (2026-11-14)

- [x] **T-089** [P1] [board/laptop] **Verify full boot and temporary USB automatic opening.** Confirm retained profiles, services, exact USB identity and browser opening on reconnection using the already available Python/ADB watcher. The user requested no additional installation. Boot persistence, USB browser tests and a physical unplug/replug passed. The watcher reopened the page after 29 seconds of observed disconnection, the model became ready, and test progress was retained. User confirmation recorded. (2026-11-14) Windows login startup is a separate optional installation and has not been changed.
