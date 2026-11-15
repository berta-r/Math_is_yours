# Submission plan (morning of 15 November 2026)

> Operational plan for handing in with minimum friction. Written 2026-11-15 around 02:15 from the repository state at that time: `main` = `9f39f94` (exp/ml-tutor merged), `exp/ml-tutor` = `3aa5720`. Re-check the branch facts in section (d) before acting on them. Anything not found in the repository is marked **confirm with organisers**.

> **Resum per a l'equip (català)**
> - **Què s'entrega:** (1) l'enllaç del repositori GitHub **públic**, (2) l'enllaç del projecte a **Arduino Project Hub**, (3) demo en directe + pitch de 3 minuts amb la placa. A més, els organitzadors executen el nostre `predict.py` a la placa amb el test ocult. L'hora límit, el formulari i el canal per enviar els enllaços **no surten al repositori: cal confirmar-ho amb els organitzadors**. Aquest pla suposa les **10:00**.
> - **Bloquejants:** falta el fitxer `LICENSE` (MIT), el `README.md` encara és la guia dels organitzadors (T-074), la visibilitat del repo no està comprovada, i la feina de redisseny (`app.js`, `index.html`, `style.css`) està sense commit al working tree de `exp/ml-tutor`.
> - **Branques:** `exp/ml-tutor` ja és a `main`. `ui/kangaroo-studio`, `ui/thinking-steps` i `ui/student-practice` ja hi són contingudes (no tenen cap commit propi). Queden `exp/reason-strategies` (Reason, toca `predict.py`) i `docs/demo-first-proposals` (només docs).
> - **Placa al matí:** desplegar el bundle amb `--with-data`, tests amb `python3 -S`, `free -m`, `predict.py` amb els 5 problemes de mostra, Wi-Fi apagat i assaig de la demo dues vegades.
> - **Mai** publicar dades de M3Kang ni res derivat (`data/`, `data/ml/`, contingut generat, imatges, `*.db`).

## (a) What the organisers collect, and how

Quoted from the organisers' guide, [DATATHON-GUIDE.md](DATATHON-GUIDE.md) (the root README at the time):

| What | Source in the README | Status |
| --- | --- | --- |
| "The project and source code documented in an open Github repository and at the Arduino Project Hub with the architecture, experiences, how to replicate the project, error analysis by topic, language and difficulty" | Deliverables | Repo exists (`origin` = `github.com/berta-r/datathon_xusigrupoo`); visibility not checked (no `gh` on this Mac). Project Hub page not started (T-075). |
| "A live demo and a 3-minute pitch on the board" | Deliverables | Scripts: [PITCH.md](PITCH.md), [DEMO-SCRIPT.md](DEMO-SCRIPT.md). |
| "Every team publishes two things: a public GitHub repository with the code, and a step-by-step write-up on Arduino Project Hub. **Send both links to the organizers.**" | Step 15 | How to send them is **not in the repo: confirm with organisers** (form, e-mail or Discord channel). |
| `predict.py` "is the entry point the jury runs"; contract `python3 predict.py --input <file>.jsonl --output <file>.csv [--rag K]`, one letter A–E, ≤ 60 s, fallback `D`, offline, temperature 0, seed 42 | Steps 8 and 11.1, [01-challenge.md](01-challenge.md) | `main` ships the organisers' baseline (`REASON_STEPS` does not exist on `main`). |
| Hidden test details | Team notes on `exp/reason-strategies` (EXPERIMENTS, error notes, 15 Nov): "the final test is 20 problems, levels 0–7, some with figures, run by the organizers on the board with `predict.py`"; DECISIONS D-006 update: "the hidden test gives the options A–E as text, and changing the model is allowed" | Relayed by the team, not in the README: **confirm with organisers** which board checkout and which branch they run, and at what time. |
| README content | Step 15.1: what it does (photo/video), architecture, replication from a board at steps 0–12, results from `results/ablations.csv` against the baseline, error analysis by topic/language/difficulty, what didn't work, team members, licence (e.g. MIT) | Not written (T-074). Use [.skills/publish-project/SKILL.md](../.skills/publish-project/SKILL.md). |
| Project Hub sections | Step 15.2: introduction, components and apps, architecture, step by step, results, what we learned | Not written (T-075). |
| Pitch structure | Step 14.5: problem 20 s, demo 90 s, numbers 40 s, lessons 30 s; "Wi-Fi off, the services started at boot"; "Record a short video of the demo working" | Follow [PITCH.md](PITCH.md). |

