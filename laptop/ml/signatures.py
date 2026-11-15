"""Error signatures: which naive operation over the text's numerals yields each distractor (T-108).

Laptop only, standard library only. For every problem whose five options are all
numbers, try cheap operations over the numerals in the problem text and record,
per distractor letter, the lowest-cost operation that produces its value. The
board reads the output (copilot/misconceptions.py) to say "that number comes from
adding 3 and 4" after a wrong answer. Output contains numbers and operation names
only, never problem text.

    python3 laptop/ml/signatures.py                       # train + val -> data/ml/signatures.json
    python3 laptop/ml/signatures.py --input data/sample_problems.jsonl --output /tmp/s.json
"""
import argparse
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from itertools import combinations, permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LETTERS = 'ABCDE'

# (name, cost). The list order is the tie-break order within a cost.
# Deviation from the first spec: square, times_ten and div_ten cost 2, not 1. With
# cost 1 they explained "2 + 3 x 4 = 20" as "2 x 10" and "9" as "3 squared",
# hiding the real slips ((2+3) x 4 and adding everything).
# copied_number comes first: picking a number straight from the text is the most
# common Kangaroo distractor, and otherwise "10" in the text became "11 minus 1".
OPERATIONS = [
    ('copied_number', 1), ('sum', 1), ('difference', 1), ('product', 1), ('quotient', 1),
    ('double', 1), ('half', 1), ('plus_one', 1), ('minus_one', 1),
    ('answer_plus_one', 1), ('answer_minus_one', 1),
    ('sum_all', 2), ('product_all', 2),
    ('sum_then_product', 2), ('product_then_sum', 2),
    ('product_then_difference', 2), ('difference_then_product', 2),
    ('square', 2), ('times_ten', 2), ('div_ten', 2), ('count_numerals', 2),
]
COST = dict(OPERATIONS)
ORDER = {name: i for i, (name, _) in enumerate(OPERATIONS)}
# Operations that say nothing about the method and so cannot describe the correct answer.
NOT_A_METHOD = {'answer_plus_one', 'answer_minus_one', 'copied_number'}
MAX_PAIRWISE = 16   # numerals used for pairwise operations
MAX_TRIPLE = 9      # numerals used for three-operand combinations
# An explanation is dropped as coincidental when operations of its cost or cheaper
# reach more than this share of the integers between the smallest and largest option.
COINCIDENCE_LIMIT = 0.6

PREFIX = re.compile(r'^\s*\d{1,2}\.\s+')
# A numeral not glued to letters ("cm2", "x2"). "1 000" groups, "1,5" and "1.5" decimals.
NUMERAL = re.compile(r'(?<![\w.,])(\d{1,3}(?: \d{3})+|\d+(?:[.,]\d+)?)(?![\w]|[.,]\d)')
UNIT_CHARS = r"A-Za-zÀ-ÖØ-öø-ÿ°%²³€$£∈'"  # letters without × and ÷
OPTION = re.compile(r'^\s*([€$£∈])?\s*(-?)\s*(\d{1,3}(?: \d{3})+|\d+(?:[.,]\d+)?)\s*'
                    rf'(?:[{UNIT_CHARS}][{UNIT_CHARS}/.]*[23]?)?\s*$')


def to_number(raw):
    raw = raw.replace(' ', '').replace(',', '.')
    return Fraction(raw)


def numerals(text):
    """Numbers in the problem text, without the leading problem number ("13. ")."""
    return [to_number(m.group(1)) for m in NUMERAL.finditer(PREFIX.sub('', text or '', count=1))]


def option_value(text):
    """Numeric value of an option after stripping units and currency, or None."""
    match = OPTION.match(text or '')
    if not match:
        return None
    value = to_number(match.group(3))
    return -value if match.group(2) else value


def plain(value):
    """JSON-friendly number: int when whole, else float."""
    return int(value) if value.denominator == 1 else float(value)


def candidates(values, answer):
    """Yield (op, operands, value) for every operation instance, cheapest first by construction order."""
    base = []
    for v in values:  # keep at most two copies of each value
        if base.count(v) < 2:
            base.append(v)
    pair = base[:MAX_PAIRWISE]
    for a, b in combinations(pair, 2):
        hi, lo = max(a, b), min(a, b)
        if lo == 0:
            continue  # adding or subtracting 0 is not an operation a student "does"
        yield 'sum', [a, b], a + b
        yield 'difference', [hi, lo], hi - lo
        if lo == 1:
            continue  # neither is multiplying or dividing by 1
        yield 'product', [a, b], a * b
        for x, y in ((a, b), (b, a)):
            if x.denominator == y.denominator == 1 and x % y == 0:
                yield 'quotient', [x, y], x / y
    for a in dict.fromkeys(pair):
        yield 'double', [a], 2 * a
        yield 'half', [a], a / 2
        yield 'plus_one', [a], a + 1
        yield 'minus_one', [a], a - 1
        yield 'copied_number', [a], a
        yield 'square', [a], a * a
        yield 'times_ten', [a], a * 10
        yield 'div_ten', [a], a / 10
    if answer is not None:
        yield 'answer_plus_one', [], answer + 1
        yield 'answer_minus_one', [], answer - 1
    if len(values) >= 3:
        yield 'sum_all', [], sum(values)
        product = Fraction(1)
        for v in values:
            product *= v
        yield 'product_all', [], product
    if values:
        yield 'count_numerals', [], Fraction(len(values))
    for a, b, c in permutations(base[:MAX_TRIPLE], 3):
        if a <= b:  # (a+b) and a*b are symmetric
            yield 'sum_then_product', [a, b, c], (a + b) * c
            yield 'product_then_sum', [a, b, c], a * b + c
            if a * b - c >= 0:
                yield 'product_then_difference', [a, b, c], a * b - c
        if a > b:
            yield 'difference_then_product', [a, b, c], (a - b) * c


