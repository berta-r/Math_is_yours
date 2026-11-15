"""Elo rating beside BKT and ~70% success targeting (T-103). Synthetic difficulty files only."""
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from copilot import scheduler, student_model
from copilot.difficulty import Difficulty, probability
from copilot.knowledge import Knowledge, ROOT
from student_app import server as app


def row(level, b):
    return {'level': level, 'points': None, 'expected_points': 4.0, 'b': b, 'source': 'predicted'}


# theta starts at 0.25: b=0.11 gives p ~= 0.70, b=0.0 p ~= 0.82, b=0.9 p ~= 0.02.
SYNTHETIC = {'version': 1, 'problems': {
    'diagnostic-arithmetic-1': row(0, 0.9), 'diagnostic-arithmetic-2': row(0, 0.11), 'diagnostic-arithmetic-3': row(0, 0.0),
    'sample-4': row(3, 0.2)}}


def write_difficulty(folder, data=SYNTHETIC):
    path = Path(folder) / 'difficulty.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return Difficulty(path, model_path=Path(folder) / 'no-model.json')


class Fixture:
    def __init__(self, folder, difficulty):
        self.db = Path(folder) / f'practice-{id(self)}.db'
        app.initialize(self.db)
        self.knowledge = Knowledge()
        self.catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(folder) / 'images')
        handler = app.make_handler(self.db, self.catalog, self.knowledge, difficulty=difficulty,
                                   map_path=Path(folder) / 'no-map.json')
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
        opened = self.post('start', problem=pid)
        steps = self.knowledge.thinking_steps(self.catalog.problems[opened['problem']['key']])[0]
        for index, step in enumerate(steps):
            self.post('step', session=opened['session'], index=index, choice=step['answer'])
        if not steps:
            self.post('reflect', session=opened['session'], reflection='I will look for equal groups and check the units.')
        return opened

    def answer(self, pid, correct=True):
        opened = self.open(pid)
        label = self.catalog.problems[opened['problem']['key']]['label']
        letter = label if correct else next(x for x in 'ABCDE' if x != label)
        return opened, self.post('answer', session=opened['session'], answer=letter)

    def skill(self, sid):
        return next(s for s in self.post('profile')['skills'] if s['id'] == sid)


class EloAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Fixture(self.temp.name, write_difficulty(self.temp.name))

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def test_correct_raises_and_wrong_lowers_theta(self):
        rating = self.app.post('profile')['rating']
        self.assertEqual(rating, {'global': student_model.INITIAL_THETA, 'by_skill': {}, 'updates': 0})
        _, right = self.app.answer('diagnostic-arithmetic-1')  # b=0.9: a surprising success
        self.assertEqual(right['evidence']['elo_before'], 0.25)
        self.assertGreater(right['evidence']['elo_after'], 0.25)
        self.assertAlmostEqual(right['evidence']['elo_after'], 0.25 + 0.08 * (1 - probability(0.25, 0.9)), places=4)
        _, wrong = self.app.answer('diagnostic-division-1', correct=False)
        self.assertLess(wrong['evidence']['elo_after'], wrong['evidence']['elo_before'])
        rating = self.app.post('profile')['rating']
        self.assertEqual(rating['updates'], 2)
        self.assertEqual(rating['global'], wrong['evidence']['elo_after'])
        self.assertGreater(rating['by_skill']['arithmetic'], 0.25)
        self.assertLess(rating['by_skill']['division'], 0.25)
        self.assertTrue(self.app.post('profile')['difficulty_enabled'])

    def test_assisted_and_repeat_attempts_do_not_change_theta(self):
        opened = self.app.open('diagnostic-arithmetic-2')
        self.app.post('hint', session=opened['session'])
        label = self.app.catalog.problems[opened['problem']['key']]['label']
        assisted = self.app.post('answer', session=opened['session'], answer=label)
        self.assertFalse(assisted['evidence']['updated'])
        self.assertEqual(assisted['evidence']['elo_before'], assisted['evidence']['elo_after'])
        _, repeat = self.app.answer('diagnostic-arithmetic-2')
        self.assertEqual(repeat['evidence']['reason'], 'repeat_or_translation')
        self.assertEqual(repeat['evidence']['elo_after'], 0.25)
        self.assertEqual(self.app.post('profile')['rating']['updates'], 0)

    def test_bkt_values_match_test_learning(self):
        self.app.answer('diagnostic-arithmetic-1')
        self.assertAlmostEqual(self.app.skill('arithmetic')['probability'], .5765, places=4)
        self.app.answer('diagnostic-division-1', correct=False)
        self.assertAlmostEqual(self.app.skill('division')['probability'], .1273, places=4)

    def test_recommendation_targets_seventy_percent(self):
        rec = self.app.post('recommendation')
        self.assertEqual(rec['problem'], 'diagnostic-arithmetic-2|eng')  # not -1 (b=0.9) or -3 (p=0.82)
        self.assertEqual((rec['p_success'], rec['b']), (0.7, 0.11))
        self.assertIn('about a 70% chance: your rating is 0.25 and this problem\'s difficulty is 0.11.', rec['reason'])

    def test_catalan_reason_and_skill_rating(self):
        with sqlite3.connect(self.app.db) as con:
            con.execute("INSERT INTO student_elo VALUES('Ada','arithmetic',0.4,3)")
        rec = self.app.post('recommendation', skill='arithmetic')
        self.assertEqual(rec['problem'], 'sample-4|cat')
        self.assertIn("la teva puntuació és 0.40 i la dificultat d'aquest problema és 0.20.", rec['reason'])
        self.assertEqual(rec['p_success'], round(probability(0.4, 0.2), 2))


