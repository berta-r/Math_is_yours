# SLM integration proposal and branch audit

Review date: 2026-11-15. Baseline: fetched `origin/main` at **8274efa**.
Implementation branch: **exp/slm-learning-coach**, created from that baseline.
Status: **historical proposal and branch audit**. Implementation was subsequently
requested and main through `0b42034` merged in `1dc4805`. The implemented feature,
current limitations and deployment instructions are in [SLM-COACH.md](SLM-COACH.md);
design integration points are in [COACH-DESIGN.md](COACH-DESIGN.md). The original
proposal below records the reasoning before implementation, not current status.

## Recommendation

Help a student explain where they are stuck, get one relevant piece of help,
and return to the existing Understand → Plan → Check → Answer → My path flow.
Keep the difficulty model, BKT/Elo updates, content bank and path selection as
the foundation. Add a small conversational interface to those capabilities.

The SLM's useful job is interpreting the student's wording and follow-up questions
and, only after evaluation, expressing a short explanation grounded in supplied
facts. Python computes arithmetic, enforces disclosure rules and records evidence.
Merely choosing a digit from a handful of generic hints already failed to address
the student's questions in our previous deployment.

## What main actually contains

| Capability | Implementation | Implication for the coach |
| --- | --- | --- |
| Difficulty | `copilot/difficulty.py`; observed paper positions take precedence, exported tree/ensemble supports prediction | Read existing difficulty and its source; avoid asking the SLM to estimate difficulty |
| Student state | `copilot/student_model.py`; BKT, global/per-skill Elo, learning and thinking events | Read independent evidence and recent process errors; unknown is not a demonstrated weakness |
| Next exercise | `copilot/scheduler.py`; prerequisites/review/freshness plus distance to estimated p=0.7 | Ask the existing scheduler for a candidate; explain its recorded reason |
| Problem map | `copilot/learning_map.py`; exported kNN graph, clusters, layout and Dijkstra paths | Use neighbours for candidates, then filter for skill, language, difficulty and usable content |
| Bilingual alignment | `copilot/alignment.py`, `laptop/ml/align.py`; Procrustes | Reuse the aligned graph; a new text-query index would need its own export and matching query alignment |
| Teaching bank | `copilot/knowledge.py`, `content_checks.py`; authored/generated steps, hints and solutions with precedence and rechecking | Retrieve only content allowed at this stage; retain provenance and language |
| Error feedback | `copilot/misconceptions.py`; numeric distractor signatures and prepared explanations | Describe a possible error, not a certain diagnosis of the student's thinking |
| UI and answer gates | `student_app/server.py`, current Solve / My path / My work views | Put optional help beside the current thinking step; preserve the step and reveal gates |
| Existing live SLM hook | `copilot/tutor.py`; bounded worker selecting authored hints | Reuse the bounded transport pattern, but measure whether interpretation adds value |

The map's proximity is similarity, not proof of a prerequisite. Its `solved`
status currently includes assisted correct answers; a coach must consult the
independent-evidence records before describing a previously solved item as mastered.
The 70% probability is a model estimate, not a calibrated promise to an individual.
Generated-content checks reject some malformed/leaking content; they are not a
mathematical or pedagogical proof.

### Artifact availability on this PC

Actual loader inspection found **170 training rows / 170 canonical IDs**, zero
loaded difficulty entries, zero map nodes/edges and zero loaded generated steps,
solutions or tags. The handler starts successfully using its fallbacks.
`data/ml/` has no available artifacts here. This differs from main's documented
1,466-problem map and larger bilingual prepared set; those are reported results
from another prepared environment, not verified assets of this checkout.

Git stores the loaders and training scripts, not the research dataset or student
database. Before a full integration demo, obtain the matching prepared artifacts
from the team's prepared environment, or reproduce them with `laptop/ml/`.
Inventory IDs/languages, model/version metadata, content coverage and checksums:

- `data/train.jsonl` and referenced images;
- `data/ml/difficulty.json`, `difficulty_model.json`, `problem_map.json`,
  `procrustes.json`, `signatures.json`;
- `data/ml/thinking_steps_generated.json`, `solutions_generated.json`,
  `slm_explanations.json`, and `data/teaching_annotations.generated.json`.

Confirm exact filenames against the loaders when packaging. The existing bundle
includes runtime ML JSON and excludes raw `embeddings.json`. It therefore does not
provide arbitrary semantic text search just because it displays an embedding map.
The first slice can use a small reviewed subset and existing graph neighbours;
full-set claims require the matching artifacts. Add an explicit capability report
so missing files cannot silently masquerade as the complete ML system.

## Student journey and request handling

1. The existing scheduler selects a fresh exercise and the UI shows its current
   thinking step. An optional “Ask about this step” opens help without resetting it.
2. The student asks “What does equally mean?”, “Why can't I add these?”, or
   “What is 18 minus 6?”. The server attaches the current problem, language,
   thinking stage, attempted steps, hint exposure and relevant independent evidence.
3. Explicit arithmetic is parsed directly. Other requests go through a bounded
   SLM intent resolver using the latest exchange. It may propose a concept lookup,
   calculation check, simpler example or clarification. Python validates every
   operation and resource ID against a small allowlist and supplied candidates.
