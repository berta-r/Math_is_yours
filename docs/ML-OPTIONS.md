# ML options for the math tutor

> Candidate improvements to the student experience that use the M3Kang dataset and
> classical ML elegantly, within the board's limits. Written 2026-11-14 as a
> decision menu; nothing here is implemented. Pick with D-0XX in [DECISIONS.md](DECISIONS.md).

## Constraints every option respects

- **Train on the laptop, infer on the board.** The board runs standard-library
  Python only. Every model below exports to JSON (tree as nested dicts, linear
  models as weight lists, graphs as edge lists) and runs as dot products, lookups
  or Dijkstra in pure Python. No scikit-learn on the board.
- **Embeddings exist already.** bge-small (384-d) runs on port 8082. `build_index.py`
  embeds the train set into SQLite. Everything that says "embedding" reuses that.
- **No student histories in M3Kang.** Anything that learns from students starts
  rule-based and is refitted once `learning_events`/`thinking_events` have data.
- **The 0.8B model stays off the critical path.** It is slow (5–6 tok/s) and a
  poor judge. ML replaces prompts; it does not add prompts.

## Signals hidden in the dataset (measured on the local 1747 English rows)

| Signal | Value | Why it matters |
| --- | --- | --- |
| Problem number prefix in the text (`"13. For 3 days…"`) | 1678 / 1747 rows | Kangaroo papers are ordered by points: first third 3 points, second 4, last 5. **Free difficulty labels** per level and year. |
| Level 0–7 and year 2007–2024 | all rows | Grade band plus a natural hold-out split by year. |
| Parallel English/Catalan pairs by id | 1747 / 1747 | A bilingual parallel corpus: bge-small is English-only, so alignment can be learned from the pairs. |
| All-numeric option sets | 669 / 1078 rows with options | Distractors are designed misconceptions; naive operations on the numbers in the text reproduce them. |
| Answer-letter prior | D 24.7%, C 21.8%, B 19.9%, E 17.6%, A 16.0% | Calibrates the model's letter bias (T-030) and makes guessing detectable. |

## Options, ranked by impact × feasibility × elegance

### 1. Difficulty model from paper position, then an Elo/IRT loop (⭐ recommended)

- **What:** predict each problem's points (3/4/5, derived from position within its
  level-year paper) and level from text features: bge embedding, length, number of
  numerals, has image, numeric spread of the options. Ordinal gradient-boosted trees
  or a small decision tree on the laptop; export the tree as JSON. The tree gives a
  continuous difficulty `b` for all 2932 rows, including ones with no prefix.
- **On the board:** each student gets an ability `θ` per skill (Elo update after each
  independent first attempt, K≈32 on a 0–1 probability). Selection targets
  `p(correct | θ, b) ≈ 0.7`, the "desirable difficulty" band, instead of today's
  level integer. BKT stays as the mastery state; Elo picks the next item.
- **Validation on the laptop:** hold out years 2023–2024; report Spearman between
  predicted and true position, and 3/4/5 accuracy versus a majority baseline.
- **Demo:** a difficulty dial. The student slides "challenge me" and sees the
  predicted success probability move; the tutor explains "chosen because you solve
  level-4 counting problems about 70% of the time".
- **Effort:** 1 day. Needs `build_index.py` to have run (T-012).

### 2. Problem map and stepping-stone paths over the embedding graph (⭐ recommended)

- **What:** the knowledge graph the team originally meant: nodes are the 1466
  canonical problems, edges are k-nearest neighbours by cosine (k=5) plus
  same-skill links; direction from easier to harder using option 1's `b`. On the
  laptop: Louvain/Leiden communities become topic clusters, UMAP gives 2-D
  coordinates. Export nodes, edges, cluster ids and coordinates as one JSON
  (≈300 KB).
- **On the board:** the student's solved problems light up on the map. To reach a
  goal problem (or skill), Dijkstra over the graph with edge cost = difficulty gap
  returns 3–5 stepping-stone problems. Pure Python, 1466 nodes, milliseconds.
- **Validation:** cluster purity against the 51 reviewed tags and the diagnostics;
  cross-lingual check that the Catalan twin of a problem lands in the same cluster.
- **Demo:** "To solve this level-6 problem, here is your path", drawn on the map,
  with the student's trail. Replaces the 10-node force graph with a 1466-node
  landscape that is still cheap to draw (precomputed coordinates, SVG circles).
- **Effort:** 1.5 days. Depends on option 1 for direction; works without it using
  level only.

### 3. Cross-lingual alignment by orthogonal Procrustes (⭐ elegant, cheap)

