# 04 · Configuration

> Read this before you change `config.env`. It's the single source of settings for the Bash scripts (`source`d) and for Python (`copilot/config.py`). Environment variables override it in Python: `LLM_PORT=9000 python3 eval.py`.

## Keys

| Key | Default | Used by | Meaning, and what to do if you change it |
| --- | --- | --- | --- |
| `LLAMA_CPP_REPO` | github ggml-org/llama.cpp | `02_build_llama_cpp.sh` | Source repository |
| `LLAMA_CPP_REF` | `2cbe0ec4…` | `02_build_llama_cpp.sh` | Pinned commit, tested on UNO Q 4 GB. Rebuild if you change it |
| `LLAMA_CPP_DIR` | `~/llama.cpp` | scripts, services | Where llama-server is built |
| `MODELS_DIR` | `~/models` | scripts, services | Where the GGUF files live |
| `LLM_REPO`, `LLM_REVISION`, `LLM_FILE`, `LLM_SHA256` | Qwen3.5 0.8B Q8_0 (835 MB) | `03_download_models.sh`, services | Language model. To swap the model, change **all four**, re-run 03 and 04, check the license, and log it in DECISIONS |
| `LLM_ALIAS` | `qwen3.5-0.8b` | service | Model name the server reports |
| `LLM_PORT` | `8081` | service, `copilot/llm.py` | Chat completions endpoint |
| `LLM_CTX` | `4096` | service | Context tokens, in one slot. Raising it costs RAM |
| `LLM_THREADS` | `4` | service | The board has 4 cores |
| `VISION_PORT` | `8083` | explorer, manual server | Optional vision server (needs the mmproj projector file, 205 MB) |
| `EMBED_REPO`, `EMBED_REVISION`, `EMBED_FILE`, `EMBED_SHA256` | bge-small-en-v1.5 Q8_0 (37 MB, 384 dimensions) | 03, service | Embedding model. If you change it, **rebuild `data/index.db`** |
| `EMBED_PORT` | `8082` | service, `copilot/embed.py` | Embeddings endpoint |
| `EMBED_CTX` | `512` | service | bge-small was trained on 512 tokens. `embed.py` cuts texts at 1400 characters |
| `EMBED_THREADS` | `4` | service | |
| `EMBED_QUERY_PREFIX` | `"Represent this sentence for searching relevant passages: "` | `copilot/embed.py` | Added to **queries only**, never to stored documents |
| `TIME_LIMIT_SECONDS` | `60` | `copilot/pipeline.py`, `eval.py` | **Official rule. Don't raise it.** |
| `SEED` | `42` | `copilot/llm.py` | Determinism |
| `FALLBACK_ANSWER` | `D` | `copilot/pipeline.py`, `eval.py` | The most common answer in M3Kang `high_quality` (24.6%) |
| `SOLVER` | `compute` | `copilot/llm.py` | `compute`: the compute-first solver ([COMPUTE_SOLVER.md](COMPUTE_SOLVER.md)). `letter`: the original one-letter grammar call. Missing = `letter` |
| `COMPUTE_REPO`, `COMPUTE_REVISION`, `COMPUTE_FILE`, `COMPUTE_SHA256` | Qwen2.5-Coder 1.5B Instruct Q8_0 (1.9 GB, Apache 2.0) | `06_compute_server.sh` | Code model of the compute solver. Change all four together and re-run 06 |
| `COMPUTE_ALIAS` | `qwen2.5-coder-1.5b` | service | Model name the server reports |
| `COMPUTE_PORT` | `8084` | service `math-compute`, `copilot/compute.py` | Its own llama-server, so nothing else evicts the cached examples |
| `COMPUTE_CTX` | `8192` | service | Two slots of 4096 tokens: one cached prompt for the blind try, one for the informed try |
| `COMPUTE_THREADS` | `4` | service | |
| `COMPUTE_MODE` | `both` | `copilot/compute.py` | `both` = blind try, then informed try; `informed`; `blind` |
| `COMPUTE_TRIES` | `3` | `copilot/compute.py` | Model calls per problem at most; stops earlier when time runs out |
| `COMPUTE_MAX_TOKENS` | `48` | `copilot/compute.py` | Tokens per expression |
| `COMPUTE_GUESS` | `balance` | `copilot/compute.py` | When nothing matched: `balance` = the letter used least so far; `fixed` = `FALLBACK_ANSWER` |
| `COMPUTE_READ_TPS`, `COMPUTE_GEN_TPS` | `4.8`, `3.0` | `copilot/compute.py` | Board speeds for the time plan. `0` = measure them at warm-up |
| `COMPUTE_DEBUG` | `0` | `copilot/compute.py` | `1` prints each expression and its value to stderr |

## After you change something

| You changed | Then run (on the board) |
| --- | --- |
| A model, port, ctx or threads | `bash board/03_download_models.sh` (if it's a new model), then `bash board/04_install_services.sh` (it regenerates the units and restarts them). If you edit by hand: `sudo systemctl daemon-reload && sudo systemctl restart math-llm math-embed` |
| A `COMPUTE_*` key | `bash board/06_compute_server.sh` (regenerates `math-compute` and `math-compute-warm` and restarts them) |
| The embedding model or prefix | `python3 build_index.py --input data/train.jsonl --db data/index.db --only-with-options` |
| Anything | `bash board/05_smoke_test.sh`, then an `eval.py` run to compare against the previous result |

## Our changes to the defaults

None yet. Log each change in [DECISIONS.md](DECISIONS.md) with the reason and the measured effect.
