"""The copilot: one problem in, one letter out.

predict.py and eval.py both call solve(), so whatever runs here is exactly what the
official run measures. The work is a short list of STEPS, chosen with --steps or
REASON_STEPS in config.env, run in this fixed order:

    dedup     a near-duplicate training problem settles the answer (no model call)
    letter    baseline: one token under the grammar [A-E]
    logprobs  the model's probabilities for A-E, calibrated against its own bias
    pot       the model writes a Python expression; Python computes it and we look
              the result up among the options (numeric options only, if time allows)

"letter" and "logprobs" are alternatives (logprobs wins if both are listed). A later
step only replaces the answer when it finds a letter, so there is always an answer.
"""
import socket
import sys
import time
import urllib.error

from .config import CONFIG
from .llm import URL, answer_letter

TIME_LIMIT = float(CONFIG["TIME_LIMIT_SECONDS"])
FALLBACK = CONFIG["FALLBACK_ANSWER"]
MARGIN = 3.0  # seconds kept free for Python and for writing the answer
KNOWN_STEPS = ("dedup", "letter", "logprobs", "pot")
DEFAULT_STEPS = CONFIG.get("REASON_STEPS", "letter")
POT_MIN_SECONDS = float(CONFIG.get("POT_MIN_SECONDS", "20"))
CALIBRATION = CONFIG.get("CALIBRATION", "cf")  # cf = content-free prior, none = raw


def parse_steps(steps):
    """'dedup, logprobs,pot' -> ['dedup', 'logprobs', 'pot'], validated."""
    if steps is None:
        steps = DEFAULT_STEPS
    if isinstance(steps, str):
        steps = [s.strip() for s in steps.split(",") if s.strip()]
    unknown = [s for s in steps if s not in KNOWN_STEPS]
    if unknown:
        raise ValueError(f"unknown step(s) {unknown}; known: {', '.join(KNOWN_STEPS)}")
    if not steps or not ({"letter", "logprobs"} & set(steps)):
        steps = list(steps) + ["letter"]  # the model must always get a chance to answer
    return list(steps)


def prepare(steps=None, llm_url=URL):
    """Do the one-off work (the calibration prompts) before the first problem is timed."""
    steps = parse_steps(steps)
    if "logprobs" in steps and CALIBRATION == "cf":
        from .logprobs import content_free_prior
        try:
            content_free_prior(url=llm_url)
        except (socket.timeout, TimeoutError, urllib.error.URLError, KeyError, ValueError) as error:
            # Never let the warm-up stop the official run: answer with raw probabilities
            print(f"warning: calibration skipped ({error}); using raw letter probabilities",
                  file=sys.stderr)
            content_free_prior.disabled = True


def _is_timeout(error):
    return isinstance(error, (socket.timeout, TimeoutError)) or (
        isinstance(error, urllib.error.URLError) and isinstance(error.reason, (socket.timeout, TimeoutError)))


def solve(problem, index=None, k=0, exclude_id=None, image_b64=None, llm_url=URL,
          time_limit=TIME_LIMIT, steps=None):
    """Return {"answer", "seconds", "status", "method", "detail", ...} for one problem.

    index and k turn on retrieval: the k most similar solved problems are added to
    the prompt as examples. index is also what the "dedup" step searches.
    image_b64 and llm_url send the problem image to a vision server (letter step only).
    """
    start = time.perf_counter()
    steps = parse_steps(steps)
    result = {"answer": FALLBACK, "status": "ok", "prompt_tokens": 0, "retrieved": "",
              "examples": [], "method": "fallback", "detail": ""}
    notes = []

    def remaining():
        return time_limit - (time.perf_counter() - start) - MARGIN

    try:
        if "dedup" in steps and index is not None:
            from .dedup import find_duplicate
            letter, detail = find_duplicate(problem, index, exclude_id=exclude_id)
            notes.append("dedup=" + detail)
            if letter:
                result.update(answer=letter, method="dedup")
                steps = []  # settled without the model

        examples = []
        if steps and index is not None and k > 0:
            hits = index.search(problem, k=k, exclude_id=exclude_id)
            examples = [p for _score, p in hits]
            result["examples"] = hits
            result["retrieved"] = ";".join(f"{p['id']}:{s:.2f}" for s, p in hits)

        if "logprobs" in steps:
            from .logprobs import choose, content_free_prior, letter_logprobs
            prior = None
            if CALIBRATION == "cf" and not getattr(content_free_prior, "disabled", False):
                prior = content_free_prior(url=llm_url)
            scores, grammar_letter, timings = letter_logprobs(
                problem, examples, timeout=max(remaining(), 1.0), url=llm_url)
            letter, calibrated = choose(scores, prior)
            result.update(answer=letter, method="logprobs", prompt_tokens=timings.get("prompt_n", 0))
            notes.append("logprobs=" + " ".join(f"{l}:{calibrated[l]:.2f}" for l in "ABCDE")
                         + f" raw={grammar_letter}")
        elif "letter" in steps:
            letter, timings = answer_letter(problem, examples, timeout=max(remaining(), 1.0),
                                            image_b64=image_b64, url=llm_url)
            result.update(answer=letter, method="letter", prompt_tokens=timings.get("prompt_n", 0))

        if "pot" in steps:
            from .pot import applicable, solve_with_program
            if not applicable(problem):
                notes.append("pot=skipped:options-not-numeric")
            elif remaining() < POT_MIN_SECONDS:
                notes.append(f"pot=skipped:{remaining():.0f}s-left")
            else:
                try:
                    letter, detail, timings = solve_with_program(
                        problem, timeout=max(remaining(), 1.0), url=llm_url)
                    notes.append("pot=" + detail)
                    result["prompt_tokens"] += timings.get("prompt_n", 0)
                    if letter:
                        result.update(answer=letter, method="pot")
                except (socket.timeout, TimeoutError, urllib.error.URLError) as error:
                    if not _is_timeout(error):
                        raise
                    notes.append("pot=timeout")  # the previous step's answer stands
    except (socket.timeout, TimeoutError, urllib.error.URLError) as error:
        result["status"] = "timeout" if _is_timeout(error) else f"error: {error.reason}"
    result["detail"] = " | ".join(notes)
    result["seconds"] = round(time.perf_counter() - start, 2)
    return result
