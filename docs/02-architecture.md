# 02 · Architecture

> Read this before you change code. It describes the template as it is today (commit `d6e3f1b`). When we change the architecture, update this file in the same commit.

## Big picture

```
            LAPTOP                                         ARDUINO UNO Q (4 GB, Debian, offline at runtime)
 ┌──────────────────────────────┐                 ┌───────────────────────────────────────────────────────────────┐
 │ laptop/prepare_m3kang.py     │  scp / adb push │  Linux side (QRB2210, 4 Arm cores)                            │
 │  HF parquet → OCR options →  │ ──────────────► │                                                               │
 │  data/train.jsonl, val.jsonl │                 │  systemd: math-llm   llama-server :8081  Qwen3.5 0.8B Q8_0    │
 │  (+ data/images/*.png)       │                 │  systemd: math-embed llama-server :8082  bge-small-en-v1.5    │
 └──────────────────────────────┘                 │  (optional)          llama-server :8083  vision (mmproj)      │
                                                  │                 ▲ HTTP 127.0.0.1 only                         │
                                                  │  copilot/ (Python stdlib) ◄── predict.py / eval.py / explorer │
                                                  │      └── data/index.db (SQLite vectors, from build_index.py)  │
                                                  │                                                               │
                                                  │  [future] App Lab app: python/main.py + web_ui brick          │
                                                  │                 │ Bridge                                      │
                                                  │  Microcontroller side: sketch.ino → 8×13 LED matrix           │
                                                  └───────────────────────────────────────────────────────────────┘
```

## Flow of one problem (`predict.py` → `solve()`)

