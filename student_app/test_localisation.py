"""Child-facing copy follows the problem language; bundled fonts are served as binary (T-101)."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from copilot.knowledge import Knowledge, ROOT
from student_app import server as app

RESEARCH_WORDS = ('independent evidence', 'prerequisite link', 'exposed item', 'diagnostic', 'assisted')


class LocalisationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'practice.db'
        app.initialize(self.db)
        self.knowledge = Knowledge()
        catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(self.temp.name) / 'images')
        handler = app.make_handler(self.db, catalog, self.knowledge)
        handler.log_message = lambda *args: None
        self.server = app.StudentServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, route, **data):
        req = urllib.request.Request(self.base + '/api/' + route, data=json.dumps({'student': 'Ada', **data}).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def work_steps(self, opened, miss_first=False):
        steps = self.knowledge.thinking_steps({'id': opened['problem']['id'], 'language': opened['problem']['language']})[0]
        results = []
        for index, step in enumerate(steps):
            if miss_first and index == 0:
                results.append(self.post('step', session=opened['session'], index=0, choice=(step['answer'] + 1) % 3))
            results.append(self.post('step', session=opened['session'], index=index, choice=step['answer']))
        return results

    def test_catalan_problem_gets_catalan_step_and_answer_messages(self):
        cat = app.MESSAGES['cat']
        opened = self.post('start', problem='sample-4')
        results = self.work_steps(opened, miss_first=True)
        self.assertEqual(results[0]['message'], cat['step_retry'])
        self.assertEqual(results[1]['message'], cat['step_next'])
        self.assertEqual(results[-1]['message'], 'Molt bé. Ara mira les opcions de resposta.')
        right = self.post('answer', session=opened['session'], answer='C')
        self.assertEqual(right['message'], "Correcte! L'has resolt pel teu compte al primer intent.")

    def test_english_problem_keeps_english_messages(self):
        opened = self.post('start', problem='sample-1')
        self.assertEqual(self.work_steps(opened)[-1]['message'], 'Yes. Now explore the answer choices.')
        wrong = self.post('answer', session=opened['session'], answer='E')
        self.assertTrue(wrong['message'].startswith('Not quite. Try a hint'))

    def test_catalan_reveal_after_unlock(self):
        opened = self.post('start', problem='sample-4')
        self.work_steps(opened)
        self.post('hint', session=opened['session'])
        self.post('answer', session=opened['session'], answer='A')
        self.post('answer', session=opened['session'], answer='B')
        revealed = self.post('reveal', session=opened['session'])
        self.assertEqual(revealed['message'], app.MESSAGES['cat']['reveal'].format(label='C'))
        self.assertTrue(revealed['message'].startswith('La resposta correcta és la C.'))

    def test_state_labels_are_child_readable_and_localised(self):
        english = self.post('profile')['state_labels']
        self.assertEqual(english, {'not_assessed': 'Not tried yet', 'developing': 'Getting there',
                                   'demonstrated': 'Got it', 'due': 'Time to review'})
        catalan = self.post('profile', language='cat')['state_labels']
        self.assertEqual(catalan['demonstrated'], 'Ho tens!')
        self.assertEqual(catalan['due'], 'Toca repassar')
        graph_js = (app.ASSETS / 'graph.js').read_text()
        for label in english.values():
            self.assertIn(label, graph_js)
        self.assertNotIn('Not assessed', graph_js)

    def test_recommendation_summary_is_plain_and_localised(self):
        for language in ('eng', 'cat'):
            rec = self.post('recommendation', language=language)
            self.assertIn('reason', rec)  # technical explanation kept for the method note
            summary = rec['summary'].lower()
            for word in RESEARCH_WORDS:
                self.assertNotIn(word, summary)
            steps = rec['learning_path']['steps']
            self.assertTrue(steps)
            for step in steps:
                self.assertIn(step['child_reason'], app.MESSAGES[language]['step_reason'].values())
        catalan = self.post('recommendation', language='cat')
        self.assertIn(catalan['skill'], catalan['summary'])
        self.assertEqual(catalan['summary'], app.MESSAGES['cat']['summary'][catalan['kind']].format(skill=catalan['skill']))
        if catalan.get('language_fallback'):
            self.assertEqual(catalan['language_note'], 'Aquesta prova només està en anglès.')

    def test_unknown_language_falls_back_to_english(self):
        self.assertIs(app.messages('fra'), app.MESSAGES['eng'])
        self.assertIs(app.messages(None), app.MESSAGES['eng'])
        self.assertEqual(set(app.MESSAGES['cat']), set(app.MESSAGES['eng']))
        for key in ('states', 'summary', 'step_reason'):
            self.assertEqual(set(app.MESSAGES['cat'][key]), set(app.MESSAGES['eng'][key]))

    def test_fonts_are_served_as_binary_woff2(self):
        for name in ('archivo-latin.woff2', 'archivo-latin-ext.woff2'):
            with urllib.request.urlopen(self.base + '/fonts/' + name) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['Content-Type'], 'font/woff2')
                self.assertTrue(response.read().startswith(b'wOF2'))
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base + '/fonts/../server.py')
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()
        css = (app.ASSETS / 'style.css').read_text()
        self.assertIn('/fonts/archivo-latin.woff2', css)
        self.assertTrue((app.ASSETS / 'fonts' / 'OFL.txt').exists())


if __name__ == '__main__':
    unittest.main()
