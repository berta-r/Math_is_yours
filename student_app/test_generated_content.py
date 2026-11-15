"""Large-model content served on the board (D-013, T-092, T-111): precedence, re-verification, provenance.

Synthetic generated files only; one test reads the real data/ml files when present.
"""
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from copilot.content_checks import leaks, verify_generated_explanation, verify_generated_solution, verify_generated_steps
from copilot.knowledge import Knowledge, ROOT
from copilot.misconceptions import Misconceptions
from student_app import server as app
from student_app.catalog import default_inputs

EXTRA = [
    {'id': 'gen-1', 'language': 'eng', 'level': 0, 'text': 'Tom has 7 marbles and gets 5 more. How many marbles does he have now?',
     'options': {'A': '7', 'B': '11', 'C': '12', 'D': '13', 'E': '35'}, 'label': 'C'},
    {'id': 'gen-2', 'language': 'eng', 'level': 0, 'text': 'A box has 9 pens and 4 more are added. How many pens are in the box?',
     'options': {'A': '5', 'B': '13', 'C': '14', 'D': '36', 'E': '9'}, 'label': 'B'},
]
STEPS = [
    {'stage': 'understand', 'language': 'eng', 'question': 'What does the question ask you to find?',
     'options': ['The total number of marbles', 'The number of marbles lost', 'The colour of the marbles'], 'answer': 0,
     'why': 'It asks how many marbles Tom has in the end.'},
    {'stage': 'plan', 'language': 'eng', 'question': 'Which operation joins the two amounts?',
     'options': ['Multiply the two amounts', 'Add the two amounts', 'Subtract the smaller amount'], 'answer': 1,
     'why': 'Getting more marbles means adding them on.'},
    {'stage': 'check', 'language': 'eng', 'question': 'How can you check your total?',
     'options': ['Guess a large number', 'Pick the biggest option', 'Count on from seven'], 'answer': 2,
     'why': 'Counting on five from seven confirms the sum.'},
]
LEAKY_STEPS = [dict(s) for s in STEPS[:2]] + [dict(STEPS[2], why='The total is 13 pens.')]
HINTS = ['What happens to the number of marbles?', 'Join the two amounts together.', 'Count on five from seven.']
EXPLANATION = {'explanation': 'That number comes from multiplying 7 by 5.',
               'question': 'Does getting more marbles mean multiplying or adding?', 'op': 'product'}
PROVENANCE = 'Model-tagged by test-model via test, 2026-11-15; educator review pending'