**Not found anywhere in the repository (all branches searched):** the hand-in time, the submission form or channel, the pitch slot and room, whether slides are allowed or projected from our laptop, and whether the jury runs `predict.py` from our public repo or from the board as we leave it. The only date reference is `docs/AI-PROPOSAL-GUIDE.md` on `docs/demo-first-proposals` and `exp/reason-strategies`: "We must present a working product tomorrow morning (15 November 2026)". **This plan assumes a hand-in at 10:00 on 15 November 2026. Confirm with organisers first thing.**

## (b) Hard pre-submission checklist

Tick every line before sending links. Commands run from the repository root unless marked **board**.

- [ ] **`predict.py` contract on the board** (5 rows, one letter each, status `ok`):
  ```bash
  # board, in the checkout the jury will use
  git status && git log --oneline -1
  python3 predict.py --input data/sample_problems.jsonl --output results/check.csv && cat results/check.csv
  ```
  Expected header `id,language,answer,seconds,status`, five rows, letters A–E. Status `error` with all `D` means the model server is down (see risks).
- [ ] **Decide what `predict.py` ships (T-039).** `main` keeps the baseline. `exp/reason-strategies` measured no variant above chance (DECISIONS D-006 on that branch). Recommendation: keep the baseline on `main`; merge the Reason branch only as documented, opt-in code with `REASON_STEPS=letter` (see section d).
- [ ] **No M3Kang data tracked or in history** (from the `publish-project` skill; each must print nothing):
  ```bash
  git ls-files | grep -E '^data/' | grep -v -E '^data/(sample_problems\.jsonl|README\.md)$'
  git ls-files | grep -E '\.(db|gguf|jsonl|png)$' | grep -v '^data/sample_problems\.jsonl$'
  git log --all --name-only --format= | sort -u | grep -E '^data/(train|val)\.jsonl$|^data/images/|\.db$|^data/ml/'
  git status --short
  ```
  Checked at 02:15: all three print nothing. Re-run after the last merge.
- [ ] **No secrets tracked:** `git ls-files | grep -iE '(^|/)\.env'` prints nothing; no API key, Wi-Fi or board password in any tracked file or commit message.
- [ ] **Licence present:** there is **no `LICENSE` file** at 02:15. Add an MIT `LICENSE` for our code and keep the credits section (M3Kang research-only licence, llama.cpp MIT, Qwen and bge model cards, RapidOCR Apache 2.0).
- [ ] **Repository is public** and opens logged out in a private browser window. Owner of `berta-r/datathon_xusigrupoo` changes it under Settings → General → Danger Zone → Change visibility. Do this only after the M3Kang check above passes, because history becomes public too.
- [ ] **README rewritten (T-074)** in the order of the `publish-project` skill: what it does with a photo or video, architecture (Linux side, model servers, M3Kang use; the LED matrix is not implemented, say so), replication from steps 0–12, results table against the 22.5% baseline with n and conditions, error analysis by topic/language/level with counts (T-071), what didn't work (Reason at chance, live Socratic SLM), team, licence. Every number must come from [EXPERIMENTS.md](EXPERIMENTS.md) with its conditions; results on 50 problems or fewer say so.
- [ ] **Project Hub page (T-075)** published, links to the repo, contains no M3Kang problem text or images.
- [ ] **Branches merged into `main`** per section (d); `main` passes the contract check on the board after the last merge.
- [ ] **Tests on `main`:** laptop `python3 -m unittest discover -s student_app` (105 tests, 1 skip, OK at 02:15 on `exp/ml-tutor`), and on the board with `python3 -S` (section c).
- [ ] **Tag the submitted commit** and push the tag so the jury and we refer to the same code:
  ```bash
  git switch main && git pull
  git tag -a submission-2026-11-15 -m "Datathon FME 2026 submission"
  git push origin main submission-2026-11-15
  ```
