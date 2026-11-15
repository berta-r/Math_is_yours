# Pitch (3 minutes)

> One story: every problem a student gets is chosen so they are likely but not certain to solve it (about 70%), and every goal is reached by small steps. We found the difficulty hidden in the Kangaroo papers, rate the student like a chess player, built a bilingual map of every training problem, and the tutor walks each student along it, makes them think before answering and explains their mistakes. The full chain with formulas and numbers is [ML.md](ML.md). The on-device SLM only does bounded jobs; all content a student reads was generated offline by a large model and verified in Python.
>
> Every number below is from [EXPERIMENTS.md](EXPERIMENTS.md) or [STATUS.md](STATUS.md), with its conditions in the "Numbers" table. Anything marked **pending** must be said as pending, or measured before the pitch. If the morning regenerates the artifacts with the board's Q8 embeddings (SUBMISSION.md, step c4), replace the three ML numbers with the new EXPERIMENTS rows.

## Spoken script (about 420 words)

Timing follows README step 14.5: problem 20 s, demo 90 s, numbers 40 s, lessons 30 s. The demo part is narrated while [DEMO-SCRIPT.md](DEMO-SCRIPT.md) runs.

**[0:00–0:20] The problem**

Maths results in Catalonia are falling, and a teacher cannot sit next to every child. An AI tutor only helps if it guides instead of answering, and if the child's data stays private. Ours runs entirely on this Arduino UNO Q. No internet, no cloud.

**[0:20–1:50] Demo**

This is Mia. She opens a real Kangaroo problem, in Catalan. Before the answer choices appear, she answers three short thinking questions: what is asked, what is the plan, how will I check. Each one gets instant feedback.

Now she answers wrong, on purpose. The tutor does not just say "wrong". It says: that number could come from adding the two numbers; the problem needs a subtraction. Kangaroo distractors are designed mistakes, and Python can reproduce many of them with one naive operation. So we can name the slip without giving the answer.

She asks for help. The first hint is a question, not a step. It was written beforehand by a large model and checked in Python so it never contains the answer, which is why it appears instantly.

She gets it right. Her next problem is chosen so she has about a 70% chance of success: her rating against the problem's difficulty.

Where does that difficulty come from? Kangaroo papers are ordered by points. A problem's position is a free difficulty label. We trained a model on it and placed every training problem on this map, in both languages. She picks a goal, and the tutor draws a path of stepping stones from what she has already solved.

**[1:50–2:30] Numbers**

On years the model never saw, difficulty is right 52% of the time across three point classes, against 40% for the majority class. Catalan-to-English retrieval goes from 50% to 72.5% at rank one with a single rotation learned from parallel problems. Error signatures explain 30% of numeric distractors. And the small model on the board? On Kangaroo answers it does not beat always choosing D, and as a live Socratic tutor only one question in five was useful, at 20 to 40 seconds each. So it only does bounded jobs, like choosing among verified hints.

**[2:30–3:00] What we learned**

Put the intelligence in the data and in Python, and keep the small model off the critical path. What is not validated yet: an educator still has to review the generated content, and we have no learning gains from real students. Our next step is a classroom pilot.

## Numbers and their conditions