def write_files(folder):
    folder = Path(folder)
    problems = folder / 'problems.jsonl'
    rows = [json.loads(line) for line in (ROOT / 'data/sample_problems.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    problems.write_text('\n'.join(json.dumps(p) for p in rows + EXTRA), encoding='utf-8')
    paths = {'problems': problems, 'steps': folder / 'steps.json', 'solutions': folder / 'solutions.json',
             'explanations': folder / 'explanations.json', 'annotations': folder / 'annotations.generated.json',
             'signatures': folder / 'signatures.json'}
    paths['steps'].write_text(json.dumps({'version': 1, 'model': 'test-model', 'problems': {
        'sample-1|eng': STEPS, 'gen-1|eng': STEPS, 'gen-2|eng': LEAKY_STEPS}}), encoding='utf-8')
    paths['solutions'].write_text(json.dumps({'version': 1, 'model': 'test-model', 'problems': {
        'sample-1|eng': {'solution': 'Generated text that must lose to the human solution.', 'hints': HINTS},
        'gen-1|eng': {'solution': 'Tom adds 7 and 5, so he has 12 marbles.', 'hints': HINTS},
        'gen-2|eng': {'solution': 'Add 9 and 4 to get 13.', 'hints': ['Add them.', 'The answer is B.', 'You get 13.']}}}), encoding='utf-8')
    paths['explanations'].write_text(json.dumps({'version': 1, 'model': 'test-model', 'generated': '2026-11-15', 'items': {
        'gen-1|eng': {'E': EXPLANATION, 'A': {'explanation': 'You copied 7, but the answer is C.', 'question': 'What changes?', 'op': 'copied_number'}}}}),
        encoding='utf-8')
    tag = {'status': 'reviewed', 'skills': ['arithmetic'], 'assessment_skill': 'arithmetic', 'language': 'eng',
           'provenance': PROVENANCE, 'hints': []}
    paths['annotations'].write_text(json.dumps({'version': 1, 'problems': {
        'gen-1': tag, 'gen-2': tag, 'sample-1': dict(tag, skills=['geometry_measurement'], assessment_skill='geometry_measurement'),
        'gen-bad': dict(tag, skills=['no_such_skill'], assessment_skill=None)}}), encoding='utf-8')
    paths['signatures'].write_text(json.dumps({'version': 1, 'problems': {'gen-1': {
        'answer_op': {'op': 'sum', 'operands': [7, 5]},
        'distractors': {'A': {'op': 'copied_number', 'operands': [7]}, 'E': {'op': 'product', 'operands': [7, 5]}}}}}), encoding='utf-8')
    return paths


def generated_knowledge(paths):
    return Knowledge(generated_steps=paths['steps'], generated_solutions=paths['solutions'], generated_annotations=paths['annotations'])


class Fixture:
    def __init__(self, folder, paths, knowledge=None, explanations=None):
        self.db = Path(folder) / f'practice-{id(self)}.db'
        app.initialize(self.db)
        self.knowledge = knowledge or generated_knowledge(paths)
        self.catalog = app.Catalog([paths['problems']], Path(folder) / 'images')
        self.log = []
        handler = app.make_handler(self.db, self.catalog, self.knowledge, signatures=paths['signatures'],
                                   explanations=explanations or paths['explanations'], log=self.log.append)
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
        return opened


class CheckTests(unittest.TestCase):
    def test_leak_patterns(self):
        self.assertTrue(leaks('The answer is B.', '13', 'B'))
        self.assertTrue(leaks('Pick (A) now', '13', 'A'))
        self.assertTrue(leaks('Try option A', '13', 'A'))
        self.assertFalse(leaks('A box has pens.', '13', 'A'))
        self.assertTrue(leaks('You get 13 pens', '13', 'A'))
        self.assertTrue(leaks('It is 81,0', '81 cm²', 'C'))
        self.assertFalse(leaks('It is 113', '13', 'A'))
        self.assertTrue(leaks('It is 13 cm', '13', None, numeric=False))

    def test_verifiers(self):
        problem = EXTRA[0]
        self.assertEqual(verify_generated_steps(STEPS, problem), (True, ''))
        self.assertFalse(verify_generated_steps(STEPS, dict(problem, language='cat'))[0])
        self.assertFalse(verify_generated_steps(STEPS[:2], problem)[0])
        self.assertFalse(verify_generated_steps(LEAKY_STEPS, EXTRA[1])[0])
        self.assertTrue(verify_generated_solution({'solution': 'He has 12.', 'hints': HINTS}, problem)[0])
        self.assertFalse(verify_generated_solution({'solution': 'He has 12.', 'hints': HINTS[:2]}, problem)[0])
        self.assertFalse(verify_generated_solution({'solution': 'x', 'hints': [HINTS[0], HINTS[1], 'Choose letter C.']}, problem)[0])
        self.assertTrue(verify_generated_explanation(EXPLANATION, problem, 'E')[0])
        self.assertFalse(verify_generated_explanation(EXPLANATION, problem, 'C')[0])  # the correct letter
        self.assertFalse(verify_generated_explanation(dict(EXPLANATION, explanation='word ' * 61), problem, 'E')[0])
        self.assertFalse(verify_generated_explanation(dict(EXPLANATION, question='Is it 12?'), problem, 'E')[0])


class PrecedenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.paths = write_files(self.temp.name)
        self.knowledge = generated_knowledge(self.paths)
        self.problems = {p['id']: p for p in EXTRA}
        self.sample = json.loads((ROOT / 'data/sample_problems.jsonl').read_text(encoding='utf-8').splitlines()[0])

    def tearDown(self):
        self.temp.cleanup()

    def test_human_beats_generated_beats_skill(self):
        k = self.knowledge
        self.assertEqual(k.thinking_steps(self.sample)[1], 'problem')
        self.assertEqual(k.hints(self.sample)[1], 'problem')
        self.assertEqual(k.solution(self.sample), (Knowledge().solution(self.sample)[0], 'problem'))
        self.assertEqual(k.annotation(self.sample)['skills'], ['arithmetic', 'multiplication'])  # human tags kept
        self.assertEqual(k.tag_source(self.sample), 'human')
        gen = self.problems['gen-1']
        self.assertEqual(k.thinking_steps(gen), (STEPS, 'generated'))
        self.assertEqual(k.hints(gen), (HINTS, 'generated'))
        self.assertEqual(k.solution(gen), ('Tom adds 7 and 5, so he has 12 marbles.', 'generated'))
        self.assertEqual(k.tag_source(gen), 'generated')
        self.assertEqual(k.annotation(gen)['provenance'], PROVENANCE)

    def test_leaking_items_are_dropped_for_the_fallback(self):
        k = self.knowledge
        gen = self.problems['gen-2']
        steps, scope = k.thinking_steps(gen)
        self.assertEqual(scope, 'skill')
        self.assertEqual(steps, k.skill_steps['arithmetic'])
        self.assertEqual(k.hints(gen), (k.skills['arithmetic']['hints'], 'skill'))
        self.assertEqual(k.solution(gen), (None, 'none'))
        report = k.generated_report([*self.problems.values(), self.sample])
        self.assertEqual(report['steps'], {'loaded': 2, 'dropped': 1})
        self.assertEqual(report['solution'], {'loaded': 2, 'dropped': 1})
        self.assertEqual(report['tags'], {'loaded': 2, 'dropped': 1})
        m = Misconceptions(self.paths['signatures'], generated=self.paths['explanations'])
        found = m.explain(self.problems['gen-1'], 'A')  # leaking generated text -> template
        self.assertEqual((found['source'], found['question']), ('template', None))
        self.assertIn('already written', found['message'])
        found = m.explain(self.problems['gen-1'], 'E')
        self.assertEqual(found, {'op': 'product', 'answer_op': 'sum', 'message': EXPLANATION['explanation'],
                                 'question': EXPLANATION['question'], 'source': 'generated'})
        self.assertEqual(m.generated_report(self.problems.values()), {'loaded': 1, 'dropped': 1})

    def test_absent_files_keep_todays_behaviour(self):
        missing = Path(self.temp.name) / 'missing.json'
        today, absent = Knowledge(), Knowledge(generated_steps=missing, generated_solutions=missing, generated_annotations=missing)
        for p in [json.loads(l) for l in (ROOT / 'data/sample_problems.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()] + EXTRA:
            for method in ('thinking_steps', 'hints', 'solution', 'annotation', 'tag_source'):
                self.assertEqual(getattr(today, method)(p), getattr(absent, method)(p), (p['id'], method))
        m = Misconceptions(self.paths['signatures'], generated=missing)
        self.assertEqual(m.explain(self.problems['gen-1'], 'E')['source'], 'template')

    def test_malformed_files_raise(self):
        bad = Path(self.temp.name) / 'bad.json'
        cases = ['not json', json.dumps([]), json.dumps({'version': 2, 'problems': {}}), json.dumps({'version': 1, 'problems': []}),
                 json.dumps({'version': 1, 'problems': {'no-language-key': {}}})]
        for text in cases:
            bad.write_text(text, encoding='utf-8')
            with self.subTest(text=text[:30]):
                for kwargs in ({'generated_steps': bad}, {'generated_solutions': bad}):
                    with self.assertRaises(ValueError):
                        Knowledge(**kwargs)
        bad.write_text(json.dumps({'version': 1, 'problems': {'x|eng': {}}}), encoding='utf-8')  # items, not problems
        with self.assertRaises(ValueError):
            Misconceptions(self.paths['signatures'], generated=bad)
        broken = Path(self.temp.name) / 'broken.json'
        broken.write_text('{', encoding='utf-8')
        with self.assertRaises(ValueError):
            Knowledge(generated_annotations=broken)
        db = Path(self.temp.name) / 'practice.db'
        app.initialize(db)
        with self.assertRaises(ValueError):
            app.make_handler(db, app.Catalog([self.paths['problems']], Path(self.temp.name) / 'images'), Knowledge(),
                             signatures=self.paths['signatures'], explanations=bad)
        bad.write_bytes(b' ' * (8 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, 'larger than'):
            Knowledge(generated_steps=bad)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.paths = write_files(self.temp.name)
        self.app = Fixture(self.temp.name, self.paths)

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def test_startup_log_and_start_sources(self):
        self.assertEqual(len(self.app.log), 1)
        self.assertIn('steps 2 served/1 dropped', self.app.log[0])
        self.assertIn('explanations 1 served/1 dropped', self.app.log[0])
        self.assertIn('tags 2 served/1 dropped', self.app.log[0])
        started = self.app.post('start', problem='gen-1')
        self.assertEqual(started['content_sources'], {'steps': 'generated', 'hints': 'generated', 'solution': 'generated',
                                                      'explanations': 'generated'})
        self.assertEqual((started['steps_scope'], started['tags_source'], started['provenance']), ('generated', 'generated', PROVENANCE))
        self.assertEqual([s['question'] for s in started['thinking_steps']], [s['question'] for s in STEPS])
        self.assertNotIn('answer', started['thinking_steps'][0])
        self.assertEqual(self.app.post('start', problem='gen-2')['content_sources'],
                         {'steps': 'skill', 'hints': 'skill', 'solution': 'none', 'explanations': 'none'})
        self.assertEqual(self.app.post('start', problem='sample-1')['content_sources'],
                         {'steps': 'problem', 'hints': 'problem', 'solution': 'problem', 'explanations': 'none'})

    def test_wrong_answer_question_hint_ladder_and_solution(self):
        opened = self.app.open('gen-1')
        session = opened['session']
        wrong = self.app.post('answer', session=session, answer='E')
        self.assertFalse(wrong['correct'])
        self.assertTrue(wrong['message'].endswith(EXPLANATION['explanation']))
        self.assertEqual(wrong['misconception'], {'op': 'product', 'answer_op': 'sum', 'question': EXPLANATION['question'],
                                                  'source': 'generated'})
        first = self.app.post('hint', session=session)
        self.assertEqual((first['message'], first['scope'], first['source']), (EXPLANATION['question'], 'question', 'generated'))
        second = self.app.post('hint', session=session)
        # The question is not a ladder rung; the recognised slip starts the ladder at the method rung.
        self.assertEqual((second['message'], second['scope'], second['rung']), (HINTS[1], 'generated', 2))
        self.app.post('answer', session=session, answer='A')
        solution = self.app.post('solution', session=session)
        self.assertEqual(solution, {'message': 'Tom adds 7 and 5, so he has 12 marbles.', 'scope': 'generated'})

    def test_template_explanation_has_no_question(self):
        opened = self.app.open('gen-1')
        wrong = self.app.post('answer', session=opened['session'], answer='A')
        self.assertEqual(wrong['misconception'], {'op': 'copied_number', 'answer_op': 'sum'})
        hint = self.app.post('hint', session=opened['session'])
        self.assertEqual((hint['message'], hint['scope']), (HINTS[1], 'generated'))

    def test_coverage_counts_human_and_generated_tags(self):
        coverage = self.app.post('profile')['coverage']
        self.assertEqual(coverage, {'tagged': 7, 'tagged_human': 5, 'tagged_generated': 2, 'exercises': 7})
        listed = self.app.post('problems')
        self.assertEqual(listed['coverage'], coverage)
        sources = {p['id']: p['tags_source'] for p in listed['problems'] if p['kind'] != 'diagnostic'}
        self.assertEqual(sources['gen-1'], 'generated')
        self.assertEqual(sources['sample-1'], 'human')

    def test_absent_files_keep_todays_answers(self):
        missing = Path(self.temp.name) / 'missing.json'
        knowledge = Knowledge(generated_steps=missing, generated_solutions=missing, generated_annotations=missing)
        fixture = Fixture(self.temp.name, self.paths, knowledge=knowledge, explanations=missing)
        try:
            self.assertEqual(fixture.log, [])
            started = fixture.post('start', problem='sample-1')
            self.assertEqual(started['content_sources'], {'steps': 'problem', 'hints': 'problem', 'solution': 'problem',
                                                          'explanations': 'none'})
            self.assertEqual(fixture.post('profile')['coverage'], {'tagged': 5, 'tagged_human': 5, 'tagged_generated': 0, 'exercises': 7})
            opened = fixture.open('sample-1')
            hints = knowledge.hints(fixture.catalog.problems['sample-1|eng'])[0]
            self.assertEqual(fixture.post('hint', session=opened['session'])['message'], hints[0])
        finally:
            fixture.close()


class RealFilesTest(unittest.TestCase):
    def test_real_generated_files_mostly_survive_reverification(self):
        paths = {name: path for name, path in app.GENERATED.items() if path.is_file()}
        if not paths:
            self.skipTest('no generated files in data/ml')
        inputs = default_inputs(ROOT)
        catalog = app.Catalog(inputs, ROOT / 'data/images')
        knowledge = Knowledge(annotations=[ROOT / 'data/teaching_annotations.json'], generated_steps=app.GENERATED['steps'],
                              generated_solutions=app.GENERATED['solutions'], generated_annotations=app.GENERATED['annotations'])
        report = knowledge.generated_report(catalog.problems.values())
        report['explanations'] = Misconceptions(generated=app.GENERATED['explanations']).generated_report(catalog.problems.values())
        print('\nReal generated content:', json.dumps(report))
        for name, counts in report.items():
            total = counts['loaded'] + counts['dropped']
            if total:
                self.assertLess(counts['dropped'] / total, .2, (name, counts))


if __name__ == '__main__':
    unittest.main()
