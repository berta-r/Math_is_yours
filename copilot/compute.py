"""Compute-first solver: the model writes ONE Python expression, Python computes the answer.

Why: asked for a letter, the small models pick a position, not a value (see
docs/EXPERIMENTS.md). Asked to *translate* the problem into a short calculation,
a small code model is right far more often, because Python does the counting.

For each problem, while there is time:

    1. "blind" try: the model sees only the statement and writes one expression
       (about 20-40 tokens). copilot/safe_eval.py evaluates it (whitelist, no free
       exec). If the value equals one of the options, that is the answer.
    2. "informed" try: the model also sees the possible answers. It may compute,
       or answer directly with one of them.
    3. If that gave nothing, one line of feedback and another informed try.
    4. Otherwise we guess, without the model.

Each kind of try has its own examples in its own system prompt. llama-server
keeps one cached prompt per slot, so the server must run with --parallel 2
(board/06_compute_server.sh does that): slot 0 holds the blind examples, slot 1
the informed ones, and each is read once, in warm_up(), not once per problem.
Use a dedicated server for this model (COMPUTE_PORT), so no other program
evicts those caches during the official run.

Turn it on with SOLVER=compute in config.env. copilot/llm.py then routes
answer_letter() here, so predict.py and eval.py need no change.
"""
import ast
import hashlib
import os
import re
import socket
import sys
import time
import urllib.error

from .client import post
from .config import CONFIG
from .safe_eval import SafeEvalError, extract_expression, safe_eval
from .values import match_option, normalize_text

LETTERS = "ABCDE"
PORT = CONFIG.get("COMPUTE_PORT") or CONFIG["LLM_PORT"]
URL = f"http://127.0.0.1:{PORT}/v1/chat/completions"
MAX_TOKENS = int(CONFIG.get("COMPUTE_MAX_TOKENS", "48"))   # an expression is rarely longer
MAX_TRIES = int(CONFIG.get("COMPUTE_TRIES", "3"))          # stops earlier when time runs out
GUESS = CONFIG.get("COMPUTE_GUESS", "balance")             # balance | fixed
DEBUG = os.environ.get("COMPUTE_DEBUG", CONFIG.get("COMPUTE_DEBUG", "0")) == "1"
SAFETY = 0.9             # trust only this share of the measured speed when planning time
MIN_TOKENS = 6           # room the informed try needs: a direct answer is 2 to 5 tokens
MIN_BLIND_TOKENS = 14    # room the blind try needs: a useful expression is rarely shorter
RESERVE_TOKENS = 12      # writing room set aside for the informed try, and needed for a retry
CHARS_PER_TOKEN = 3.0    # rough, on the pessimistic side, used only until the server has counted

MODE = CONFIG.get("COMPUTE_MODE", "both")                   # both | informed | blind

# Stable system prompts: each is read once, then cached by llama-server in its slot.
# Do not edit them between problems, and keep the examples different from any test problem.
_RULES = ("Let Python do the work: try every case with range() and count, sum, min or max. "
          "Reply with the expression only, on one line: no words, no code fences, no \"=\".\n"
          "You may use: + - * / // % **, comparisons, and, or, not, sum, len, min, max, abs, sorted, set, str, int, "
          "range, all, any, math.gcd, math.lcm, math.comb, math.factorial, math.prod, Fraction, "
          "itertools.permutations, itertools.combinations, itertools.product.")
