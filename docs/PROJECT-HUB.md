# Arduino Project Hub write-up (draft)

> Text to paste into a new project on <https://projecthub.arduino.cc/>, one section per Project Hub section. Replace every `[PHOTO: …]` with a photo or screenshot the team took. Do not upload M3Kang problem text, images or screenshots that show a problem: crop them out, or use the original `sample-*` problems in `data/sample_problems.jsonl`. Every number comes from [EXPERIMENTS.md](EXPERIMENTS.md) or [STATUS.md](STATUS.md); keep the conditions when you edit. Code link: <https://github.com/berta-r/datathon_xusigrupoo>.

**Title:** Math Is Yours: an offline maths tutor on the Arduino UNO Q

**One-line summary:** A maths tutor that runs entirely on an Arduino UNO Q 4 GB: thinking steps before the answer, feedback that names the likely slip, and a map of Kangaroo problems with a path for each student.

---

## Introduction

Maths results in Catalonia are falling in PISA, and a teacher cannot sit next to every student. An AI tutor helps only if it guides the reasoning instead of giving the answer, and only if the student's data stays private.

Math Is Yours runs entirely on an Arduino UNO Q 4 GB. It needs no internet while a student uses it. The student's record stays in a SQLite file on the board. A PC or laptop only shows the web page, over the USB cable.

The student opens a Kangaroo competition problem in English or Catalan. Before the answer choices appear, they answer three short questions: what is asked, what is the plan, how will I check. After a wrong answer, the tutor says which slip could give that number, without giving the answer. The next problem is picked so the student has about a 70% chance of success. A map shows the training problems and a path of gradually harder ones.