- [ ] **Clean-clone test:** clone the public URL into a new folder and follow the README replication steps far enough to start the student app with `data/sample_problems.jsonl`.
- [ ] **Both links sent** to the organisers through the channel they confirm; screenshot the confirmation.

## (c) Morning board checklist

Board: UNO Q `xusigrupo`, last seen at `10.198.34.77` (STATUS). Team checkout per AGENTS.md: `~/datathon-UPC-maths-qualcomm-arduino-unoq`; tutor releases under `/home/arduino/math-tutor-releases/`, progress in `/var/lib/math-student/progress.db`. Do not run two jobs that use the model servers at the same time (evaluation, embedding, live hints).

**1. Connect and check health (board)**
```bash
ssh arduino@10.198.34.77            # laptop; if refused see README step 0.3, if Wi-Fi is down use adb shell
systemctl status math-llm math-embed math-student --no-pager
curl -s http://127.0.0.1:8081/health; echo
curl -s http://127.0.0.1:8082/health; echo
curl -s http://127.0.0.1:7011/api/health; echo
free -m
```

**2. Update the checkout the jury will use (board).** First check where it points: `git remote -v`. If it is still the organisers' template, add ours and track it; never discard teammates' uncommitted work without asking.
```bash
cd ~/datathon-UPC-maths-qualcomm-arduino-unoq
git remote -v
git status --short
git fetch origin && git switch main && git pull --ff-only
```

**3. Embed every problem on the board (T-100; optional for the demo, needed for "Q8" numbers).** Needs `data/train.jsonl` on the board (`scp data/train.jsonl arduino@10.198.34.77:~/datathon-UPC-maths-qualcomm-arduino-unoq/data/` from the laptop). About 4 minutes per 911 problems (README 13.1), so roughly 13 minutes for 2932 rows.
```bash
time python3 build_index.py --input data/train.jsonl --db data/index.db
```

**4. Regenerate the ML artifacts with the board's Q8 embeddings (laptop, optional).** EXPERIMENTS "Embedding note" says the difficulty model, alignment and map use laptop fp32 vectors and should be regenerated with `--port 8082` before quoting final numbers. Forward the board's embedding port, then run the chain in order. Skip this whole step if the morning is short: then the pitch says "laptop fp32 embeddings of the same bge-small model".
```bash
# terminal 1 (laptop): forward board 8082 to laptop 8082; nothing else may use 8082 locally
ssh -o ExitOnForwardFailure=yes -N -L 127.0.0.1:8082:127.0.0.1:8082 arduino@10.198.34.77
# terminal 2 (laptop), repository root
.venv-ml/bin/python laptop/ml/embed_problems.py --port 8082
.venv-ml/bin/python laptop/ml/features.py
.venv-ml/bin/python laptop/ml/difficulty.py train
.venv-ml/bin/python laptop/ml/align.py
.venv-ml/bin/python laptop/ml/build_map.py --input data/train.jsonl
python3 laptop/ml/signatures.py
python3 -m unittest discover -s student_app
```
Copy the new numbers from `results/difficulty-metrics.json`, `results/alignment-metrics.json` and `results/map-metrics.json` into EXPERIMENTS as new rows (do not overwrite the fp32 rows), and update PITCH.md if they move.

