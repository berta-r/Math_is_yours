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

## D-003 · Deliver both Teach and Reason (2026-11-14)
**Status:** accepted
**Context:** the task list treated Teach approaches as optional candidates alongside the official Reason score.
**Decision:** the team will deliver both Teach and Reason as required main workstreams, each with a P0 MVP and an owner. T-020 chooses the Teach approach and scopes the first Reason experiment.
**Consequences:** evaluate Reason accuracy and latency, validate the selected Teach learning flow, and demonstrate both offline on the UNO Q. The Teach approach is now defined by D-004 to D-013.
## D-004 · Local-first teaching prototype (2026-11-14)
**Status:** accepted
**Context:** the team requested both reasoning and teaching, with an offline browser interface and persistent student skill evidence.
**Decision:** start with a standard-library Python web server and SQLite in `student_app/`, using invented sample problems and reviewed hints. The same server can run on the PC or board and be accessed through USB port forwarding. Use fixed illustrative topic edges until clustering is validated.
**Consequences:** no runtime dependencies or cloud hosting; no changes to the official solver. Nicknames are prototype profile selectors, not authenticated accounts. Model integration and the App Lab LED adapter are subsequent work. First-exposure success is tracked separately from assisted or repeated practice; the graph does not claim measured mastery.

## D-005 · Prepared M3Kang media in the student app (2026-11-14)
**Status:** accepted
**Context:** students must view question text, original diagrams and image-based answer choices offline.
**Decision:** load prepared JSONL on startup, defaulting to training only, and serve original local images via catalog keys. Identify translations with `id|language`. Display text plus image by default, with optional text/image views. Use the backend answer key for grading, never include it in public problem responses. Real problems remain unclassified until reviewed tags exist, with unavailable hints/explanations disabled.
**Consequences:** laptop-only preparation dependencies; board runtime remains standard library. A 60-row English starter subset (52 train, 8 validation) is prepared with original images and no OCR. Answer choices can be read directly from images. The app makes no dataset network requests during practice. Official solver evaluation remains separate.

## D-006 · Choice extraction is separate from answer correctness (2026-11-14)
**Status:** accepted
**Context:** missing OCR left A–E buttons without readable content; students also need an explicit way to reveal the correct choice.
**Decision:** enrich existing local JSONL using laptop-only OCR. For diagram options with a detected full A–E marker sequence, save layout-based image previews. Grade and reveal only using the dataset's existing official label. Showing an answer marks the session as assisted. Do not describe answer revelation as an SLM solution or an explanation.
**Consequences:** automatic text/crops may need review against the preserved original; runtime stays offline and standard-library only. Official labels are never modified by OCR. The `predict.py` algorithm is unchanged; no reasoning accuracy improvement is claimed.

## D-007 · Shared curriculum graph, separate student state (2026-11-14)
**Status:** accepted; supersedes D-003 and the illustrative graph in D-004
**Context:** the user requested implementation of the proposed knowledge-graph teaching architecture in the working student interface.
**Decision:** extend `student_app/` with ten authored skills, explicit prerequisites, thirty original diagnostics, provisional standard-library BKT, conservative first-exposure attribution and separate review dates. Keep SQLite history and offer an explainable deterministic selector plus Markdown export. Use laptop k-means to propose groups and explicit reviewed mappings to label problems. The optional SLM selects authored hints in a bounded background worker; it never grades or authors unchecked mathematics.
**Alternatives:** moving practice into the organizer's explorer would duplicate the working interface. Inferring prerequisites or mastery directly from clusters lacks supporting evidence. Freeform model hints cannot be assumed correct.
**Consequences:** no new board dependencies or official-solver imports. Parameters, 1/3/7-day intervals and initial Codex topic annotations need validation. Embedding quality, live model selection, RAM/latency on the board, physical controls and real learning outcomes remain to be evaluated. A correct multi-skill answer can be logged as independent performance without assigning mastery to every skill.

## D-008 · Connected map, reflection and portable board deployment (2026-11-14)
**Status:** accepted
**Context:** the user requested an Obsidian-like knowledge map, a progressive route from strengths/weaknesses, thinking before answering and automatic opening when plugging in the UNO Q.
**Decision:** render a settled force graph in the browser with distinct similarity and prerequisite edges. Export compact skill relationships on the laptop; the board reads edges only. Use the same evidence-based route for recommendations and path display. Require a student-written thought before accepting a letter, then two attempts plus available help before answer review unless solved. Store reflections without claiming to grade them. Keep a constrained local hint selector. Provide versioned board deployment, a boot service and an explicitly installed per-user Windows ADB watcher that opens the browser once per connection.
**Consequences:** no third-party board dependencies, background training or graph-layout work on the board. Current relatedness is an explicit keyword baseline, with embeddings import/local generation supported. Original images can still contain choices. One-time PC setup is required; hardware and live-model tests are deferred by user instruction. Student records persist outside versioned code releases. No automatic OS or board installation was performed while preparing the implementation.

