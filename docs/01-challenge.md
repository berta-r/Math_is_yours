# 01 · The challenge

> Read this to understand what we must build, the rules and how we're judged. The source is the organizers' text in [../README.md](../README.md#the-challenge).

## The prompt

> Design and build a Math copilot that runs entirely on the Arduino UNO Q and uses M3Kang in an innovative way to help students learn to reason mathematically.

**Motivation:** maths results in Catalonia are falling in PISA. Teachers are stretched. AI helps only if it **guides reasoning without doing the homework** and **keeps student data private**, which is why everything runs on the device.

## Two possible directions (pick at least one)

| Direction | What it means | How it's judged |
| --- | --- | --- |
| **Teach** | An experience that sparks curiosity and guides the student **without giving away the answer**: hints, adaptive practice, error analysis, physical interaction, collaboration | Demo, pitch, originality, our own metrics |
| **Reason** | Given a Kangaroo-style problem, choose the correct letter | **Objectively, on a hidden test set**, by running our `predict.py` |

`predict.py` is scored on the hidden test set **for every team**, even teams that focus on Teach. Keep it working and within the rules at all times.

The most original uses of M3Kang score highest. M3Kang can serve as a retrieval knowledge base, a training set, a source of embeddings, a difficulty map, a multilingual bridge, or something new.

## Deliverables

1. **A public GitHub repository** with the code and a README covering: what it does (photo or video), architecture, how to replicate it from a board set up with steps 0–12, results against the baseline (from `results/ablations.csv`), **error analysis by topic, language and difficulty**, what didn't work, team members and a license (for example MIT).
2. **An Arduino Project Hub write-up**: a step-by-step from a fresh board to the demo. See [../README.md#152-a-step-by-step-on-arduino-project-hub](../README.md#152-a-step-by-step-on-arduino-project-hub).
3. **A live demo and a 3-minute pitch** on the board. Suggested split: problem 20 s, demo 90 s, numbers 40 s, lessons 30 s.

Send both links to the organizers. **Don't publish any M3Kang data.**

## Official run rules (the jury's `predict.py` run)

| Rule | Value | Where it's enforced |
| --- | --- | --- |
| Output | One letter `A`–`E` per problem, CSV `id,language,answer,seconds,status` | `predict.py`, and the grammar `root ::= [A-E]` in `copilot/llm.py` |
| Time | ≤ 60 s per problem | `TIME_LIMIT_SECONDS` in `config.env`, timeout in `copilot/pipeline.py` |
| Fallback | `D` on timeout or error (D is the most common answer, 24.6%) | `FALLBACK_ANSWER` |
| Network | None. Everything runs on the board | Design rule |
| Determinism | temperature 0, seed 42 | `copilot/llm.py`, `SEED` |
| Command | `python3 predict.py --input <file>.jsonl --output <file>.csv [--rag K]` | `predict.py` |

## Hardware limits (measured by the organizers)

| What | Cost on the board |
| --- | --- |
| Total RAM | 4 GB (about 3.6 GB usable, shared with App Lab) |
| CPU | Qualcomm QRB2210, 4 Arm cores |
| Prefill (reading the prompt) | about 11–12 tokens/s |
| Generation (writing) | about 5–6 tokens/s |
| Embed one problem (bge-small) | a fraction of a second (911 problems in about 4 min) |
| One letter, baseline | 8.7 s mean, 12.7 s worst |
| With 2 RAG examples | about 30 s |
| One line of reasoning, then the letter | about 26 s |
| Vision server (image input) | 28–38 s |

**Rule of thumb:** embeddings, retrieval, Python and the LED matrix are almost free. The language model is expensive. Use it for a few short things.

## The number to beat (organizers' measurement)

40 English text-only problems with OCR'd options:

| Approach | Accuracy | Mean time |
| --- | --- | --- |
| Always `D` | 25% (train set) | 0 s |
| **Baseline (one letter, grammar)** | **22.5%** (9/40) | 8.7 s |
| Option value instead of letter | 17.5% | 9.3 s |
| One line of reasoning, then letter | 17.5% | 26.3 s |

The baseline has a strong letter bias: it answered D 21 times and A 14 times out of 40. **We must measure our own baseline on our board.** See TODO T-011.

## Hardware for the UI

The **only** hardware output allowed is the board's own **8×13 LED matrix**. No external modules. Student input comes from a **web page served by the board** (App Lab `web_ui` brick). See [../.skills/unoq-hardware-ui/SKILL.md](../.skills/unoq-hardware-ui/SKILL.md).

## References

- M3Kang dataset and paper: <https://huggingface.co/datasets/qualcomm/M3Kang>, Torres-Camps et al., 2026, arXiv:2601.16218
- RAG at the Edge on UNO Q (Marcelo Rovai): <https://mjrovai.github.io/genai-uno-q/content/rag/rag.html>
- LLMs on the UNO Q (Project Hub example): <https://projecthub.arduino.cc/marc-edgeimpulse/running-local-llms-and-vlms-on-the-arduino-uno-q-with-yzma-74e288>
