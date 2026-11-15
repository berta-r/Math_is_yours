"""Evidence, scheduling and bounded tutoring checks using original fixtures only."""
import copy
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

from copilot import scheduler, student_model
from copilot.knowledge import Knowledge, ROOT
from copilot.tutor import Tutor
from student_app import server as app


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'practice.db'
        app.initialize(self.db)
        self.knowledge = Knowledge()
        self.catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(self.temp.name) / 'images')
        handler = app.make_handler(self.db, self.catalog, self.knowledge)
        handler.log_message = lambda *args: None
        self.server = app.StudentServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}/api/'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, route, **data):
        reflect = data.pop('_reflect', True)
        req = urllib.request.Request(self.url + route, data=json.dumps({'student':'Ada', **data}).encode(),
                                     headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as response:
            result = json.load(response)
        if route == 'start' and reflect:
            self.post('reflect', session=result['session'], reflection='I will look for equal groups and check the units.')
            self.complete_steps(result)
        return result

    def complete_steps(self, opened):
        # Thinking steps now gate the answer stage; answer them correctly so BKT tests are unaffected.
        problem = self.catalog.problems[opened['problem']['key']]
        steps, _ = self.knowledge.thinking_steps(problem)
        for index, step in enumerate(steps):
            self.post('step', session=opened['session'], index=index, choice=step['answer'])

    def answer(self, pid, correct=True, **data):
        opened = self.post('start', problem=pid, **data)
        problem = self.catalog.problems[opened['problem']['key']]
        letter = problem['label'] if correct else next(x for x in 'ABCDE' if x != problem['label'])
        return opened, self.post('answer', session=opened['session'], answer=letter)

    def state(self, sid):
        return next(s for s in self.post('profile')['skills'] if s['id'] == sid)

    def test_unassessed_is_unknown_and_three_distinct_successes_demonstrate(self):
        self.assertIsNone(self.state('arithmetic')['probability'])
        self.assertTrue(self.post('recommendation')['problem'].startswith('diagnostic-arithmetic-'))
        self.answer('diagnostic-arithmetic-1')
        first = self.state('arithmetic')
        self.assertAlmostEqual(first['probability'], .5765, places=4)
        self.assertEqual(first['state'], 'developing')
        for number in (2, 3):
            self.answer(f'diagnostic-arithmetic-{number}')
        self.assertEqual(self.state('arithmetic')['state'], 'demonstrated')
        self.assertEqual(self.state('arithmetic')['evidence'], 3)
        self.assertEqual(self.state('multiplication')['state'], 'not_assessed')
        app.initialize(self.db)
        self.assertEqual(self.state('arithmetic')['evidence'], 3)
        other = self.post('profile', student='Other')
        self.assertTrue(all(s['evidence'] == 0 for s in other['skills']))

    def test_wrong_first_answer_updates_once_retry_does_not(self):
        opened, result = self.answer('diagnostic-division-1', correct=False)
        self.assertTrue(result['evidence']['updated'])
        before = self.state('division')['probability']
        self.assertAlmostEqual(before, .1273, places=4)
        result = self.post('answer', session=opened['session'], answer=self.catalog.problems[opened['problem']['key']]['label'])
        self.assertTrue(result['correct'])
        self.assertFalse(result['evidence']['updated'])
        self.assertEqual(self.state('division')['probability'], before)
        self.assertEqual(self.state('multiplication')['evidence'], 0)
        rec = self.post('recommendation', focus=opened['session'])
        self.assertEqual(rec['kind'], 'prerequisite')
        self.assertEqual(rec['skill_id'], 'arithmetic')
        plan = self.post('profile', focus=opened['session'])['learning_path']
        self.assertEqual(rec['skill_id'], plan['next_skill'])
        self.assertEqual(rec['return_to'], opened['problem']['key'])

    def test_hint_reveal_solution_and_reopening_are_assisted(self):
        for action, number in [('hint', 1), ('reveal', 2), ('solution', 3)]:
            pid = f'diagnostic-arithmetic-{number}'
            opened = self.post('start', problem=pid)
            if action != 'hint':
                self.post('hint', session=opened['session'])
                wrong = next(c for c in 'ABCDE' if c != self.catalog.problems[opened['problem']['key']]['label'])
                for _ in range(2):
                    self.post('answer', session=opened['session'], answer=wrong)
            self.post(action, session=opened['session'])
            _, result = self.answer(pid)
            self.assertFalse(result['evidence']['updated'])
        self.assertEqual(self.state('arithmetic')['evidence'], 0)
        self.assertEqual(self.post('profile')['attempts'], 7)

    def test_reflection_and_help_gate_are_enforced_on_server(self):
        opened = self.post('start', problem='diagnostic-arithmetic-1', _reflect=False)
        sid = opened['session']
        # Problems with thinking steps gate on the steps; the written note is optional.
        self.assertFalse(opened['reflection_required'])
        self.assertEqual(opened['steps_scope'], 'skill')
        with self.assertRaises(urllib.error.HTTPError):
            self.post('reflect', session=sid, reflection='   ')
        self.post('reflect', session=sid, reflection='I need to subtract the beads that were removed.')
        for action, body in [('answer', {'answer':'C'}), ('reveal', {}), ('solution', {})]:
            with self.assertRaises(urllib.error.HTTPError):
                self.post(action, session=sid, **body)
        self.complete_steps(opened)
        for _ in range(2):
            result = self.post('answer', session=sid, answer='A')
            self.assertFalse(result['can_reveal'])
        with self.assertRaises(urllib.error.HTTPError):
            self.post('reveal', session=sid)
        self.assertTrue(self.post('hint', session=sid)['can_reveal'])
        self.assertEqual(self.post('reveal', session=sid)['answer'], 'C')
        self.assertIn('subtract the beads', self.post('report')['markdown'])
        self.assertEqual(self.state('arithmetic')['evidence'], 1)

    def test_health_has_app_identity_without_student_history(self):
        with urllib.request.urlopen(self.url.replace('/api/', '/api/health')) as response:
            data = json.load(response)
        self.assertEqual(data['app'], 'math-is-yours')
        self.assertEqual(data['model']['state'], 'disabled')
        self.assertNotIn('student', data)

    def test_goal_path_and_recommendation_align(self):
        profile = self.post('profile', goal='proportional_reasoning')
        plan = profile['learning_path']
        self.assertTrue(profile['related_edges'])
        rec = self.post('recommendation', goal='proportional_reasoning')
        self.assertEqual(rec['kind'], 'path')
        self.assertEqual(rec['skill_id'], plan['next_skill'])
        with self.assertRaises(urllib.error.HTTPError):
            self.post('profile', goal='nonexistent')

    def test_translations_and_unloaded_old_variants_are_not_new_evidence(self):
        key = 'diagnostic-arithmetic-1|eng'
        translated = dict(self.catalog.problems[key], language='cat')
        self.catalog.problems['diagnostic-arithmetic-1|cat'] = translated
        self.answer(key)
        _, translated_result = self.answer('diagnostic-arithmetic-1|cat')
        self.assertFalse(translated_result['evidence']['updated'])
        with app.connection(self.db) as con:
            con.execute('INSERT INTO sessions(id,student,problem,tries) VALUES(?,?,?,?)',
                        ('historical', 'Ada', 'diagnostic-arithmetic-2|spa', 1))
        _, result = self.answer('diagnostic-arithmetic-2')
        self.assertFalse(result['evidence']['updated'])
        self.assertEqual(self.state('arithmetic')['evidence'], 1)

    def test_concurrent_submissions_count_canonical_item_once(self):
        a = self.post('start', problem='diagnostic-arithmetic-1')
        b = self.post('start', problem='diagnostic-arithmetic-1')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda opened: self.post('answer', session=opened['session'], answer='C'), [a, b]))
        self.assertEqual(sum(r['evidence']['updated'] for r in results), 1)
        self.assertEqual(self.state('arithmetic')['evidence'], 1)
        self.assertEqual(self.post('profile')['attempts'], 2)

    def test_multi_skill_error_is_logged_without_lowering_any_skill(self):
        opened, result = self.answer('sample-1', correct=False)
        self.assertEqual(result['evidence']['reason'], 'multi_skill_requires_diagnostic')
        self.assertTrue(all(s['evidence'] == 0 for s in self.post('profile')['skills']))
        rec = self.post('recommendation', focus=opened['session'])
        self.assertEqual(rec['kind'], 'diagnostic')
        self.assertIn(rec['skill_id'], ['arithmetic', 'multiplication'])
        self.assertTrue(rec['problem'].startswith('diagnostic-'))

    def test_overdue_review_keeps_mastery_and_prefers_new_item(self):
        self.answer('diagnostic-arithmetic-1')
        before = self.state('arithmetic')['probability']
        with app.connection(self.db) as con:
            con.execute("UPDATE student_skills SET next_review='2000-01-01T00:00:00+00:00' WHERE student='Ada'")
        due = self.state('arithmetic')
        self.assertEqual(due['probability'], before)
        self.assertEqual(due['display_state'], 'due')
        self.assertEqual(due['state'], 'developing')
        rec = self.post('recommendation')
        self.assertEqual(rec['kind'], 'review')
        self.assertTrue(rec['fresh'])
        self.assertNotEqual(rec['id'], 'diagnostic-arithmetic-1')
        _, repeated = self.answer('diagnostic-arithmetic-1')
        self.assertEqual(repeated['evidence']['reason'], 'spaced_repeat_review_only')
        after = self.state('arithmetic')
        self.assertEqual(after['probability'], before)
        self.assertEqual(after['evidence'], 1)
        self.assertFalse(after['due'])

    def test_demonstrated_skill_transfers_to_different_problem(self):
        for number in (1, 2, 3):
            opened, _ = self.answer(f'diagnostic-order_of_operations-{number}')
        rec = self.post('recommendation', focus=opened['session'])
        self.assertEqual(rec['kind'], 'transfer')
        self.assertEqual(rec['id'], 'sample-2')

    def test_student_can_choose_stretch_without_prerequisite_lock(self):
        rec = self.post('recommendation', skill='proportional_reasoning', language='cat')
        self.assertEqual(rec['kind'], 'chosen')
        self.assertEqual(rec['skill_id'], 'proportional_reasoning')
        self.assertTrue(rec['language_fallback'])

    def test_report_and_session_access_are_profile_scoped(self):
        opened, _ = self.answer('diagnostic-division-1')
        report = self.post('report')['markdown']
        self.assertIn('Provisional BKT', report)
        self.assertIn('diagnostic-division-1', report)
        self.assertNotIn('diagnostic-division-1', self.post('report', student='Other')['markdown'])
        with self.assertRaises(urllib.error.HTTPError):
            self.post('hint', student='Other', session=opened['session'])
        self.assertNotIn('label', opened['problem'])
        self.assertNotIn('solution', opened['problem'])