_EXAMPLES = [  # (problem, possible answers, expression)
    ("Anna has 3 bags with 4 apples in each bag. She eats 2 apples. How many apples are left?",
     "5; 9; 10; 12; 14", "3 * 4 - 2"),
    ("How many two-digit numbers have digits that add up to 5?",
     "4; 5; 6; 9; 10", "sum(1 for n in range(10, 100) if n // 10 + n % 10 == 5)"),
    ("What is the smallest positive whole number that is divisible by 6 and by 8 and leaves a remainder of 3 "
     "when divided by 5?",
     "24; 48; 63; 72; 96", "min(n for n in range(1, 10000) if n % 6 == 0 and n % 8 == 0 and n % 5 == 3)"),
    ("Quants nombres enters de l'1 al 50 són múltiples de 3 però no de 6?",
     "6; 8; 9; 16; 17", "sum(1 for n in range(1, 51) if n % 3 == 0 and n % 6 != 0)"),
    ("How many three-digit numbers have three different digits?",
     "504; 648; 720; 729; 900", "sum(1 for n in range(100, 1000) if len(set(str(n))) == 3)"),
    ("Two dice are rolled. What is the probability that the sum is 9?",
     "1/12; 1/9; 1/6; 1/4; 1/3", "Fraction(sum(1 for a in range(1, 7) for b in range(1, 7) if a + b == 9), 36)"),
    ("In how many ways can 3 of 7 different books be placed in a row?",
     "21; 35; 210; 343; 5040", "len(list(itertools.permutations(range(7), 3)))"),
    ("A snail climbs 4 m each day and slips back 1 m each night. On which day does it first reach the top "
     "of a 10 m wall?",
     "2; 3; 4; 5; 10", "min(d for d in range(1, 100) if 4 * d - 1 * (d - 1) >= 10)"),
    ("Avui és dilluns. Quin dia de la setmana serà d'aquí a 100 dies?",
     "dilluns; dimarts; dimecres; dijous; divendres",
     '["dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"][100 % 7]'),
    ("What is the last digit of 3^100?", "1; 3; 5; 7; 9", "3 ** 100 % 10"),
]
SYSTEM_BLIND = (
    "You turn a maths competition problem into ONE Python expression whose value is the answer. " + _RULES
    + "".join(f"\n\nProblem: {q}\nExpression: {e}" for q, _a, e in _EXAMPLES))
SYSTEM_INFORMED = (
    "You solve a maths competition problem by writing ONE Python expression whose value is the answer. "
    "The answer is always one of the possible answers listed. " + _RULES
    + " If the possible answers are words, reply with the right one in quotes."
    + "".join(f"\n\nProblem: {q}\nPossible answers: {a}\nExpression: {e}" for q, a, e in _EXAMPLES))
PROMPTS = {"blind": (0, SYSTEM_BLIND), "informed": (1, SYSTEM_INFORMED)}   # kind: (server slot, system prompt)

WARM_UP = [  # (problem text, possible answers): the first one is long enough to time the model
    ("How many whole numbers from 1 to 100 are divisible by 7 but not by 2?", "5; 7; 8; 14; 50"),
    ("What is 2 + 3?", "4; 5; 6; 7; 8"),
]

_state = {
    "warm": False, "usable": True, "kinds": [], "slots": True,
    "read_tps": float(CONFIG.get("COMPUTE_READ_TPS", "0") or 0),   # 0 = measure in warm_up()
    "gen_tps": float(CONFIG.get("COMPUTE_GEN_TPS", "0") or 0),
    "answered": {letter: 0 for letter in LETTERS},   # letters the model has given so far
    "guessed": {letter: 0 for letter in LETTERS},    # letters given by a guess so far
}


class Unavailable(Exception):
    """The compute server can't be used: the caller falls back to the plain letter call."""


def _say(message):
    print(f"[compute] {message}", file=sys.stderr, flush=True)


def _is_timeout(error):
    return isinstance(error, (socket.timeout, TimeoutError)) or (
        isinstance(error, urllib.error.URLError) and isinstance(error.reason, (socket.timeout, TimeoutError)))


def _chat(kind, turns, max_tokens, timeout, url):
    """One model call. kind picks the system prompt and the server slot that caches it."""
    slot, system = PROMPTS[kind]
    payload = {
        "messages": [{"role": "system", "content": system}] + turns,
        "max_tokens": max_tokens, "temperature": 0, "seed": int(CONFIG["SEED"]),
        "cache_prompt": True,
        "stop": ["\n\n", "\nProblem", "\nExpression", "\nPossible"],
    }
    if _state["slots"]:
        payload["id_slot"] = slot
    response = post(url, payload, timeout=timeout)
    return (response["choices"][0]["message"]["content"] or ""), response.get("timings", {})


def _user_message(kind, text, answers):
    if kind == "informed":
        return f"Problem: {text}\nPossible answers: {answers}\nExpression:"
    return f"Problem: {text}\nExpression:"


def _ask_warm_up(kind, which, max_tokens, url):
    text, answers = WARM_UP[which]
    return _chat(kind, [{"role": "user", "content": _user_message(kind, text, answers)}], max_tokens, 900, url)


