# Demo script (90 seconds, live on the board)

> Runs inside the pitch, [PITCH.md](PITCH.md) 0:20–1:50. Board Wi-Fi **off**, services started at boot, the page opened over USB. Rehearse twice with a timer (T-072). No M3Kang problem text or answer appears in this file on purpose (research-only licence): print the crib below on the laptop and keep it on paper.

## The problem

**Primary: `lvl-0_2019_1`, Catalan row** (`lvl-0_2019_1 · cat · text` in the problem picker). Why this one:

- A real level-0 Kangaroo training problem with text options (`text_only`), so no diagram is needed and missing images do not matter.
- It is on the problem map (training ids only), has a generated skill tag (`data/ml/skills_generated.json`), difficulty `b = 0.0` (observed, 3 points).
- It has two explained distractors in `data/ml/signatures.json`, one of them `sum` with `answer_op = difference`, so the wrong-answer message is the clearest kind: "Aquest nombre podria sortir de sumar … i …. El problema demana restar un nombre d'un altre." It does not contain the correct value or letter (checked with `copilot/misconceptions.py` at 02:15).
- It is Kangaroo-themed, short, and readable aloud in five seconds.

**Backup problem:** `lvl-0_2019_19` (level 0, text options, explained `half` and off-by-one distractors, `answer_op = difference`). **Fallback without M3Kang data:** `sample-4` in Catalan with the samples server (see "If things go wrong").

**Crib (run on the laptop, never commit the output):**
```bash
python3 - <<'PY'
import json
sig = json.load(open('data/ml/signatures.json'))['problems']
for pid in ('lvl-0_2019_1', 'lvl-0_2019_19'):
    row = next(json.loads(l) for l in open('data/train.jsonl') if json.loads(l)['id'] == pid and json.loads(l)['language'] == 'cat')
    print(pid, 'correct:', row['label'], '| explained wrong letters:',
          {k: v['op'] for k, v in sig[pid]['distractors'].items()})
PY
```
For the primary problem, the wrong letter to click is the one whose op is `sum`.

**Generated content check.** Generation finished at 05:31 and both demo ids have steps, explanations and solutions in `cat` and `eng` (verified on the laptop). Before rehearsal, confirm the files reached the board and that it served them (the startup log prints "Generated content: steps … served/… dropped"):
```bash
python3 - <<'PY'
import json, os
for f in ('data/ml/thinking_steps_generated.json', 'data/ml/slm_explanations.json', 'data/ml/solutions_generated.json'):
    if os.path.exists(f):
        d = json.load(open(f)); items = d.get('problems') or d.get('items') or {}
        print(f, [k for k in items if k.startswith(('lvl-0_2019_1|', 'lvl-0_2019_19|'))])
    else:
        print(f, 'MISSING')
PY
```
If the files did not ship, rebuild the bundle with `--with-data` (SUBMISSION.md step c6). Without generated steps, the problem uses the general steps of its tagged skill (if a tag was loaded) or the written-note gate; without a generated explanation, the template sentence from the signature still appears and hints start at the method rung. The demo still works; adjust the narration.

## Setup, 10 minutes before

1. Board powered, `systemctl status math-llm math-embed math-student --no-pager` all active, `free -m` noted.
2. Board Wi-Fi off. Laptop opens the tutor over USB: the installed Windows launcher opens it automatically, or `adb forward tcp:7011 tcp:7011` and open `http://127.0.0.1:7011`.
3. Nickname **`Kanga`**, fresh (never used on this board), so the notebook starts empty and the path starts from the demo problem. Prepare a second nickname **`Kanga2`** the same way as a spare.
4. In a second browser tab, have `http://127.0.0.1:7011/map?student=Kanga` loaded but not focused (it is 244 KB; loading it live wastes seconds).
5. Language filter set to **cat**. Open **Change problem**, select `lvl-0_2019_1 · cat · text` (type `lvl-0_2019_1` in the select to jump), but do not click **Open** yet.
6. Zoom the browser so the problem and three step choices fit on the projector without scrolling.
7. Crib paper at hand: correct letter, the `sum` letter, the expected goal on the map.

## Timeline