class ModelAndCurriculumTests(unittest.TestCase):
    def test_bayes_observation_and_learning_transition(self):
        parameters = Knowledge().model
        self.assertAlmostEqual(student_model.update_probability(.2, True, parameters), .5764705882352941)
        self.assertAlmostEqual(student_model.update_probability(.2, False, parameters), .1272727272727273)

    def test_legacy_attempts_survive_without_fabricated_skill_history(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'old.db'
            with app.connection(db) as con:
                con.executescript('''CREATE TABLE sessions(id TEXT PRIMARY KEY,student TEXT,problem TEXT,hints INTEGER DEFAULT 0,tries INTEGER DEFAULT 0,revealed INTEGER DEFAULT 0,solved INTEGER DEFAULT 0);
                    CREATE TABLE attempts(id INTEGER PRIMARY KEY,student TEXT,problem TEXT,answer TEXT,correct INTEGER,independent INTEGER,created TEXT);
                    INSERT INTO attempts VALUES(1,'Ada','sample-1','C',1,1,'2026-01-01');''')
            app.initialize(db)
            app.initialize(db)
            with app.connection(db) as con:
                con.row_factory = sqlite3.Row
                self.assertEqual(con.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)
                self.assertEqual(con.execute('SELECT count(*) FROM learning_events').fetchone()[0], 0)
                self.assertTrue(all(s['evidence'] == 0 for s in student_model.states(con, 'Ada', Knowledge()).values()))

    def test_invalid_curriculum_cycle_and_annotations_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'knowledge'
            shutil.copytree(ROOT / 'knowledge', target)
            path = target / 'skills/arithmetic.md'
            path.write_text(path.read_text(encoding='utf-8').replace('prerequisites: []', 'prerequisites: ["division"]'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'cycle'):
                Knowledge(target)
        knowledge = Knowledge()
        with self.assertRaises(ValueError):
            knowledge.validate_annotation({'skills':['arithmetic'], 'assessment_skill':'division'})
        with self.assertRaises(ValueError):
            knowledge.validate_annotation({'skills':['unknown']})


class TutorTests(unittest.TestCase):
    def run_tutor(self, raw):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({'choices':[{'message':{'content':raw}}]}).encode()
        with patch('copilot.tutor.urllib.request.build_opener', return_value=opener):
            tutor = Tutor(enabled=True)
            result = tutor.request('Ada', {'text':'Compute a value.', 'label':'E'}, 'Arithmetic', 'B', ['First hint', 'Second hint', 'Third hint'], 1, 'problem')
            tutor.close()
            status = tutor.status('Ada', result['job'])
        payload = json.loads(opener.open.call_args.args[0].data)
        self.assertNotIn('label', payload['messages'][1]['content'])
        self.assertEqual(payload['temperature'], 0)
        self.assertEqual(payload['seed'], 42)
        with self.assertRaises(ValueError):
            tutor.status('Other', result['job'])
        return status

    def test_only_permitted_hint_text_can_be_selected(self):
        result = self.run_tutor('{"hint":1}')
        self.assertEqual(result['message'], 'First hint')
        self.assertEqual(result['source'], 'local_model_selected')

    def test_invalid_or_freeform_model_output_preserves_stored_hint(self):
        for invalid in ['The correct answer is E.', '{"hint":99}', '{"hint":true}', '{"hint":0,"answer":"E"}']:
            result = self.run_tutor(invalid)
            self.assertEqual(result['message'], 'Second hint')
            self.assertEqual(result['source'], 'stored')

    def test_missing_model_falls_back_without_losing_hint(self):
        opener = MagicMock()
        opener.open.side_effect = OSError('Model offline')
        with patch('copilot.tutor.urllib.request.build_opener', return_value=opener):
            tutor = Tutor(enabled=True)
            result = tutor.request('Ada', {}, 'Arithmetic', None, ['Stored hint'], 0, 'skill')
            self.assertEqual(result['message'], 'Stored hint')
            tutor.close()
            self.assertEqual(tutor.status('Ada', result['job'])['message'], 'Stored hint')


if __name__ == '__main__':
    unittest.main()