**5. Generated content for the demo problems (laptop).** At 02:10 only `data/ml/skills_generated.json` existed; explanations, steps and solutions were still being generated (D-013). Make sure at least the demo problems in [DEMO-SCRIPT.md](DEMO-SCRIPT.md) have content, then verify:
```bash
.venv-ml/bin/python laptop/ml/generate_content.py --api-base https://api.helmcode.com/v1 --kind all --ids lvl-0_2019_1 lvl-0_2019_19 --resume
ls -la data/ml data/teaching_annotations.generated.json
```
Rejected items land in `results/content-rejects.json`. The board re-verifies every item at start (`copilot/content_checks.py`) and logs served/dropped counts.

**6. Build and deploy the bundle with data (T-110).** The bundle carries `data/train.jsonl`, annotations, `data/ml/*.json` (except `embeddings.json`) and training images; it refuses credentials and model weights. Note: this Mac has **no `data/images/`**, so the bundle will report `missing_original_images`; the problems that need a diagram will show a missing-image warning. Build from the PC that holds the restored images, or demo only text problems.
```bash
python3 laptop/deploy_student.py --with-data      # prints file count, sha256, training_rows, missing images
```
Over USB (serial verified in STATUS: `2727288917`):
```bash
python3 laptop/deploy_student.py --serial 2727288917 --with-data --install --local-tutor
```
Over Wi-Fi (STUDENT_DEPLOYMENT.md "Wi-Fi connection"): upload to a new release folder, verify, extract, install.
```bash
R=/home/arduino/math-tutor-releases/$(date -u +%Y%m%d-%H%M%S)-submission
ssh arduino@10.198.34.77 "mkdir -p $R"
scp results/math-tutor-bundle.tar.gz arduino@10.198.34.77:$R/bundle.tar.gz
ssh arduino@10.198.34.77 "cd $R && sha256sum bundle.tar.gz && tar -xzf bundle.tar.gz"
ssh -t arduino@10.198.34.77 "cd $R && python3 board/install_student_service.py --local-tutor"
```
Compare the printed SHA-256 with the one `deploy_student.py` printed. Type the sudo password yourself. Earlier release folders stay as a rollback: re-run their installer to point the service back.

**7. Tests on the board with `python3 -S`** (standard library only). The bundle excludes `test_*.py`, so run them from the updated checkout:
```bash
cd ~/datathon-UPC-maths-qualcomm-arduino-unoq
python3 -S -m unittest discover -s student_app 2>&1 | tail -3
python3 -S -m unittest laptop.test_usb_launcher 2>&1 | tail -3
```

**8. Services, memory and timings (board).**
```bash
sudo systemctl restart math-llm math-embed math-student
systemctl status math-llm math-embed math-student math-tutor-usb-drive --no-pager
curl -s http://127.0.0.1:7011/api/health; echo
free -m
```
Record in STATUS (T-110): minimum `free -m` available with the full stack, and the time of `/api/recommendation` and `/map` from the browser's network panel. Earlier reference: minimum MemAvailable 2697 MiB during contract/eval (EXPERIMENTS, T-088).

**9. Contract check on the official entry point (board).**
```bash
python3 predict.py --input data/sample_problems.jsonl --output results/check.csv && cat results/check.csv
python3 predict.py --input data/sample_problems.jsonl --output results/check2.csv && diff results/check.csv results/check2.csv | grep -v seconds
```
Same five letters both times (seconds may differ).

**10. Demo conditions.** Turn the board's Wi-Fi off, open the tutor over USB (installed Windows launcher, or `adb forward tcp:7011 tcp:7011` then `http://127.0.0.1:7011`), and run [DEMO-SCRIPT.md](DEMO-SCRIPT.md) twice with a timer.

## (d) Merge plan

### What each branch contains (as of 02:15)