1. `predict.py` reads the JSONL and calls `copilot.pipeline.solve(problem, index, k)` for each problem.
2. `solve()` starts a timer and sets the default result to `FALLBACK_ANSWER` (`D`) with status `ok`.
3. **If `k > 0`:** `index.search(problem, k, exclude_id)` embeds the query (with the bge query prefix) and runs a brute-force dot product over all vectors in memory. It returns the top k `(score, problem)` pairs.
4. **Time budget:** `remaining = 60 − elapsed − 3 s margin`.
5. `llm.answer_letter()` builds the chat messages:
   - a fixed system prompt (kept stable so llama-server's prompt cache reuses it),
   - for each example, a user turn (problem + `Answer:`) followed by an assistant turn (its label letter),
   - the target problem as text, `A) … E)`, then `Answer:`. If the options are missing: "(The options are in a picture…)". If `image_b64` is set, an `image_url` part is added.
6. It POSTs to `:8081/v1/chat/completions` with `grammar: root ::= [A-E]`, `max_tokens 1`, `temperature 0`, `seed 42`, `cache_prompt true`.
7. On a timeout, status is `timeout` and the answer stays `D`. On another URL error, status is `error: …`.
8. It returns `{answer, seconds, status, prompt_tokens, retrieved, examples}`, and `predict.py` writes the CSV row.

## Modules

| File | Responsibility | Key API | Notes |
| --- | --- | --- | --- |
| `copilot/config.py` | Parse `config.env` (KEY=VALUE, shlex, `~` expanded). Environment variables override it | `CONFIG` dict, `ROOT` | Try a setting without editing: `LLM_PORT=9000 python3 eval.py` |
| `copilot/client.py` | JSON over `urllib` | `post(url, payload, timeout)`, `get(url)` | stdlib only |
| `copilot/llm.py` | Prompt format and LLM call | `SYSTEM`, `format_problem(p, sees_image)`, `build_messages(p, examples, image_b64)`, `answer_letter(p, examples, timeout, image_b64, url)` → `(letter, timings)` | `timings.prompt_n` = tokens actually read |
| `copilot/embed.py` | Embeddings | `embed(texts, query=False)` → unit vectors | Truncates to 1400 characters (about 512 tokens). Adds the query prefix only when `query=True` |
| `copilot/rag.py` | Vector index in SQLite | `build(db_path, problems)` (generator), `Index(db_path).search(problem, k, exclude_id)` | Table `problems(key='id\|lang', problem JSON, vec float32 BLOB)`. Loads everything into RAM. `exclude_id` skips the same problem in every language |
| `copilot/pipeline.py` | **The copilot.** One problem in, one letter out | `solve(problem, index=None, k=0, exclude_id=None, image_b64=None, llm_url=URL, time_limit=60)` | **Change this first.** `MARGIN = 3.0` s |
| `predict.py` | Official entry point | CLI `--input --output [--rag K] [--index]` | Flushes the CSV after each row |
| `eval.py` | Accuracy and latency on validation | CLI `--input --limit --languages --rag --index --name` | Shuffles with seed 42 (same sample every run). Writes `results/eval-<stamp>-<name>.csv` and appends a row to `results/ablations.csv` with the git commit |
| `build_index.py` | Builds `data/index.db` from the train set | CLI `--input --db --languages --only-with-options` | Deletes the existing DB first. Only the train set goes in |
| `explorer/server.py` | Web app (stdlib `http.server`) to inspect problems | `GET /`, `/api/info`, `/api/problems`, `/api/problem?key=`, `/api/similar?key=`; `POST /api/check`, `/api/ask` | Default `127.0.0.1:8000`. Needs `data/images` for pictures. Can use the vision server on :8083 |
| `laptop/prepare_m3kang.py` | Builds the dataset | see [03-data.md](03-data.md) | Laptop only; needs pip packages |
| `board/*.sh` | Board setup, idempotent, sources `common.sh` → `config.env` | 00 check, 01 apt, 02 build llama.cpp, 03 models + SHA256, 04 systemd services, 05 smoke test | |
| `board/systemd/*.service` | Templates with `@VAR@` placeholders, filled in by `04_install_services.sh` | | LLM: `--parallel 1 --cache-ram 0 --jinja --reasoning off`. Embed: `--embedding`, batch = ctx = 512 |

## Extension points (where our idea will plug in)

- **Reasoning improvements:** `copilot/pipeline.py` (strategy), `copilot/llm.py` (prompt, logprobs, grammar). Keep `solve()`'s return shape, because `eval.py` depends on the keys `answer`, `seconds`, `status`, `prompt_tokens` and `retrieved`.
- **Retrieval improvements:** `copilot/rag.py` (hybrid search, score threshold, filter by level or language).
- **Teaching features:** new modules under `copilot/` (for example `copilot/hints.py`, `copilot/trainer.py`) that reuse `embed`, `rag` and `llm`, plus an App Lab app (`python/main.py`, `sketch/sketch.ino`). See the `unoq-hardware-ui` skill.
- **New metadata (topic, difficulty map):** add fields to the JSONL or a new SQLite table. Remember M3Kang has **no topic field**.

## Invariants to keep

- No third-party imports in anything that runs on the board.
- Model servers listen on `127.0.0.1` only.
- `solve()` must always return within `time_limit`, whatever happens: retrieval and any extra model call count against the same 60 s.
- Keep the system prompt stable across calls so prompt caching keeps working.

## Implemented teaching path

`student_app/server.py` serves the offline browser UI on `127.0.0.1:7011`, prepared
M3Kang media and 30 original diagnostics. This flow is separate from `predict.py`.

| Component | Responsibility |
| --- | --- |
| `knowledge/skills/*.md`, `copilot/knowledge.py` | Validated shared curriculum and prerequisite DAG, hints and reviewed tags |
| `copilot/student_model.py` | Provisional BKT, conservative attribution, persistent events, review dates, Markdown report |
| `copilot/scheduler.py` | Deterministic diagnostics, supporting practice, due review, transfer and stretch recommendations |
| `copilot/tutor.py` | Optional single local SLM worker selecting permitted hints; immediate stored fallback |
| `student_app/progress.db` | Per-student history and state; old attempts retained |
| `laptop/annotate_problems.py` | English-per-ID k-means candidates and explicit reviewed-tag export |
| `laptop/eval_teaching.py` | Synthetic comparison with random and correct-harder selectors |

The browser submits a letter. Python grades it with the supplied key, records help
and exposure, and updates only a defensible assessment skill. Multi-skill ambiguity
triggers a diagnostic. The browser then reloads graph state and the next-step
reason. Tutor requests immediately return a stored hint and optionally a local
job token; newer feedback or a different session invalidates late browser updates.
Model calls never hold the SQLite write transaction open.

The Linux side of the board can host the same server behind USB forwarding. The
physical microcontroller adapter remains pending. See [app instructions](../student_app/README.md)
and [curriculum/model details](../knowledge/README.md).

The connected-map version adds `copilot/learning_graph.py` and a compact relation
artifact built by `laptop/build_skill_graph.py`. Similarity influences exploration;
authored prerequisites and saved evidence define the progressive path. The browser
performs the force layout, search, zoom and dragging. `/api/reflect` stores a thought
before `/api/answer` is accepted; reviewed answers are gated after attempts/help.
`GET /api/health` identifies the app and reports bounded local-model readiness.
Deployment tools install a board boot service with a stable database location and
a PC USB watcher. See [deployment workflow](../board/STUDENT_DEPLOYMENT.md).

### ML tutor modules (T-101 to T-109)

All optional: each loads a laptop-built artifact from `data/ml/` (gitignored, shipped
by T-110) and falls back to the earlier behaviour when the file is missing.

| Module | Artifact | Used by |
| --- | --- | --- |
| `copilot/difficulty.py` | `difficulty.json`, `difficulty_model.json` | Problem difficulty b in [0, 1], `probability`, `elo_update`; `student_model` keeps `student_elo` and `scheduler` targets p ≈ 0.7 |
| `copilot/learning_map.py` | `problem_map.json` | `POST /api/map`, `POST /api/path` and the `/map` page (`assets/map.html`, `assets/map.js`) |
| `copilot/alignment.py` | `procrustes.json` | `rag.Index` rotates Catalan query vectors when `ALIGN_CATALAN=1` (default 0) |
| `copilot/misconceptions.py` | `signatures.json` | Wrong-answer feedback naming a likely slip |