## D-009 · Wi-Fi verification and persistent board service (2026-11-14)
**Status:** accepted; updates D-008 deployment state
**Context:** the user connected the UNO Q in App Lab and authorized Wi-Fi setup/testing.
**Decision:** deploy a separate release over SSH, reuse the pinned local model services and expose the interface to the PC through a loopback SSH tunnel. Generate skill-relatedness metadata from the existing bge model; keep authored prerequisites and BKT evidence separate. The owner authenticates sudo locally to install the system boot service. Verify its real systemd syntax before installation, retain progress under `/var/lib/math-student`, and test automatic process recovery with a synthetic notebook.
**Consequences:** no changes to teammate Git checkouts, model settings or Windows startup. The app and live hints pass physical-board checks. The 11/30 development solving baseline trails always-D on this small validation set; the tutor continues to grade against the dataset key. USB opening, full-board reboot and educator validation remain separate checks. The PC's earlier prototype database was not migrated into the fresh board database.

## D-010 · Temporary USB demonstration without additional installation (2026-11-14)
**Status:** accepted
**Context:** the user requested plug-in opening without installing anything further.
**Decision:** run the existing repository watcher temporarily with Python and ADB already available on this PC. Do not run its installation command or register Windows startup. Match the connected board identity before forwarding its app port. Observe a real shutdown, unplug/replug and automatic browser reopening.
**Consequences:** the test succeeds and saved board progress survives. This PC still executes a watcher; it does not resume after Windows restarts. Ordinary USB does not provide reliable zero-setup browser autorun on arbitrary computers. An installation-free product needs a manual opening step or a separately designed browser-accessible connection; persistent automatic opening requires host preparation. No keyboard emulation or OS security-setting changes were introduced.

## D-011 · Explicit first-time PC setup carried by the Arduino (2026-11-14)
**Status:** accepted; supersedes D-010's no-installation constraint for the new requested flow
**Context:** the user asked whether the Arduino could configure a small launcher on each computer on first connection, then instructed us to implement it.
**Decision:** package an offline Windows x64 setup executable containing Python/Tk and ADB. A student runs it and clicks setup once; subsequent user logins start a board-specific watcher. Offer the installer on a read-only USB mass-storage function added beside existing ADB/serial. Preserve the original gadget descriptors for rollback and use ADB's WinUSB compatibility descriptors. Install a separate dependent board service, leaving the vendor ADB service intact.
**Consequences:** the authorized standalone launcher is installed on this PC. Its registered login command works with only Windows System32 on PATH and no external Python. First execution remains manual on every new Windows user account. The unsigned prototype requires a fresh-PC check; Windows ARM, macOS and Linux packages are outside this implementation. Models, problems and notebooks remain on the board. The owner authenticated sudo to enable the drive; Windows mounted it and selected inbox storage, WinUSB and serial drivers. Automatic browser reopening succeeded after reconfiguration and after a full shutdown/replug; the drive returned and test progress survived. No hidden autorun, keyboard emulation, cloud runtime or machine-wide PC installation is used.

## D-012 · Multiple-choice thinking steps replace mandatory free-text reflection (2026-11-14)
**Status:** accepted; updates the reflection gate in D-008
**Context:** students had to write ungraded free text before the A–E choices appeared. Nothing checked it, so it gave no feedback, and many students type filler to get past it. We wanted a process scaffold that teaches, following the /teach skill and standard learning science: tiny working-memory-sized steps, one tangible win each, immediate automatic feedback.
**Decision:** before answering, the student answers three multiple-choice process questions (understand, plan, check) from `knowledge/thinking_steps.json`. Problem-specific steps in the problem's language come first, then general English steps of the problem's skill, then none (unclassified problems keep the written-thought gate). Pure Python checks each choice and returns an authored one-sentence reason; a wrong choice is retried. Completing the steps unlocks the answer and counts like a reflection for the review gate. Option lengths are balanced, key positions balanced and answer values leak-checked at load and at server start. A missed plan step starts hints at the method rung. Steps are logged in `thinking_events` and never update BKT, eligibility or review dates.
**Alternatives:** grading free text with the 0.8B model: too slow on the board (about 5 tok/s) and unreliable as a judge, and it would put a model on the critical path of every problem. Generating steps on the board at runtime: same speed problem and no way to review them; steps for the training set are generated offline instead (T-092). Keeping free text mandatory alongside steps: doubles the work before every answer.
**Consequences:** the answer gate now depends on loaded content, so `/api/start` returns `thinking_steps` (questions and options only, never keys or explanations) and `steps_scope`. Today only the five samples have problem steps; the 170 training items use the general skill steps until T-092. Process metrics are descriptive (T-093); no learning gain is claimed. The tutor grammar and selection contract are unchanged; `predict.py`/`pipeline.py` are untouched.