| Branch | Ahead of / behind `main` | Commits not in `main` | Files touched vs merge base |
| --- | --- | --- | --- |
| `exp/ml-tutor` | 0 / 2 | none: merged as `9f39f94` | Already in `main`. The merge resolved docs conflicts with T-083 in `AGENTS.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/TODO.md`. **Uncommitted in its working tree:** `docs/STATUS.md`, `docs/TODO.md`, `student_app/assets/app.js`, `index.html`, `style.css` (Kangaroo Studio redesign T-096–T-099, being edited now) and untracked `docs/KANGAROO-REDESIGN.md`, plus these three new docs. |
| `ui/kangaroo-studio` | 0 / 10 | none | Its tip `8a697ff` is an ancestor of `exp/ml-tutor`, so it is already in `main`. The later redesign work is the uncommitted working-tree change above, not on this branch. |
| `ui/thinking-steps` | 0 / 12 | none | Tip `3b6d7be` ("Liam_INTERFACE_done") is in `main`; T-091 itself was committed as `1aff9f7` and is in `main`. |
| `ui/student-practice` | 0 / 12 | none | Contained in `main`. |
| `docs/demo-first-proposals` | 1 / 15 | `0b5c85f` Add AI proposal guide and update documentation for demo-first approach | `AGENTS.md`, `docs/AI-PROPOSAL-GUIDE.md` (new), `docs/STATUS.md`, `docs/TODO.md` (branched from `8fa9747`, older than `main`). |
| `exp/reason-strategies` (not in the original list, but it holds the Reason work) | 8 / 12 | `a945cff` composable Reason steps; `891d44d` token counts; `6dcbc88` `--text-only`; `4c67d3a` proposal guide; `01bd796` 200 top_logprobs; `327fdaf` Reason results in docs; `8eb528d` hidden-test facts; `8be6a33` practice-set runs | `AGENTS.md`, `analyze_data.py`, `config.env`, `copilot/dedup.py`, `copilot/logprobs.py`, `copilot/pipeline.py`, `copilot/pot.py`, `copilot/safe_eval.py`, `copilot/values.py`, `docs/02-architecture.md`, `docs/AI-PROPOSAL-GUIDE.md`, `docs/DECISIONS.md`, `docs/EXPERIMENTS.md`, `docs/STATUS.md`, `docs/TODO.md`, `eval.py`, `predict.py`, `tests/test_safe_eval.py`, `tests/test_values.py` |

### Overlaps to resolve