def warm_up(url=URL, force=False):
    """Read the examples once (outside any problem's clock), time the model, check the cache.

    Safe to call many times. Never raises: on failure the solver is marked unusable
    and answer() raises Unavailable, so the caller falls back to the letter call.
    """
    if _state["warm"] and not force:
        return _state["usable"]
    _state["warm"] = True
    started = time.perf_counter()
    kinds = {"both": ["blind", "informed"], "blind": ["blind"]}.get(MODE, ["informed"])
    try:
        _say(f"warming up the model on port {PORT} (one-off: it reads the examples once)...")
        try:
            first = {kind: _ask_warm_up(kind, 0, 32, url) for kind in kinds}
        except urllib.error.HTTPError:
            # The server refused a slot number: it runs with one slot. Use one prompt only.
            _say("the server has a single slot: start it with --parallel 2. Using the informed try only.")
            _state["slots"] = False
            kinds = ["informed"]
            first = {"informed": _ask_warm_up("informed", 0, 32, url)}
        # Second round: a kind is usable only if its examples were NOT read again,
        # even after the other kind used the server in between.
        reread = {kind: int(_ask_warm_up(kind, 1, 8, url)[1].get("prompt_n") or 0) for kind in kinds}
        if len(kinds) == 2 and max(reread.values()) > 120:
            _say(f"the server keeps only one cached prompt (re-read {reread}): start it with --parallel 2. "
                 "Using the informed try only.")
            kinds = ["informed"]
            _ask_warm_up("informed", 0, 8, url)
            reread = {"informed": int(_ask_warm_up("informed", 1, 8, url)[1].get("prompt_n") or 0)}
    except (OSError, urllib.error.URLError, KeyError, ValueError) as error:
        _state["usable"] = False
        _say(f"not available ({error}); answering with the plain letter call instead")
        return False
    if max(reread.values()) > 120:   # without the cache every problem would time out
        _state["usable"] = False
        _say(f"the server did not cache the examples (re-read {reread}); "
             "answering with the plain letter call instead")
        return False
    text, t = first[kinds[0]] if kinds[0] in first else first["informed"]
    # When the examples were already cached (a second run), only a few tokens are read: still a fair timing
    read = float(t.get("prompt_per_second") or 0) if int(t.get("prompt_n") or 0) >= 8 else 0.0
    gen = float(t.get("predicted_per_second") or 0) if int(t.get("predicted_n") or 0) >= 8 else 0.0
    _state["read_tps"] = _state["read_tps"] or read or 5.0
    _state["gen_tps"] = _state["gen_tps"] or gen or 2.5
    _state["kinds"] = kinds
    _say(f"ready in {time.perf_counter() - started:.0f} s ({' + '.join(kinds)}): reads {_state['read_tps']:.1f} tok/s, "
         f"writes {_state['gen_tps']:.1f} tok/s; warm-up answer: {text.strip()[:60]!r}")
    return True


def clean_text(text):
    """The statement without its leading problem number ("12. ...")."""
    return re.sub(r"^\s*\d+\s*[.)]\s*", "", str(text).strip())


def clean_options(options):
    """Options as text, with the commonest OCR slip fixed (the letter O for the digit 0)."""
    out = {}
    for letter in LETTERS:
        if letter in (options or {}):
            value = str(options[letter]).strip()
            out[letter] = "0" if value in ("O", "o") else value
    return out


def _loose(text):
    """For comparing words read by OCR: 'LIuC' and 'Lluc' are the same."""
    return normalize_text(text).replace("i", "l").replace("1", "l").replace("0", "o").strip(".,;:")


def match_value(value, options):
    """The single letter whose option equals value, or None."""
    letter = match_option(value, options)
    if letter:
        return letter
    if isinstance(value, str):
        hits = [l for l in LETTERS if l in options and _loose(options[l]) == _loose(value)]
        if len(hits) == 1:
            return hits[0]
    return None


def _is_literal(expression):
    """True for a bare number or word: the model answered directly instead of computing."""
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return False
    if isinstance(node, ast.UnaryOp):
        node = node.operand
    return isinstance(node, ast.Constant)