We built it for the Datathon FME 2026, Qualcomm challenge "Math on the Edge", with the M3Kang dataset (Torres-Camps et al., 2026, [arXiv:2601.16218](https://arxiv.org/abs/2601.16218)).

[PHOTO: the UNO Q connected to a laptop by USB, with the tutor open in the browser]

[VIDEO: 90-second demo recorded on the board with Wi-Fi off; problem text cropped or a sample problem used]

## Components and apps

Hardware:

- Arduino UNO Q 4 GB
- USB-C data cable and a PC or laptop with a browser

Software and models:

- Arduino App Lab (first board setup and the board's IP address)
- [llama.cpp](https://github.com/ggml-org/llama.cpp), commit `2cbe0ec429b849a88664e0f62388fc92a5abd699`, built on the board
- Qwen3.5 0.8B, Q8_0 GGUF (language model, port 8081)
- bge-small-en-v1.5, Q8_0 GGUF (embedding model, port 8082)
- Python 3 standard library on the board (no `pip`)
- On the laptop only: Python with scikit-learn, NetworkX, umap-learn and sentence-transformers for the ML artifacts, and the organisers' hosted API for offline content generation
- [ADB](https://developer.android.com/tools/adb) to reach the board over USB (App Lab ships one)

Dataset: [M3Kang](https://huggingface.co/datasets/qualcomm/M3Kang), research use only. We do not redistribute it.

## Architecture

```
            LAPTOP (before use)                            ARDUINO UNO Q, Linux side (offline)
 ┌──────────────────────────────────────┐        ┌──────────────────────────────────────────────┐
 │ prepare_m3kang.py → train/val JSONL  │        │ math-student  student_app/server.py :7011    │
 │ laptop/ml: embeddings, difficulty,   │ bundle │   copilot/*.py (standard library) + SQLite   │
 │   alignment, map, error signatures   │ ─────► │   difficulty · map · signatures · BKT/Elo    │
 │ generate_content.py + verify_content │ USB or │   content checks run again on start          │
 │   (large model, organisers' API)     │ Wi-Fi  │        │ hint choice only (optional)         │
 └──────────────────────────────────────┘        │        ▼                                     │
                                                 │ math-llm    llama-server :8081 Qwen3.5 0.8B  │
   PC browser ◄── adb forward / ssh tunnel ────► │ math-embed  llama-server :8082 bge-small    │
                                                 │ predict.py (official one-letter solver)      │
                                                 └──────────────────────────────────────────────┘
                                                   Microcontroller + LED matrix: not implemented
```

The board's Linux side runs three services. `math-llm` and `math-embed` are the organisers' model servers on `127.0.0.1`. `math-student` is our tutor: a standard-library Python web server on port 7011 with a SQLite database in `/var/lib/math-student/`.

The heavy work happens on the laptop, before use. Small models are trained there and exported as JSON files: a difficulty model, a 384×384 rotation that aligns Catalan embeddings with English ones, a problem map, and error signatures for numeric distractors. A large model writes the thinking steps, hints, solutions and explanations through the organisers' API. Python rejects any item that leaks the answer, is in the wrong language or is too long. The board checks every item again when it starts.

The small model on the board never writes text a student reads. In the tutor it only chooses among stored, verified hints, in the background, and the stored hint is shown at once. It also answers `predict.py`, the challenge's official one-letter solver.

How M3Kang is used: Kangaroo papers go from 3-point to 5-point problems, so a problem's position is a free difficulty label. The English/Catalan pairs train the alignment. The numeric distractors give the error signatures. The tutor serves the training split only. All M3Kang data and everything derived from it stay in git-ignored folders.

The microcontroller and the 8×13 LED matrix are not used yet.

[PHOTO: architecture diagram exported as an image]

## Step 1: Set up the board with the organisers' guide

Follow steps 0 to 12 of the organisers' guide, kept in our repository as [docs/DATATHON-GUIDE.md](https://github.com/berta-r/datathon_xusigrupoo/blob/main/docs/DATATHON-GUIDE.md). They connect the board, build llama.cpp, download and verify both models, install them as services and prepare M3Kang on the laptop.

On the board, check both model services:

```bash
systemctl status math-llm math-embed --no-pager
```

You should see both `active (running)`.

On the laptop, step 9 must include images:

```bash
python3 laptop/prepare_m3kang.py --languages eng,cat --save-images
```

It ends with `train eng: 1466` and `val eng: 281`.

## Step 2: Get our code

On the laptop and on the board:

```bash
git clone https://github.com/berta-r/datathon_xusigrupoo.git
cd datathon_xusigrupoo
```

Copy the prepared `data/train.jsonl`, `data/val.jsonl` and `data/images/` into `data/` on the laptop.

On the board, check the official entry point:

```bash
python3 predict.py --input data/sample_problems.jsonl --output results/check.csv && cat results/check.csv
```

You should see five rows, each with a letter A–E and status `ok`.

## Step 3: Try the tutor on the laptop

```bash
python3 student_app/server.py --input data/sample_problems.jsonl
```

Open `http://127.0.0.1:7011`, type a nickname and start. You should see five sample problems and 30 diagnostic questions. Press Ctrl+C to stop.

[PHOTO: the start page]

## Step 4: Build the ML artifacts on the laptop

This step is optional: without these files the tutor uses simpler rules. Create an environment and run the scripts in order:

```bash
python3 -m venv .venv-ml
.venv-ml/bin/pip install numpy scipy scikit-learn networkx umap-learn sentence-transformers
.venv-ml/bin/python laptop/ml/embed_problems.py --local
.venv-ml/bin/python laptop/ml/features.py
.venv-ml/bin/python laptop/ml/difficulty.py train
.venv-ml/bin/python laptop/ml/align.py
.venv-ml/bin/python laptop/ml/build_map.py --input data/train.jsonl
python3 laptop/ml/signatures.py
```

Each script prints its metrics. `difficulty.py` prints hold-out accuracy, `align.py` prints `recall@1 … -> …`, and `build_map.py` prints `nodes 1466`, the cluster sizes and the modularity. The files land in `data/ml/`, which git ignores.

## Step 5: Generate the teaching content

```bash
.venv-ml/bin/python laptop/ml/generate_content.py --api-base https://api.helmcode.com/v1 --kind all --resume
```

It needs an API key in `HELMCODE_API_KEY` and sends problem text to that API. It prints how many items each kind accepted and rejected. Without a key, `--port 8081` uses the board's own model through a forwarded port, which is slower and weaker. The content is model-written and checked automatically; an educator has not reviewed it yet.

## Step 6: Deploy to the board

Build the bundle:

```bash
python3 laptop/deploy_student.py --with-data
```

It prints the file count, the SHA-256 and the number of training rows. Then install it over USB:

```bash
python3 laptop/usb_launcher.py devices
python3 laptop/deploy_student.py --serial <BOARD_SERIAL> --with-data --install --local-tutor
```

Type the board's sudo password yourself when asked. The installer creates the `math-student` service, which starts at boot and keeps progress in `/var/lib/math-student/progress.db`. Wi-Fi deployment with `scp` is in the repository README.

## Step 7: Check the board

```bash
systemctl status math-llm math-embed math-student --no-pager
curl -s http://127.0.0.1:7011/api/health; echo
free -m
```

You should see three active services and JSON with `"status": "ready"`.

## Step 8: Open the tutor over USB

Turn the board's Wi-Fi off. On the PC:

```bash
adb forward tcp:7011 tcp:7011
```

Open `http://127.0.0.1:7011`. Type a nickname, open a problem, answer the three thinking steps, then pick a letter. Try a wrong one to see the feedback. Open `http://127.0.0.1:7011/map?student=<nickname>` for the map, and click a problem to get a path.

[PHOTO: the thinking steps (Understand, Plan, Check) on a sample problem]

[PHOTO: the feedback after a wrong answer, on a sample problem]

[PHOTO: the problem map with a path, without problem text]

## Results and error analysis

All our own reasoning results are on 30 problems, so treat them as indicative.

| What | Result | Conditions |
| --- | --- | --- |
| `predict.py` on the board | 36.7% (11/30), mean 10.4 s, worst 25.6 s, none over 60 s | 30 English validation problems, organisers' solver unchanged |
| Always answering D | 43.3% (13/30) | Same 30 problems |
| Organisers' baseline | 22.5% (9/40), mean 8.7 s | 40 English text-only problems |
| Difficulty model | 0.516 accuracy on 3/4/5 points vs 0.395 for the majority class | Hold-out years 2023–2024, 215 problems |
| Catalan→English alignment | recall@1 0.501 → 0.725 | 349 held-out problem pairs |
| Problem map | 1466 problems, 14 clusters | Training problems only, k=5 neighbours |
| Error signatures | 981 of 3220 numeric distractors explained (30.5%) | 805 problems with numeric options |
| Signature spot check | 11/30 plausible | Judged by an AI agent, not yet by a person |
| Small model as live Socratic tutor | 1/5 useful questions, about 19–38 s per turn (estimated) | Board model on the laptop, five sample problems |
| Live hint choice on the board | 10.1–23.0 s (4 requests); stored hint in 16–21 ms | UNO Q, Wi-Fi |
| Memory | At least 2697 MiB available with both models and the tutor | 206 samples during evaluation |

The small model scored below always-D, so we kept the official solver as it was. On the 30 problems it got 7/17 right when OCR had read the options as text and 4/13 when they were only in the picture; 7/20 at level 0 and 4/10 at level 1. It almost never chose C, which was the right answer 7 times. The full analysis by topic, language and level is still to do.

We have no measurements with real students, and no learning gain to claim. The difficulty, alignment and map numbers use laptop fp32 embeddings of the same bge-small model, not the board's Q8 version.

## What we learned, and what's next

What we learned:

- On this board, time is the limit: about 11 tokens per second to read and 5–6 to write. A 0.8B model needs 20–40 seconds for one useful sentence, and a child will not wait.
- Put the intelligence in the data and in Python. Small JSON files trained on the laptop (a tree ensemble, one rotation matrix, a graph) give instant, deterministic and inspectable behaviour on the board.
- Kangaroo papers carry hidden labels: the problem order gives difficulty, and the distractors are designed mistakes.
- Check every generated text with code before a student sees it, and check it again on the device.
- Report what did not work. Our reasoning score trails always-D, and we say so.

What's next:

- An educator reviews the generated content and the skill tags.
- Measure the full bundle on the board: memory and page latency.
- Regenerate the ML files with the board's own embeddings.
- Finish the error analysis by topic, language and level.
- A classroom pilot to measure the process indicators with real students.
- Use the UNO Q's LED matrix through App Lab and the Bridge.

Code, documentation and every measurement with its conditions: <https://github.com/berta-r/datathon_xusigrupoo>.

**Credits:** M3Kang (Qualcomm; Torres-Camps et al., 2026, arXiv:2601.16218; research use only), the organisers' template by Marc Pous, llama.cpp, Qwen3.5 0.8B, bge-small-en-v1.5, RapidOCR. Our code is MIT.

[TEAM: add the team members' names and photos]