| Spoken | Exact value | Conditions | Source |
| --- | --- | --- | --- |
| Difficulty 52% vs 40% | Gradient boosting 0.516 hold-out accuracy vs 0.395 majority; Spearman 0.435 with paper position; MAE 0.644 points | Target = points 3/4/5 from position within level-year paper; hold-out years 2023–2024, 215 rows; laptop fp32 bge-small embeddings | EXPERIMENTS, "Difficulty model (T-102)" |
| Retrieval 50% → 72.5% | cat→eng recall@1 0.501 → 0.725; recall@5 0.696 → 0.894 | Orthogonal Procrustes on 1398 training pairs, 349 held out, seed 42; overfits on training (0.97), quote held-out only | EXPERIMENTS, "Cross-lingual alignment (T-104)" |
| Every training problem on a map | 1466 problems (eng + cat rows), 5858 edges, 14 clusters, modularity 0.688, 244 KB | Deployed map built from training ids only; kNN k=5, Louvain and UMAP seed 42; first build on 1747 ids had 15 clusters | EXPERIMENTS "Problem map (T-106)"; `results/map-metrics.json` |
| Both languages land together | Catalan vector's nearest English neighbour in the twin's cluster 0.722 → 0.888 | 349 held-out ids, 1747-node build | EXPERIMENTS, T-106 |
| Signatures explain 30% | 981 / 3220 numeric distractors (30.5%); 402 (12.5%) excluding copied numbers and off-by-one | 1747 problems, 805 with all-numeric options; coincidence limit 0.6. Agent spot check: 11/30 plausible. **Human check pending** | EXPERIMENTS, "Error signatures (T-108)" |
| Small model does not beat always-D | Board: 11/30 = 36.7% vs always-D 43.3%, mean 10.4 s, worst 25.6 s, 0 over 60 s | UNO Q, 30 English validation problems, development release, not main-branch validation | EXPERIMENTS `unoq-wifi-baseline`; STATUS |
| (if asked) on more problems | Laptop baseline 20.1% ±0.7 vs always-D 24.7% on 3494 problems; no strategy beats chance (logprobs, program of thought, RAG, Qwen3.5 2B) | Same GGUF and llama.cpp commit on the laptop; on branch `exp/reason-strategies`, not yet in `main` | `exp/reason-strategies` EXPERIMENTS, DECISIONS D-006 |
| 1 in 5 useful, 20–40 s | Socratic question 1/5 useful (4/5 restated, 1/5 leaked); strategy label 7/12 | Board GGUF on the laptop, temperature 0, seed 42; board time **estimated** from tokens at 11 / 5.5 tok/s (≈ 19 s and ≈ 38 s) | EXPERIMENTS "Live SLM probes"; DECISIONS D-013 |
| Bounded SLM job | Live hint selection 10.1–23.0 s (4 requests); stored guidance 16–21 ms | UNO Q over Wi-Fi, 2026-11-14 release (before the ML bundle) | EXPERIMENTS T-088 |
| Fits in the board | Minimum MemAvailable 2697 MiB; LLM RSS 1058.7 MiB; tutor service 18.1 MiB peak | 206 samples during contract/eval/repeat, 2026-11-14 release | EXPERIMENTS T-088 |
| Organisers' baseline | 22.5% (9/40) | 40 English text-only problems | README 11.3 |
| Tested | 105 student-app tests pass (1 skipped) | Laptop, `exp/ml-tutor`, 2026-11-15 02:15 | `python3 -m unittest discover -s student_app` |

**Pending (say so if asked, do not imply otherwise):** board timing and RAM of the new ML bundle (T-110), `/api/recommendation` latency on the board, Q8 regeneration of the ML artifacts, `ALIGN_CATALAN` measured with `eval.py` on the board, educator review of generated content and of the 51 tags, human check of the signatures, real-student process metrics (T-093), any learning gain, fitted BKT parameters (they are unfitted defaults), the LED matrix (not implemented).

## Slides (9)