def _evaluate(text, options, eval_timeout=6.0):
    """Return (letter, kind, note). kind: computed | direct | nomatch | invalid."""
    expression = extract_expression(text)
    if not expression:
        return None, "invalid", "empty"
    # A word or a time copied from the options ("Marc", "9:10") is a direct answer
    direct = match_value(expression.strip("\"'"), options)
    try:
        value = safe_eval(expression, timeout=eval_timeout)
    except SafeEvalError as error:
        if direct:
            return direct, "direct", expression
        return None, "invalid", f"{expression[:80]} ({str(error).split(':')[0]})"
    except Exception as error:  # an expression must never stop the run
        return None, "invalid", f"{expression[:80]} ({type(error).__name__})"
    letter = match_value(value, options)
    shown = f"{expression[:100]} = {value!r}"[:140]
    if letter:
        return letter, ("direct" if _is_literal(expression) else "computed"), shown
    return None, "nomatch", shown


def _feedback(kind, note, answers):
    if kind == "invalid":
        return (f"That is not a valid Python expression. The answer is one of: {answers}. "
                "Write ONE expression that computes it.\nExpression:")
    if kind == "direct":
        return (f"Do not guess. The answer is one of: {answers}. Write ONE expression that computes it "
                "by trying every case.\nExpression:")
    value = note.rsplit(" = ", 1)[-1][:40]
    return (f"That gives {value}, but the answer is one of: {answers}. Read the problem again and "
            "write a different expression.\nExpression:")


def _guess(problem, options):
    """No calculation settled it: pick a letter without the model.

    balance: the answer keys of this competition use every letter equally often
    (the organisers' practice set says so), so prefer the letter the model has
    given least so far, then the one guessed least. Ties are ordered by the
    problem id, so a run always gives the same letters. fixed: FALLBACK_ANSWER.
    """
    letters = [l for l in LETTERS if l in options] or list(LETTERS)
    if GUESS != "balance":
        fallback = CONFIG["FALLBACK_ANSWER"]
        return fallback if fallback in letters else letters[0]
    digest = hashlib.sha256(str(problem.get("id", problem.get("text", ""))).encode()).hexdigest()
    order = sorted(letters, key=lambda l: hashlib.sha256((digest + l).encode()).hexdigest())
    return min(order, key=lambda l: (_state["answered"][l], _state["guessed"][l]))


