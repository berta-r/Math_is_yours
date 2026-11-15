"""Misconception feedback checks (T-109): signatures from the samples only, no M3Kang data."""
import contextlib
import io
import json
import sqlite3
import tempfile
import threading
import unittest
import unittest.mock
import urllib.request
from pathlib import Path

from copilot.knowledge import Knowledge, ROOT
from copilot.misconceptions import Misconceptions
from student_app import server as app
try:
    from laptop.ml import signatures as sig
except ImportError:  # the board bundle ships copilot/ and student_app/ only
    sig = None

# What laptop/ml/signatures.py produces for the samples; used where laptop/ is not deployed.
SAMPLE_SIGNATURES = {
    'sample-1': {'answer_op': None, 'distractors': {'A': {'op': 'product', 'operands': [4, 2]}, 'B': {'op': 'answer_minus_one', 'operands': []},
                                                   'D': {'op': 'product', 'operands': [3, 4]}}},
    'sample-2': {'answer_op': None, 'distractors': {'A': {'op': 'sum_then_product', 'operands': [2, 3, 4]}, 'C': {'op': 'product_all', 'operands': []},
                                                   'D': {'op': 'sum_all', 'operands': []}, 'E': {'op': 'product_then_sum', 'operands': [2, 3, 4]}}},
    'sample-3': {'answer_op': None, 'distractors': {'A': {'op': 'copied_number', 'operands': [36]}, 'B': {'op': 'double', 'operands': [36]}}},
    'sample-4': {'answer_op': {'op': 'difference', 'operands': [15, 6]},
                 'distractors': {'A': {'op': 'copied_number', 'operands': [6]}, 'B': {'op': 'answer_minus_one', 'operands': []},
                                 'E': {'op': 'sum', 'operands': [15, 6]}}},
    'sample-5': {'answer_op': None, 'distractors': {'A': {'op': 'minus_one', 'operands': [5]}, 'C': {'op': 'plus_one', 'operands': [5]},
                                                   'E': {'op': 'double', 'operands': [5]}}},
}


def write_sample_signatures(path):
    """Generate signatures for the samples with the laptop script when present, else write the known output."""
    if sig is None:
        path.write_text(json.dumps({'version': 1, 'source': 'sample_problems.jsonl', 'problems': SAMPLE_SIGNATURES}), encoding='utf-8')
        return path
    with contextlib.redirect_stdout(io.StringIO()):
        sig.main(['--input', str(ROOT / 'data/sample_problems.jsonl'), '--output', str(path), '--report', str(path.with_suffix('.report.json'))])
    return path