4. Retrieve the current permitted hint, a reviewed concept card, or a suitable
   earlier/easier example. A prepared bank entry must actually address the question;
   otherwise explain what is missing or ask a focused clarification. Do not keep
   substituting the same generic “try smaller steps” sentence.
5. Save the question, assistance and response, then return to the original exercise.
   A subsequent fresh independent check supplies evidence for BKT/Elo and the map.

### Arithmetic policy

| Situation | Intended behaviour |
| --- | --- |
| Standalone calculator/practice question: “What is 18 − 6?” | Python returns 12 immediately, with a short verified decomposition if useful |
| “18 − 6 = 13” during an exercise | Python identifies the incorrect equality and offers a small check; no full-solution verification claim |
| Arithmetic likely to reveal the current exercise's final answer | Request a student attempt first or use the existing review gate; clearly explain why |
| Relation to the final answer is unknown | Ask whether this is a proposed step; do not trust an SLM's “safe to reveal” verdict |
| Longer word problem translated into an expression by the SLM | Confirm the interpreted expression/quantities; exact evaluation does not prove correct translation |

Implement a bounded numeric parser for integers, decimals, fractions, parentheses
and +/−/×/÷. Cap expression length, depth and operand sizes; handle zero division
explicitly. Evaluate allowed nodes with `Fraction`, without arbitrary execution.
Checking whether the result equals an option is only a leak signal, not a general
way to determine whether an expression solves the problem. Use reviewed step
metadata where available. Standalone practice must be an explicit UI mode; it does
not secretly turn an assisted exercise into independent evidence.

### Context and retrieval

Start with direct current-problem lookup and its current allowed stage. Fetch
at most one concept card or simpler example using existing tags and graph edges.
Filter neighbours to training items, available language/content, appropriate
difficulty and the student's exposure history. Use a separately labelled similar
example if it is new; never call it something the student already knows.

Pass the SLM a bounded context: current question, latest exchange, current stage,
one relevant skill and prerequisite, source IDs and only permitted excerpts.
Do not send the whole database, 1,466 nodes, hidden labels, later-stage solutions
or every past message. If later semantic query retrieval is worthwhile, build a
small concept-card index on the laptop and measure it separately against keyword
and direct-ID retrieval; embedding calls add latency on the shared board.

### Live language generation

Main's **D-013** explicitly rejects live generated student-facing prose following
poor pilot results. The archived branch has a different D-013; its IDs do not
supersede main's decision. This proposal does not silently undo that rule.

First evaluate intent interpretation and retrieval in shadow mode: students keep
receiving the existing content while proposed actions are scored offline. Then
evaluate a feature-flagged, one- or two-sentence paraphrase of one approved fact,
without new numerical procedures. A future decision may enable that limited mode
only if the comparison supports it. A keyword/answer filter alone is insufficient.
Report source and fallbacks honestly. Missing diagram information requires a
description or suitable prepared guidance; the current text SLM cannot see it.

## Implementation order and stopping points

These are rough focused-development estimates, excluding missing-data preparation;
reserve at least the final quarter of the available time for board checks/demo.
If the deadline is closer, deliver only the first complete arithmetic/help slice.

| Stage | Work and integration seam | Completion evidence | Estimate |
| --- | --- | --- | --- |
| 0 | Inventory artifacts; establish baseline; resolve the two observed test issues in a separate fix | Capabilities/coverage recorded; baseline reproducible | 0.5–1.5 h plus artifact transfer |
| 1 | Exact arithmetic + disclosure policy; additive help-turn storage; integrate with main's current session and thinking steps | 18−6 works in standalone mode; active-answer gate intact; saves/retries/profile isolation work | 2–3 h |
| 2 | Intent resolver + bounded evidence retrieval, initially shadowed | Outperforms direct rules on varied student wording; no invented candidate IDs; useful source retrieved | 2–3 h |
| 3 | Optional grounded phrasing experiment; one short asynchronous request at a time | Human-reviewed explanation quality and board latency beat the existing experience | 1–2 h plus review |
| 4 | Main UI integration, bilingual walkthrough, migration and board package | Fresh independent check updates existing BKT/Elo; assisted help does not; restart restores work | 1–2 h |

Limit the MVP to **arithmetic checking, concept clarification and a simpler example**.
Path explanations can initially use the scheduler's existing reason. Defer new
models, arbitrary generated exercises, live graph recomputation and broad chat.
Avoid needing two sequential SLM calls per turn: use deterministic dispatch where
possible and select either interpretation or short phrasing for the measured slice.

Port selectively from `694d2b6`: idempotent turn storage, drafts, pending-job
recovery and assistance-at-request-time are useful patterns. Adapt their SQL to
main's `thinking_events`, ratings, step counters and misconception flow. Do not
replace main's server, UI, knowledge loader or deployment bundler wholesale.
Preserve the currently deployed board DB via a SQLite backup and test migration
of both main and archived conversation schemas on copies before a versioned release.

## Acceptance and demonstration