def best(found):
    return min(found, key=lambda item: (COST[item[0]], ORDER[item[0]]))


def coincidence(by_value, parsed, cost):
    """Share of the integers in the option span that operations up to `cost` reach (None if not integral)."""
    values = list(parsed.values())
    if any(v.denominator != 1 for v in values):
        return None
    low, high = min(values), max(values)
    hits = sum(1 for v, found in by_value.items() if v.denominator == 1 and low <= v <= high
               and any(COST[op] <= cost and not op.startswith('answer_') for op, _ in found))
    return hits / (high - low + 1)


def signature(problem):
    """(signature, dropped coincidental matches) for one problem, or None when not all options are numeric."""
    options = problem.get('options') or {}
    if set(options) != set(LETTERS) or problem.get('label') not in options:
        return None
    parsed = {k: option_value(v) for k, v in options.items()}
    if any(v is None for v in parsed.values()):
        return None
    answer = parsed[problem['label']]
    values = numerals(problem.get('text', ''))
    by_value = {}
    for op, operands, value in candidates(values, answer):
        by_value.setdefault(value, []).append((op, operands))
    result = {'answer_op': None, 'distractors': {}}
    dropped = 0
    methods = [x for x in by_value.get(answer, []) if x[0] not in NOT_A_METHOD and not x[0].startswith('answer_')]
    if methods:
        cheapest = min(COST[op] for op, _ in methods)
        kinds = {op for op, _ in methods if COST[op] == cheapest}
        # Two different operations reach the answer at the same cost: no reliable contrast.
        if len(kinds) == 1:
            op, operands = best(methods)
            result['answer_op'] = {'op': op, 'operands': [plain(x) for x in operands]}
    for letter in LETTERS:
        value = parsed[letter]
        if letter == problem['label'] or value == answer:
            continue  # the correct value never receives a distractor operation
        found = by_value.get(value)
        if found:
            op, operands = best(found)
            chance = coincidence(by_value, parsed, COST[op])
            if not op.startswith('answer_') and chance is not None and chance > COINCIDENCE_LIMIT:
                dropped += 1  # so many values are reachable that a match says nothing
                continue
            result['distractors'][letter] = {'op': op, 'operands': [plain(x) for x in operands]}
    return result, dropped


def load_rows(paths):
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build(rows):
    """Return (signatures, report). English row wins when both languages exist."""
    groups = {}
    for row in rows:
        groups.setdefault(row['id'], {})[row.get('language', 'eng')] = row
    problems, ops, mismatched = {}, Counter(), []
    stats = Counter()
    for pid, variants in groups.items():
        row = variants.get('eng') or next(iter(variants.values()))
        stats['problems_considered'] += 1
        if 'eng' in variants and 'cat' in variants:
            if Counter(numerals(variants['eng'].get('text', ''))) != Counter(numerals(variants['cat'].get('text', ''))):
                mismatched.append(pid)
        sig = signature(row)
        if sig is None:
            continue
        sig, dropped = sig
        stats['distractors_dropped_as_coincidental'] += dropped
        stats['problems_all_numeric'] += 1
        stats['distractors_total'] += sum(1 for k in LETTERS if k != row['label'])
        stats['distractors_explained'] += len(sig['distractors'])
        stats['problems_with_explained_distractor'] += bool(sig['distractors'])
        stats['problems_with_answer_op'] += sig['answer_op'] is not None
        ops.update(d['op'] for d in sig['distractors'].values())
        problems[pid] = sig
    report = dict(stats)
    for key in ('distractors_dropped_as_coincidental', 'problems_considered', 'problems_all_numeric', 'distractors_total', 'distractors_explained',
                'problems_with_explained_distractor', 'problems_with_answer_op'):
        report.setdefault(key, 0)
    total = report['distractors_total']
    report['coverage'] = round(report['distractors_explained'] / total, 4) if total else None
    report['coverage_without_copied_or_off_by_one'] = round(
        sum(n for op, n in ops.items() if op not in NOT_A_METHOD) / total, 4) if total else None
    report['bilingual_pairs_mismatched'] = len(mismatched)
    report['mismatched_examples'] = sorted(mismatched)[:30]
    report['ops'] = dict(sorted(ops.items(), key=lambda kv: (-kv[1], kv[0])))
    return problems, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/ml/signatures.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'results/signatures-report.json')
    args = parser.parse_args(argv)
    inputs = args.input or [p for p in (ROOT / 'data/train.jsonl', ROOT / 'data/val.jsonl') if p.exists()] \
        or [ROOT / 'data/sample_problems.jsonl']
    problems, report = build(load_rows(inputs))
    source = ', '.join(Path(p).name for p in inputs)
    report['source'] = source
    for path, value in ((args.output, {'version': 1, 'source': source, 'problems': problems}), (args.report, report)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':') if path == args.output else None,
                                   indent=None if path == args.output else 2), encoding='utf-8')
    json.dump({k: v for k, v in report.items() if k != 'mismatched_examples'}, sys.stdout, indent=2)
    print(f"\nWrote {len(problems)} signatures to {args.output} and the report to {args.report}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