- **What:** bge-small is an English model, so Catalan embeddings are weak. The 1747
  English/Catalan pairs give a closed-form solution: find the rotation `W`
  (384×384) minimising `‖W·cat − eng‖` by SVD. One matrix, ≈1 MB as JSON, exact
  and deterministic.
- **On the board:** multiply any Catalan embedding by `W` before retrieval, skill
  tagging or map placement. One matrix-vector product in Python (147k
  multiplications, under 50 ms).
- **Validation:** retrieval accuracy cat→eng (does the Catalan text find its own
  English twin at rank 1?) before and after alignment, on held-out pairs.
- **Demo:** the map and RAG work identically in both languages; the pitch can show
  the before/after retrieval accuracy as one number.
- **Effort:** half a day. Needs embeddings of both languages.

### 4. Skill tagging by label propagation (replaces hand review at scale)

- **What:** 51 reviewed tags plus 30 diagnostics are seeds. Semi-supervised label
  spreading over the option-2 kNN graph assigns skills to all problems with a
  confidence. Low confidence stays "needs diagnostic", which the scheduler already
  handles. Cross-lingual twins must agree, which is a free consistency test.
- **Validation:** leave-one-out on the 51 reviewed tags; report accuracy and
  coverage at a confidence threshold. Educator reviews only the disagreements.
- **Effort:** half a day after option 2. Output goes to `data/teaching_annotations.json`
  through the existing export, so the app needs no change.

### 5. Misconception signatures from numeric distractors (no ML, pure engineering)

- **What:** for the 669 problems with numeric options, precompute on the laptop
  which naive operation over the numerals in the text yields each distractor:
  sum instead of product, difference, off-by-one, forgotten unit conversion,
  halved instead of doubled. Store a signature per (problem, letter).
- **On the board:** when the student picks C and C is "sum instead of product",
  the feedback and the first hint target that misconception, and the thinking
  step "Plan" distractor for that problem can be the same misconception.
- **Validation:** fraction of distractors explained by a signature; manual check
  of 30 problems.
- **Demo:** "You added where the problem needed multiplying" is the single most
  impressive line a tutor can say, and it is deterministic.
- **Effort:** 1 day.

### 6. Analogical hints: nearest easier solved problem

- **What:** for the current problem, retrieve the nearest neighbour in the map
  that is one difficulty step lower and that this student already solved. Show
  it as "You solved this one; the same idea works here", with the student's own
  saved reflection or the authored solution. This is T-040 made student-aware.
- **Effort:** half a day after option 2.

### 7. Edge AI as a peer: uncertainty map and devil's advocate

- **What:** run `predict.py` with `top_logprobs` offline over the training set on
  the board (it is the scored pipeline anyway) and store the letter distribution
  and entropy per problem. High-entropy problems are flagged "even the AI is
  unsure" and offered as challenges; the model's top-2 letters feed T-051's
  devil's-advocate prompt without any new generation.
- **Validation:** calibration curve of model confidence versus correctness per
  level, which doubles as the error analysis T-071 needs.
- **Effort:** 1 day of board time, mostly waiting.

### 8. Guessing and disengagement detector (phase 2, needs student data)

- **What:** features per attempt: seconds per thinking step, steps wrong, tries,
  hints, time of day, difficulty gap. Start with a rule (under 4 s per step and a
  wrong first answer marks "guessing"); after real sessions, fit a decision tree
  and export it. A guessed attempt is logged but not used as BKT evidence.
- **Why a tree:** it is the one model the pitch can show as a picture, and it
  runs as nested ifs on the board.
- **Effort:** half a day for the rule; the fit waits for T-093 data.

### 9. Language-hard versus math-hard classifier

- **What:** readability features (sentence length, clauses, negations, numerals)
  predict the gap between the model's accuracy in English and Catalan on the same
  id. When a student struggles on a Catalan item that is "language-hard", offer
  the English twin, and vice versa. Also informs T-014 and T-058.
- **Effort:** half a day once option 7 has per-language accuracies.

## Suggested bundle for the datathon

Options 1, 2, 3 and 5 together give one story: *"We found the difficulty hidden
in the Kangaroo papers, built a 1466-problem map in both languages, and the tutor
walks each student along it and explains their mistakes."* Each has a laptop
metric, a JSON artifact under ignored `data/`, and a board-side pure-Python
consumer. Options 4, 6 and 7 are follow-ups that reuse the same artifacts. Option
8 is honest about needing data and should be presented as the plan, not a result.

## What not to do

- No model fitting on the board; no scikit-learn, numpy or torch there.
- No prompting the 0.8B model to grade reflections or generate problems.
- No claims of learning gains without T-093 data. Say "indicator", not "proof".
- Never commit the exported artifacts that contain M3Kang text; vectors, trees and
  the Procrustes matrix contain no text and may be committed if small.