## D-013 · The on-device SLM never generates or judges content live; large-model content is generated offline and verified (2026-11-15)
**Status:** accepted
**Context:** the team wants the board's 0.8B model to be part of teaching. Probes with the exact board GGUF (EXPERIMENTS, "Live SLM probes") gave 1/5 useful Socratic questions, 7/12 correct strategy labels, and 19–38 s of estimated board time per turn. The organisers provided a Helmcode API key (OpenAI-compatible, EU-hosted open models); `deepseek-v4-flash` produced good Catalan in 4 s.
**Decision:** all content a student reads (misconception explanations, Socratic questions, per-problem thinking steps, solutions, hint ladders, skill tags) is generated offline with the large model through `laptop/ml/generate_content.py`, verified by the standard-library `laptop/ml/verify_content.py` (leak, language, length and bank rules), stored under ignored `data/ml/`, and served instantly by pure-Python board code. The live SLM keeps only bounded roles: choosing among authored hints (grammar-constrained index) and, later, the letter distribution as "the AI's opinion". The same generator can run against the board's llama-server (`--port`) to extend content on-device, but that is optional.
**Alternatives:** live Socratic turns with the 0.8B (rejected: quality and latency); grading the student's note live (rejected: 58% label accuracy would mislead); a local 7B via llama.cpp (superseded by the hosted large model).
**Consequences:** the pitch says "generated offline by a large model and verified; served on-device". The API key lives only in `.env.local` (gitignored). Educator review of generated content is still pending; provenance fields name the model and date.

## D-014 · Bundle the OFL font Archivo instead of relying on system Arial (2026-11-15)
**Status:** accepted
**Context:** the MATH IS YOURS identity depends on a 900-weight display face. Arial has no true 900 weight (browsers synthesise or substitute Arial Black where installed), and the board, Linux laptops and Windows PCs fall back to different faces, so the wordmark, step rail and result bands changed shape from machine to machine. The app must stay fully offline.
**Decision:** ship Archivo (SIL Open Font License, variable weight 100–900) as two woff2 subsets, latin and latin-ext (Catalan needs à è é í ï ò ó ú ü ç and the middle dot of l·l), 68 KB in total, under `student_app/assets/fonts/` with `OFL.txt`. `server.py` serves `/fonts/<name>.woff2` from an allowlist as `font/woff2` without a charset; the stylesheet declares both subsets with `unicode-range` and `font-display: swap`. Display text uses 900, body text 400/700.
**Alternatives:** keep Arial/Arial Black (rejected: inconsistent rendering and no real 900 on Linux); load Google Fonts at runtime (rejected: breaks the offline rule); a static per-weight family (rejected: about five times larger than the variable file).
**Consequences:** identical rendering on the board, Windows and macOS; 68 KB more in the bundle; Arial stays in the stack as the fallback while the font loads.

## D-015 · Localise the child-facing UI to the open problem's language, with server-side message tables (2026-11-15)
**Status:** accepted
**Context:** M3Kang problems come in Catalan and English, but the interface, server feedback and recommendation reasons were English only and used research vocabulary ("independent evidence", "diagnostic", "authored prerequisite links"). A Catalan student read a Catalan question surrounded by English instructions.
**Decision:** the interface language follows the open problem (`cat` → Catalan, anything else → English). Static copy lives in a `STRINGS` table in `app.js` and is applied through `data-i18n` attributes whenever the language changes. Every message the server returns to the child comes from `MESSAGES` in `server.py`, chosen by the session's problem language (answers, steps, reveal) or the request's `language` (profile state labels, recommendation `summary`, path `child_reason`), with English fallback. The technical recommendation `reason` stays in the API and appears only in the adult-facing "About these learning estimates" note. Skill names remain English until the curriculum file has translations.
**Alternatives:** a separate language switch (rejected: one more control for a child, and it can disagree with the problem); translating only on the client (rejected: server messages would stay English and tests could not check them).
**Consequences:** English API strings that tests pin are unchanged; Catalan variants are tested in `student_app/test_localisation.py`; adding a language means one more column in each table.
