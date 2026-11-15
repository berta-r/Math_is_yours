"""Checks for child-facing content, shared by the authored bank and generated files. Standard library only.

The board re-verifies large-model content (D-013) against the loaded problem before
serving it, with the same rules the laptop verifier (laptop/ml/verify_content.py)
applied when the content was generated. Every helper here is pure and cheap.

    leaks(text, correct_value, correct_letter)       -> bool
    within(text, max_words)                         -> bool
    valid_steps(steps, where)                       -> raises ValueError (the bank rules)
    verify_generated_steps(steps, problem)          -> (ok, reason)
    verify_generated_solution(item, problem)        -> (ok, reason)
    verify_generated_explanation(item, problem, letter) -> (ok, reason)

`problem` is a prepared row: {"id", "language", "options", "label", ...}.
"""
import re
from fractions import Fraction

STAGES = ('understand', 'plan', 'check')
LETTERS = 'ABCDE'
MAX_EXPLANATION_WORDS = 60
MAX_QUESTION_WORDS = 30
MAX_SOLUTION_WORDS = 120
MAX_HINT_WORDS = 25

# A number not glued to letters or other digits; "1,5" and "1.5" are decimals and
# "1 000" is a grouped integer (same rule as laptop/ml/verify_content.py).
NUMBER = re.compile(r'(?<![\w.,])(\d{1,3}(?: \d{3})+|\d+(?:[.,]\d+)?)(?![\w]|[.,]\d)')
OPTION_NUMBER = re.compile(r'-?\d+(?:[.,]\d+)?')


def words(text):
    return len(text.split())


def within(text, max_words):
    """True for non-empty text of at most `max_words` words."""
    return isinstance(text, str) and bool(text.strip()) and words(text) <= max_words


def _fraction(raw):
    try:
        return Fraction(raw.replace(' ', '').replace(',', '.'))
    except (ValueError, ZeroDivisionError):
        return None


def value_leak(text, correct_value, numeric=True):
    """Whole-token match of the correct option's text, or (numeric) any number equal to its value."""
    value = (correct_value or '').strip()
    if not value or not isinstance(text, str):
        return False
    # Token boundaries: the value "5" is not leaked by "15", but "5 cm" or "is 5" is.
    if re.search(r'(?<!\w)' + re.escape(value) + r'(?!\w)', text, re.I):
        return True
    if not numeric:
        return False
    match = OPTION_NUMBER.search(value.replace(' ', ''))
    correct = _fraction(match.group()) if match else None
    return correct is not None and any(_fraction(m.group(1)) == correct for m in NUMBER.finditer(text))


def letter_leak(text, letter):
    """True when `text` names `letter` as the answer: "answer is B", "(B)", "B)", "letter B", "option B".

    B to E are never words in English or Catalan, so any standalone capital B-E counts;
    "A" is an article, so for A only the explicit patterns count.
    """
    if not letter or letter not in LETTERS or not isinstance(text, str):
        return False
    L = re.escape(letter)
    patterns = [r'\(\s*' + L + r'\s*\)', r'(?<![\w])' + L + r'\)',
                r'\b(?i:answer|option|letter|choice|resposta|opció|opcio|lletra)\s*(?i:is|és|es|=|:)?\s*["\'«]?' + L + r'(?![\w\'’])',
                r'\b(?i:is|és)\s+' + L + r'(?![\w\'’])\s*[.!]?$']
    if letter != 'A':
        patterns.append(r'(?<![\w\'’])' + L + r'(?![\w\'’])')
    return any(re.search(p, text) for p in patterns)


def leaks(text, correct_value, correct_letter=None, numeric=True):
    """True when `text` gives away the correct option, by its value or by its letter."""
    return value_leak(text, correct_value, numeric) or letter_leak(text, correct_letter)


