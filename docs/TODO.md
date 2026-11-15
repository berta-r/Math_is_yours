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

### D6 · Teach: thinking steps

- [ ] **T-092** [P1] [laptop] **Generate per-problem thinking steps offline for the 170 training exercises with a strong model, validated by the bank rules and leak check; educator review.**
- [ ] **T-093** [P2] [board] **Measure process metrics with real students: first-try step rate, conditional first-attempt accuracy, hints per problem before/after steps.**

### D7 · Teach: ML tutor bundle (see [ML-OPTIONS.md](ML-OPTIONS.md); order is the dependency order)

- [ ] **T-100** [P0] [board] **Embed every problem in both languages.** `python3 build_index.py --input data/train.jsonl --db data/index.db` (no `--only-with-options`, no language filter), then `scp` `data/index.db` to the laptop. Done when the `problems` table has one row per (id, language) and STATUS records the time it took. Everything below needs this.
- [ ] **T-101** [P0] [laptop] **Dataset feature table.** `laptop/ml/features.py` → `data/ml/features.jsonl`: id, language, level, year, position parsed from the text prefix, points (3/4/5 by thirds of the max position per level-year), text length, numeral count, has image, option count, numeric options, embedding from `index.db`. Done when ≥1600 English rows have points and the counts are in 03-data.md.
- [ ] **T-102** [P0] [laptop] **Difficulty model.** Gradient-boosted trees (or one depth-6 tree) on `features.jsonl`, target points then level, years 2023–2024 held out. Export `data/ml/difficulty_tree.json` (nested dicts) and `data/ml/difficulty.json` (id → b in [0,1]). Done when EXPERIMENTS has Spearman and 3/4/5 accuracy versus the majority baseline.
- [ ] **T-103** [P0] [board] **Elo selection.** `copilot/difficulty.py` evaluates the exported tree in pure Python; `student_model` gains `student_elo(student, skill, theta)` updated after each eligible first attempt (K=32 on logistic scale); `scheduler.recommend` prefers items with p(correct)=1/(1+e^-(θ−b)) closest to 0.7 among the current rules. Tests for determinism and that BKT is unchanged.
- [ ] **T-104** [P1] [laptop] **Procrustes alignment.** From the 1747 (eng, cat) embedding pairs compute the orthogonal W by SVD; export `data/ml/procrustes.json` (384×384). Done when EXPERIMENTS shows cat→eng retrieval@1 on held-out pairs before and after.
- [ ] **T-105** [P1] [board] **Apply W for Catalan.** `copilot/embed.py` multiplies Catalan vectors by W when the file exists (pure Python matvec, < 50 ms measured on the board). Test with a fixed pair.
- [ ] **T-106** [P1] [laptop] **Problem map.** kNN graph (k=5, cosine, aligned vectors), Louvain communities, UMAP 2-D coordinates. Export `data/ml/problem_map.json` (nodes: id, x, y, cluster, b; edges: source, target, weight). Done when the file is < 400 KB and cluster purity against the 51 reviewed tags is in EXPERIMENTS.
- [ ] **T-107** [P1] [board] **Map UI and stepping-stone paths.** New `/api/map` and `/api/path` (Dijkstra, edge cost = |b_target − b_source| + 0.1, from any solved node to the goal). Renderer reuses `graph.js` zoom/pan with precomputed coordinates; solved nodes highlighted; goal selection draws the path. Tests for path determinism and 390 px width.
- [x] **T-108** [P1] [laptop] **Error signatures.** `laptop/ml/signatures.py`: for problems with all-numeric options, try naive operations over the numerals in the text (sum, difference, product, quotient, half, double, ±1, unit ×10/×100) and record which generates each distractor → `data/ml/signatures.json`. Done when coverage (distractors explained / distractors) is in EXPERIMENTS and 30 were checked by hand. `laptop/ml/signatures.py` explains 981/3220 numeric distractors (30.5%; 12.5% without copied numbers and off-by-one); an agent spot check found 11/30 plausible, human check still to do. (2026-11-15)
- [x] **T-109** [P1] [board] **Misconception feedback.** On a wrong answer with a signature, the feedback names the operation and the hint rung starts at the method hint. Tests. `copilot/misconceptions.py` adds an eng/cat sentence to `message`, `misconception` in the answer, `sessions`/`learning_events` columns, method-rung hint and a "Common slips" notebook section; BKT unchanged; 9 new app tests. (2026-11-15)
- [ ] **T-110** [P0] [board] **Deploy and verify the bundle.** Add `data/ml/*.json` to `laptop/deploy_student.py`; run all tests on the board with `python3 -S`; record `free -m` minimum and `/api/recommendation` latency in STATUS.
- [ ] **T-111** [P2] [laptop] **Label propagation for skills.** Seeds: 51 reviewed tags + 30 diagnostics; spread over the T-106 graph; export only rows above a confidence threshold through `annotate_problems.py export`. Leave-one-out accuracy in EXPERIMENTS; eng/cat twins must agree.
- [ ] **T-112** [P1] [team] **Pitch numbers.** One table: difficulty accuracy, retrieval@1 before/after alignment, signature coverage, map size, board latency and RAM. Feed README and the 3-minute pitch.

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

- [x] **T-095** [P1] [laptop] **Build the blue typographic child-facing interface.** Original reference-inspired entrance with a visible first-screen start action, focused Solve workspace, readable skill tiles in My path and My work record. Existing tutor state and offline flow retained; 48 app tests and Chrome checks at five widths pass. Physical touch and board visual review remain pending. (2026-11-15)

- [x] **T-094** [P1] [laptop] **Redesign the offline tutor as Kangaroo Studio.** Editorial identity, exercise-first layout, separate map and notebook views, compact responsive navigation, and accessible loading feedback. Browser and application checks pass. (2026-11-15)

## Done

- [x] **T-091** [P1] [laptop] **Thinking-step process questions before answering.** Three multiple-choice steps (Understand · Plan · Check) with immediate, pure-Python feedback replace the mandatory free-text thought when steps exist; the note stays optional. `knowledge/thinking_steps.json` holds 30 general English skill steps and 15 sample-problem steps (Catalan for sample-4/5), validated at load (stage order, three options of balanced length, balanced key positions, one-sentence explanations, answer-leak check, repeated against the catalog at server start). New `/api/step`, `thinking_events` table, plan-miss hint rule, profile `process`/`process_summary` and a notebook "Thinking process" section. BKT is unaffected. 48 tests pass; browser flow checked at 390px in headless Chrome. Real-student metrics remain T-093; training-set steps remain T-092. (2026-11-14)

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
