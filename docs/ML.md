# How the tutor chooses the next problem

The one thing this project does that a prompt cannot: **every problem a student
gets is chosen so that they are likely, but not certain, to solve it, and every
goal they pick is reached by small steps.** The student stays in the band where
learning happens (about a 70% chance of success), which keeps frustration low and
progress continuous. Everything below runs on the Arduino in pure Python from
JSON files computed on the laptop; the numbers are from
[EXPERIMENTS.md](EXPERIMENTS.md).

## 1. The difficulty hidden in the dataset

Kangaroo papers are ordered: the first third of a paper is worth 3 points, the
middle third 4, the last third 5. M3Kang keeps the level (0–7), the year and the
position of every problem, so each problem gets a free difficulty label with no
human rating:

```
b = (level + (points − 3) / 2) / 8        ∈ [0, 1]
```

Level is the coarse band, points the fine position inside it. A level-0 three-point
problem has b = 0; a level-7 five-point problem has b = 1.

## 2. A model for problems without a position

For problems whose position is unknown we trained a **gradient-boosted tree
ensemble** (150 trees, depth 3) and, as a readable baseline, a **depth-6 decision
tree**, both on the laptop with scikit-learn and exported to JSON. Features: a
32-component PCA of the problem's text embedding, level, text length, word and
numeral counts, whether it has a picture, the number of options, whether the
options are numeric and how spread they are. Target: 3, 4 or 5 points.

| Model | Hold-out accuracy (2023–24 papers) | Majority class | Spearman vs position, within paper |
| --- | --- | --- | --- |
| Decision tree, depth 6 | 0.465 | 0.395 | 0.343 |
| Gradient boosting | **0.516** | 0.395 | **0.475** |

The board evaluates the exported trees in pure Python (matches scikit-learn within
5·10⁻⁷). Observed positions always win; the model only fills the gaps.

## 3. A rating for the student

Each student has a rating θ on the same [0, 1] scale, one global and one per skill,
starting at 0.25 (the level-2 band). The probability of solving a problem of
difficulty b is a logistic curve, and after every **independent** attempt (no
hints, first time on that problem) the rating moves like an Elo score:

```
p(correct) = 1 / (1 + e^(−6 (θ − b)))
θ ← θ + 0.08 · (outcome − p)         outcome ∈ {0, 1}
```

Solving a hard problem raises θ a lot, failing an easy one lowers it a lot, and
assisted or repeated attempts never move it. The update is deterministic and
costs nothing.

## 4. The 70% rule

When the student asks for the next problem, two layers decide:

1. **Which skill.** A Bayesian Knowledge Tracing estimate per skill (updated with
   the same independent attempts) and the hand-authored prerequisite graph of 10
   skills choose what to practise: a diagnostic for an unseen skill, a missing
   prerequisite, a skill due for review, or a transfer to a new kind of problem.
2. **Which problem.** Among the candidates for that skill, the scheduler ranks by
   `|p(correct) − 0.7|` using the student's rating and each problem's b, and
   explains itself: "chosen so you have about a 70% chance: your rating is 0.28 and
   this problem's difficulty is 0.13".

70% is the usual target for adaptive practice: high enough to avoid frustration,
low enough that each problem still carries information and effort.

## 5. The map and the stepping stones

Every training problem is embedded with the board's own embedding model
(bge-small, 384 dimensions). Catalan vectors are rotated into the English space with
an **orthogonal Procrustes** matrix fitted on the 1398 English–Catalan training
pairs (held-out recall@1 of the Catalan twin: 0.50 → 0.73; recall@5: 0.70 → 0.89).
A 5-nearest-neighbour cosine graph, **Louvain** communities (14 clusters,
modularity 0.70) and a **UMAP** layout give the problem map: 1466 training
problems, both languages on the same dots, point size = b.

A goal can be a problem or a skill. For a skill, the server picks the unsolved
tagged problem whose difficulty is closest to the student's mean solved b + 0.5 (a
reachable stretch). Then **Dijkstra** finds the cheapest route from what the
student has solved, with

```
cost(edge) = 10 · (b_target − b_source)² + 0.1
```

so one big jump (Δb 0.6 costs 3.7) is dearer than six small ones (1.2): the path
prefers steady steps between similar problems. On the real map a route from the
easiest problems to the hardest climbs 0.38 → 0.5 → 0.63 → 0.69 → 0.75 → 0.88 →
1.0. A path over 1466 nodes takes under 100 ms on the laptop in pure Python.

## 6. What happens around each problem

The selection is the spine; these are the ribs that make each chosen problem teach:

- **Thinking steps before the options.** Three multiple-choice questions
  (understand, plan, check) with one-sentence feedback; the options stay hidden
  until the steps are done. Gives process metrics (first-try step rate,
  conditional first-attempt accuracy), not just accuracy.
- **Error signatures.** For 805 all-numeric problems we tested which naive operation
  on the problem's numbers produces each distractor; 981 of 3220 distractors (30.5%)
  are explained. A wrong answer with a signature is named ("this could come from
  adding instead of subtracting") without revealing the answer.
- **Verified content.** Steps, hint ladders, solutions, explanations and skill tags
  were written offline by a large model for 94–99% of the prepared set and checked in
  Python (no answer value or letter, right language, length); the board checks again
  at start. The on-device SLM never writes what a student reads (D-013): live probes
  gave one useful Socratic question in five and one answer leak.

## 7. What we measure and what we do not claim

Measured: the difficulty model, the alignment, the map, the signature coverage, the
content acceptance, and every selection decision is logged with its reason, p and b.
Not validated yet: learning gains with real students, the BKT parameters (defaults),
the pedagogical quality of the generated content (no educator review), board timing
of the full bundle. The process metrics are defined and recorded but have no
real-student data.

## One slide

```
difficulty   b = (level + (points − 3)/2) / 8      from the paper position; GBT fills gaps (0.52 vs 0.40 majority)
student      θ, start 0.25; per skill and global
probability  p = 1 / (1 + e^(−6(θ − b)))
update       θ += 0.08 (outcome − p)                independent attempts only
selection    skill by BKT + prerequisites; problem by argmin |p − 0.7|
map          bge-small + Procrustes (recall@1 0.50 → 0.73) + kNN + Louvain (14) + UMAP
path         Dijkstra, cost 10·Δb² + 0.1            small steps beat one big jump
```

Code: `copilot/difficulty.py`, `copilot/student_model.py`, `copilot/scheduler.py`,
`copilot/alignment.py`, `copilot/learning_map.py`; laptop training in `laptop/ml/`.
Options considered and rejected: [ML-OPTIONS.md](ML-OPTIONS.md). Decisions: D-012,
D-013 in [DECISIONS.md](DECISIONS.md).