- **exp/ml-tutor vs ui/kangaroo-studio** on `student_app/server.py`, `assets/app.js`, `assets/index.html`, `assets/style.css`, `docs/TODO.md`, `docs/STATUS.md`: **no committed conflict**. The committed kangaroo-studio history is already inside exp/ml-tutor, and `main`'s copies of the four app files equal exp/ml-tutor's. The only open overlap is the uncommitted redesign edits to `app.js`, `index.html`, `style.css`, `STATUS.md` and `TODO.md` in the shared working tree. `server.py` is untouched by the redesign. The map page (`map.html`, `map.js`) is separate and has no overlap.
- **Committed `exp/ml-tutor` vs `main`:** differs only in `AGENTS.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/TODO.md` (the merge's conflict resolution). Merging exp/ml-tutor again will conflict only in those docs.
- **`exp/reason-strategies` vs `main`:** both change `AGENTS.md`, `config.env` (main adds `ALIGN_CATALAN`, reason adds `REASON_STEPS` and friends at the end of the file: keep both blocks), `docs/02-architecture.md`, `docs/DECISIONS.md`, `docs/EXPERIMENTS.md`, `docs/STATUS.md`, `docs/TODO.md`. **Decision numbers collide:** reason uses D-003 "Idea to build (pending)", D-004 "Deliver both Teach and Reason", D-005 and D-006, while `main` already has D-003 to D-013. Renumber the reason entries D-005 → D-014 and D-006 → D-015 and drop its duplicate D-003/D-004. No code overlap: `main` changed `copilot/rag.py`, reason changed `copilot/pipeline.py`, `predict.py`, `eval.py`.
- **`docs/demo-first-proposals` vs `exp/reason-strategies`:** both add `docs/AI-PROPOSAL-GUIDE.md` (add/add conflict) and edit `AGENTS.md`, `STATUS.md`, `TODO.md`. Keep the newer guide from `exp/reason-strategies` (`4c67d3a` "restore proposal guide and require direct critical responses").

### Recommended order

1. **Redesign owner (UI, `ui/kangaroo-studio`):** finish and commit the working-tree redesign on `exp/ml-tutor` (or `git stash`, create `ui/kangaroo-studio-final` from `exp/ml-tutor`, `git stash pop`, commit). Run `python3 -m unittest discover -s student_app` and the browser flow first. The ML owner commits these three docs in a separate commit so the two changes can be reviewed apart.
2. **ML owner (`exp/ml-tutor`):** merge that branch into `main` again. Expect conflicts only in `docs/STATUS.md` and `docs/TODO.md`; keep both sides' entries (the redesign lines and `main`'s T-083 lines). Re-run the student-app tests on `main`.
3. **Reason owner (`exp/reason-strategies`):** merge into `main` with `REASON_STEPS=letter` (baseline behaviour unchanged), renumber decisions, keep both `config.env` blocks. Then run the contract check on the board (section c, step 9) **before** anything else touches `main`. If the board is not reachable in time, skip this merge: `main` already ships the safe baseline and the Reason results can be quoted from the branch.
4. **Docs owner:** `docs/demo-first-proposals` last, or not at all: its guide is superseded by the one on `exp/reason-strategies` and its STATUS/TODO lines are outdated. Cherry-pick only what is still true.
5. **Delete merged pointers** after the team confirms nobody has local unpushed work on them: `ui/kangaroo-studio`, `ui/thinking-steps`, `ui/student-practice` (all contained in `main`).
6. **Repo owner:** add `LICENSE`, rewritten README, tag `submission-2026-11-15`, make public.

Owners above are roles. Suggested from the commit history (confirm in the team chat): ML and docs = joancardonall; UI redesign = liamotal01; repository settings = berta-rov (owner of the GitHub remote).

## (e) Risks

