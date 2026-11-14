"""Program of thought: the model writes one Python expression, Python computes it.

A 0.8B model cannot reason for hundreds of tokens inside 60 s, but it can often
translate a counting or arithmetic problem into a short expression (50-100 tokens).
Python then does the arithmetic and the exhaustive search without mistakes, and the
result is looked up among the options. If the result matches no option we know the
attempt failed and keep the letter from the previous step.

Only problems whose five options are plain numbers are tried. The expression is
checked against a whitelist (copilot/safe_eval.py) and never executed freely.
"""
from .config import CONFIG
from .client import post
from .llm import URL, format_problem
from .safe_eval import SafeEvalError, extract_expression, safe_eval
from .values import match_option, numeric_options

MAX_TOKENS = int(CONFIG.get("POT_MAX_TOKENS", "96"))

# Stable system prompt: llama-server caches it, so the examples are read only once.
SYSTEM = """You translate a maths competition problem into ONE Python expression that computes the answer. Reply with the expression only: no words, no explanation, no code fences. Allowed: numbers, + - * / // % **, comparisons, sum, len, min, max, abs, range, sorted, math.gcd, math.comb, math.factorial, Fraction, generator expressions.

Problem: Anna has 3 bags with 4 apples in each bag. She eats 2 apples. How many apples are left?
Expression: 3 * 4 - 2

Problem: How many two-digit numbers have digits that add up to 5?
Expression: sum(1 for n in range(10, 100) if n // 10 + n % 10 == 5)

Problem: A square has a perimeter of 36 cm. What is its area in cm²?
Expression: (36 / 4) ** 2

Problem: In how many ways can 2 of 5 children be chosen?
Expression: math.comb(5, 2)"""


def build_messages(problem):
    user = "Problem: " + format_problem(problem) + "\nExpression:"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def applicable(problem):
    return bool(numeric_options(problem.get("options")))


def solve_with_program(problem, timeout=30, url=URL):
    """Return (letter, detail, timings). letter is None when the program does not settle it."""
    response = post(url, {
        "messages": build_messages(problem),
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "seed": int(CONFIG["SEED"]),
        "cache_prompt": True,
        "stop": ["\n\n", "Problem:"],
    }, timeout=timeout)
    text = response["choices"][0]["message"]["content"] or ""
    timings = response.get("timings", {})
    expression = extract_expression(text)
    if not expression:
        return None, "empty", timings
    try:
        value = safe_eval(expression, timeout=2.0)
    except SafeEvalError as error:
        return None, f"{expression!r}:{error}", timings
    letter = match_option(value, problem.get("options"))
    detail = f"{expression!r}={value!r}" + ("" if letter else ":not-in-options")
    return letter, detail, timings
