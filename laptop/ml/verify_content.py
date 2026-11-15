"""Checks for generated child-facing content. Standard library only, no numpy.

Importable from board code later (a nightly SLM job can run the same checks), so
it depends on nothing outside the standard library and nothing in this repo.

    verify_explanation(item, problem, label) -> (ok, reasons)
    verify_steps(steps, problem)              -> (ok, reasons)

`problem` is a prepared row: {"id", "language", "text", "options", "label"}.
`item` is {"explanation": str, "question": str} for the wrong option `label`.
`steps` is a list of three dicts in the knowledge/thinking_steps.json format.
The step rules mirror Knowledge.validate_steps in copilot/knowledge.py, plus the
leak, language and voice checks below. Reasons are short stable codes so they can
be counted in a histogram.
"""
import re
from fractions import Fraction

STAGES = ('understand', 'plan', 'check')
MAX_EXPLANATION_WORDS = 40
MAX_QUESTION_WORDS = 20
MAX_STEP_QUESTION_WORDS = 25
MAX_STEP_WHY_WORDS = 25
MAX_OPTION_WORDS = 10

# A number not glued to letters or other digits; "1,5" and "1.5" are decimals,
# "1 000" is a grouped integer. Same idea as copilot/misconceptions.py.
NUMBER = re.compile(r'(?<![\w.,])(\d{1,3}(?: \d{3})+|\d+(?:[.,]\d+)?)(?![\w]|[.,]\d)')
OPTION_NUMBER = re.compile(r'-?\d+(?:[.,]\d+)?')

# Function words: one must appear for the language, none of the other language's.
CATALAN_WORDS = {'el', 'la', 'els', 'les', 'de', 'del', 'que', 'i', 'és', 'per', 'un', 'una', 'amb', 'què',
                 'quants', 'quantes', 'quin', 'quina', 'com', 'cada', 'si', 'en', 'al', 'dels', 'has', 'pots',
                 'no', 'més', 'nombre', 'aquest', 'aquesta', 'són', 'ha', 'hi', 'tens', 'fer', 'cal'}
ENGLISH_WORDS = {'the', 'is', 'of', 'and', 'you', 'to', 'a', 'what', 'how', 'that', 'in', 'are', 'it', 'your',
                 'which', 'each', 'if', 'many', 'number', 'this', 'can', 'from', 'by', 'with', 'for', 'do'}
# Words that only one of the two languages uses (no overlap such as "a", "in", "no").
CATALAN_ONLY = {'els', 'les', 'és', 'amb', 'què', 'perquè', 'del', 'dels', 'una', 'aquest', 'aquesta', 'quants',
                'quantes', 'quin', 'quina', 'són', 'pots', 'cal', 'tens'}
ENGLISH_ONLY = {'the', 'is', 'of', 'and', 'you', 'what', 'how', 'that', 'are', 'your', 'which', 'many', 'this',
                'from', 'with', 'should', 'does', 'there'}
WORD = re.compile(r"[\wÀ-ÿ·]+", re.U)
SELF_TALK = [re.compile(p, re.I) for p in (r'\bas an ai\b', r'\blanguage model\b', r'\bcom a (ia|model)\b',
                                           r'\bassistant\b', r'\bassistent\b')]


def words(text):
    return len(text.split())


def _number(text):
    match = OPTION_NUMBER.search((text or '').replace(' ', ''))
    return Fraction(match.group().replace(',', '.')) if match else None


def _as_fraction(raw):
    return Fraction(raw.replace(' ', '').replace(',', '.'))


def letter_leak(text, letter):
    """True when `text` names the correct letter as an answer ("answer is B", "(B)", "letter B", ...).

    B to E are never words in English or Catalan, so any standalone capital B-E counts.
    "A" is an article/preposition, so for A only the explicit patterns count.
    """
    if not letter:
        return False
    L = re.escape(letter)
    patterns = [
        r'\(\s*' + L + r'\s*\)',
        r'(?<![\w])' + L + r'\)',
        r'\b(?i:answer|option|letter|choice|resposta|opció|opcio|lletra)\s*(?i:is|és|es|=|:)?\s*["\'«]?' + L + r'(?![\w\'’])',
        r'\b(?i:is|és)\s+' + L + r'(?![\w\'’])\s*[.!]?$',
    ]
    if letter != 'A':
        patterns.append(r'(?<![\w\'’])' + L + r'(?![\w\'’])')
    return any(re.search(p, text) for p in patterns)