class Fixture:
    """One running app with an optional signatures file (same style as test_thinking)."""

    def __init__(self, folder, signatures):
        self.db = Path(folder) / f'practice-{id(self)}.db'
        app.initialize(self.db)
        self.knowledge = Knowledge()
        self.catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(folder) / 'images')
        handler = app.make_handler(self.db, self.catalog, self.knowledge, signatures=signatures)
        handler.log_message = lambda *args: None
        self.server = app.StudentServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}/api/'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, route, **data):
        req = urllib.request.Request(self.url + route, data=json.dumps({'student': 'Ada', **data}).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def open(self, pid):
        """Start a problem and answer its thinking steps correctly (they gate the answer)."""
        opened = self.post('start', problem=pid)
        steps = self.knowledge.thinking_steps(self.catalog.problems[opened['problem']['key']])[0]
        for index, step in enumerate(steps):
            self.post('step', session=opened['session'], index=index, choice=step['answer'])
        return opened


class MisconceptionAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = write_sample_signatures(Path(self.temp.name) / 'signatures.json')
        self.app = Fixture(self.temp.name, self.path)

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def test_wrong_answer_names_the_operation_without_the_answer(self):
        opened = self.app.open('sample-1')  # 3 bags x 4 apples, eats 2 -> 10 (C); D = 12 = 3 x 4
        result = self.app.post('answer', session=opened['session'], answer='D')
        self.assertFalse(result['correct'])
        self.assertIn('multiplying 3 by 4', result['message'])
        self.assertNotIn('10', result['message'])
        self.assertNotRegex(result['message'], r'\bC\b')
        self.assertEqual(result['misconception'], {'op': 'product', 'answer_op': None})
        with app.connection(self.app.db) as con:
            self.assertEqual(con.execute('SELECT misconception FROM sessions WHERE id=?', (opened['session'],)).fetchone()[0], 'product')
            self.assertEqual(con.execute('SELECT misconception FROM learning_events').fetchone()[0], 'product')
        self.assertIn('| product | 1 |', self.app.post('report')['markdown'])

    def test_catalan_contrast_and_unexplained_letter(self):
        opened = self.app.open('sample-4')  # 15 - 6 = 9; E = 21 = 15 + 6
        result = self.app.post('answer', session=opened['session'], answer='E')
        self.assertIn('sumar 15 i 6', result['message'])
        self.assertIn('restar', result['message'])
        self.assertNotRegex(result['message'], r'(?<!\d)9(?!\d)')
        self.assertEqual(result['misconception'], {'op': 'sum', 'answer_op': 'difference'})
        other = self.app.open('sample-4')
        plain = self.app.post('answer', session=other['session'], answer='D')  # 11: no signature
        self.assertNotIn('misconception', plain)
        # sample-4 is Catalan, so the child reads the Catalan message (T-101).
        self.assertEqual(plain['message'], app.MESSAGES['cat']['wrong'])

    def test_slip_starts_hints_at_the_method_rung(self):
        opened = self.app.open('sample-1')
        hints = self.app.knowledge.hints(self.app.catalog.problems['sample-1|eng'])[0]
        self.app.post('answer', session=opened['session'], answer='D')
        tutor = type(self.app.server.RequestHandlerClass.teaching_tutor)
        with unittest.mock.patch.object(tutor, 'request', autospec=True, side_effect=tutor.request) as spy:
            hint = self.app.post('hint', session=opened['session'])
        self.assertEqual((hint['rung'], hint['message']), (2, hints[1]))
        self.assertTrue(spy.call_args.kwargs['reflection'].endswith('; misconception: product'))
        # Without a recognised slip the first hint stays the broad one.
        clean = self.app.open('sample-1')
        self.app.post('answer', session=clean['session'], answer='E')  # dropped as coincidental
        self.assertEqual(self.app.post('hint', session=clean['session'])['rung'], 1)


class MisconceptionModelTests(unittest.TestCase):
    @unittest.skipIf(sig is None, 'laptop/ml is not deployed here')
    def test_embedded_fixture_matches_the_laptop_script(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_sample_signatures(Path(folder) / 'signatures.json')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['problems'], SAMPLE_SIGNATURES)

    def test_bkt_is_identical_with_and_without_signatures(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_sample_signatures(Path(folder) / 'signatures.json')
            evidence = []
            for signatures in (path, Path(folder) / 'missing.json'):
                fixture = Fixture(folder, signatures)
                try:
                    opened = fixture.open('sample-2')  # order of operations; A = (2+3) x 4
                    result = fixture.post('answer', session=opened['session'], answer='A')
                    evidence.append(result['evidence'])
                    skill = next(s for s in fixture.post('profile')['skills'] if s['id'] == 'order_of_operations')
                    evidence.append(skill['probability'])
                finally:
                    fixture.close()
            self.assertTrue(evidence[0]['updated'])
            self.assertEqual(evidence[0], evidence[2])
            self.assertEqual(evidence[1], evidence[3])

    def test_missing_file_keeps_todays_behaviour(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(len(Misconceptions(Path(folder) / 'none.json')), 0)
            fixture = Fixture(folder, Path(folder) / 'none.json')
            try:
                opened = fixture.open('sample-1')
                result = fixture.post('answer', session=opened['session'], answer='D')
                self.assertNotIn('misconception', result)
                self.assertTrue(result['message'].startswith('Not quite. Try a hint'))
                self.assertNotIn('multiplying', result['message'])
                hints = fixture.knowledge.hints(fixture.catalog.problems['sample-1|eng'])[0]
                self.assertEqual(fixture.post('hint', session=opened['session'])['message'], hints[0])
                self.assertNotIn('Common slips', fixture.post('report')['markdown'])
            finally:
                fixture.close()

    def test_malformed_files_raise(self):
        good = {'version': 1, 'problems': {'p': {'answer_op': None, 'distractors': {'A': {'op': 'sum', 'operands': [1, 2]}}}}}
        bad = [('not json', 'not valid JSON'), (json.dumps({'version': 2, 'problems': {}}), 'version'),
               (json.dumps({'version': 1, 'problems': {'p': {'distractors': []}}}), 'distractors'),
               (json.dumps({'version': 1, 'problems': {'p': {'answer_op': None, 'distractors': {'F': {'op': 'sum', 'operands': [1, 2]}}}}}), 'unknown letter'),
               (json.dumps({'version': 1, 'problems': {'p': {'answer_op': None, 'distractors': {'A': {'op': 'magic', 'operands': []}}}}}), 'known "op"'),
               (json.dumps({'version': 1, 'problems': {'p': {'answer_op': None, 'distractors': {'A': {'op': 'sum', 'operands': [1]}}}}}), 'wrong number'),
               (json.dumps({'version': 1, 'problems': {'p': {'answer_op': {'op': 'sum', 'operands': ['x', 1]}, 'distractors': {}}}}), 'numeric'),
               ('x' * (2 * 1024 * 1024 + 1), 'larger than')]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'signatures.json'
            path.write_text(json.dumps(good), encoding='utf-8')
            self.assertEqual(len(Misconceptions(path)), 1)
            for text, message in bad:
                with self.subTest(message):
                    path.write_text(text, encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, message):
                        Misconceptions(path)
            path.write_text('[]', encoding='utf-8')
            db = Path(folder) / 'practice.db'
            app.initialize(db)
            with self.assertRaises(ValueError):
                app.make_handler(db, app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(folder) / 'images'), Knowledge(), signatures=path)

    def test_message_never_reveals_the_correct_value(self):
        # A difference whose operand is the correct value itself falls back to the generic message.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'signatures.json'
            entry = {'answer_op': None, 'distractors': {'A': {'op': 'difference', 'operands': [10, 2]}}}
            path.write_text(json.dumps({'version': 1, 'problems': {'q': entry}}), encoding='utf-8')
            problem = {'id': 'q', 'language': 'eng', 'label': 'B', 'options': dict(zip('ABCDE', ['8', '10 cm', '12', '6', '4']))}
            found = Misconceptions(path).explain(problem, 'A')
            self.assertEqual(found['message'], 'That is what you get by subtracting one number from another. Re-read what the question asks.')
            self.assertIsNone(Misconceptions(path).explain(problem, 'B'))  # the correct letter
            self.assertTrue(Misconceptions.leaks('It is 10,0.', dict(problem, language='cat')))
            self.assertFalse(Misconceptions.leaks('It is 110.', problem))
            self.assertTrue(Misconceptions.leaks('Pick B.', problem))

    def test_old_database_is_migrated(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'old.db'
            con = sqlite3.connect(db)
            con.executescript('''CREATE TABLE sessions (id TEXT PRIMARY KEY, student TEXT NOT NULL, problem TEXT NOT NULL,
                hints INTEGER NOT NULL DEFAULT 0, tries INTEGER NOT NULL DEFAULT 0, revealed INTEGER NOT NULL DEFAULT 0, solved INTEGER NOT NULL DEFAULT 0);''')
            con.close()
            app.initialize(db)
            con = sqlite3.connect(db)
            self.assertIn('misconception', {r[1] for r in con.execute('PRAGMA table_info(sessions)')})
            self.assertIn('misconception', {r[1] for r in con.execute('PRAGMA table_info(learning_events)')})
            con.close()


if __name__ == '__main__':
    unittest.main()