| # | Title | Three bullets | Figure / number |
| --- | --- | --- | --- |
| 1 | Math Is Yours: a maths tutor that lives on the board | Offline on an Arduino UNO Q 4 GB · Catalan and English · Teaches, does not answer | Photo of the board with the tutor open on the laptop over USB |
| 2 | Guide the reasoning, keep the data | PISA maths falling in Catalonia · A tutor must not do the homework · Student records stay on the board (SQLite) | "0 network calls at runtime" |
| 3 | The difficulty hidden in the papers | Kangaroo papers are ordered by points: thirds = 3/4/5 · Position is a free label for 1747 problems · Gradient boosting on embedding + text features | 0.516 vs 0.395 majority, Spearman 0.435 (years 2023–24 held out) |
| 4 | One map, two languages | 1466 training problems, kNN graph, 14 clusters · One 384×384 rotation aligns Catalan to English · Paths = cheapest stepping stones (Dijkstra) | Map screenshot; recall@1 0.50 → 0.725 (held out) |
| 5 | Think before you answer | Three steps: Understand · Plan · Check · Instant feedback, retries allowed, no model needed · Next problem at about 70% predicted success (Elo beside BKT) | Screenshot of the step rail and the 70% sentence |
| 6 | Mistakes have a name | Distractors are designed slips · Python reproduces them with one naive operation · "Could come from…", never the answer | 981 / 3220 explained (30.5%); spot check 11/30 plausible, human check pending |
| 7 | Who does what | Large model, offline: steps, solutions, explanations, skill tags · Python verifies twice: laptop and board (leak, language, length) · On-board SLM: picks among verified hints, in the background | Diagram laptop → JSON → board; stored hint 16–21 ms vs live selection 10–23 s |
| 8 | Reason, honestly | `predict.py`: one letter, ≤ 60 s, deterministic · Board 11/30 vs always-D 13/30 · Logprobs, program of thought, RAG and a 2B model: none beats chance | Table: baseline 22.5% (organisers), 36.7% (board, n=30), 20.1% vs 24.7% (laptop, n=3494, branch) |
| 9 | What is not validated, and what's next | Educator review of generated content · Real-student metrics (T-093) and a classroom pilot · Board timing of the new bundle; LED matrix | "Model-written, verified automatically, educator review pending" |

## Anticipated jury questions

- **Why not fine-tune the model?** The binding limit on the board is time, not knowledge: about 11 tokens/s read and 5–6 written. A fine-tuned 0.8B still needs tens of seconds per explanation, and a 2B model was still at chance on Kangaroo answers. Training on the laptop and shipping small JSON artifacts (a tree, a rotation matrix, a graph) gives instant, deterministic, inspectable behaviour.
- **Why BKT and Elo together?** They answer different questions. BKT tracks whether a skill is demonstrated, with conservative rules: only the first unaided answer counts, at least three observations and two successes. Elo gives a single ability to compare with each problem's difficulty, so we can aim at about 70% success. Neither is fitted to real students yet; the parameters are documented defaults.
- **How is it deterministic?** Grading uses the dataset key. Selection, Elo, BKT, paths and signature messages are pure Python. Generated content is fixed files. Model calls use temperature 0 and seed 42, and the model only picks an index among stored hints. `predict.py` repeated the same five answers on the board.
- **What runs where?** Laptop, before the event: data preparation, embeddings, difficulty model, alignment, map, signatures, large-model content generation and verification. Board, at runtime: standard-library Python app and SQLite, the content checks again, llama.cpp with Qwen3.5 0.8B (hints, `predict.py`) and bge-small (embeddings). The PC only renders the page over USB.
- **Licence?** M3Kang is research-use only. No problem text, image, derived table or generated content is in the repository or the write-up; they live in ignored `data/` on the laptop and board. Our code is MIT (LICENSE to be added before publication).
- **What exactly does the SLM do?** It chooses one of the permitted, already verified hints for the student's note, constrained by a grammar to an index, with a 25-second timeout and the stored hint shown immediately. It also answers `predict.py`. It never writes text a student reads.
- **Who wrote the hints and thinking steps?** A large open model through the organisers' hosted API, offline, before the event. Python rejected anything that leaked the answer, was in the wrong language or too long, and the board checks again at start. An educator has not reviewed them yet.
- **Does it improve learning?** We do not know yet. We measure process indicators (first-try step rate, accuracy after steps right vs missed), but have no real-student data. That is the next step.
- **What is not validated?** Educator review, real students, board timing of the new bundle, human check of the signatures, Q8 versus fp32 embedding differences, the LED matrix.
- **Why is the reasoning score so low?** Under the one-letter grammar the 0.8B picks a position, not an answer: on trivial additions it chose the right letter 19% of the time but wrote the right number 82% of the time (`exp/reason-strategies` error notes). We report that as a measured negative result and kept the safe baseline.