def valid_steps(steps, where):
    """The thinking-step bank rules (knowledge/README.md, "Thinking steps"); raises ValueError."""
    if not isinstance(steps, list) or len(steps) != len(STAGES):
        raise ValueError(f'Thinking steps for {where}: expected exactly {len(STAGES)} steps')
    for expected, step in zip(STAGES, steps):
        if not isinstance(step, dict) or step.get('stage') != expected:
            raise ValueError(f'Thinking steps for {where}: stages must be {", ".join(STAGES)} in that order')
        label = f'Thinking step {where}/{expected}'
        for key in ('language', 'question', 'why'):
            if not isinstance(step.get(key), str) or not step[key].strip():
                raise ValueError(f'{label}: {key} must be non-empty text')
        options = step.get('options')
        if not isinstance(options, list) or len(options) != 3 or any(not isinstance(o, str) or not o.strip() for o in options):
            raise ValueError(f'{label}: exactly three non-empty options are required')
        if len(set(o.strip().lower() for o in options)) != 3:
            raise ValueError(f'{label}: options must be distinct')
        if type(step.get('answer')) is not int or not 0 <= step['answer'] <= 2:
            raise ValueError(f'{label}: answer must be an integer from 0 to 2')
        counts = [words(o) for o in options]
        if max(counts) > 10 or max(counts) - min(counts) > 2:
            raise ValueError(f'{label}: options need at most 10 words and word counts within 2 of each other')
        if any(o.split()[0].strip(',.').lower() in ('all', 'none', 'both') for o in options):
            raise ValueError(f'{label}: options may not start with "All", "None" or "Both"')
        if words(step['question']) > 25 or words(step['why']) > 25:
            raise ValueError(f'{label}: question and why must be at most 25 words')
        why = step['why'].strip()
        if why[-1] not in '.!?' or re.search(r'[.!?]\s', why):
            raise ValueError(f'{label}: why must be exactly one sentence')
    if len({step['language'] for step in steps}) != 1:
        raise ValueError(f'Thinking steps for {where}: all steps need the same language')


def _correct(problem):
    label = problem.get('label')
    if label not in LETTERS:
        return None, None
    return (problem.get('options') or {}).get(label), label


def verify_generated_steps(steps, problem):
    """Bank rules, the problem's language, and no step text that names the correct value or letter."""
    try:
        valid_steps(steps, 'generated')
    except ValueError as error:
        return False, str(error)
    if steps[0]['language'] != problem.get('language'):
        return False, 'language mismatch'
    value, letter = _correct(problem)
    if letter is None:
        return False, 'no answer key to verify against'
    if any(leaks(text, value, letter) for step in steps for text in [step['question'], step['why'], *step['options']]):
        return False, 'leaks the correct option'
    return True, ''


def verify_generated_hints(hints, problem):
    """Three distinct short hints, none naming the correct value or letter."""
    if not isinstance(hints, list) or len(hints) != 3 or not all(within(h, MAX_HINT_WORDS) for h in hints):
        return False, f'expected three hints of at most {MAX_HINT_WORDS} words'
    if len({h.strip().lower() for h in hints}) != 3:
        return False, 'hints are not distinct'
    value, letter = _correct(problem)
    if letter is None:
        return False, 'no answer key to verify against'
    if any(leaks(h, value, letter) or re.search(r'\b(?i:option|opció|lletra|letter)\s+[A-E]\b', h) for h in hints):
        return False, 'a hint leaks the correct option'
    return True, ''


def verify_generated_solution(item, problem):
    """A worked solution (shown only after the reveal gate, so it may state the value) and a leak-free hint ladder."""
    if not isinstance(item, dict):
        return False, 'not an object'
    if not within(item.get('solution'), MAX_SOLUTION_WORDS):
        return False, f'solution must be non-empty and at most {MAX_SOLUTION_WORDS} words'
    return verify_generated_hints(item.get('hints'), problem)


def verify_generated_explanation(item, problem, letter):
    """A short explanation of a wrong letter plus a Socratic question; neither may give away the answer."""
    if not isinstance(item, dict):
        return False, 'not an object'
    value, label = _correct(problem)
    if label is None or letter == label or letter not in LETTERS:
        return False, 'not a wrong letter of a keyed problem'
    explanation, question = item.get('explanation'), item.get('question')
    if not within(explanation, MAX_EXPLANATION_WORDS):
        return False, f'explanation must be non-empty and at most {MAX_EXPLANATION_WORDS} words'
    if not within(question, MAX_QUESTION_WORDS):
        return False, f'question must be non-empty and at most {MAX_QUESTION_WORDS} words'
    if leaks(explanation, value, label) or leaks(question, value, label):
        return False, 'leaks the correct option'
    return True, ''
