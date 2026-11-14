# Related knowledge areas and progressive paths

The map has two different edge types:

- **Supporting prerequisites** come from the reviewed Markdown curriculum.
  They can justify a suggested order of study.
- **Related areas** come from similarity between English skill descriptions.
  They influence visual proximity and exploration, but never assert a prerequisite
  or update a mastery estimate.

`knowledge/relations.json` ships a small, reproducible **keyword TF-IDF baseline**.
It is not a result from a semantic embedding model. The board loads that fallback
when `data/skill_graph.json` is absent. Only IDs, relationship weights and provenance
are loaded; neither full vectors nor a graph library is needed at runtime.

## Build better relations on the laptop

With the local embedding service running, or its board port forwarded over USB:

```powershell
python laptop/build_skill_graph.py --port 8082
```

The script embeds each skill's English title, description, common difficulty and
hint strategy. It exports the union of each skill's two closest neighbors above
the cosine threshold. It does not infer prerequisites or calibrate difficulty.
The default output is ignored `data/skill_graph.json`; copy this small file to the
board along with the curriculum and restart the teaching service.

To use vectors prepared elsewhere, supply a JSON object mapping **skill IDs** to
numeric vector lists, all with the same dimensionality:

```powershell
python laptop/build_skill_graph.py --vectors data/english-skill-vectors.json
```

An explicit offline keyword baseline can be regenerated without a model:

```powershell
python laptop/build_skill_graph.py --features tfidf
```

`--neighbors` accepts 1–5 and `--threshold` accepts values from 0 up to, but not
including, 1. Higher thresholds produce fewer related edges. A failed embedding
request does not silently become a keyword result. All model calls use loopback;
environment proxies and redirects are disabled.

## What the student path means

An explicit student-selected goal takes priority. Otherwise the path targets a
developing skill first, then an overdue review. With no observed need, similarity
to demonstrated areas can suggest a nearby unassessed skill. Unknown skills are
described as needing a diagnostic, never as weaknesses.

The route follows authored prerequisite links. Demonstrated supporting skills
anchor the route without forcing their already-supported ancestors to be retested.
At most six next steps are displayed, in prerequisite order. Several supporting
branches may feed one goal, so adjacent steps need not have a direct edge between
them. Due review dates do not lower mastery probabilities.

The route is guidance, not a lock on the curriculum. It does not diagnose a
specific misconception from a wrong answer or claim validated learning gains.
Its estimates and tags retain the limitations described in [README](README.md).

## Validation

```powershell
python -m unittest student_app.test_graph -v
```

The checks cover deterministic cosine neighbors, bounded artifacts, malformed
vectors/edges, prerequisite order, strengths, unknown evidence, review state and
the rule that similarity cannot create prerequisites or alter student state.
