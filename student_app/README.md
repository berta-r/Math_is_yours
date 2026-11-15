# Offline student app

M3Kang practice with a shared skill graph, separate student estimates, diagnostics,
explainable recommendations and scheduled reviews. Python's standard library is
the only runtime dependency. The page, problems, images and progress work offline.

## Run on your PC

In a terminal at the repository root:

```powershell
python student_app/server.py
```

Open **http://127.0.0.1:7011**. Enter a nickname and choose **Open my notebook**. The Kangaroo Studio navigation separates Solve, My path and My work while keeping your exercise in progress when you switch views.
Use `py` instead of `python` if necessary. Leave the terminal running; **Ctrl+C**
stops it. Restart with the same command after code or annotation changes. If the
port is occupied, stop the earlier server; Windows may need a short wait to release
a recently closed connection. `--port 7012` selects another port if needed.

The app loads `data/train.jsonl` if present, otherwise five original sample
problems. It adds **30 original diagnostic questions across 10 skills**. Use
`--input data/sample_problems.jsonl` for a demo without downloading M3Kang.
Do not open `assets/index.html` directly: the page needs the Python server.

Your history is in `student_app/progress.db`. Reuse the same nickname after a
restart. Nicknames select local profiles; there are no passwords. Existing
prototype attempts are retained, while richer skill estimates start with new
attempts. Use `--db path/to/practice.db` for a separate demo database.

## Try the teaching flow

1. Open a new notebook. A short diagnostic is suggested, with a reason.
2. Choose **Quick check: Division · 1 · eng** from the problem list and open it.
   Answer three short thinking steps (Understand · Plan · Check). Each choice gets
   immediate feedback with a one-sentence reason; a wrong choice can be retried.
   The answer choices appear after the last step. **Add a note (optional)** still
   saves a written idea. Problems without reviewed skills have no steps: write a
   first idea, then choose **Explore answer choices**.
3. Submit a wrong answer. Only division receives that observation; other
   nodes remain unknown. The route can first check addition/subtraction, then
   multiplication, before returning to division, depending on existing evidence.
4. Follow **Start next step**. Answer independent checks to build evidence, or
   request a hint. Each new recommendation explains the skill it targets.
5. Drag, zoom or search the connected map. Select a skill to inspect its evidence,
   practise it freely or build a path toward it. Arrows show authored supporting
   prerequisites; dashed links show related ideas. A highlighted route uses
   strengths and missing evidence to suggest a progression.
6. Download the notebook as Markdown. Attempts, hints, first answers, diagnostic
   outcomes, language variants and subsequent review dates remain in SQLite.

The map distinguishes **not assessed**, **developing**, **demonstrated
independently** and **due for review**. The provisional model needs at least three
distinct independent observations, two successes and estimated probability >= 0.8
before showing demonstrated. A wrong unaided first answer is evidence too.

Hints, solutions, revealed answers, retries and previously exposed translations
cannot inflate the estimate. A multi-skill question without a reviewed primary
assessment skill is logged, then diagnosed separately. Estimates never cascade
along graph edges. Review dates use provisional 1/3/7-day intervals; becoming
overdue does not lower the mastery estimate. See [the model and curriculum
documentation](../knowledge/README.md) for exact rules and authoring instructions.

## M3Kang text and images

The default view displays text and the original image together. The display menu
also supports text only and image only. Enlarge an image and return with **Close**,
**Escape**, or a click outside the viewer; the selected answer stays in place.
The language filter selects available dataset variants. If a diagnostic has no
matching translation, the recommendation explicitly says it is in English.

