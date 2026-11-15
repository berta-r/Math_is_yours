# Status

> What's done and working **right now**. Update it whenever a task in [TODO.md](TODO.md) is finished. Keep it short: facts, numbers with their conditions, and dates.

**Last updated:** 2026-11-15

## Summary

**T-115 problem map restyled (2026-11-15, laptop only):** the standalone `/map` page shares the student app's visual system (blue header with wordmark, cream surface, Archivo, 3px frames, accent-blue path) and plainer copy; map API and path logic unchanged, 17 map tests pass.

**T-114 designer critique applied (2026-11-15, laptop only):** the student app now speaks the problem's language: open a Catalan problem and the navigation, steps, buttons, server feedback, recommendations and state labels switch to Catalan (English fallback for anything else). Research terms left the child's flow (plain recommendation summaries, "Not tried yet / Getting there / Got it / Time to review", readable problem labels); answers show ✓ only when correct and ✗ when wrong, with a Next problem action after a correct result; each phase has one feedback channel; actions follow three levels; Solve is a single 920 px column; the phone header is 112 px; nothing the child reads is under 16 px; the bundled OFL font Archivo replaces system Arial and the blue is `#8a9ed4`. My path links to the problem map, and the map's `/?problem=<key>` links open that problem directly. 112 student-app tests pass; Chrome checks at 320–1440 px show no errors, overflow, sub-16 px text or 2 px borders. Board touch review pending. See [DECISIONS D-014 and D-015](DECISIONS.md).

**Fix: problem images restored (2026-11-15, laptop):** the student app showed no images because `data/images/` did not exist on the laptop (the JSONL files were prepared without `--save-images`), so `Catalog.image()` returned nothing and the figure stayed hidden. `laptop/prepare_m3kang.py --images-only` now exports the images from the cached parquet shard without re-running OCR or rewriting train/val; 3494 images (eng + cat, 144 MB) are back and the local server serves them for all 2932 train problems. The board needs the same folder (`scp -r data/images` or a `--with-data` bundle).