def value_leak(text, problem):
    """True when `text` contains the correct option's value as a whole number, or its whole text."""
    label = problem.get('label')
    option = ((problem.get('options') or {}).get(label) or '').strip()
    if not option:
        return False
    if re.search(r'(?<!\w)' + re.escape(option) + r'(?!\w)', text, re.I):
        return True  # same token rule as copilot/knowledge.py leaked()
    correct = _number(option)
    if correct is None:
        return False
    return any(_as_fraction(m.group(1)) == correct for m in NUMBER.finditer(text))


def language_reasons(text, language):
    tokens = {w.lower() for w in WORD.findall(text)}
    reasons = []
    if language == 'cat':
        if not tokens & CATALAN_WORDS:
            reasons.append('language:no_catalan_words')
        if tokens & ENGLISH_ONLY:
            reasons.append('language:english_words_in_cat')
    else:
        if not tokens & ENGLISH_WORDS:
            reasons.append('language:no_english_words')
        if tokens & CATALAN_ONLY:
            reasons.append('language:catalan_words_in_eng')
    return reasons


def voice_reasons(text, language):
    reasons = []
    if language != 'cat' and re.search(r"(?<![\w'’])I(?![\w])", text):
        reasons.append('voice:first_person')
    if language == 'cat' and re.search(r'\b(jo|sóc)\b', text, re.I):
        reasons.append('voice:first_person')
    if any(p.search(text) for p in SELF_TALK):
        reasons.append('voice:as_an_ai')
    return reasons


def sentences(text):
    """Rough sentence count: terminal punctuation followed by space or end."""
    return len([s for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()])


def verify_explanation(item, problem, label):
    """Check a generated distractor explanation and Socratic question for wrong option `label`."""
    reasons = []
    if not isinstance(item, dict):
        return False, ['format:not_object']
    explanation, question = item.get('explanation'), item.get('question')
    if not isinstance(explanation, str) or not explanation.strip():
        reasons.append('format:empty_explanation')
    if not isinstance(question, str) or not question.strip():
        reasons.append('format:empty_question')
    if reasons:
        return False, reasons
    explanation, question = explanation.strip(), question.strip()
    if label == problem.get('label'):
        reasons.append('format:label_is_correct')
    if words(explanation) > MAX_EXPLANATION_WORDS:
        reasons.append('length:explanation_words')
    if sentences(explanation) > 2:
        reasons.append('length:explanation_sentences')
    if words(question) > MAX_QUESTION_WORDS:
        reasons.append('length:question_words')
    if not question.endswith('?'):
        reasons.append('format:question_mark')
    language = 'cat' if problem.get('language') == 'cat' else 'eng'
    both = explanation + ' ' + question
    if value_leak(both, problem):
        reasons.append('leak:value')
    if letter_leak(both, problem.get('label')):
        reasons.append('leak:letter')
    reasons += language_reasons(both, language)
    reasons += voice_reasons(both, language)
    return not reasons, reasons