class EloModelTests(unittest.TestCase):
    def test_missing_difficulty_file_keeps_todays_behaviour(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Fixture(folder, Difficulty(Path(folder) / 'none.json', Path(folder) / 'none-model.json'))
            try:
                profile = fixture.post('profile')
                self.assertFalse(profile['difficulty_enabled'])
                rec = fixture.post('recommendation')
                self.assertEqual(rec['problem'], 'diagnostic-arithmetic-1|eng')
                self.assertNotIn('p_success', rec)
                self.assertNotIn('70%', rec['reason'])
            finally:
                fixture.close()

    def test_scheduler_without_theta_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'x.db'
            app.initialize(db)
            knowledge = Knowledge()
            catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(folder) / 'images')
            for p in knowledge.diagnostics:
                catalog.problems[p['id'] + '|' + p['language']] = p
            difficulty = write_difficulty(folder)
            con = sqlite3.connect(db)
            con.row_factory = sqlite3.Row
            try:
                for sid in ('arithmetic', 'multiplication', 'order_of_operations'):
                    plain = scheduler.recommend(con, 'Ada', catalog, knowledge, skill_id=sid)
                    half = scheduler.recommend(con, 'Ada', catalog, knowledge, skill_id=sid, difficulty=difficulty)
                    self.assertEqual(plain, half)
                    self.assertNotIn('p_success', plain)
            finally:
                con.close()

    def test_record_without_difficulty_argument_uses_default(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'x.db'
            app.initialize(db)
            con = sqlite3.connect(db)
            con.row_factory = sqlite3.Row
            try:
                knowledge = Knowledge()
                problem = next(p for p in knowledge.diagnostics if p['id'] == 'diagnostic-arithmetic-1')
                session = {'id': 's', 'tries': 0, 'hints': 0, 'revealed': 0, 'started_at': None, 'reflection': ''}
                out = student_model.record(con, 'Ada', session, problem, knowledge.annotation(problem), True, 1, True,
                                           'independent_first_attempt', knowledge)
                self.assertGreater(out['elo_after'], out['elo_before'])
                self.assertEqual(student_model.ratings(con, 'Ada')['updates'], 1)
            finally:
                con.close()


if __name__ == '__main__':
    unittest.main()