def answer(problem, timeout=57.0, url=URL):
    """Return (letter, timings, info). info["method"]: computed | direct | guess."""
    if not _state["warm"]:
        warm_up(url)          # normally done before the first problem; this is the safety net
    start = time.perf_counter()
    deadline = start + max(float(timeout) - 1.0, 1.0)
    if not _state["usable"]:
        raise Unavailable("compute server not usable")

    options = clean_options(problem.get("options"))
    timings = {"prompt_n": 0, "predicted_n": 0}
    info = {"method": "guess", "tries": [], "seconds": 0.0}

    def finish(letter, method):
        info["method"] = method
        info["seconds"] = round(time.perf_counter() - start, 2)
        if letter in LETTERS:
            _state["guessed" if method == "guess" else "answered"][letter] += 1
        if DEBUG:
            _say(f"{problem.get('id', '?')} -> {letter} ({method}, {info['seconds']:.1f} s) "
                 + " || ".join(f"{t['kind']}: {t['note']}" for t in info["tries"]))
        return letter, timings, info

    if len(options) < 2:
        return finish(_guess(problem, options), "guess")           # nothing to match a value against
    if problem.get("text_only") is False:
        info["tries"].append({"kind": "skipped", "note": "needs its figure"})
        return finish(_guess(problem, options), "guess")           # the figure is not in the text

    answers = "; ".join(options[l] for l in LETTERS if l in options)
    text = clean_text(problem.get("text", ""))
    kinds = _state["kinds"] or ["informed"]

    def speeds():
        return max(_state["read_tps"] * SAFETY, 0.1), max(_state["gen_tps"] * SAFETY, 0.1)

    def learn(t):
        """Remember the best speed the board has shown. A busy moment (someone else using
        the board) must not make the plan give up: the request's own timeout is the limit."""
        if int(t.get("prompt_n") or 0) >= 30 and float(t.get("prompt_per_second") or 0) > 0:
            _state["read_tps"] = max(_state["read_tps"], float(t["prompt_per_second"]))
        if int(t.get("predicted_n") or 0) >= 10 and float(t.get("predicted_per_second") or 0) > 0:
            _state["gen_tps"] = max(_state["gen_tps"], float(t["predicted_per_second"]))

    def ask(kind, turns, room):
        """One try. Returns (letter, result, note, reply), or None when it could not run."""
        remaining = deadline - time.perf_counter()
        try:
            reply, t = _chat(kind, turns, max(1, min(MAX_TOKENS, room)), max(remaining, 1.0), url)
        except (socket.timeout, TimeoutError, urllib.error.URLError) as error:
            if not _is_timeout(error) and not info["tries"]:
                _state["usable"] = False
                raise Unavailable(str(error))
            info["tries"].append({"kind": f"{kind}:timeout", "note": ""})
            return None
        learn(t)
        timings["prompt_n"] += int(t.get("prompt_n") or 0)
        timings["predicted_n"] += int(t.get("predicted_n") or 0)
        # A brute-force search can take seconds on the board: give it what the clock allows
        letter, result, note = _evaluate(reply, options, min(6.0, max(1.0, deadline - time.perf_counter() - 1.0)))
        if kind == "blind" and result == "direct":
            result, letter = "nomatch", None    # a bare number without seeing the options is a blind guess
        info["tries"].append({"kind": f"{kind}:{result}", "note": note, "letter": letter,
                              "prompt_n": int(t.get("prompt_n") or 0), "predicted_n": int(t.get("predicted_n") or 0)})
        return letter, result, note, reply

    # Tokens to read. Before the first call this is an estimate from the length; after
    # the blind try the server has counted the statement, so the informed try knows.
    statement = len(_user_message("blind", text, answers)) / CHARS_PER_TOKEN + 10
    listed = len(answers) / CHARS_PER_TOKEN + 8

    # 1. Blind try, with the time for the informed try set aside first. The informed
    #    try answers more problems, so when only one fits, it is the one that runs.
    if "blind" in kinds:
        read_tps, gen_tps = speeds()
        remaining = deadline - time.perf_counter()
        reserve = ((statement + listed) / read_tps + RESERVE_TOKENS / gen_tps) if "informed" in kinds else 0.0
        room = int((remaining - statement / read_tps - reserve) * gen_tps)
        if room >= MIN_BLIND_TOKENS:
            done = ask("blind", [{"role": "user", "content": _user_message("blind", text, answers)}], room)
            if done:
                if done[1] == "computed":
                    return finish(done[0], "computed")
                counted = info["tries"][-1].get("prompt_n") or 0
                if counted >= 10:
                    statement = counted          # the real size, counted by the server
                    listed = len(answers) / CHARS_PER_TOKEN + 4
        else:
            info["tries"].append({"kind": "blind:skipped", "note": "no time for two tries"})

    # 2. Informed try, then retries with one line of feedback while time remains.
    if "informed" in kinds:
        turns = [{"role": "user", "content": _user_message("informed", text, answers)}]
        to_read = statement + listed
        for attempt in range(max(1, MAX_TRIES - (1 if "blind" in kinds else 0))):
            read_tps, gen_tps = speeds()
            remaining = deadline - time.perf_counter()
            room = int((remaining - to_read / read_tps) * gen_tps)
            fresh = all(t["kind"].endswith("skipped") for t in info["tries"])   # nothing has used the clock yet
            if attempt == 0 and fresh:
                room = max(room, MIN_TOKENS)     # with the whole time available, always try
            elif room < (MIN_TOKENS if attempt == 0 else RESERVE_TOKENS):
                info["tries"].append({"kind": "informed:stopped", "note": f"{remaining:.0f} s left"})
                break
            done = ask("informed", turns, room)
            if not done:
                break
            letter, result, note, reply = done
            if result in ("computed", "direct"):
                return finish(letter, result)   # asking again rarely turns a direct answer into a calculation
            feedback = _feedback(result, note, answers)
            turns = turns + [{"role": "assistant", "content": reply}, {"role": "user", "content": feedback}]
            to_read = len(feedback) / CHARS_PER_TOKEN + 12

    return finish(_guess(problem, options), "guess")


def answer_letter(problem, timeout=57.0, url=URL):
    """Same shape as copilot.llm.answer_letter: (letter, timings)."""
    letter, timings, _info = answer(problem, timeout=timeout, url=url)
    return letter, timings
