"""Misconception feedback from precomputed error signatures (T-109). Standard library only.

laptop/ml/signatures.py writes data/ml/signatures.json: for each canonical problem
id, which naive operation over the text's numerals gives each distractor. After a
wrong answer the app names that operation in one or two short sentences, in the
problem's language, without ever giving away the correct option.
"""
import json
import re
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024
LETTERS = 'ABCDE'

# Sentence fragments per operation: (eng, cat). {a} {b} {c} are the operands.
# Phrased as "could come from": a signature is a likely slip, not a certainty.
PHRASES = {
    'sum': ('adding {a} and {b}', 'sumar {a} i {b}'),
    'difference': ('subtracting {b} from {a}', 'restar {b} a {a}'),
    'product': ('multiplying {a} by {b}', 'multiplicar {a} per {b}'),
    'quotient': ('dividing {a} by {b}', 'dividir {a} entre {b}'),
    'double': ('doubling {a}', 'fer el doble de {a}'),
    'half': ('halving {a}', 'fer la meitat de {a}'),
    'plus_one': ('adding 1 to {a}', 'sumar 1 a {a}'),
    'minus_one': ('taking 1 away from {a}', 'restar 1 a {a}'),
    'square': ('multiplying {a} by itself', 'multiplicar {a} per si mateix'),
    'times_ten': ('multiplying {a} by 10', 'multiplicar {a} per 10'),
    'div_ten': ('dividing {a} by 10', 'dividir {a} entre 10'),
    'sum_all': ('adding all the numbers in the problem', 'sumar tots els nombres del problema'),
    'product_all': ('multiplying all the numbers in the problem', 'multiplicar tots els nombres del problema'),
    'count_numerals': ('counting how many numbers the problem shows', 'comptar quants nombres surten al problema'),
    'sum_then_product': ('adding {a} and {b} and then multiplying by {c}', 'sumar {a} i {b} i després multiplicar per {c}'),
    'product_then_sum': ('multiplying {a} by {b} and then adding {c}', 'multiplicar {a} per {b} i després sumar {c}'),
    'product_then_difference': ('multiplying {a} by {b} and then subtracting {c}', 'multiplicar {a} per {b} i després restar {c}'),
    'difference_then_product': ('subtracting {b} from {a} and then multiplying by {c}', 'restar {b} a {a} i després multiplicar per {c}'),
}
# Same operations without numbers, for the generic message and for the contrast.
GENERIC = {
    'sum': ('adding two numbers', 'sumar dos nombres'),
    'difference': ('subtracting one number from another', 'restar un nombre d\'un altre'),
    'product': ('multiplying two numbers', 'multiplicar dos nombres'),
    'quotient': ('dividing one number by another', 'dividir un nombre entre un altre'),
    'double': ('doubling a number', 'fer el doble d\'un nombre'),
    'half': ('halving a number', 'fer la meitat d\'un nombre'),
    'plus_one': ('adding 1 to a number', 'sumar 1 a un nombre'),
    'minus_one': ('taking 1 away from a number', 'restar 1 a un nombre'),
    'square': ('multiplying a number by itself', 'multiplicar un nombre per si mateix'),
    'times_ten': ('multiplying by 10', 'multiplicar per 10'),
    'div_ten': ('dividing by 10', 'dividir entre 10'),
    'sum_all': ('adding all the numbers', 'sumar tots els nombres'),
    'product_all': ('multiplying all the numbers', 'multiplicar tots els nombres'),
    'count_numerals': ('counting the numbers', 'comptar els nombres'),
    'sum_then_product': ('adding and then multiplying', 'sumar i després multiplicar'),
    'product_then_sum': ('multiplying and then adding', 'multiplicar i després sumar'),
    'product_then_difference': ('multiplying and then subtracting', 'multiplicar i després restar'),
    'difference_then_product': ('subtracting and then multiplying', 'restar i després multiplicar'),
}
# Operations that are not a calculation: their own whole messages.
SPECIAL = {
    'copied_number': ('That number is already written in the problem. The question asks for something you have to work out.',
                      'Aquest nombre ja surt a l\'enunciat. La pregunta demana una cosa que has de calcular.'),
    'answer_plus_one': ('You are close. Count again carefully, especially the first and the last one.',
                        'Hi ets a prop. Torna a comptar amb cura, sobretot el primer i l\'últim.'),
    'answer_minus_one': ('You are close. Count again carefully, especially the first and the last one.',
                         'Hi ets a prop. Torna a comptar amb cura, sobretot el primer i l\'últim.'),
}
OPS = set(PHRASES) | set(SPECIAL)
ARITY = {'sum': 2, 'difference': 2, 'product': 2, 'quotient': 2, 'sum_then_product': 3, 'product_then_sum': 3,
         'product_then_difference': 3, 'difference_then_product': 3, 'double': 1, 'half': 1, 'plus_one': 1,
         'minus_one': 1, 'square': 1, 'times_ten': 1, 'div_ten': 1, 'copied_number': 1}
