"""Pick the letter from the model's probabilities for A-E, after removing its letter bias.

The baseline asks for one token under the grammar [A-E] and takes whatever comes out.
Here we also read the probability the model gives to each letter, and we divide out
the probability it gives to each letter when the problem is *empty* (contextual
calibration). A model that says "D" for every problem gets that habit subtracted.

    score(letter) = log p(letter | problem) - log p(letter | content-free problem)

The content-free prior is measured once per process (three tiny prompts) and cached.
"""
import math

from .config import CONFIG
from .client import post
from .llm import URL, build_messages
from .values import LETTERS

FLOOR = -30.0  # log-probability given to a letter the server did not list
TOP_N = 10     # letters are not always the top-5 tokens; ask for a few more
CONTENT_FREE = ("N/A", "", "[MASK]")
_prior_cache = {}


def letter_logprobs(problem, examples=(), timeout=60, url=URL):
    """Return ({letter: logprob}, grammar_letter, timings) for one problem."""
    response = post(url, {
        "messages": build_messages(problem, examples),
        "grammar": "root ::= [A-E]",
        "max_tokens": 1,
        "temperature": 0,
        "seed": int(CONFIG["SEED"]),
        "cache_prompt": True,
        "logprobs": True,
        "top_logprobs": TOP_N,
    }, timeout=timeout)
    choice = response["choices"][0]
    letter = (choice["message"]["content"] or "").strip()[:1]
    scores = _parse_top_logprobs(choice.get("logprobs"))
    if letter in LETTERS and letter not in scores:
        scores[letter] = max(scores.values(), default=0.0)  # the server picked it, so it leads
    return scores, letter, response.get("timings", {})


def _parse_top_logprobs(logprobs):
    """{letter: logprob} from llama-server's OpenAI-style logprobs block; {} when missing."""
    scores = {}
    if not logprobs:
        return scores
    content = logprobs.get("content") or []
    if not content:
        return scores
    first = content[0]
    candidates = list(first.get("top_logprobs") or [])
    if first.get("token") is not None:
        candidates.append(first)
    for item in candidates:
        token = (item.get("token") or "").strip().upper()
        if len(token) == 1 and token in LETTERS:
            value = float(item.get("logprob", FLOOR))
            if token not in scores or value > scores[token]:
                scores[token] = value
    return scores


def content_free_prior(timeout=30, url=URL):
    """Mean probability of each letter on empty problems: the model's own bias."""
    if url in _prior_cache:
        return _prior_cache[url]
    totals = {letter: 0.0 for letter in LETTERS}
    for filler in CONTENT_FREE:
        problem = {"text": filler, "options": {letter: filler for letter in LETTERS}}
        scores, _letter, _timings = letter_logprobs(problem, timeout=timeout, url=url)
        probs = _softmax(scores)
        for letter in LETTERS:
            totals[letter] += probs[letter] / len(CONTENT_FREE)
    _prior_cache[url] = totals
    return totals


def _softmax(scores):
    values = {letter: scores.get(letter, FLOOR) for letter in LETTERS}
    top = max(values.values())
    weights = {letter: math.exp(v - top) for letter, v in values.items()}
    total = sum(weights.values()) or 1.0
    return {letter: w / total for letter, w in weights.items()}


def calibrated_scores(scores, prior=None):
    """log p(letter | problem) - log prior(letter), for every letter."""
    probs = _softmax(scores)
    out = {}
    for letter in LETTERS:
        p = max(probs[letter], 1e-12)
        q = max((prior or {}).get(letter, 0.2), 1e-12)
        out[letter] = math.log(p) - math.log(q)
    return out


def choose(scores, prior=None):
    """The letter with the best calibrated score; ties go to the alphabetical first."""
    calibrated = calibrated_scores(scores, prior)
    return max(LETTERS, key=lambda letter: (calibrated[letter], -LETTERS.index(letter))), calibrated