| Time | Click | Say |
| --- | --- | --- |
| 0:00–0:08 | Enter nickname `Kanga` → start. Click **Open ↗** on the prepared problem. | "This is Kanga. She opens a real Kangaroo problem, in Catalan." |
| 0:08–0:30 | Answer **Understand**, **Plan**, **Check**: click one wrong choice on Plan first, read the one-sentence feedback, then the right one. | "Before the choices appear, three thinking questions. Each choice gets instant feedback from Python; a wrong one can be retried. No model involved." |
| 0:30–0:45 | Answer choices appear. Click the **`sum` letter** from the crib → **Check my answer →**. Red signal and the misconception sentence. | "Now a wrong answer, on purpose. It doesn't just say wrong: that number could come from adding the two numbers; the problem needs a subtraction. It names the slip without giving the answer." |
| 0:45–0:58 | Click **Get a hint** (labelled "Help me think" if the redesign renamed it). The Socratic question shows. | "The first hint is a question. A large model wrote it before the event, Python checked it never contains the answer, so it is instant." |
| 0:58–1:08 | Click the correct letter → **Check my answer →**. Green signal. | "Now she gets it." |
| 1:08–1:20 | Open **My path**. Point at the recommendation reason: "Triat perquè tinguis prop d'un 70% de probabilitats d'encert: la teva puntuació és … i la dificultat d'aquest problema és …". | "Her next problem is chosen so she has about a 70% chance: her rating against the problem's difficulty." |
| 1:20–1:30 | Switch to the `/map?student=Kanga` tab, reload once. Her solved problem has a dark ring. Click a dot in a harder region of the same colour cluster. Read the path list on the right; **do not click the step links**. | "Difficulty comes from the position in the Kangaroo papers. Every training problem is on this map, in both languages. She picks a goal, and the tutor lays out stepping stones from what she has solved." |

Stop at 1:30. If you are ahead, show **My work** and the downloadable notebook for five seconds ("everything stays on the board").

## If things go wrong

- **The model server is slow or down.** Nothing in the timeline waits for the model. **Get a hint** shows the stored (generated or authored) hint immediately; the live SLM only re-selects in the background with a 25 s timeout. Say: "The small model works in the background; the student never waits for it." Do not wait for a model-selected hint on stage.
- **Steps do not appear** (no tag loaded for the problem): type a one-line note in the text box and click **Explore answer choices →**. Say: "Problems without thinking steps ask for a first idea instead."
- **No misconception sentence**: you clicked a letter without a signature. Click the other explained letter from the crib, or go on to the hint.
- **No 70% sentence**: the recommendation fell back to the level rule (difficulty file missing or no tagged candidate). Say "the next problem is picked by skill and level" and move on.
- **Map says not installed or is empty**: `data/ml/problem_map.json` did not ship. Skip to the closing line: "Every training problem is placed on a map in both languages; paths are computed on the board in milliseconds."
- **Map path link clicked by mistake**: the link opens the start page, not the problem (`app.js` does not read `?problem=` yet). Go back with the browser tab.
- **Whole app unreachable over USB**: `adb devices`, then `adb forward tcp:7011 tcp:7011`; if the board did not boot, switch to the backup video.
- **Fallback without M3Kang data (`sample-4`, Catalan):** start a separate samples server on the board, `python3 student_app/server.py --input data/sample_problems.jsonl --port 7012 --db /tmp/demo.db`, forward 7012, open `sample-4`. It has authored Catalan thinking steps. It shows a misconception sentence only if `signatures.json` was rebuilt with the samples (`python3 laptop/ml/signatures.py --input data/train.jsonl data/val.jsonl data/sample_problems.jsonl`); the map will not include samples.

## Backup plan: recorded video (T-072)

Record during the 09:15 block of [SUBMISSION.md](SUBMISSION.md), after rehearsal 1, on the real board with Wi-Fi off:

1. Screen recording of the laptop browser plus a phone shot of the board and cable (proves it runs on the board).
2. Follow the timeline exactly, 90 s, no cuts. Keep a second take.
3. Save it locally and on a USB stick; do not upload anywhere public if it shows M3Kang problem text (licence). For the README and Project Hub, record a separate clip using `sample-4` or crop the problem text out.
4. On stage, if the live demo fails at any point, say "here is the same flow recorded this morning on this board" and play from that point.
