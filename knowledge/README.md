# Curriculum and student model

The shared graph is authored in `skills/*.md`. Each student has independent state
in the app's SQLite database. Clusters organise exercises for review; they never
determine prerequisites or mastery automatically.

The connected map also supports weighted related-area links and progressive study
routes. See [GRAPH.md](GRAPH.md) for embedding preparation, the explicitly labelled
keyword fallback, artifact deployment, and how strengths and prerequisite gaps
shape a route. Semantic proximity never changes a student's mastery estimate.

## Author a skill

Use UTF-8 Markdown with this restricted YAML front matter:

```markdown
---
id: new_skill
title: A readable skill name
prerequisites: ["arithmetic"]
---
Describe what the student can do.

## Common difficulty
A mathematical misconception to investigate.

## Hint strategy
How to guide the next step.

## Hints
- A broad first prompt.
- A more specific method prompt.
- A final scaffold that does not reveal the answer.
```

Lists must use JSON-style brackets; no YAML dependency is installed. The loader
rejects unknown skills, duplicate IDs, cycles and invalid parameters. Prerequisite
arrows mean "supports learning"; students can still choose any skill.
`diagnostics.json` contains 30 original questions, three per skill, with three
hints and an explanation each. Answer positions are balanced across A–E.
The five original sample problems have scaffolding in `sample_annotations.json`.

## Cluster and review M3Kang on the laptop

Only use training data. English is canonical for embeddings; translated display
variants inherit annotations by problem ID.

```powershell
# Existing training index, copied from the board if needed:
python laptop/annotate_problems.py cluster --index data/index.db --clusters 8

# Or call a local embedding server on port 8082:
python laptop/annotate_problems.py cluster --clusters 8

# Explicit keyword-vector fallback when embeddings are unavailable:
python laptop/annotate_problems.py cluster --features tfidf --out data/keyword-clusters
```

`--vectors file.json` also accepts `{ "canonical-id": [embedding, ...] }`.
Deterministic k-means uses seed 42 and stores centroids, vectors, assignments and
representative IDs in `clusters.json`. One English row per ID is clustered.
TF-IDF is a keyword baseline, not semantic embeddings. The board teaching app
does not load these preparation artifacts into RAM.

Edit `cluster-review.csv`. Inspect the questions and original diagrams, then fill:

| Column | Meaning |
| --- | --- |
| `skills` | Known skill IDs separated by semicolons; multiple labels allowed |
| `assessment_skill` | Single skill that can be assessed confidently; otherwise blank |
| `status` | `reviewed` to accept; otherwise pending/rejected |
| `reviewer` | Reviewer and provenance/limitations |

```powershell
python laptop/annotate_problems.py export --review data/clustering/cluster-review.csv --output data/teaching_annotations.json
```

Only explicitly reviewed rows are accepted. Unknown skills or a primary skill
outside the label set are rejected. Pending/rejected rows in the CSV revoke an
existing mapping; mappings absent from that CSV are retained. Re-export preserves
authored hints/solutions on accepted mappings. Restart the server to load changes.
A missing annotations file leaves real problems unclassified; original diagnostics
still work. Generated data stays under ignored `data/` and is copied separately
to the board.

Optional scaffolding in the generated annotation JSON:

```json
{
  "version": 1,
  "problems": {
    "your-problem-id": {
      "status": "reviewed",
      "skills": ["arithmetic", "multiplication"],
      "assessment_skill": null,
      "language": "eng",
      "provenance": "Team review",
      "hints": ["First scaffold", "Second scaffold", "Third scaffold"],
      "solution": "Reviewed mathematical explanation"
    }
  }
}
```

Do not assign a primary skill merely to obtain an update. Use a diagnostic when
attribution is ambiguous. Scaffolding is shown only for its declared language;
English general skill hints are a labelled fallback for known primary skills.
The loader does not validate arbitrary authored mathematics.

## Provisional Bayesian Knowledge Tracing

`model.json` holds unfitted prototype parameters: prior 0.20, guess 0.20, slip
0.10, learning 0.10. A correct independent observation gives:

`posterior = p*(1-slip) / (p*(1-slip) + (1-p)*guess)`

An incorrect observation gives:

`posterior = p*slip / (p*slip + (1-p)*(1-guess))`

Then `p_next = posterior + (1-posterior)*learn`. Only the reviewed assessment
skill changes. The [pyBKT project](https://github.com/CAHLR/pyBKT) provides general
model background. This implementation is standard-library only and does not fit
parameters from M3Kang, which has no student histories.

Only the first unaided answer to a canonical ID contributes. Wrong first answers
contribute too; retries, hints, explanations, revelations and translated repeats
do not. Exposure checks and writes share a SQLite transaction, preventing two
simultaneous sessions from double-counting. Old attempts remain stored without
retroactive skill attribution.

Demonstrated requires probability >= 0.8, at least three observations and two
successes. Unassessed skills display no probability. Review dates are separate:
success advances through 1/3/7 days; difficulty schedules a 1-day check. A first
unaided answer to a due repeated item can update the date but never the estimate.
These intervals and thresholds are defaults, not calibrated measurements.

## Selection and persistence

The selector considers missing evidence for the current problem, supporting skill
gaps, overdue reviews, a new application of the same skill, and occasional stretch
opportunities. It prefers fresh canonical IDs, the requested language and a
defensible primary assessment. Required images must exist. Selection is
deterministic for the same state and time. Every result explains its reason;
explicit graph-node choices override suggestions.

| SQLite table | Stored data |
| --- | --- |
| `curriculum_skills`, `prerequisites`, `problem_skills` | Loaded graph and tags |
| `sessions` | Variant, start time, hints, tries, revealed state, last answer and original focus |
| `attempts` | Every letter and key-based result; legacy rows retained |
| `learning_events` | First-attempt flag, help used, question kind, language, attribution, time and before/after estimates |
| `student_skills` | Per-student probability, evidence/success counts and review schedule |

The app derives the interactive graph and downloadable Markdown report from these
records. No graph database or browser persistence is needed. The official
`predict.py` and `copilot/pipeline.py` do not import this teaching flow.