## Execution plan, night of 2026-11-15 (laptop only; board unreachable from this Mac)

Order follows the TODO block D7. Everything is trained on the laptop, exported as
JSON under ignored `data/ml/`, consumed by pure-Python board code with tests, and
committed per task on branch `exp/ml-tutor`. Nothing is pushed or merged.

| Step | Task | Depends on | Output |
| --- | --- | --- | --- |
| 1 | Local embeddings with `BAAI/bge-small-en-v1.5` (same model as the board's GGUF, fp32 instead of Q8) for all 2932 rows | internet, `.venv-ml` | `data/ml/embeddings.json` |
| 2 | T-108/T-109 error signatures and misconception feedback | nothing | `data/ml/signatures.json`, `copilot/misconceptions.py` |
| 3 | T-101/T-102/T-103 features, difficulty tree, Elo selection | step 1 | `data/ml/difficulty_tree.json`, `data/ml/difficulty.json`, `copilot/difficulty.py` |
| 4 | T-104/T-105 Procrustes alignment | step 1 | `data/ml/procrustes.json`, change in `copilot/embed.py` |
| 5 | T-106/T-107 problem map, Dijkstra paths, map UI | steps 3, 4 | `data/ml/problem_map.json`, `/api/map`, `/api/path` |
| 6 | SLM nightly cache (see evaluation below), tested with a mocked server | step 2 | `board/nightly_slm.py`, `slm_cache` table |
| 7 | Docs: EXPERIMENTS rows, STATUS, DECISIONS D-013, README of `laptop/ml` | all | |

**Status at 05:45:** steps 1–5 done and committed (105 student-app tests, 54 laptop tests); step 6 was replaced by offline generation through the organisers' Helmcode API (D-013), finished for the whole prepared set (tags 1746/1747, steps 96%, solutions 94%, explanations 95%; see EXPERIMENTS "Generated teaching content"); the submission plan is in [SUBMISSION.md](SUBMISSION.md), the pitch in [PITCH.md](PITCH.md) and the demo in [DEMO-SCRIPT.md](DEMO-SCRIPT.md).

**Morning checklist (needs the board; the exact commands are in SUBMISSION.md):** `build_index.py` on the board, re-run the
laptop scripts with `--port 8082` forwarded so the artifacts use the exact Q8
vectors, `laptop/deploy_student.py` with the new `data/ml` files, tests on the
board with `python3 -S`, `free -m`, and the first nightly SLM batch.

**Known merge risk:** branch `ui/kangaroo-studio` (teammate, 2026-11-15) redesigns
`student_app/assets`. The map UI is kept in a new file (`map.js`) and one new
section to limit conflicts.

## Evaluation: using the SLM to help the student

The team is right that the 0.8B model on the board is part of the story. The
question is where it helps without hurting. Facts that bound the answer: prefill
≈ 11 tok/s, generation ≈ 5–6 tok/s, so a 200-token prompt plus a 30-token reply
costs about 25 s; its accuracy on Kangaroo is 36.7%, below always-D; four live hint
selections took 10–23 s. A child will not wait 25 s, and a wrong explanation is
worse than none.

| Use | Verdict | Why |
| --- | --- | --- |
| Select among authored hints (today) | Keep | Bounded, falls back instantly; already measured |
| Letter distribution as "the AI's opinion" (devil's advocate, T-051) | Yes, live | One grammar-constrained call, prefill-bound (~15 s), shown asynchronously; no generated text can be wrong |
| Verbalise a misconception signature in the child's language | Yes, cached | The fact comes from Python; the model only phrases it. Generated at idle time per (problem, distractor, language), leak-checked, stored in SQLite, served in milliseconds |
| Socratic follow-up question after a wrong answer | Yes, cached, labelled | Same batch; Python rejects any output containing the correct option value or a letter claim |
| Candidate worked solutions | Only offline, filtered by the answer key, marked "AI draft" for educator review | 36.7% accuracy; a solution reaching the right letter may still reason wrongly |
| Grade free-text reflections | No | Unreliable judge at 0.8B; would put the model on the critical path |
| Generate new problems | No | Licence and correctness; the dataset has 2932 already |

**Design: "the SLM works while the student sleeps."** A `board/nightly_slm.py`
job runs when the board is idle (systemd timer or manual), walks problems in
priority order (those with signatures and tagged skills first), asks the model for
one sentence per (problem, distractor, language) with `temperature 0, seed 42`,
runs the leak check and a length/language check in Python, and stores accepted
rows in `slm_cache` with the prompt digest. The server serves cached sentences
instantly and falls back to the template when none exists. The pitch can show
both the live selection and the cache growing overnight, and the student never
waits for the model.