| Risk | Likelihood / impact | Mitigation |
| --- | --- | --- |
| **Board unreachable** (Wi-Fi changed IP, SSH refused, venue network blocks SSH) | Medium / high: no deploy, no demo | `adb shell` over USB (README step 0.4); deploy over USB with `deploy_student.py --serial`; find the IP in App Lab or `hostname -I`. If the board cannot be updated, demo the release already installed on it (verified 2026-11-14) and say which features are not on it. |
| **Model servers down** (`math-llm` or `math-embed`) | Medium / high for `predict.py` (all `D`, status error), low for the tutor | `sudo systemctl restart math-llm math-embed`, `journalctl -u math-llm -n 50`, `pgrep -a llama-server` for a duplicate on the same port. The tutor still serves stored hints, steps, signatures and generated content without the model (STUDENT_DEPLOYMENT: "Model warming/unavailability does not prevent opening the application and its stored guidance"). |
| **RAM** (App Lab + both models + tutor + an embedding job) | Low / high | Measured minimum MemAvailable 2697 MiB with LLM 1058.7 MiB RSS and the tutor under 32 MiB (EXPERIMENTS, T-088). Do not run `build_index.py`, `embed_problems.py --port 8082` and a demo at the same time. Check `free -m` before the pitch. If `journalctl -k` shows OOM, stop hand-started servers (`pkill llama-server`) and restart services. |
| **Embeddings mismatch fp32 vs Q8** | Certain if step c4 is skipped / low | All ML numbers in EXPERIMENTS come from laptop fp32 bge-small; the board serves the Q8 GGUF. Board code only reads precomputed artifacts, so the app is consistent either way; only `ALIGN_CATALAN=1` RAG would mix spaces (it is off by default). Say "laptop fp32" in the pitch, or regenerate (step c4) and add new EXPERIMENTS rows. |
| **Generated content not reviewed by an educator** | Certain / medium (credibility) | Every item passed automatic checks twice (laptop verifier, board re-verification: leak, language, word limits). Label it "model-written, verified automatically, educator review pending" in pitch, README and UI provenance. Pick demo problems whose content the team has read. Never claim pedagogical validity. |
| **Signature wording** (agent spot check 11/30 plausible) | Medium / medium | Messages say "could come from", one sentence, never the answer. A teammate repeats the 30-item check before quoting a precision figure (T-108). |
| **Licence of M3Kang-derived files** | Low / severe (cannot be undone once public) | Never commit or publish `data/train.jsonl`, `val.jsonl`, `data/images/`, `*.db`, `data/ml/*` (signatures, difficulty table, map, Procrustes, generated steps, solutions, explanations, skill tags) or `data/teaching_annotations*.json`. `.gitignore` covers `data/*`; run the three checks in (b) before making the repo public. No problem text or screenshots of problems in README, slides or Project Hub unless the dataset card allows it. Problem text was sent to the organisers' hosted API for generation: confirm with organisers that this is within the terms they intended. |
| **Map step links do not open the problem** | Certain / low | `map.js` links each path step to `/?problem=<key>`, but `app.js` does not read the `problem` parameter (checked at 02:15). In the demo, read the path aloud and do not click the step links, or the UI owner adds the parameter handling. |
| **Missing images in the new bundle** | Certain on this Mac / medium | Build the bundle on the PC that holds the 170 restored images, or restrict the demo to text problems. |
| **Hidden-test run differs from our check** | Unknown | Confirm with organisers which checkout, branch and command they run; leave the services enabled at boot and `main` on the board checked out at the tag. |
| **Live demo fails on stage** | Low / high | Recorded backup video (T-072), see [DEMO-SCRIPT.md](DEMO-SCRIPT.md). |

## (f) Time plan, 15-minute blocks (assumes hand-in at 10:00; confirm)

| Time | Who | Block |
| --- | --- | --- |
| 07:30–07:45 | All | Confirm deadline, submission channel and pitch slot with organisers. Read this file. |
| 07:45–08:00 | Board | Section c steps 1–2: connect, health, update the board checkout. |
| 07:45–08:00 | UI | Commit the redesign; tests and one browser pass. |
| 08:00–08:15 | ML | Merge plan step 2 (redesign + docs into `main`); laptop tests on `main`. |
| 08:00–08:15 | Board | Start `build_index.py` (step 3) only if steps 4 will run; otherwise skip. |
| 08:15–08:30 | ML | Generated content for the demo ids (step 5); build bundle (step 6). |
| 08:30–08:45 | Board | Deploy bundle, tests with `python3 -S`, restart services, `free -m` (steps 6–8). |
| 08:45–09:00 | Reason | Merge `exp/reason-strategies` (or decide to skip); contract check on the board (step 9). Freeze `main`. |
| 08:45–09:00 | Docs | README rewrite (T-074) from PITCH numbers; add `LICENSE`. |
| 09:00–09:15 | Docs | Project Hub page (T-075): text, architecture image, link to repo. |
| 09:00–09:15 | Demo | Wi-Fi off; demo rehearsal 1 with timer; fix the script, not the code. |
| 09:15–09:30 | Demo | Record the backup video; pitch rehearsal 1 and 2 with timer. |
| 09:30–09:45 | Repo owner | Checklist (b): M3Kang checks, tag, make public, clean clone. |
| 09:45–10:00 | All | Send both links, screenshot the confirmation, board left powered with services enabled. |

If the deadline is earlier, drop in this order: Q8 regeneration (c4), `build_index.py` (c3), the Reason merge, the Project Hub polish. Never drop the M3Kang check, the contract check or the backup video.
