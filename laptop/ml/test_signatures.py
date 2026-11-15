"""Error-signature checks on the committed sample problems. Run: python3 -m unittest laptop.ml.test_signatures"""
import contextlib
import io
import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from laptop.ml import signatures as sig

ROOT = Path(__file__).resolve().parents[2]


def samples():
    rows = [json.loads(line) for line in (ROOT / 'data/sample_problems.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    return {r['id']: r for r in rows}


class ParsingTests(unittest.TestCase):
    def test_numerals_skip_problem_number_prefix(self):
        self.assertEqual(sig.numerals('13. For 3 days, he caught 2 more.'), [3, 2])
        self.assertEqual(sig.numerals('13.  \nJosep has 4 toys.'), [4])
        self.assertEqual(sig.numerals('A rope of 1,5 m and 2.25 m and 1 000 beads.'), [Fraction(3, 2), Fraction(9, 4), 1000])
        self.assertEqual(sig.numerals('The numbers 3, 4 and 5 in 81 cm2 or x2.'), [3, 4, 5, 81])

    def test_option_units_are_stripped(self):
        cases = {'13 cm': 13, '81 cm²': 81, '€ 12': 12, '1.5': Fraction(3, 2), '1,5': Fraction(3, 2),
                 '12cm2': 12, '45°': 45, '30 %': 30, '7,5m': Fraction(15, 2), '-3': -3, '1 000': 1000}
        for text, value in cases.items():
            with self.subTest(text):
                self.assertEqual(sig.option_value(text), value)
        for text in ('2×3', '3/4', '9π', 'O', '2 13', ''):
            with self.subTest(text):
                self.assertIsNone(sig.option_value(text))

    def test_non_numeric_options_get_no_signature(self):
        problem = {'id': 'x', 'text': '1 and 2', 'label': 'A', 'options': {k: v for k, v in zip('ABCDE', ['1', '2', '3', 'π', '5'])}}
        self.assertIsNone(sig.signature(problem))


class SampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problems, cls.report = sig.build(list(samples().values()))

    def test_sample_1_bags_of_apples(self):
        found = self.problems['sample-1']['distractors']  # 3 bags x 4 apples, eats 2 -> 10
        self.assertEqual(found['D'], {'op': 'product', 'operands': [3, 4]})  # forgot she ate 2
        self.assertEqual(found['A'], {'op': 'product', 'operands': [4, 2]})
        self.assertEqual(found['B']['op'], 'answer_minus_one')
        # E = 14 = (3+4) x 2 or 3 x 4 + 2, but at cost 2 most values from 8 to 14 are reachable: dropped as coincidental.
        self.assertNotIn('E', found)

    def test_sample_2_order_of_operations(self):
        found = self.problems['sample-2']['distractors']  # 2 + 3 x 4 = 14
        self.assertEqual(found['A'], {'op': 'sum_then_product', 'operands': [2, 3, 4]})  # (2+3) x 4
        self.assertEqual(found['D']['op'], 'sum_all')  # 2 + 3 + 4
        self.assertEqual(found['C']['op'], 'product_all')
        # 14 is both (3+4) x 2 and 3 x 4 + 2: two methods at the same cost, so no contrast is claimed.
        self.assertIsNone(self.problems['sample-2']['answer_op'])

    def test_sample_4_catalan_only_row(self):
        entry = self.problems['sample-4']  # 15 - 6 = 9
        self.assertEqual(entry['distractors']['E'], {'op': 'sum', 'operands': [15, 6]})
        self.assertEqual(entry['distractors']['A'], {'op': 'copied_number', 'operands': [6]})
        self.assertEqual(entry['answer_op'], {'op': 'difference', 'operands': [15, 6]})

    def test_correct_value_never_gets_a_distractor_op(self):
        rows = samples()
        for pid, entry in self.problems.items():
            label = rows[pid]['label']
            self.assertNotIn(label, entry['distractors'], pid)
            answer = sig.option_value(rows[pid]['options'][label])
            for letter in entry['distractors']:
                self.assertNotEqual(sig.option_value(rows[pid]['options'][letter]), answer)
        # Even an option equal in value to the answer ("10" vs "10 cm") is skipped.
        twin = {'id': 't', 'text': 'Add 4 and 6.', 'label': 'A', 'options': dict(zip('ABCDE', ['10', '10 cm', '24', '3', '2']))}
        self.assertNotIn('B', sig.signature(twin)[0]['distractors'])

    def test_report_and_cli(self):
        self.assertEqual(self.report['problems_all_numeric'], 5)
        self.assertEqual(self.report['distractors_total'], 20)
        self.assertEqual(self.report['distractors_explained'], sum(self.report['ops'].values()))
        with tempfile.TemporaryDirectory() as folder:
            out, rep = Path(folder) / 'ml/s.json', Path(folder) / 'r.json'
            with contextlib.redirect_stdout(io.StringIO()):
                code = sig.main(['--input', str(ROOT / 'data/sample_problems.jsonl'), '--output', str(out), '--report', str(rep)])
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual((data['version'], set(data['problems'])), (1, set(self.problems)))
            self.assertIn('coverage', json.loads(rep.read_text(encoding='utf-8')))

    def test_bilingual_mismatch_is_reported(self):
        eng = {'id': 'p', 'language': 'eng', 'text': '1. Add 3 and 4.', 'label': 'A', 'options': dict(zip('ABCDE', '71234'))}
        cat = dict(eng, language='cat', text='1. Suma 3 i 5.')
        _, report = sig.build([eng, cat])
        self.assertEqual(report['bilingual_pairs_mismatched'], 1)
        _, report = sig.build([eng, dict(cat, text='1. Suma 3 i 4.')])
        self.assertEqual(report['bilingual_pairs_mismatched'], 0)


if __name__ == '__main__':
    unittest.main()