- Compare current main, deterministic tools/retrieval, and tools/retrieval plus SLM
  on the same small bilingual set (at least 40 distinct requests across the three
  MVP intents, including follow-ups, wrong calculations, ambiguity and answer requests).
- Record intent correctness, source relevance, mathematically correct explanation,
  whether the student's actual question was answered, repeats, fallback rate and
  disclosure. Human review is necessary; JSON validity is not teaching quality.
- Proposed release gate: all supported arithmetic fixtures exact; no evidence
  inflation or bypass of answer gates; no observed answer leaks on the test set;
  at least 90% appropriate intent/source decisions and 80% useful explanations,
  improving over the deterministic baseline. These are proposed engineering gates,
  not validated educational thresholds or guarantees beyond the test set.
- On the UNO Q, target immediate stored/calculator feedback below 0.5 s and live
  reply p95 below 25 s on the test set, with a bounded 45 s fallback deadline.
  Measure queue time, memory and model contention. Do not assume these targets
  follow from the earlier two successful dialogue examples.
- Verify chat helps without awarding BKT/Elo credit; a new independent exercise
  can update them. Keep thinking-step process metrics separate. Save source IDs,
  tool result, stage, model version and assistance reason with each turn.
- After runtime changes, run the official sample contract and named board eval;
  preserve `predict.py` scoring independently. Current task changes only docs/Git.

90-second demo: open a curated equal-sharing exercise → ask what “equally” means
→ receive relevant grounded help → check a proposed arithmetic step → finish
the thinking questions → answer → open a fresh related check → show the persisted
evidence/path after reload. Demonstrate 18−6→12 separately in explicit calculator
mode. If live generation misses the acceptance gates, ship verified arithmetic
and retrieved guidance and label the SLM experiment as unfinished.

## Branch audit

Fetched all advertised origin heads before review. “Merged” means the tip is an
ancestor of main 8274efa, not that its complete tree is identical to main.

| Branch (origin unless stated) | Tip | State and disposition |
| --- | --- | --- |
| main (local and origin) | 8274efa | Current foundation; local fast-forwarded |
| exp/slm-learning-coach (local) | based on 8274efa | New planning/implementation branch |
| fix/adaptive-tutor-dialogue (local) | 694d2b6 | Saved deployed work; 1 unique commit, missing 39 main commits; selective port only |
| ui/graph-aware-coach, ui/student-practice (local and origin) | 3b6d7be | Merged historical aliases; retained for team traceability |
| exp/ml-tutor | a873578 | Merged ML, content and packaging foundation |
| exp/path-goal-skill | cce640e | Merged goal-to-problem path logic |
| docs/next-problem | a7cd1c2 | Merged explanation of selection and ML |
| fix/local-problem-images | 6efdb60 | Merged local image restoration |
| ui/kangaroo-studio | 7797563 | Merged redesigned workspace |
| ui/design-critique | 4a7b595 | Merged polish/localisation |
| ui/problem-map-style | e649258 | Merged map styling |
| ui/skill-tree | 7041639 | Merged skill-tree navigation |
| ui/path-problems | 67c5f02 | Merged goal problem cards |
| ui/picture-answers | 54a84b1 | Merged picture-option display |
| ui/solve-layout | 0e8f85c | Merged latest Solve layout |
| side-project | 8b00b20 | Ancestor of main; unrelated dashboard retained |
| fix/ocr-options | 7d6b02b | Contains current main plus 3 commits; tolerant parser/refill and coverage report. Coordinate before merging; no SLM dependency |
| exp/reason-strategies | 8be6a33 | 8 unique commits, missing 39 main commits; separate solver experiments, not the current teaching baseline |

The Reason branch contains AST-whitelisted `safe_eval.py`, value parsing, PoT,
logprobs and deduplication. Its evaluator allows broader Python expressions and
uses signal timing; review thread compatibility before borrowing it for a web
worker. Its laptop practice-set results report baseline 24%, PoT 28%, RAG1 12%,
RAG2 18% (100 translated rows; some timings estimated). These do not establish
that adding worked-example RAG will improve live teaching or board reasoning.

No remote branch was deleted, pushed or merged into main. Existing branches have
colliding task/decision IDs: archived T-091–T-093 and D-012/D-013 mean different
things from main; OCR and UI also both use T-120. Refer to branch + commit + title
when integrating. This review uses **T-128** and **D-019** (the branch called them T-121 and D-018; those ids were taken on main) on the new branch.

## Baseline verification in this workspace

`python -m unittest discover -s student_app -p 'test*.py' -q` on unchanged
8274efa: 113 tests, **108 passed, 3 skipped, 1 failure, 1 error**. Both affected
tests reproduce individually:

- `test_difficulty.test_tree_and_ensemble_evaluation`: exact list comparison
  rejects 0.7000000000000001 versus 0.7 after probability normalization.
- `test_elo.EloAppTests.test_catalan_reason_and_skill_rating`: Windows teardown
  cannot delete an open SQLite file (WinError 32, then cleanup WinError 267).

Loader smoke check succeeds using a temporary database, with the missing-artifact
fallbacks described above. This audit does not deploy main, overwrite the Arduino
notebooks, re-run model training, or claim board validation of the newer ML bundle.
