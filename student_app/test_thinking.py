"""Thinking-step checks: bank rules, answer gate, hint adaptation and process metrics."""
import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from copilot.knowledge import Knowledge, ROOT, STAGES, leaked
from student_app import server as app


def sample_problems():
    rows = [json.loads(line) for line in (ROOT / 'data/sample_problems.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    return {r['id']: r for r in rows}


class BankTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = Knowledge()
        self.bank = json.loads((ROOT / 'knowledge/thinking_steps.json').read_text(encoding='utf-8'))

    def all_steps(self):
        return [s for group in ('skills', 'problems') for steps in self.bank[group].values() for s in steps]

    def test_bank_covers_every_skill_and_sample(self):
        self.assertEqual(set(self.bank['skills']), set(self.knowledge.skills))
        samples = sample_problems()
        self.assertEqual(set(self.bank['problems']), set(samples))
        for pid, steps in self.bank['problems'].items():
            self.assertTrue(all(s['language'] == samples[pid]['language'] for s in steps), pid)
            self.assertEqual(self.knowledge.thinking_steps(samples[pid]), (steps, 'problem'))

    def test_positions_lengths_stages_and_leaks(self):
        steps = self.all_steps()
        positions = Counter(s['answer'] for s in steps)
        self.assertTrue(all(positions[i] >= .25 * len(steps) for i in range(3)), positions)
        for group in ('skills', 'problems'):
            for steps_list in self.bank[group].values():
                self.assertEqual([s['stage'] for s in steps_list], list(STAGES))
                for s in steps_list:
                    counts = [len(o.split()) for o in s['options']]
                    self.assertLessEqual(max(counts) - min(counts), 2, s['options'])
                    self.assertLessEqual(max(counts), 10)
        for pid, problem in sample_problems().items():
            self.assertFalse(leaked(self.bank['problems'][pid], problem['options'][problem['label']]), pid)
        self.assertTrue(leaked([{'question': 'q', 'why': 'It is 10 apples.', 'options': ['a', 'b', 'c']}], '10'))
        self.assertFalse(leaked([{'question': 'q', 'why': 'It is 15.', 'options': ['a', 'b', 'c']}], '5'))

    def broken(self, change, message):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'knowledge'
            shutil.copytree(ROOT / 'knowledge', target)
            bank = json.loads((target / 'thinking_steps.json').read_text(encoding='utf-8'))
            change(bank)
            (target / 'thinking_steps.json').write_text(json.dumps(bank), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, message):
                Knowledge(target)

    def test_malformed_banks_are_rejected(self):
        def bad_answer(bank):
            bank['skills']['arithmetic'][0]['answer'] = 3

        def unequal(bank):
            bank['skills']['arithmetic'][0]['options'][1] = 'A much much longer option that has far too many words'

        def duplicate_stage(bank):
            bank['skills']['division'][1]['stage'] = 'understand'

        def leak(bank):
            bank['problems']['sample-1'][0]['options'][0] = 'Whether the total is 10 apples'

        def starts_with_all(bank):
            bank['skills']['patterns'][2]['options'][0] = 'All steps follow the same rule'

        def unbalanced(bank):
            for steps in bank['skills'].values():
                for step in steps:
                    correct = step['options'][step['answer']]
                    step['options'].remove(correct)
                    step['options'].insert(0, correct)
                    step['answer'] = 0
        for change, message in [(bad_answer, 'answer must be an integer'), (unequal, 'word counts'),
                                (duplicate_stage, 'stages must be'), (leak, 'correct option value'),
                                (starts_with_all, 'may not start'), (unbalanced, 'answer position')]:
            with self.subTest(change.__name__):
                self.broken(change, message)


class ThinkingFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'practice.db'
        app.initialize(self.db)
        self.knowledge = Knowledge()
        self.catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(self.temp.name) / 'images')
        # An invented unclassified problem: no annotation, so no thinking steps.
        self.catalog.problems['plain|eng'] = {'id': 'plain', 'language': 'eng', 'text': 'What is 1 + 1?',
                                              'options': {'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5'}, 'label': 'B'}
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
        req = urllib.request.Request(self.url + route, data=json.dumps({'student': 'Ada', **data}).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def rejected(self, route, **data):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post(route, **data)
        self.assertEqual(ctx.exception.code, 400)

    def steps(self, opened):
        return self.knowledge.thinking_steps(self.catalog.problems[opened['problem']['key']])[0]

    def work_steps(self, opened, miss=()):
        """Answer every step; for stages in `miss`, choose a wrong option first."""
        for index, step in enumerate(self.steps(opened)):
            if step['stage'] in miss:
                wrong = self.post('step', session=opened['session'], index=index, choice=(step['answer'] + 1) % 3)
                self.assertFalse(wrong['correct'])
                self.assertEqual(wrong['why'], step['why'])
                self.assertEqual(wrong['next_index'], index)
            self.assertTrue(self.post('step', session=opened['session'], index=index, choice=step['answer'])['correct'])

    def answer(self, opened, correct=True):
        label = self.catalog.problems[opened['problem']['key']]['label']
        return self.post('answer', session=opened['session'], answer=label if correct else next(x for x in 'ABCDE' if x != label))

    def test_start_returns_steps_without_answers(self):
        opened = self.post('start', problem='sample-4')
        self.assertEqual(opened['steps_scope'], 'problem')
        self.assertFalse(opened['reflection_required'])
        self.assertEqual([s['stage'] for s in opened['thinking_steps']], list(STAGES))
        for step in opened['thinking_steps']:
            self.assertEqual(set(step), {'stage', 'question', 'options'})
        self.assertIn('cromos', opened['thinking_steps'][0]['question'] + ' '.join(opened['thinking_steps'][0]['options']))
        fallback = self.post('start', problem='diagnostic-division-1')
        self.assertEqual(fallback['steps_scope'], 'skill')
        self.assertEqual(fallback['steps_skill'], 'Division')

    def test_steps_gate_the_answer_and_never_touch_bkt(self):
        opened = self.post('start', problem='diagnostic-arithmetic-1')
        sid = opened['session']
        self.rejected('answer', session=sid, answer='C')
        self.rejected('step', session=sid, index=1, choice=0)  # not the current step
        self.rejected('step', session=sid, index=0, choice=3)
        self.rejected('step', session=sid, index=0, choice=True)
        steps = self.steps(opened)
        wrong = self.post('step', session=sid, index=0, choice=(steps[0]['answer'] + 2) % 3)
        self.assertEqual((wrong['correct'], wrong['next_index'], wrong['completed']), (False, 0, False))
        right = self.post('step', session=sid, index=0, choice=steps[0]['answer'])
        self.assertEqual((right['correct'], right['next_index'], right['stage']), (True, 1, 'understand'))
        self.rejected('answer', session=sid, answer='C')
        self.post('step', session=sid, index=1, choice=(steps[1]['answer'] + 1) % 3)
        self.post('step', session=sid, index=1, choice=steps[1]['answer'])
        last = self.post('step', session=sid, index=2, choice=steps[2]['answer'])
        self.assertTrue(last['completed'])
        self.rejected('step', session=sid, index=3, choice=0)
        result = self.answer(opened)
        self.assertTrue(result['correct'])
        self.assertTrue(result['evidence']['updated'])
        arithmetic = next(s for s in self.post('profile')['skills'] if s['id'] == 'arithmetic')
        self.assertAlmostEqual(arithmetic['probability'], .5765, places=4)  # same as test_learning
        with app.connection(self.db) as con:
            rows = con.execute('SELECT stage, choice, correct, first, scope, skill_id FROM thinking_events ORDER BY id').fetchall()
        self.assertEqual(len(rows), 5)
        self.assertEqual([(r[0], r[2], r[3]) for r in rows],
                         [('understand', 0, 1), ('understand', 1, 0), ('plan', 0, 1), ('plan', 1, 0), ('check', 1, 1)])
        self.assertTrue(all(r[4] == 'skill' and r[5] == 'arithmetic' for r in rows))

    def test_missed_plan_step_starts_hints_at_method_rung(self):
        missed = self.post('start', problem='diagnostic-arithmetic-1')
        self.work_steps(missed, miss=('plan',))
        hint = self.post('hint', session=missed['session'])
        hints = self.knowledge.hints(self.catalog.problems[missed['problem']['key']])[0]
        self.assertEqual((hint['rung'], hint['message']), (2, hints[1]))
        self.assertEqual(self.post('hint', session=missed['session'])['rung'], 3)
        for miss in [(), ('understand', 'check')]:
            clean = self.post('start', problem='diagnostic-arithmetic-2')
            self.work_steps(clean, miss=miss)
            self.assertEqual(self.post('hint', session=clean['session'])['rung'], 1)

    def test_profile_process_and_report(self):
        empty = self.post('profile')
        self.assertIsNone(empty['process_summary']['steps_first_try_rate'])
        self.assertIsNone(empty['process_summary']['first_attempt_accuracy_when_steps_right'])
        missed = self.post('start', problem='diagnostic-arithmetic-1')
        self.work_steps(missed, miss=('plan',))
        self.answer(missed, correct=True)
        clean = self.post('start', problem='diagnostic-arithmetic-2')
        self.work_steps(clean)
        self.answer(clean, correct=False)
        profile = self.post('profile')
        arithmetic = profile['process']['arithmetic']
        self.assertEqual((arithmetic['asked'], arithmetic['correct_first']), (6, 5))
        self.assertEqual(arithmetic['by_stage']['plan'], {'asked': 2, 'correct_first': 1})
        self.assertEqual(arithmetic['by_stage']['check'], {'asked': 2, 'correct_first': 2})
        self.assertEqual(profile['process']['division']['asked'], 0)
        summary = profile['process_summary']
        self.assertEqual(summary['steps_first_try_rate'], round(5 / 6, 4))
        self.assertEqual(summary['problems_with_all_steps_right'], 1)
        self.assertEqual(summary['first_attempt_accuracy_when_steps_right'], 0.0)
        self.assertEqual(summary['first_attempt_accuracy_when_step_missed'], 1.0)
        report = self.post('report')['markdown']
        self.assertIn('## Thinking process', report)
        self.assertIn('| Addition and subtraction | 6 | 5 | 2/2 | 1/2 | 2/2 |', report)
        self.assertIn('not validated learning gains', report)
        self.assertEqual(self.post('profile', student='Other')['process']['arithmetic']['asked'], 0)

    def test_unclassified_problem_still_requires_reflection(self):
        opened = self.post('start', problem='plain|eng')
        self.assertEqual((opened['steps_scope'], opened['thinking_steps'], opened['reflection_required']), ('none', [], True))
        self.rejected('step', session=opened['session'], index=0, choice=0)
        self.rejected('answer', session=opened['session'], answer='B')
        self.post('reflect', session=opened['session'], reflection='One plus one, so I count two things.')
        self.assertTrue(self.post('answer', session=opened['session'], answer='B')['correct'])


class AnnotationStepTests(unittest.TestCase):
    def test_annotation_steps_are_validated_and_leak_checked_at_startup(self):
        steps = json.loads((ROOT / 'knowledge/thinking_steps.json').read_text(encoding='utf-8'))['problems']['sample-2']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'annotations.json'
            annotation = {'status': 'reviewed', 'skills': ['order_of_operations'], 'assessment_skill': 'order_of_operations',
                          'language': 'eng', 'thinking_steps': steps}
            path.write_text(json.dumps({'version': 1, 'problems': {'sample-2': annotation}}), encoding='utf-8')
            knowledge = Knowledge(annotations=[path])
            self.assertEqual(knowledge.thinking_steps({'id': 'sample-2', 'language': 'eng'})[1], 'problem')
            leaking = json.loads(json.dumps(steps))
            leaking[2]['why'] = 'The value of the expression is 14.'
            annotation['thinking_steps'] = leaking
            path.write_text(json.dumps({'version': 1, 'problems': {'sample-2': annotation}}), encoding='utf-8')
            catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(folder) / 'images')
            db = Path(folder) / 'practice.db'
            app.initialize(db)
            with self.assertRaisesRegex(ValueError, 'correct option value'):
                app.make_handler(db, catalog, Knowledge(annotations=[path]))
            annotation['thinking_steps'] = leaking[:2]
            path.write_text(json.dumps({'version': 1, 'problems': {'sample-2': annotation}}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'exactly 3 steps'):
                Knowledge(annotations=[path])


if __name__ == '__main__':
    unittest.main()