TEXT = {
    'lead': ('That number could come from {phrase}.', 'Aquest nombre podria sortir de {phrase}.'),
    'contrast': ('The problem needs {phrase}.', 'El problema demana {phrase}.'),
    'same': ('The problem uses that kind of step, but with other numbers.', 'El problema fa servir aquest tipus de pas, però amb altres nombres.'),
    'reread': ('Re-read what the question asks.', 'Torna a llegir què demana la pregunta.'),
    'generic': ('That is what you get by {phrase}. Re-read what the question asks.',
                'Això és el que surt de {phrase}. Torna a llegir què demana la pregunta.'),
}
NUMBER = re.compile(r'(?<![\w.,])\d+(?:[.,]\d+)?(?![\w]|[.,]\d)')
OPTION = re.compile(r'-?\d+(?:[.,]\d+)?')


def _number(text):
    match = OPTION.search((text or '').replace(' ', ''))
    return Fraction(match.group().replace(',', '.')) if match else None


def _format(value, language):
    text = str(int(value)) if float(value).is_integer() else str(value)
    return text.replace('.', ',') if language == 'cat' else text


def _valid_op(entry, where, allow_null=False):
    if entry is None and allow_null:
        return
    if not isinstance(entry, dict) or entry.get('op') not in OPS:
        raise ValueError(f'Signatures: {where} needs a known "op"')
    operands = entry.get('operands')
    if not isinstance(operands, list) or not all(type(x) in (int, float) for x in operands):
        raise ValueError(f'Signatures: {where} needs numeric "operands"')
    if entry['op'] in ARITY and len(operands) != ARITY[entry['op']]:
        raise ValueError(f'Signatures: {where} has the wrong number of operands')


class Misconceptions:
    def __init__(self, path=ROOT / 'data/ml/signatures.json'):
        self.path = Path(path)
        self.problems = {}
        if not self.path.exists():
            return  # no artifact deployed: today's behaviour
        if self.path.stat().st_size > MAX_BYTES:
            raise ValueError(f'Signatures file is larger than {MAX_BYTES} bytes: {self.path}')
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as error:
            raise ValueError(f'Signatures file is not valid JSON: {error}') from error
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('problems'), dict):
            raise ValueError('Signatures file must be {"version": 1, "problems": {...}}')
        for pid, entry in data['problems'].items():
            if not isinstance(entry, dict) or not isinstance(entry.get('distractors'), dict):
                raise ValueError(f'Signatures: {pid} needs "answer_op" and "distractors"')
            _valid_op(entry.get('answer_op'), f'{pid} answer_op', allow_null=True)
            for letter, item in entry['distractors'].items():
                if letter not in LETTERS:
                    raise ValueError(f'Signatures: {pid} has an unknown letter {letter!r}')
                _valid_op(item, f'{pid} {letter}')
        self.problems = data['problems']

    def __len__(self):
        return len(self.problems)

    def explain(self, problem, letter):
        """{'op', 'answer_op', 'message'} for a wrong letter with a signature, else None."""
        entry = self.problems.get(problem.get('id'))
        label = problem.get('label')
        if not entry or letter == label or letter not in entry['distractors']:
            return None
        item, answer = entry['distractors'][letter], entry.get('answer_op')
        language = 'cat' if problem.get('language') == 'cat' else 'eng'
        index = 1 if language == 'cat' else 0
        op = item['op']
        if op in SPECIAL:
            message = SPECIAL[op][index]
        else:
            names = dict(zip('abc', (_format(x, language) for x in item['operands'])))
            message = TEXT['lead'][index].format(phrase=PHRASES[op][index].format(**names))
            if answer and answer['op'] == op:
                message += ' ' + TEXT['same'][index]
            elif answer and answer['op'] in GENERIC:
                message += ' ' + TEXT['contrast'][index].format(phrase=GENERIC[answer['op']][index])
            else:
                message += ' ' + TEXT['reread'][index]
        if self.leaks(message, problem):
            # Operands can include the correct value: fall back to a message without numbers.
            message = SPECIAL[op][index] if op in SPECIAL else TEXT['generic'][index].format(phrase=GENERIC[op][index])
        assert not self.leaks(message, problem), 'misconception message would reveal the answer'
        return {'op': op, 'answer_op': answer['op'] if answer else None, 'message': message}

    @staticmethod
    def leaks(message, problem):
        """True when the message shows the correct option's value as a whole number, or its letter."""
        label = problem.get('label')
        correct = _number((problem.get('options') or {}).get(label))
        if label and re.search(r'(?<![\w\'’])' + re.escape(label) + r'(?![\w\'’])', message):
            return True
        if correct is None:
            return False
        return any(Fraction(m.group().replace(',', '.')) == correct for m in NUMBER.finditer(message))