def verify_steps(steps, problem):
    """Check three thinking steps against the bank rules plus leak, language and voice checks."""
    reasons = []
    if not isinstance(steps, list) or len(steps) != len(STAGES):
        return False, ['format:three_steps']
    language = 'cat' if problem.get('language') == 'cat' else 'eng'
    texts = []
    for expected, step in zip(STAGES, steps):
        if not isinstance(step, dict) or step.get('stage') != expected:
            reasons.append('format:stage_order')
            continue
        if step.get('language') != problem.get('language'):
            reasons.append('format:language_field')
        bad = False
        for key in ('question', 'why'):
            if not isinstance(step.get(key), str) or not step[key].strip():
                reasons.append(f'format:empty_{key}')
                bad = True
        options = step.get('options')
        if not isinstance(options, list) or len(options) != 3 or any(not isinstance(o, str) or not o.strip() for o in options):
            reasons.append('format:three_options')
            bad = True
        if type(step.get('answer')) is not int or not 0 <= step['answer'] <= 2:
            reasons.append('format:answer_index')
        if bad:
            continue
        if len({o.strip().lower() for o in options}) != 3:
            reasons.append('options:not_distinct')
        counts = [words(o) for o in options]
        if max(counts) > MAX_OPTION_WORDS:
            reasons.append('length:option_words')
        if max(counts) - min(counts) > 2:
            reasons.append('options:word_count_spread')
        if any(o.split()[0].strip(',.').lower() in ('all', 'none', 'both') for o in options):
            reasons.append('options:all_none_both')
        if words(step['question']) > MAX_STEP_QUESTION_WORDS:
            reasons.append('length:question_words')
        if words(step['why']) > MAX_STEP_WHY_WORDS:
            reasons.append('length:why_words')
        why = step['why'].strip()
        if why[-1] not in '.!?' or re.search(r'[.!?]\s', why):
            reasons.append('format:why_one_sentence')
        texts += [step['question'], step['why'], *options]
    if len({s.get('language') for s in steps if isinstance(s, dict)}) != 1:
        reasons.append('format:mixed_language')
    if texts:
        joined = ' \n '.join(texts)
        if any(value_leak(t, problem) for t in texts):
            reasons.append('leak:value')
        if any(letter_leak(t, problem.get('label')) for t in texts):
            reasons.append('leak:letter')
        reasons += language_reasons(joined, language)
        reasons += voice_reasons(joined, language)
    reasons = list(dict.fromkeys(reasons))
    return not reasons, reasons


MAX_SOLUTION_WORDS = 90
MAX_HINT_WORDS = 20


def verify_solution(item, problem):
    """Worked solution (<= 90 words, ends with the correct value) plus a ladder of three hints without it."""
    if not isinstance(item, dict):
        return False, ['format:not_object']
    solution, hints = item.get('solution'), item.get('hints')
    reasons = []
    if not isinstance(solution, str) or not solution.strip():
        return False, ['format:empty_solution']
    if not isinstance(hints, list) or len(hints) != 3 or any(not isinstance(h, str) or not h.strip() for h in hints):
        return False, ['format:three_hints']
    solution = solution.strip()
    if words(solution) > MAX_SOLUTION_WORDS:
        reasons.append('length:solution_words')
    if not value_leak(solution, problem):
        reasons.append('solution:missing_correct_value')
    else:
        last = [s for s in re.split(r'(?<=[.!?])\s+', solution) if s.strip()][-1]
        if not value_leak(last, problem):
            reasons.append('solution:value_not_at_end')
    if len({h.strip().lower() for h in hints}) != 3:
        reasons.append('hints:not_distinct')
    for hint in hints:
        if words(hint) > MAX_HINT_WORDS:
            reasons.append('length:hint_words')
        if value_leak(hint, problem):
            reasons.append('leak:value_in_hint')
        if letter_leak(hint, problem.get('label')) or re.search(r'\b(?i:option|opció|lletra|letter)\s+[A-E]\b', hint):
            reasons.append('leak:letter_in_hint')
    language = 'cat' if problem.get('language') == 'cat' else 'eng'
    joined = solution + ' \n ' + ' \n '.join(hints)
    reasons += language_reasons(joined, language)
    reasons += voice_reasons(joined, language)
    reasons = list(dict.fromkeys(reasons))
    return not reasons, reasons


def verify_skills(item, known):
    """1-3 distinct known skill ids, assessment_skill one of them or null, confidence in [0, 1]."""
    if not isinstance(item, dict):
        return False, ['format:not_object']
    reasons = []
    skills = item.get('skills')
    if not isinstance(skills, list) or not 1 <= len(skills) <= 3 or any(not isinstance(s, str) for s in skills):
        return False, ['skills:count']
    if len(set(skills)) != len(skills):
        reasons.append('skills:duplicate')
    if any(s not in known for s in skills):
        reasons.append('skills:unknown_id')
    primary = item.get('assessment_skill')
    if primary is not None and primary not in skills:
        reasons.append('skills:assessment_not_in_skills')
    confidence = item.get('confidence')
    if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
        reasons.append('skills:confidence')
    return not reasons, reasons