**T-074/T-075 publication docs (2026-11-15, laptop only):** the root `README.md` is now our public project README (architecture, replication, results with conditions, error analysis, what didn't work, team, licenses), the organisers' guide moved to [DATATHON-GUIDE.md](DATATHON-GUIDE.md) with every link updated and checked, and the Project Hub text is drafted in [PROJECT-HUB.md](PROJECT-HUB.md); photos, team names and posting are pending.

**T-100 framed controls and reading surface (2026-11-15, laptop only):** the landing keeps the blue field with the MATH IS YOURS wordmark top-left, a 3px square frame around the nickname field and an arrow submit; Solve, My path and My work render on a cream reading surface under the blue header, every control shares one 3px frame with hover lift, hard shadow and press feedback, and the thinking rail is a numbered headline-weight bar. Chrome checks at 1440 and 390 px pass with no JS errors or overflow; 105 student-app tests pass. Board touch review pending.

**T-098 typography and copy correction (2026-11-15, laptop only):** the landing is blue through the full viewport, with a transparent start action and only the brand, headline, nickname and local-privacy note. The exercise begins with the actual question under compact navigation; duplicate titles, topic and scope copy are visually removed while keeping accessible labels. One Arial family and a restrained type scale now cover the app. Navigation clicks are scoped to navigation buttons, avoiding the prior body-wide refocus. Chrome checks at five widths and a wrong/correct answer flow pass; 89 student-app tests passed during this review. Board touch review is pending.

**Generated content served (T-092, T-111; 2026-11-15, laptop only, branch `exp/ml-tutor`):** the student app loads the optional large-model files (`data/ml/thinking_steps_generated.json`, `solutions_generated.json`, `slm_explanations.json`, `data/teaching_annotations.generated.json`), re-verifies every item against its problem on the board (`copilot/content_checks.py`: bank rules, language, no correct value/letter, word limits) and drops failures. Precedence is human, then generated, then skill fallback; `/api/start` reports `content_sources`, `tags_source` and `provenance`. A wrong answer with a generated explanation shows it and its Socratic question, which becomes the first hint; `/api/solution` serves generated solutions; coverage counts human and generated tags separately. The `--with-data` bundle carries `data/ml`. Generation finished 05:31 (two passes through the organisers' API, D-013): tags for 1746/1747 problems, thinking steps for 96% and solutions with hints for 94% of the (problem, language) rows, explanations for 95% of the signed distractors; the laptop re-verification serves 1786 step sets, 1761 solutions, 857 hint ladders, 1746 tags and 1545 explanations with 0 dropped (EXPERIMENTS "Generated teaching content"). 105 student-app tests pass; not yet deployed to the board; educator review pending.

**T-103/T-105/T-107 integration (2026-11-15, laptop only, branch `exp/ml-tutor`):** the student app keeps an Elo rating beside BKT and picks problems near a 70% predicted success with an explained reason, serves a standalone problem map at `/map?student=<nickname>` with stepping-stone paths, and `ALIGN_CATALAN` (off by default) can rotate Catalan RAG queries; 93 student-app tests pass, nothing is deployed or measured on the board yet.

**T-097 flat interface correction (2026-11-15, laptop only):** the decorative arithmetic preview and white/pale-blue cards are removed. The nickname field sits directly on the blue landing area with a black underline; Solve, My path and My work use spacing and separators. A final answer now produces a large green or red inline signal with reduced-motion support. Chrome at 390/1440px showed no page errors or overflow, both answer states were exercised, and all 75 current student-app tests pass. Physical touch and board visual review are pending.

**ML tutor bundle, night of 2026-11-15 (laptop only, board unreachable from this Mac):** difficulty model from Kangaroo paper position (ensemble 0.516 vs 0.395 majority on 2023–24), Procrustes Catalan→English alignment (held-out recall@1 0.50 → 0.72), 1747-problem map with 15 clusters and stepping-stone paths, and error signatures with misconception feedback (30.5% of numeric distractors explained; an automated spot check found only 11/30 explanations plausible, so the wording is tentative and a human check is pending). Board code for these is pure Python with tests; server integration, deployment and board timing are in progress. See [ML-OPTIONS.md](ML-OPTIONS.md) and the EXPERIMENTS rows.

**T-108/T-109 error signatures (2026-11-15, laptop only, branch `exp/ml-tutor`):** a laptop script explains 981 of 3220 numeric distractors with a naive operation on the problem's numbers (`data/ml/signatures.json`), and after a matching wrong answer the student app says which operation gives that number, without revealing the answer, and starts hints at the method rung; BKT is unchanged and nothing is deployed yet (T-110).

**T-091 thinking steps (2026-11-14, laptop only, uncommitted on `ui/thinking-steps`):**
before the A–E choices, students now answer three multiple-choice process steps
(Understand · Plan · Check) with immediate, model-free feedback; the written note
is optional when steps exist and still required for unclassified problems. The
bank has general English steps for all 10 skills and problem steps for the five
samples (Catalan for sample-4/5), validated at load and leak-checked against the
catalog at startup. BKT is unchanged. 48 tests pass locally; not yet deployed or
tried with students. Training items use the general skill steps until T-092.

**T-090 one-time Windows setup (2026-11-14):** the user subsequently authorized
installation. A standalone 26.8 MB `START.EXE` bundles Python/Tk and ADB; it installs
per user, creates a Start-menu control and registers the USB watcher at login.
Version `1.0.20261114205347` is installed on this PC. Its exact registered startup
command reopens the tutor with only Windows System32 on PATH and invalid external
Python paths; both graphical windows open correctly. Nine setup/image/rollback
checks pass on the board, including simulated USB bind failure. A validated
64 MiB read-only MATHTUTOR drive is now active and enabled at board boot. Windows
mounted it as `D:`; `START.EXE` matches the build checksum and verifies all 993
bundled files when executed from the drive. The new composite interfaces use
Windows inbox `usbstor.inf`, `winusb.inf` and `usbser.inf`; ADB reports the
`USB\MS_COMP_WINUSB` compatibility ID. The installed watcher detected the USB
reconfiguration at 22:08:55 Europe/Madrid and reopened the tutor at 22:08:59.
All four board services are active; the three synthetic test attempts and SQLite
integrity are intact. A subsequent safe shutdown and physical replug passed:
the board boot ID changed, all four services started, the drive returned and the
installed watcher opened the tutor at 22:12:15 Europe/Madrid; the model was ready
by 22:12:21. Windows confirms the volume is read-only, the installer checksum
still matches, and the test notebook retains three attempts with SQLite integrity
ok. The user confirmed that both drive and browser appeared automatically.
First-time execution is manual on each Windows account. A genuinely fresh PC
and actual Windows reboot/login remain untested. macOS/Linux/Windows ARM
installers are not provided.

**T-087 software update:** the map now supports zoom/pan/drag, search and related
knowledge areas alongside explicit prerequisites. A progressive path follows
independent evidence and skips already demonstrated foundations. Students write a
first thought before selecting an answer; reveal/explanations require solving or
two attempts plus available help. The local tutor receives a short reasoning
excerpt and still selects only authored guidance.

**Wi-Fi board verification (2026-11-14):** SSH now works to UNO Q `xusigrupo` at
`10.198.34.77`; the existing language and embedding services are healthy. A separate
release under `/home/arduino/math-tutor-releases/20261114-185436-c48de06f83` runs the
tutor with all 170 training images and 30 diagnostics. The team's Git checkouts
were not changed. All 39 application tests and 12 deployment checks pass on the
board with `python3 -S`. Real systemd validation caught and fixed quoted
`WorkingDirectory` syntax before any boot-service installation.

The deployed graph has 12 embedding-based related edges generated by the board's
existing bge model from authored skill descriptions (2 neighbors, cosine > 0.65).
The repository's keyword graph remains a fallback. Four live hint selections took
10.1–23.0 seconds, with stored guidance in 16–21 ms. The owner installed the tested
boot service from App Lab; `math-student` is active and enabled. A deliberate
failure of only this service triggered automatic recovery: the test notebook's
three attempts and demonstrated skill survived, and SQLite `quick_check` passed.
Records live at `/var/lib/math-student/progress.db` with mode 0600. A later board
boot (2026-11-14 19:27:16 UTC) started all three services; the test notebook kept
its three attempts and SQLite integrity passed. USB serial `2727288917` was
verified as this same board. The earlier demonstration used a temporary watcher
with Python and ADB already on the PC, opening http://127.0.0.1:7013 through USB.
No software or Windows startup entry was installed for that demonstration.
Physical reconnect also passed: the watcher detected disconnection at 20:32:37
Europe/Madrid and reopened the page at 20:33:06 after a new board boot. The model
was ready by 20:33:12, and all three saved test attempts remained. The user
confirmed automatic opening. T-090 above subsequently replaced the temporary
watcher with the authorized standalone installation. See
[deployment instructions](../board/STUDENT_DEPLOYMENT.md).

Final packaging restored 118 missing training images from the existing local
Parquet cache without changing JSONL, labels or existing images. All 170 training
originals are now available. `results/math-tutor-bundle.tar.gz` includes runtime,
curriculum and training media, with no progress database or validation records.
The connected-map server is live on port 7011; all 126 existing attempts were
retained after migration. Real-M3Kang browser checks confirm image-dialog Close,
Escape and backdrop dismissal preserve both written thoughts and answer selection.

The existing models and pinned llama.cpp checkout were verified. A development
deployment baseline scored **11/30 (36.7%)**, mean **10.4 s**, worst **25.6 s**, with
no errors/timeouts. This trails always-D (13/30) on the small, D-heavy English set;
it does not establish reliable mathematical reasoning or hidden-test performance.
The official solver was unchanged. Main-branch confirmation and broader evaluation
remain pending. There are ten authored skill nodes, thirty original diagnostics
and 51 provisional M3Kang topic annotations. The Tukey side project is separate
in [its workspace](../side-project/README.md).

## Setup progress (README steps)

| Step | What | State | Date | Notes |
| --- | --- | --- | --- | --- |
| 0 | Connect to the board (App Lab, IP, SSH) | Verified | 2026-11-14 | Existing App Lab connection; dedicated SSH key; firmware updates not performed by this task |
| 1 | Check the board (RAM, disk, clock, internet) | Partial | 2026-11-14 | RAM, disk and clock inspected; no internet dependency introduced |
| 2 | Install the build tools | ⬜ pending | | |
| 3 | Build llama.cpp at the pinned commit | Existing build | 2026-11-14 | Running server; checkout matches pinned commit |
| 4 | Download and verify the models | Verified | 2026-11-14 | Existing model files match both pinned hashes |
| 5 | Hello world: language model | Verified inference | 2026-11-14 | Contract/eval and four bounded hint selections; tokens/s profiling remains separate |
| 6 | Hello world: embeddings | Verified | 2026-11-14 | Ten authored skill descriptions embedded; 12 graph relations exported |
| 7 | Run both models as services | Active | 2026-11-14 | All three services active after the owner reconnected the powered board |
| 8 | Clone repo and run sample problems | Verified | 2026-11-14 | Existing clones retained; isolated release passed five-row contract twice |
| 9 | Prepare M3Kang on the laptop | 🟨 in progress | 2026-11-14 | 200 English starter rows; full multilingual preparation pending |
| 10 | Copy data to the board | Done | 2026-11-14 | Training media in runtime; validation separately for QA |
| 11 | Measure our baseline | Development check | 2026-11-14 | 11/30; main-branch confirmation pending |
| 12 | Build the RAG index and try it | ⬜ pending | | |
| — | Explorer (optional) | ⬜ pending | | |
| 13 | Choose the idea | Done | 2026-11-14 | Adaptive teaching plus separate reasoning evaluation |
| 14 | Implement, measure, analyse errors, UI, pitch | In progress | 2026-11-14 | Tutor deployed over Wi-Fi/USB; educator review and pitch pending; temporary USB reconnect passed |
| 15 | Publish (GitHub + Project Hub) | ⬜ pending | | |

States: ⬜ pending · 🟨 in progress · ✅ done · ❌ blocked (say why).

## Environment facts

| What | Value |
| --- | --- |
| Board IP | 10.198.34.77 (`xusigrupo`, UNO Q verified over SSH) |
| Board memory with app and both models | Minimum MemAvailable 2697 MiB, swap used 0; 206 samples at 2 s during contract/eval/repeat |
| llama.cpp checkout | Pinned `2cbe0ec429b849a88664e0f62388fc92a5abd699`; both model SHA-256 hashes verified |
| Languages in our dataset | English starter set; final language coverage not decided |
| Train / val sizes | 170 / 30 on PC and board; student app loads training only |

## Key numbers

| Metric | Value | Conditions |
| --- | --- | --- |
| Development baseline accuracy | 11/30 = 36.7% | UNO Q, English starter validation; always-D 43.3%; not main-branch release validation |
| Baseline latency (mean / worst) | 10.4 / 25.6 s | 30/30 status ok, no requests over 60 s |
| RAG k=1 accuracy | — | |
| Best accuracy so far | — | |

## Main workstreams

Both **Teach and Reason are required main deliverables** (TODO T-023 and T-024). Teach is delegated to a teammate; its specific learning flow and the first Reason improvement still need to be scoped in T-020. Neither MVP is marked complete. See [DECISIONS.md](DECISIONS.md).

The team wants reasoning plus adaptive teaching. The teaching path now uses authored Markdown skills, reviewed problem tags, conservative Bayesian Knowledge Tracing, diagnostics and 1/3/7-day reviews. A wrong multi-skill answer never lowers all its connected skills. An optional bounded SLM worker selects permitted stored hints; deterministic Python owns grading, state and recommendations. Laptop k-means exports candidates for explicit review. See [curriculum documentation](../knowledge/README.md) and [student app instructions](../student_app/README.md).

The Kangaroo Studio redesign on `ui/kangaroo-studio` now uses a blue typographic entrance based on the supplied reference, child-facing Solve / My path / My work views, an exercise-first layout and readable skill tiles. The start action is visible at 320–1440px with no horizontal overflow. Chrome checks at desktop and mobile widths report no JavaScript errors; the full three-step answer-to-next-exercise flow and 48 application tests pass locally. A 20-point visual review then removed black surface borders, decorative grid lines, the duplicate wordmark, excess display labels and the repeated current-exercise recommendation; the blue keyboard focus ring remains. Physical touch and board visual validation remain pending.

The follow-up screen review removed the visible nickname label and local-storage note, applied the same blue/black/underline language to all three workspace views, and reserved green/red for answer results. My path now shows its route and skill list before an optional connection map; selecting a skill expands its detail. The recommendation action now opens the exercise and switches to Solve. Desktop and phone Chrome checks found no JavaScript errors or horizontal overflow; physical board and touch validation remains pending.

## Known issues

39 application/graph tests and 12 deployment/launcher tests pass on the UNO Q. Installed-Chrome checks against the actual board at 1440x1100 and 390x844 cover reflection, answer gates, search, goals, zoom, dragging, combined media and image Close/Escape/backdrop dismissal. No JavaScript errors or external page requests were observed. The same browser checks also pass through actual USB forwarding, with no JavaScript errors or external page requests. Physical touch devices and Windows login startup remain unverified.

The 51 local tags were provisionally reviewed by Codex from question text; educator and diagram review is pending. Most real questions have only general skill guidance or no hint, and no authored solution. OCR/crops also need review. BKT parameters and review intervals are unfitted defaults. There are no real student learning outcomes. Skill embeddings and live selection now work on the board, but relatedness quality and problem-cluster labels still need educator validation. The physical LED adapter is not implemented.

The updated app is running on default port **7011** with 170 exercises plus 30 diagnostics. After dataset regeneration during this task, choice enrichment was restored: train 101 text sets, 10 picture sets and 59 requiring the original; validation 17 text sets, 1 picture set and 12 requiring the original. All 200 supplied labels were preserved. Existing 119 attempts and 132 sessions survived migration; no old attempt is retroactively interpreted as new skill evidence. New diagnostics have balanced A–E answer positions and three stored hints each.

The board `predict.py` check emitted five valid letters with status `ok`; repeating
it after evaluation gave the same five answers. The earlier laptop 13/30 result
was only the D fallback and must not be described as model accuracy. See
[EXPERIMENTS](EXPERIMENTS.md) for conditions and artifacts. The earlier synthetic
teaching comparison measures the old selector, not the new path-first API.