Prepare JSONL and images using [README step 9](../README.md#step-9-prepare-m3kang-on-your-laptop),
including `--save-images`. For a small starter set on a Windows laptop:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install huggingface_hub pyarrow
$env:PYTHONUTF8 = '1'
$env:HF_HOME = Join-Path (Get-Location) 'data/.hf-cache'
.venv/Scripts/python.exe laptop/prepare_m3kang.py --languages eng,cat --save-images --no-ocr --limit 60
```

Preparation needs internet; practice does not. The row limit follows source order
and may contain only one requested language. Images are named `<id>_<language>.png`.
Image-only rows may omit text and options. A missing label makes a problem
view-only. No runtime uploads, raw Parquet or remote images are required.

```powershell
python student_app/server.py --input data/train.jsonl --images data/images --annotations data/teaching_annotations.json
```

Multiple JSONL paths may follow `--input`. Keep validation for official evaluation.
All generated M3Kang files, extracted images, annotations and clusters stay under
ignored `data/`. Copy them separately when deploying to the board.

To extract answer text and picture-choice previews from existing images:

```powershell
.venv/Scripts/python.exe -m pip install rapidocr_onnxruntime
.venv/Scripts/python.exe laptop/read_options.py --input data/train.jsonl data/val.jsonl
```

OCR and crops can be imperfect; the original remains available for comparison.
The current local starter set has 170 training exercises: 101 complete text-choice
sets, 10 complete picture-choice sets, and 59 requiring the original image.
51 have prototype topic annotations reviewed from the question text by Codex;
educator validation remains pending. Most real questions have general skill hints
or no hint, rather than an authored solution. Diagnostics have three stored hints
and an explanation. The source/scope is shown beside the guidance.

**Check my answer** and **Review the answer** use the supplied official label.
They do not claim to solve an unseen picture. Keys are absent from public problem
responses; explicitly revealing one marks the question as assisted. The server
requires a written reflection before accepting an answer. Review and solutions
unlock after solving, or after two attempts plus a hint when hints are available.
Original images may already contain choice text; the gate controls submitting an
answer, not the pixels of the preserved source. Reflections are saved with attempts
and included in reports, but are not graded as mathematical explanations.

## Optional local SLM

```powershell
python student_app/server.py --local-tutor
```

This uses `127.0.0.1:<LLM_PORT>` from `config.env`, temperature 0, seed 42 and at
most 10 output tokens. The tutor selects one of the permitted authored hints;
it cannot replace the answer key or generate unverified mathematical text. Each
click immediately shows the stored hint. One background worker handles at most
two pending requests, with a 25-second request timeout and stored fallback.
Changing problem or requesting newer feedback prevents old jobs overwriting it.
The latest written thought (bounded to 160 characters for the prompt) also informs
hint selection. Live model selection and latency still need testing on the Arduino.

The map currently uses a small, explicitly labelled keyword-vector baseline.
The [graph preparation tool](../knowledge/GRAPH.md) can replace it with local model
embeddings without changing the runtime. Similarity never creates prerequisites
or directly changes mastery. Layout computation runs in the student's browser.

## Run on the Arduino over USB

For the complete prepared workflow—versioned upload, automatic board service,
persistent board database, Windows USB detection, automatic browser opening and
uninstall—follow [USB deployment](../board/STUDENT_DEPLOYMENT.md). Install the PC
helper once per computer; an arbitrary USB device cannot supply universal autorun.
No board or Windows startup configuration has been changed during implementation;
hardware testing is deferred at the user's request.

Copy this branch's app, `copilot/` and `knowledge/`, plus the prepared local data,
to the board repository. On its **Linux side**:

```bash
python3 student_app/server.py --local-tutor
```

In a **PC terminal**:

```powershell
adb devices
adb forward tcp:7011 tcp:7011
```

Open **http://127.0.0.1:7011** on the PC. Stop the PC's own server first when using
that port for forwarding. The board then owns the database, graph and local SLM;
the PC renders the browser page. The app has been tested on a physical UNO Q over
Wi-Fi and USB. Physical reconnect automatically reopens the page with the
temporary PC watcher running, and saved progress survives board reboot. That
earlier demonstration required existing Python/ADB. The requested standalone
Windows setup now bundles those tools and is installed on this PC with a login
entry. The registered command was tested, but an actual Windows login and fresh
PC remain unverified. The Arduino now offers a verified read-only **MATHTUTOR**
drive containing **START.EXE** for first-time student installation. The installed
watcher reopened the tutor after USB reconfiguration and after a full board
shutdown/replug. The drive returned and saved progress survived; both were
confirmed on this PC. See the deployment instructions below. For Wi-Fi,
forward PC port 7012 to board loopback port 7011 and open
**http://127.0.0.1:7012**; see [deployment instructions](../board/STUDENT_DEPLOYMENT.md).
An App Lab/Bridge adapter for the built-in LED matrix remains future
work; see [hardware UI guidance](../.skills/unoq-hardware-ui/SKILL.md).

## Verification

```powershell
python -m unittest discover -s student_app -v
python laptop/eval_teaching.py
```

39 application/graph tests cover Bayesian updates, migration, concurrent submissions, multilingual
exposure, assistance, multi-skill attribution, prerequisites, due reviews,
transfer, profile isolation, image handling, deterministic clustering, explicit
review/export and model-output fallback. Browser checks in installed Chrome at
1360x1000 and 390x844 cover the practice flow, graph selection, report download,
image dismissal and display modes, with no JavaScript errors or external requests.
Twelve additional deployment/launcher checks cover USB readiness, reconnects, occupied
ports, archive boundaries and service rendering, including real systemd validation
on Linux (that check is skipped on Windows). All 51 checks pass on the UNO Q.
Connected-map browser checks at
1440x1100 and 390x844 cover reflection and review gates, search, focus, zoom,
dragging and goal selection. Real touch hardware remains untested.

The earlier simulation compares the original selector with random and correct-harder
selection on original fixtures; it does not measure the new path-first API policy.
Its metrics are proxies under fixed synthetic
abilities, not evidence of improved learning. Results and limitations are recorded
in [EXPERIMENTS](../docs/EXPERIMENTS.md). Physical-board browser checks also cover
combined text/images, reflection, goal alignment, dragging and image dismissal
with no page JavaScript errors or external page requests. Live hint selection
took 20.5–23.0 seconds for two requests, while stored guidance arrived in about
20 ms. These are two samples, not a latency distribution. Educator review, real
student outcomes and delayed assessments remain unmeasured. The official solver
is unchanged; board benchmark conditions are recorded in EXPERIMENTS.
