"""The live coach must preserve main's answer gates and independent evidence."""
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from student_app import server as app
from copilot.coach import Coach, check_reply


class FakeTutor:
    def __init__(self, **kwargs):
        self.calls = []
        self.callback = None

    def generate_hint(self, messages, completed):
        self.calls.append(messages)
        self.callback = completed

    def health(self):
        return {'state': 'ready'}

    def close(self):
        pass


class CoachTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'progress.db'
        app.initialize(self.db)
        with patch.object(app, 'Tutor', FakeTutor):
            self.handler = app.make_handler(self.db, include_diagnostics=False, local_tutor=True,
                                            poweroff_file=Path(self.temp.name) / 'poweroff.request')
        self.handler.log_message = lambda *args: None
        self.tutor = self.handler.teaching_tutor
        self.server = app.StudentServer(('127.0.0.1', 0), self.handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.counter = 0

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, endpoint, **body):
        request = urllib.request.Request(self.url + '/api/' + endpoint,
            data=json.dumps({'student': 'Ada', **body}).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def ask(self, message, **kwargs):
        self.counter += 1
        return self.post('coach', message=message, request_id='request_' + str(self.counter), **kwargs)

    def test_standalone_exactness_and_wrong_claim_without_model(self):
        reply = self.ask('What is 18 - 6?', mode='practice')['turns'][-1]
        self.assertEqual(reply['source'], 'verified_arithmetic')
        self.assertIn('12', reply['tutor_message'])
        wrong = self.ask('I got 13 for 18 - 6', mode='practice')['turns'][-1]
        self.assertEqual(wrong['source'], 'verified_arithmetic')
        self.assertNotEqual(wrong['tutor_message'], reply['tutor_message'])
        self.assertNotIn('state_json', wrong)
        self.assertEqual(self.tutor.calls, [])
        profile = self.post('profile')
        self.assertEqual(profile['attempts'], 0)
        self.assertEqual(profile['rating']['updates'], 0)
        invalid = self.ask('9 / 0', mode='practice')['turns'][-1]
        self.assertEqual(invalid['calculation_status'], 'invalid')

    def test_guided_followups_persist_and_mark_assistance(self):
        session = self.post('start', problem='sample-1')['session']
        first = self.ask('What is 18 - 6?', mode='exercise', session=session)
        self.assertNotIn('12', first['turns'][-1]['tutor_message'])
        self.assertEqual(first['assistance']['hints'], 1)
        self.assertTrue(first['assistance']['assisted'])
        second = self.ask('2', mode='exercise', session=session)
        self.assertIn('10', second['turns'][-1]['tutor_message'])
        app.initialize(self.db)
        last = self.ask('12', mode='exercise', session=session)['turns'][-1]
        self.assertEqual(last['source'], 'verified_arithmetic')
        self.assertEqual(self.post('resume')['session'], session)
        with self.assertRaises(urllib.error.HTTPError):
            self.post('answer', session=session, answer='C')
        self.post('reflect', session=session, reflection='I checked the calculation and compared quantities.')
        steps = app.Knowledge(annotations=[app.ROOT / 'data/teaching_annotations.json']).thinking_steps({'id': 'sample-1', 'language': 'eng'})[0]
        for index, step in enumerate(steps):
            self.post('step', session=session, index=index, choice=step['answer'])
        graded = self.post('answer', session=session, answer='C')
        self.assertFalse(graded['evidence']['updated'])
        self.assertEqual(self.post('profile')['rating']['updates'], 0)

    def test_conceptual_reply_actual_model_context_and_rejection(self):
        session = self.post('start', problem='sample-1')['session']
        result = self.ask('Why does subtraction work?', mode='exercise', session=session)
        self.assertTrue(result['pending'])
        self.assertEqual(len(self.tutor.calls), 1)
        self.assertLessEqual(sum(len(m['content']) for m in self.tutor.calls[0]), 1100)
        prompt = json.dumps(self.tutor.calls[0])
        self.assertIn('Subtraction finds what remains', prompt)
        self.assertIn('not_assessed', prompt)
        self.assertNotIn('"label"', prompt)
        self.assertNotIn('"options"', prompt)
        self.tutor.callback('Subtraction describes taking an amount away. What would happen if you put that amount back?', 'local_model_generated', {})
        history = self.post('coach-history', mode='exercise', session=session)
        self.assertFalse(history['pending'])
        self.assertEqual(history['turns'][-1]['source'], 'local_model_generated')
        self.ask('Can you explain that differently?', mode='exercise', session=session)
        self.tutor.callback('The answer is C.', 'local_model_generated', {})
        rejected = self.post('coach-history', mode='exercise', session=session)['turns'][-1]
        self.assertEqual(rejected['source'], 'stored_checked')
        self.assertEqual(rejected['reason'], 'answer_disclosure')
        self.assertNotIn('answer is C', rejected['tutor_message'])

    def test_idempotence_ownership_drafts_and_recovery(self):
        session = self.post('start', problem='sample-1')['session']
        args = dict(mode='exercise', session=session, message='Why does subtraction work?', request_id='request_abc')
        self.post('coach', **args)
        self.post('coach', **args)
        self.assertEqual(len(self.tutor.calls), 1)
        with self.assertRaises(urllib.error.HTTPError):
            self.post('coach', **dict(args, message='different'))
        with self.assertRaises(urllib.error.HTTPError):
            self.post('coach-history', student='Other', mode='exercise', session=session)
        draft = self.post('coach-draft', mode='exercise', session=session, draft='My next thought', revision=5)
        stale = self.post('coach-draft', mode='exercise', session=session, draft='old', revision=3)
        self.assertEqual(stale['draft'], draft['draft'])
        self.assertEqual(stale['revision'], 5)
        Coach(self.db, self.tutor, app.Knowledge(annotations=[app.ROOT / 'data/teaching_annotations.json']))
        restored = self.post('coach-history', mode='exercise', session=session)
        self.assertFalse(restored['pending'])
        self.assertEqual(restored['turns'][0]['source'], 'stored_recovered')
        self.assertEqual(restored['draft'], 'My next thought')
        # A late callback from the old worker cannot overwrite a recovered reply.
        self.tutor.callback('Subtraction compares amounts. What is changing?', 'local_model_generated', {})
        self.assertEqual(self.post('coach-history', mode='exercise', session=session)['turns'][0]['source'], 'stored_recovered')

    def test_practice_during_exercise_counts_help_and_shutdown_waits(self):
        session = self.post('start', problem='sample-1')['session']
        result = self.ask('18-6', mode='practice', session=session)
        self.assertIn('12', result['turns'][-1]['tutor_message'])
        self.assertTrue(result['assistance']['assisted'])
        self.ask('Why does subtraction work?', mode='practice')
        with self.assertRaises(urllib.error.HTTPError):
            self.post('finish')
        self.tutor.callback(None, 'stored_timeout', {})
        finished = self.post('finish')
        self.post('coach-draft', mode='practice', draft='A new thought', revision=4)
        with self.assertRaises(urllib.error.HTTPError):
            self.post('poweroff', finish_token=finished['finish_token'], confirm='poweroff')
        finished = self.post('finish')
        with self.assertRaises(urllib.error.HTTPError):
            self.post('poweroff', finish_token=finished['finish_token'], confirm='no')
        self.post('poweroff', finish_token=finished['finish_token'], confirm='poweroff')
        self.assertTrue((Path(self.temp.name) / 'poweroff.request').exists())

    def test_migrate_old_conversation_and_preserve_original(self):
        session = self.post('start', problem='sample-1')['session']
        with app.connection(self.db) as con:
            con.execute('''CREATE TABLE coach_turns(id INTEGER PRIMARY KEY,student TEXT,session_id TEXT,
              user_text TEXT,response TEXT,status TEXT,source TEXT,context_json TEXT,created TEXT,completed TEXT,timings_json TEXT)''')
            con.execute("INSERT INTO coach_turns VALUES(1,'Ada',?,'Why?','An old reply.','done','stored','{}','today','today','{}')", (session,))
        app.initialize(self.db)
        app.initialize(self.db)
        history = self.post('coach-history', mode='exercise', session=session)
        self.assertEqual(len(history['turns']), 1)
        self.assertEqual(history['turns'][0]['student_message'], 'Why?')
        with app.connection(self.db) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM coach_turns').fetchone()[0], 1)


class OutputChecks(unittest.TestCase):
    def test_generated_math_and_bilingual_disclosure_are_rejected(self):
        for text in ('Subtract 18 from 6.', 'The answer is twelve.', 'La resposta és C.', 'Choose option A.', 'C is the best choice.'):
            self.assertIsNone(check_reply(text, {}, [])[0], text)
        self.assertIsNotNone(check_reply('Restar compara quantitats. Què ha canviat?', {}, [])[0])


if __name__ == '__main__':
    unittest.main()
